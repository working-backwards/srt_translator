"""
AI Configuration Generator
Handles AI-powered analysis of SRT content to generate translation configurations
"""

import json
import logging
import os
import re
import unicodedata
from typing import Dict, List, Optional

from openai import OpenAI


from srt_core.translator.srt_parser import SRTParser

from srt_core.config.language_config import language_config


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""

    def __init__(self, api_key: str):
        """Initialize the AI config generator with OpenAI API key"""
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        # GUI-only model selection for AI config generation is intentionally
        # isolated from CLI/env to avoid cross-mode confusion
        self.DEFAULT_MODEL = "gpt-4o-mini"
        # GUI-local approximation for characters per token to guide truncation.
        # Keep GUI/CLI separation: do not read from env.
        self.CHARS_PER_TOKEN = 4

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
            # Normalize to NFC to reduce odd splits of composed characters/emoji
            combined_text = unicodedata.normalize("NFC", combined_text)

            # --- Safe character-based truncation (avoids tiktoken in packaged builds) ---
            # Approximate 1 token ≈ 4 characters and truncate at sentence boundaries
            approximate_chars = self.MAX_INLINE_TOKENS * self.CHARS_PER_TOKEN
            if len(combined_text) > approximate_chars:
                truncated_text = self._truncate_text_intelligently(
                    combined_text, target_length=approximate_chars
                )
                self.logger.info(
                    f"Transcript truncated to ~{approximate_chars:,} chars for safe analysis"
                )
                return truncated_text

            # Under limit—return whole thing
            self.logger.info(
                f"Transcript size: {len(combined_text):,} chars (no truncation needed)"
            )
            return combined_text

        except Exception as e:
            self.logger.error(f"Error extracting subtitle content: {e}")
            # Provide a clearer message to the GUI layer
            raise RuntimeError(
                "Failed to prepare transcript content for AI analysis. Please verify your files and try again."
            ) from e

    def generate_dnt_terms(self, content: str) -> List[str]:
        """
        Generate list of terms that should stay in the original language

        Args:
            content: Clean text content from SRT files

        Returns:
            List of terms to exclude from translation
        """
        try:
            prompt = f"""
You are analyzing educational video transcript content to identify terms that should NOT be translated and should remain in the original language.

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
This is for subtitling and educational translation. Be conservative — only include terms that should clearly remain in the original language across all target languages.

TRANSCRIPT:
{content}

OUTPUT:
Return ONLY a JSON array of strings. No explanations, no markdown.

EXAMPLE FORMAT:
["Vivaldi", "API", "MIDI", "Adobe Premiere", "GPU", "NASA"]
"""

            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
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
    - Are listed in DNT_TERMS (do not extract any terms that appear in the DNT_TERMS list)

3. Pass 2: Identify 10 additional English words or phrases from the transcript that are likely to be:
   - mistranslated,
   - interpreted too literally,
   - or misunderstood without context.

   These may include single words, figurative language, verbs or idioms with a special usage, or phrases that learners might take the wrong way in another culture or language.
   Pay special attention to single words that could be confused with similar words (e.g., "thrash" vs "trash").
   Only include these 10 if their mistranslation could cause confusion or reduce learner understanding.
   Do not include merely colorful or stylistic phrases.

       ➤ Add these 10 to your list of 20 extracted terms, for a total of 30.

4. Return both:
   - The extracted list of 30 terms, with a brief reason for each


5. You should expect heavy overlap of key terms across languages that are central to understanding the course’s subject matter, but there should also be language-specific variations when a term poses a unique translation risk in that language (e.g., cultural mismatch, ambiguity, idiomatic differences).
   Do not artificially diversify the termbase across languages.

6. For each language in TARGET_LANGUAGES:
   - Translate all 30 terms from the "extracted_terms" list.
   - Each language's termbase must include translations for every term — even if no direct equivalent exists, provide a concise, localized explanation.
   - If a term is ambiguous or hard to translate literally, provide a culturally adapted equivalent or subtitle-friendly explanation.
   - You may extract terms that overlap with DNT_TERMS, but exclude them from the `termbase_results`. Do not translate or include them in any language termbase.



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

IMPORTANT: If you cannot complete this task, return a JSON object with an "error" field containing a brief explanation of why you failed. Otherwise, return only the JSON object. No commentary, markdown, or extra formatting.
"""

            self.logger.info("Sending comprehensive termbase request to OpenAI")
            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,  # GUI isolation: fixed model for consistency
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": content},
                ],
                max_tokens=10000,  # Increased to handle 30 terms × 12 languages
                temperature=0.6,
            )

            result_text = response.choices[0].message.content.strip()
            self.logger.info(
                f"Received response from OpenAI ({len(result_text)} characters)"
            )
            # Debug: Log the first 500 characters of the response to see what we're getting
            print(f"DEBUG: Response preview: {result_text[:500]}...")
            self.logger.info(f"Response preview: {result_text[:500]}...")

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

            # Check for error response
            if "error" in raw_data:
                error_msg = raw_data.get("error", "Unknown error")
                # Clean up the error message to avoid format specifier issues
                if isinstance(error_msg, str):
                    # Remove any JSON-like content that might cause format issues
                    clean_error = (
                        error_msg.split('"')[0] if '"' in error_msg else error_msg
                    )
                    clean_error = (
                        clean_error.split("{")[0] if "{" in clean_error else clean_error
                    )
                    clean_error = clean_error.strip()
                    if clean_error:
                        error_msg = clean_error
                self.logger.error("AI returned error: %s", str(error_msg))
                return {}

            # Handle extracted_terms: can be a list of strings or list of {"term": ..., "reason": ...}
            extracted_terms = raw_data.get("extracted_terms", [])
            if extracted_terms:
                if isinstance(extracted_terms[0], dict):  # Detailed with reasoning
                    self.logger.info(
                        f"AI extracted {len(extracted_terms)} terms with reasons:"
                    )

                    # Temporarily disable DNT filtering to debug the issue
                    filtered_terms = extracted_terms
                    self.logger.info(
                        f"Using all {len(filtered_terms)} extracted terms (DNT filtering disabled)"
                    )

                    # Show first 20 as Pass #1, remaining as Pass #2
                    for i, item in enumerate(filtered_terms):
                        term = item.get("term")
                        reason = item.get("reason", "No reason provided")
                        if term:
                            if i < 20:
                                self.logger.info(
                                    f"  Pass #1 ({i + 1}/20): {term}: {reason}"
                                )
                            else:
                                self.logger.info(
                                    f"  Pass #2 ({i - 19}/10): {term}: {reason}"
                                )
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
            print(
                f"DEBUG: termbase_data type: {type(termbase_data)}, length: {len(termbase_data) if termbase_data else 0}"
            )
            if not termbase_data:
                self.logger.warning("No termbase_results found in AI response.")
                print("DEBUG: No termbase_results found in AI response")
                return {}

            # Use filtered_terms for the actual termbase generation
            # The AI response contains termbase_results based on the original extracted_terms
            # We need to filter the termbase_results to exclude DNT terms
            filtered_termbase_data = []
            for lang_data in termbase_data:
                code = lang_data.get("code")
                name = lang_data.get("name")
                termbase = lang_data.get("termbase", {})

                # Temporarily disable DNT filtering in termbase
                filtered_termbase = termbase
                self.logger.info(
                    f"Using all {len(filtered_termbase)} terms for {code} (DNT filtering disabled)"
                )

                filtered_termbase_data.append(
                    {"code": code, "name": name, "termbase": filtered_termbase}
                )

            termbase_data = filtered_termbase_data

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
                model=self.DEFAULT_MODEL,
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
