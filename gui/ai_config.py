"""
AI Configuration Generator
Handles AI-powered analysis of SRT content to generate translation configurations
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

import tiktoken
from openai import OpenAI

from srt_core.config.settings import SOURCE_LANG
from srt_core.translator.srt_parser import SRTParser

from srt_core.config.language_config import language_config


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""

    def __init__(self, api_key: str):
        """Initialize the AI config generator with OpenAI API key"""
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)

        # Configuration constants
        self.MAX_INLINE_TOKENS = 12500  # Precise token limit for inline content
        self.MAX_CONTENT_TOKENS = (
            100000  # Token limit for AI analysis (well within OpenAI's 128K limit)
        )
        self.MAX_CONTENT_LENGTH = (
            400000  # Character limit as fallback (roughly 100K tokens)
        )

    def get_supported_languages(self) -> List[str]:
        """Get all supported languages from unified configuration"""
        return language_config.get_language_codes()

    def get_supported_language_names(self) -> List[str]:
        """Get all supported language names from unified configuration"""
        return list(language_config.get_language_names().values())

    def extract_subtitle_content(self, srt_files: List[str]) -> str:
        """
        Extract text from SRT files, then truncate to the first MAX_INLINE_TOKENS tokens.

        Args:
            srt_files: List of paths to SRT files

        Returns:
            Clean text content limited to exactly MAX_INLINE_TOKENS tokens for safe AI processing
        """
        try:
            parser = SRTParser()
            all_text_chunks = []

            for file_path in srt_files:
                if not os.path.exists(file_path):
                    self.logger.warning(f"SRT file not found: {file_path}")
                    continue

                # Parse SRT file and extract subtitle text
                subtitles = parser.parse_file(file_path)

                for subtitle in subtitles:
                    # Clean the subtitle text
                    clean_text = self._clean_subtitle_text(subtitle.content)
                    if clean_text:
                        all_text_chunks.append(clean_text)

            # Join all text
            combined_text = " ".join(all_text_chunks)

            # --- Precise token-based truncation ---
            enc = tiktoken.encoding_for_model("gpt-4o-mini")
            tokens = enc.encode(combined_text)

            if len(tokens) > self.MAX_INLINE_TOKENS:
                truncated_tokens = tokens[: self.MAX_INLINE_TOKENS]
                truncated_text = enc.decode(truncated_tokens)
                self.logger.info(
                    f"Truncated transcript from {len(tokens):,} to {self.MAX_INLINE_TOKENS:,} tokens"
                )
                return truncated_text

            # Under limit—return whole thing
            self.logger.info(f"Transcript size: {len(tokens):,} tokens")
            return combined_text

        except Exception as e:
            self.logger.error(f"Error extracting subtitle content: {e}")
            raise

    def generate_dnt_terms(self, content: str, source_lang: str = None) -> List[str]:
        """
        Generate list of terms that should stay in the source language

        Args:
            content: Clean text content from SRT files
            source_lang: Source language name (defaults to SOURCE_LANG from settings)

        Returns:
            List of terms to exclude from translation
        """
        try:
            # Use SOURCE_LANG if source_lang is not provided
            if source_lang is None:
                source_lang = language_config.get_language_name(SOURCE_LANG)

            prompt = f"""
You are analyzing educational video transcript content to identify terms that should NOT be translated and should remain in {source_lang}.

TASK: From the transcript, extract terms that should be excluded from translation and kept in the original language.

INCLUDE:
• Proper names (people, organizations, institutions)
• Product or software names mentioned in the transcript
• Acronyms, abbreviations, or technical codes that would be confusing or incorrect if translated
• Units, version numbers, model names, or similar specifications
• Words that are culturally fixed or trademarked
• Any other terms that would sound unnatural or be misleading if translated

DO NOT INCLUDE:
• Common nouns or verbs that are expected to be translated
• Educational concepts that have clear equivalents in other languages
• General phrases or filler words

CONTEXT:
This is for subtitling and educational translation. Be conservative — only include terms that should clearly remain in {source_lang} across all target languages.

TRANSCRIPT:
{content}

OUTPUT:
Return ONLY a JSON array of strings. No explanations, no markdown.

EXAMPLE FORMAT:
["Vivaldi", "API", "MIDI", "Adobe Premiere", "GPU", "NASA"]
"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content.strip()
            dnt_terms = self._parse_dnt_terms_response(result_text)
            self.logger.info(f"Generated {len(dnt_terms)} DNT terms")
            return dnt_terms

        except Exception as e:
            self.logger.error(f"Error generating DNT terms: {e}")
            raise

    def generate_termbase(
        self,
        content: str,
        target_languages: List[str],
        dnt_terms: List[str] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate termbase for all target languages using systematic analysis framework

        Args:
            content: Clean text content from SRT files
            target_languages: List of target languages for translation
            dnt_terms: List of terms that should not be included in the termbase

        Returns:
            Dictionary with language keys and term-translation pairs
        """
        try:
            # Get all supported languages from unified config
            supported_languages = self.get_supported_languages()
            self.logger.info(f"Supported languages count: {len(supported_languages)}")

            valid_languages = [
                lang for lang in target_languages if lang in supported_languages
            ]
            self.logger.info(f"Valid languages from input: {valid_languages}")

            if not valid_languages:
                self.logger.warning("No valid target languages provided")
                self.logger.warning(f"Input languages: {target_languages}")
                self.logger.warning(
                    f"Supported languages sample: {supported_languages[:10]}"
                )
                return {}

            # Convert language codes to structured format for the AI prompt
            language_names = []
            for lang_code in valid_languages:
                lang_name = language_config.get_language_name(lang_code)
                if lang_name:
                    language_names.append({"code": lang_code, "name": lang_name})
                else:
                    self.logger.warning(
                        f"Could not get language name for code: {lang_code}"
                    )

            if not language_names:
                self.logger.warning(
                    "Could not get language names for codes: %s", valid_languages
                )
                return {}

            self.logger.info(f"Generating termbase for {len(language_names)} languages")

            # Generate comprehensive termbase for all languages at once
            termbase = self._generate_comprehensive_termbase(
                content, language_names, dnt_terms
            )

            self.logger.info(f"Generated termbase for {len(termbase)} languages")
            return termbase

        except Exception as e:
            self.logger.error(f"Error generating termbase: {e}")
            raise

    def _generate_comprehensive_termbase(
        self,
        content: str,
        language_names: List[Dict[str, str]],
        dnt_terms: List[str] = None,
    ) -> Dict[str, Dict[str, str]]:
        """Generate comprehensive termbase for all target languages using systematic analysis framework"""
        try:
            self.logger.info(
                f"Generating comprehensive termbase for {len(language_names)} languages"
            )

            lang_json = json.dumps(language_names, ensure_ascii=False)

            # Prepare DNT terms JSON
            dnt_json = json.dumps(dnt_terms or [], ensure_ascii=False)

            prompt = f"""
You are an expert in terminology extraction and localization.

INPUT:
– Transcript attached as "document_1" (course transcript from an English-language video)

TARGET_LANGUAGES:
{lang_json}

DNT_TERMS:
{dnt_json}

TASK:
1. Carefully analyze the transcript in `document_1`.

2. Pass 1: Extract the 20 English terms or phrases most likely to cause confusion or mistranslation in subtitle translation. These should meet one or more of the following criteria:

   INCLUDE if they:
   - Are central to understanding the course’s subject matter (e.g., key frameworks, structured methods, strategic terms)
   - Could be misunderstood or mistranslated due to ambiguity, abstraction, cultural specificity, or figurative language
   - Are important for learners to grasp — even if they appear only once
   - Would benefit from a standardized, subtitle-friendly translation to avoid confusion

   AVOID if they:
   - Are obvious, literal, or easily translatable without risk of confusion
   - Are purely stylistic idioms or colorful language with little instructional value
   - Are listed in DNT_TERMS

3. Pass 2: Identify 5 additional English, words or phrases, not in DNT_TERMS, from the transcript that are likely to be:
   - mistranslated,
   - interpreted too literally,
   - or misunderstood without context.

   These may include figurative language, verbs or idioms with a special usage, or phrases that learners might take the wrong way in another culture or language.
   Only include these 5 if their mistranslation could cause confusion or reduce learner understanding.
   Do not include merely colorful or stylistic phrases.

   ➤ Add these 5 to your list of 20 extracted terms, for a total of 25.

4. Return both:
   - The extracted list of 25 terms, none of which appear in DNT_TERMS, with a brief reason for each
   - A per-language termbase of 4–6 of the most important or difficult terms, based on difficulty, relevance, or risk of mistranslation

5. You should expect heavy overlap of key terms across languages that are central to understanding the course’s subject matter, but there should also be language-specific variations when a term poses a unique translation risk in that language (e.g., cultural mismatch, ambiguity, idiomatic differences).
   Do not artificially diversify the termbase across languages.

6. For each language in TARGET_LANGUAGES:
   - Select 4–6 terms from the "extracted_terms" list that are most important to translate well for learners in that language.
   - Only include terms in the termbase that appear in the "extracted_terms" list.
- Each termbase must include translations for all selected terms — even if no direct equivalent exists, provide a concise, localized explanation.
   - If a term is ambiguous or hard to translate literally, provide a culturally adapted equivalent or an explanation that would work in subtitle context.
   - Do not include any terms from DNT_TERMS, even if they appear in the extracted list.


7. Output MUST use this JSON format:

{{
  "extracted_terms": [
    {{"term": "term1", "reason": "reason1"}},
    {{"term": "term2", "reason": "reason2"}},
    ...
  ],
  "termbase_results": [
    {{
      "code": string,  // ISO code from TARGET_LANGUAGES
      "name": string,  // Human-readable name
      "termbase": {{
          "<Source Term 1>": "<Translation 1>",
          "<Source Term 2>": "<Translation 2>"
      }}
    }},
    ...
  ]
}}

Only return the JSON object. No commentary, markdown, or extra formatting.
"""

            self.logger.info("Sending comprehensive termbase request to OpenAI")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use GPT-4 for better analysis
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": content},
                ],
                max_tokens=3000,  # Increased to prevent JSON truncation
                temperature=0.6,
            )

            result_text = response.choices[0].message.content.strip()
            self.logger.info(
                f"Received response from OpenAI ({len(result_text)} characters)"
            )

            parsed_termbase = self._parse_comprehensive_termbase_response(result_text)
            self.logger.info(f"Parsed termbase with {len(parsed_termbase)} languages")

            return parsed_termbase

        except Exception as e:
            self.logger.error(f"Error in comprehensive termbase generation: {e}")
            raise

    def _clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text for analysis"""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove speaker indicators (e.g., "Speaker 1:", "John:")
        text = re.sub(r"^[A-Za-z\s]+:\s*", "", text)

        # Remove timestamps
        text = re.sub(r"\d{1,2}:\d{2}:\d{2}", "", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters that might interfere with analysis
        text = re.sub(r"[^\w\s\-.,!?;:()]", "", text)

        return text.strip()

    def _truncate_text_intelligently(self, text: str, target_length: int = None) -> str:
        """Truncate text at sentence boundaries to stay within target length"""
        if target_length is None:
            # Use safe token limit for AI models (15K tokens = ~60K characters)
            # Leave buffer for prompts and responses
            target_length = 60000  # ~15K tokens, leaving buffer for prompt

        if len(text) <= target_length:
            return text

        # Find the last sentence boundary within the limit
        truncated = text[:target_length]

        # Look for sentence endings
        sentence_endings = [".", "!", "?"]
        last_sentence_end = -1

        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos

        if last_sentence_end > 0:
            # Truncate at the last complete sentence
            return text[: last_sentence_end + 1]
        else:
            # Fall back to word boundary
            last_space = truncated.rfind(" ")
            if last_space > 0:
                return text[:last_space]
            else:
                return truncated

    def _parse_dnt_terms_response(self, response_text: str) -> List[str]:
        """Parse the AI response for DNT terms"""
        try:
            # Extract JSON array from response

            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # Parse JSON
            terms = json.loads(cleaned)

            # Ensure it's a list and all items are strings
            if isinstance(terms, list):
                return [str(term).strip() for term in terms if term]
            else:
                self.logger.warning("AI response is not a list format")
                return []

        except Exception as e:
            self.logger.error(f"Error parsing DNT terms response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return []

    def _parse_comprehensive_termbase_response(
        self, response_text: str
    ) -> Dict[str, Dict[str, str]]:
        """
                Parses the structured JSON response from the AI containing extracted terms and termbase results.
        Returns a dictionary of language codes with their termbase entries.
        """
        try:
            import json

            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # Check if response appears to be truncated
            if not cleaned.endswith("}"):
                self.logger.warning(
                    "Response appears to be truncated - attempting to fix JSON"
                )
                # Try to find the last complete object and close it
                last_complete = cleaned.rfind("}")
                if last_complete > 0:
                    cleaned = cleaned[: last_complete + 1]
                else:
                    # If no closing brace found, try to close the main object
                    cleaned = cleaned.rstrip() + "}"

            # Parse the JSON
            raw_data = json.loads(cleaned)

            # Handle extracted_terms: can be a list of strings or list of {"term": ..., "reason": ...}
            extracted_terms = raw_data.get("extracted_terms", [])
            if extracted_terms:
                if isinstance(extracted_terms[0], dict):  # Detailed with reasoning
                    self.logger.info(
                        f"AI extracted {len(extracted_terms)} terms with reasons:"
                    )
                    for item in extracted_terms:
                        term = item.get("term")
                        reason = item.get("reason", "No reason provided")
                        if term:
                            self.logger.info(f"  - {term}: {reason}")
                elif isinstance(extracted_terms[0], str):  # Simple list
                    self.logger.info(
                        f"AI extracted {len(extracted_terms)} terms: {', '.join(extracted_terms)}"
                    )
                else:
                    self.logger.warning("Unexpected format for extracted_terms.")
            else:
                self.logger.warning("No extracted terms found in AI response.")

            # Parse termbase results
            termbase_data = raw_data.get("termbase_results", [])
            if not termbase_data:
                self.logger.warning("No termbase_results found in AI response.")
                return {}

            parsed = {}
            for lang in termbase_data:
                code = lang.get("code")
                termbase = lang.get("termbase", {})
                if code and isinstance(termbase, dict):
                    parsed[code] = termbase
                    self.logger.debug(
                        f"Parsed {len(termbase)} terms for language: {code}"
                    )
                else:
                    self.logger.warning(f"Invalid termbase entry for language: {lang}")

            return parsed

        except json.JSONDecodeError as e:
            self.logger.error(
                f"JSON decode error in comprehensive termbase response: {e}"
            )
            self.logger.debug(f"Raw response: {response_text}")
            return {}

        except Exception as e:
            self.logger.error(f"Error parsing comprehensive termbase response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return {}

    def _parse_termbase_response(self, response_text: str) -> Dict[str, str]:
        """Parse the AI response for termbase (legacy method)"""
        try:

            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # Parse JSON
            termbase = json.loads(cleaned)

            # Ensure it's a dict and all values are strings
            if isinstance(termbase, dict):
                return {
                    str(k).strip(): str(v).strip()
                    for k, v in termbase.items()
                    if k and v
                }
            else:
                self.logger.warning("AI response is not a dictionary format")
                return {}

        except Exception as e:
            self.logger.error(f"Error parsing termbase response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return {}

    def validate_api_key(self) -> bool:
        """Validate that the API key is working"""
        try:
            # Make a simple test call
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "authentication" in error_msg:
                self.logger.error(
                    "Invalid API key - please check your key at platform.openai.com"
                )
            elif (
                "quota" in error_msg or "billing" in error_msg or "credits" in error_msg
            ):
                self.logger.error(
                    "Insufficient API credits - please add credits to your OpenAI account"
                )
            elif "rate" in error_msg:
                self.logger.error(
                    "Rate limit exceeded - please wait a moment and try again"
                )
            elif "network" in error_msg or "connection" in error_msg:
                self.logger.error(
                    "Network connection issue - please check your internet connection"
                )
            else:
                self.logger.error(f"API key validation failed: {e}")
            return False

    def get_error_details(self, error: Exception) -> dict:
        """Get detailed error information for GUI display"""
        error_msg = str(error).lower()

        # Check for context length exceeded first (before "invalid" check)
        if (
            "context length" in error_msg
            or "maximum context length" in error_msg
            or "context_length_exceeded" in error_msg
        ):
            return {
                "type": "context_length_exceeded",
                "title": "Content Too Large for Analysis",
                "message": "The selected files contain too much text for the AI model to process at once",
                "suggestion": "Try selecting fewer files or use the content truncation feature",
            }
        elif "invalid" in error_msg and "authentication" in error_msg:
            return {
                "type": "invalid_api_key",
                "title": "Invalid API Key",
                "message": "Please check your API key at platform.openai.com",
                "suggestion": "Get your key at: platform.openai.com",
            }
        elif "quota" in error_msg or "billing" in error_msg or "credits" in error_msg:
            return {
                "type": "insufficient_credits",
                "title": "Insufficient API Credits",
                "message": "Please add credits to your OpenAI account",
                "suggestion": "Add credits at: platform.openai.com",
            }
        elif "rate" in error_msg:
            return {
                "type": "rate_limit",
                "title": "Rate Limit Exceeded",
                "message": "Please wait a moment and try again",
                "suggestion": "Wait 1-2 minutes before retrying",
            }
        elif "network" in error_msg or "connection" in error_msg:
            return {
                "type": "network_error",
                "title": "Network Connection Issue",
                "message": "Please check your internet connection",
                "suggestion": "Check your internet connection and try again",
            }
        elif "content" in error_msg and (
            "too small" in error_msg or "insufficient" in error_msg
        ):
            return {
                "type": "insufficient_content",
                "title": "Insufficient Content for Analysis",
                "message": "Selected files contain very little text for analysis",
                "suggestion": "Try selecting larger files or more files from your course",
            }
        else:
            return {
                "type": "unknown_error",
                "title": "AI Configuration Failed",
                "message": f"An error occurred: {str(error)}",
                "suggestion": "Please check your settings and try again",
            }
