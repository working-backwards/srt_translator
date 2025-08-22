#!/usr/bin/env python3
"""
AI Configuration Generator for SRT Translator.
Generates DNT terms and termbase using OpenAI API.
"""

import json
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List

from openai import OpenAI

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.srt_parser import SRTParser
from srt_translator.core.terminology_utils import is_numeric_like, is_hard_preserve

# Batch-level AI config constants
_CHARS_PER_TOKEN = 4  # rough heuristic: ~4 chars per token
_TOKEN_CAP = 12_500
_CHAR_CAP = _TOKEN_CAP * _CHARS_PER_TOKEN  # ~50k chars

@dataclass
class BatchAIConfig:
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]  # lang -> {source_term: mapped_translation}


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""

    def __init__(self, api_key: str, language_config: LanguageConfig = None):
        """Initialize the AI config generator with OpenAI API key and language configuration"""
        if language_config is None:
            raise ValueError("LanguageConfig is required for AIConfigGenerator")
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger('srt_translator.gui.ai_config')
        # GUI-only model selection for AI config generation is intentionally
        # isolated from CLI/env to avoid cross-mode confusion
        self.DEFAULT_MODEL = "gpt-4o-mini"
        # GUI-local approximation for characters per token to guide truncation.
        # Keep GUI/CLI separation: do not read from env.
        self.CHARS_PER_TOKEN = 4
        
        # Language configuration for script validation
        self._lang_cfg = language_config

        # Configuration constants
        self.MAX_INLINE_TOKENS = 12500  # Precise token limit for inline content
        self.MAX_CONTENT_TOKENS = (
            100000  # Token limit for AI analysis (well within OpenAI's 128K limit)
        )
        self.MAX_CONTENT_LENGTH = 400000  # Character limit as fallback (roughly 100K tokens)

    def get_supported_languages(self) -> List[str]:
        """Get all supported languages from unified configuration"""
        return self._lang_cfg.get_language_codes()

    def get_supported_language_names(self) -> List[str]:
        """Get all supported language names from unified configuration"""
        return list(self._lang_cfg.get_language_names().values())

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

            result_text = response.choices[0].message.content
            if result_text is None:
                raise ValueError("OpenAI response content is None")
            result_text = result_text.strip()
            dnt_raw = self._parse_dnt_terms_response(result_text) or []
            
            # Apply hard-preserve filtering to DNT terms
            dnt_terms = []
            for term in dnt_raw:
                if is_numeric_like(term):   # remove numeric/number-like
                    continue
                if is_hard_preserve(term):
                    dnt_terms.append(term)
            
            dnt_terms = sorted(set(dnt_terms), key=str.lower)
            self.logger.info(f"Generated {len(dnt_raw)} DNT terms, filtered to {len(dnt_terms)} (hard-preserve only)")
            
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
        Generate termbase for all target languages using a simple two-stage pipeline:
        1. Extract risk terms once (canonical English list) - inline
        2. Translate per language for reliability
        
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

            valid_languages = [lang for lang in target_languages if lang in supported_languages]
            self.logger.info(f"Valid languages from input: {valid_languages}")

            if not valid_languages:
                self.logger.warning("No valid target languages provided")
                self.logger.warning(f"Input languages: {target_languages}")
                self.logger.warning(f"Supported languages sample: {supported_languages[:10]}")
                return {}

            # Stage 1: Extract canonical English risk terms once (inline)
            self.logger.info("Stage 1: Extracting canonical English risk terms")
            
            # Filter out DNT terms (case-insensitive)
            dnt_set = {term.lower().strip() for term in (dnt_terms or [])}
            
            prompt = f"""
You are analyzing educational video transcript content to identify terms that are likely to be mistranslated.

TASK: Extract 20-25 English terms or phrases that pose translation risks.

INCLUDE terms that:
• Are central to understanding the course's subject matter (frameworks, methods, strategic concepts)
• Could be misunderstood due to ambiguity, abstraction, or cultural specificity
• Have figurative or idiomatic meanings that might be translated too literally
• Are technical or business terms that may not have direct equivalents
• Would benefit from standardized, subtitle-friendly translations

EXCLUDE:
• Terms that are obvious, literal, or easily translatable
• Purely stylistic idioms with little instructional value
• Terms already in the DNT list (these will be filtered out)

CONTEXT: This is for subtitle translation. Focus on terms where mistranslation could reduce learner understanding.

DNT_TERMS (already excluded): {list(dnt_set)}

TRANSCRIPT:
{content}

OUTPUT: Return ONLY a JSON array of objects with "term" and "reason" fields.
EXAMPLE: [{{"term": "operating cadence", "reason": "Figurative term that could be translated too literally"}}]

Return valid JSON only. No explanations or markdown.
"""

            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            if not result_text:
                raise ValueError("Empty response from AI")

            # Parse the response
            try:
                data = json.loads(result_text)
                terms = data.get("terms", [])
                
                # Validate structure
                if not isinstance(terms, list):
                    raise ValueError("Response is not a list")
                
                # Filter out any DNT terms that might have slipped through
                filtered_terms = []
                for item in terms:
                    if not isinstance(item, dict):
                        continue
                    term = item.get("term", "").strip()
                    reason = item.get("reason", "").strip()
                    
                    if term and reason and term.lower() not in dnt_set:
                        filtered_terms.append({"term": term, "reason": reason})
                
                self.logger.info(f"Extracted {len(filtered_terms)} risk terms (filtered from {len(terms)} total)")
                
                if not filtered_terms:
                    self.logger.warning("No risk terms extracted, skipping termbase generation")
                    return {}
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse AI response as JSON: {e}")
                self.logger.debug(f"Raw response: {result_text}")
                raise

            # Stage 2: Generate termbase per language for reliability
            self.logger.info("Stage 2: Generating termbase per language")
            termbase = {}
            
            for lang_code in valid_languages:
                try:
                    lang_name = self._lang_cfg.get_language_name(lang_code)
                    if not lang_name:
                        self.logger.warning(f"Could not get language name for {lang_code}, skipping")
                        continue
                    
                    self.logger.info(f"Generating termbase for {lang_code} ({lang_name})")
                    lang_termbase = self.generate_single_language_termbase(
                        filtered_terms, lang_code, lang_name
                    )
                    
                    if lang_termbase:
                        termbase[lang_code] = lang_termbase
                        self.logger.info(f"Successfully generated termbase for {lang_code}: {len(lang_termbase)} terms")
                    else:
                        self.logger.warning(f"Empty termbase for {lang_code}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to generate termbase for {lang_code}: {e}")
                    # Continue with other languages instead of failing the whole batch
                    continue

            self.logger.info(f"Generated termbase for {len(termbase)} languages (batch-level)")
            return termbase

        except Exception as e:
            self.logger.error(f"Error generating termbase: {e}")
            raise

    def _clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text by removing timestamps and formatting"""
        # Remove timestamp patterns like [00:00:00] or (00:00:00)
        text = re.sub(r'\[?\d{1,2}:\d{2}:\d{2}\]?', '', text)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _norm(self, text: str) -> str:
        """Normalize text for consistent matching (NFKC, lowercase)"""
        return unicodedata.normalize("NFKC", text.lower().strip())



    def filter_dnt_terms(self, dnt_terms: List[str]) -> List[str]:
        """Filter DNT terms to exclude numeric and number-like items"""
        if not dnt_terms:
            return []
        
        filtered_terms = []
        for term in dnt_terms:
            if not term or not term.strip():
                continue
                
            # Skip pure numbers and number-like terms
            if is_numeric_like(term):
                self.logger.debug(f"Filtering out numeric DNT term: '{term}'")
                continue
                
            filtered_terms.append(term)
        
        if len(filtered_terms) != len(dnt_terms):
            self.logger.info(f"Filtered DNT terms: {len(dnt_terms)} -> {len(filtered_terms)} (removed numeric items)")
        
        return filtered_terms

    def filter_dnt_terms_with_metadata(self, dnt_terms: List[str]) -> tuple[List[str], List[str]]:
        """
        Filter DNT terms and return both filtered terms and metadata about what was filtered out.
        
        Args:
            dnt_terms: List of DNT terms to filter
            
        Returns:
            Tuple of (filtered_terms, filtered_out_terms)
        """
        if not dnt_terms:
            return [], []
        
        filtered_terms = []
        filtered_out = []
        
        for term in dnt_terms:
            if not term or not term.strip():
                continue
                
            # Skip pure numbers and number-like terms
            if is_numeric_like(term):
                self.logger.debug(f"Filtering out numeric DNT term: '{term}'")
                filtered_out.append(f"{term} (filtered: numeric/number-like)")
                continue
                
            filtered_terms.append(term)
        
        if len(filtered_terms) != len(dnt_terms):
            self.logger.info(f"Filtered DNT terms: {len(dnt_terms)} -> {len(filtered_terms)} (removed numeric items)")
        
        return filtered_terms, filtered_out

    def _truncate_text_intelligently(self, text: str, target_length: int) -> str:
        """Truncate text at sentence boundaries to stay within target length"""
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

    def _parse_termbase_response(self, response_text: str) -> Dict[str, str]:
        """Parse the AI response for termbase"""
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
                return {str(k).strip(): str(v).strip() for k, v in termbase.items() if k and v}
            else:
                self.logger.warning("AI response is not a dictionary format")
                return {}

        except Exception as e:
            self.logger.error(f"Error parsing termbase response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return {}

    def generate_single_language_termbase(
        self,
        terms: List[Dict[str, str]],
        lang_code: str,
        lang_name: str,
    ) -> Dict[str, str]:
        """
        Generate termbase for a single target language.
        
        Args:
            terms: List of {"term": str, "reason": str} from extract_risk_terms
            lang_code: ISO language code (e.g., "es", "zh-Hans")
            lang_name: Human-readable language name (e.g., "Spanish", "Chinese (Simplified)")
            
        Returns:
            Dictionary mapping English terms to target language translations
        """
        try:
            # Convert terms to simple list for the prompt
            term_list = [item["term"] for item in terms]
            
            prompt = f"""
You translate an English term list into {lang_name} for subtitle use.

Return JSON only: {{"<EN term>": "<{lang_name} term>", ...}}

Rules:
- 1-4 words per entry; concise and subtitle-friendly
- If no exact equivalent, give the most natural localized term (not a long definition)
- Preserve capitalization of proper names. Don't translate trademarks
- Do NOT include any DNT term (they're already excluded from the input)
- Do NOT add terms, do NOT skip terms

INPUT TERMS (JSON array of strings):
{json.dumps(term_list, ensure_ascii=False)}

Return valid JSON only. No explanations or markdown.
"""

            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            if not result_text:
                raise ValueError("Empty response from AI")

            # Parse the response
            try:
                translations = json.loads(result_text)
                
                # Validate that all input terms are present
                missing_terms = []
                result = {}
                
                for term in term_list:
                    if term in translations:
                        target = translations[term].strip()
                        if target:
                            result[term] = target
                        else:
                            # Empty translation - use English key and warn
                            result[term] = term
                            self.logger.warning(f"Empty translation for '{term}' in {lang_code}, using English key")
                    else:
                        missing_terms.append(term)
                        # Missing term - use English key and warn
                        result[term] = term
                        self.logger.warning(f"Missing translation for '{term}' in {lang_code}, using English key")

                if missing_terms:
                    self.logger.warning(f"Missing {len(missing_terms)} terms in {lang_code}: {missing_terms}")

                self.logger.info(f"Generated termbase for {lang_code}: {len(result)} terms")
                return result

            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse {lang_code} response as JSON: {e}")
                self.logger.debug(f"Raw response: {result_text}")
                raise

        except Exception as e:
            self.logger.error(f"Error generating termbase for {lang_code}: {e}")
            raise

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
                self.logger.error("Invalid API key - please check your key at platform.openai.com")
            elif "quota" in error_msg or "billing" in error_msg or "credits" in error_msg:
                self.logger.error(
                    "Insufficient API credits - please add credits to your OpenAI account"
                )
            elif "rate" in error_msg:
                self.logger.error("Rate limit exceeded - please wait a moment and try again")
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
        elif "content" in error_msg and ("too small" in error_msg or "insufficient" in error_msg):
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

    def generate_batch_ai_config(
        self,
        source_file_paths: List[str],
        target_lang_codes: List[str],
        token_cap: int = _TOKEN_CAP,
    ) -> BatchAIConfig:
        """
        Build ONE batch-level DNT list and ONE termbase (per target language)
        by sampling up to ~12,500 tokens (~50k chars) from the selected source SRTs.
        """
        if not source_file_paths:
            raise ValueError("No source files provided for AI config generation.")

        # 1) Read & parse SRTs, concatenate subtitle text up to char budget
        char_budget = token_cap * _CHARS_PER_TOKEN
        sampler = []
        total = 0
        parser = SRTParser()

        for path in source_file_paths:
            try:
                subs = parser.parse_file(path)
            except Exception:
                # Fallback: read raw text if parsing fails
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                text_only = self._strip_srt_markup(raw)
                if total < char_budget:
                    take = text_only[: max(0, char_budget - total)]
                    sampler.append(take)
                    total += len(take)
                continue

            # join subtitle contents
            joined = "\n".join((s.content or "").strip() for s in subs if s.content)
            if not joined:
                continue
            if total < char_budget:
                take = joined[: max(0, char_budget - total)]
                sampler.append(take)
                total += len(take)
            if total >= char_budget:
                break

        transcript_sample = "\n".join(sampler)
        approx_tokens = len(transcript_sample) // _CHARS_PER_TOKEN
        self.logger.info(f"Transcript sampled for AI config: ~{approx_tokens} tokens (~{len(transcript_sample)} chars)")

        # 2) Generate a SINGLE DNT list for the whole run
        dnt_terms = self.generate_dnt_terms(transcript_sample)
        self.logger.info(f"Generated {len(dnt_terms)} DNT terms (batch-level)")

        # 3) Generate termbase using the new two-stage pipeline
        termbase_by_lang = self.generate_termbase(
            transcript_sample,
            target_lang_codes,
            dnt_terms=dnt_terms,
        )
        self.logger.info(f"Generated termbase for {len(termbase_by_lang)} languages (batch-level)")

        return BatchAIConfig(dnt_terms=dnt_terms, termbase=termbase_by_lang)

    @staticmethod
    def _strip_srt_markup(raw: str) -> str:
        """Remove index/timestamps and keep visible text as a fallback sampler."""
        # kill timestamps 00:00:00,000 --> 00:00:00,000
        raw = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}", "", raw)
        # kill pure index lines
        raw = re.sub(r"(?m)^\s*\d+\s*$", "", raw)
        return raw
