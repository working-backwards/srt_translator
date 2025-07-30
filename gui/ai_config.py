"""
AI Configuration Generator
Handles AI-powered analysis of SRT content to generate translation configurations
"""

import os
import re
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from srt_core.translator.srt_parser import SRTParser


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""
    
    def __init__(self, api_key: str):
        """Initialize the AI config generator with OpenAI API key"""
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        
        # Configuration constants
        self.MAX_CONTENT_LENGTH = 8000  # Character limit for AI analysis
        self.SUPPORTED_LANGUAGES = [
            "Spanish", "French", "German", "Italian", "Japanese", 
            "Chinese Simplified", "Vietnamese", "Portuguese - Brazilian",
            "Indonesian", "Arabic", "Turkish", "Azerbaijani"
        ]
    
    def extract_subtitle_content(self, srt_files: List[str]) -> str:
        """
        Extract clean text content from SRT files for AI analysis
        
        Args:
            srt_files: List of paths to SRT files
            
        Returns:
            Clean text content limited to MAX_CONTENT_LENGTH characters
        """
        try:
            parser = SRTParser()
            all_text = []
            
            for file_path in srt_files:
                if not os.path.exists(file_path):
                    self.logger.warning(f"SRT file not found: {file_path}")
                    continue
                
                # Parse SRT file and extract subtitle text
                subtitles = parser.parse_srt_file(file_path)
                file_text = []
                
                for subtitle in subtitles:
                    # Clean the subtitle text
                    clean_text = self._clean_subtitle_text(subtitle.text)
                    if clean_text:
                        file_text.append(clean_text)
                
                # Join all text from this file
                if file_text:
                    all_text.extend(file_text)
            
            # Join all text and limit to character count
            combined_text = " ".join(all_text)
            
            if len(combined_text) > self.MAX_CONTENT_LENGTH:
                # Truncate intelligently (try to break at sentence boundaries)
                truncated = self._truncate_text_intelligently(combined_text)
                self.logger.info(f"Content truncated from {len(combined_text)} to {len(truncated)} characters")
                return truncated
            
            return combined_text
            
        except Exception as e:
            self.logger.error(f"Error extracting subtitle content: {e}")
            raise
    
    def generate_excluded_terms(self, content: str) -> List[str]:
        """
        Generate list of terms that should stay in English
        
        Args:
            content: Clean text content from SRT files
            
        Returns:
            List of terms to exclude from translation
        """
        try:
            prompt = f"""
            Analyze the following course content and identify terms that should remain in English during translation.
            
            Focus on:
            - Proper names (people, companies, brands)
            - Technical acronyms (API, CEO, CFO, etc.)
            - Product names and trademarks
            - Industry-specific terms that are commonly used in English
            - Abbreviations that should stay as-is
            
            Content to analyze:
            {content}
            
            Return ONLY a JSON array of terms, like: ["Amazon", "CEO", "API"]
            Do not include explanations or additional text.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            # Extract and parse the response
            result_text = response.choices[0].message.content.strip()
            excluded_terms = self._parse_excluded_terms_response(result_text)
            
            self.logger.info(f"Generated {len(excluded_terms)} excluded terms")
            return excluded_terms
            
        except Exception as e:
            self.logger.error(f"Error generating excluded terms: {e}")
            raise
    
    def generate_business_glossary(self, content: str, target_languages: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Generate business glossary for each target language
        
        Args:
            content: Clean text content from SRT files
            target_languages: List of target languages for translation
            
        Returns:
            Dictionary with language keys and term-translation pairs
        """
        try:
            # Filter to only supported languages
            valid_languages = [lang for lang in target_languages if lang in self.SUPPORTED_LANGUAGES]
            
            if not valid_languages:
                self.logger.warning("No valid target languages provided")
                return {}
            
            business_glossary = {}
            
            for language in valid_languages:
                try:
                    language_glossary = self._generate_language_glossary(content, language)
                    if language_glossary:
                        business_glossary[language] = language_glossary
                        
                except Exception as e:
                    self.logger.error(f"Error generating glossary for {language}: {e}")
                    continue
            
            self.logger.info(f"Generated business glossary for {len(business_glossary)} languages")
            return business_glossary
            
        except Exception as e:
            self.logger.error(f"Error generating business glossary: {e}")
            raise
    
    def _generate_language_glossary(self, content: str, language: str) -> Dict[str, str]:
        """Generate glossary for a specific language"""
        prompt = f"""
        Analyze the following course content and identify key business/technical terms that need translation.
        
        For the language: {language}
        
        Focus on:
        - Business terminology
        - Technical concepts
        - Industry-specific terms
        - Important phrases that should be consistently translated
        
        Content to analyze:
        {content}
        
        Return ONLY a JSON object with English terms as keys and {language} translations as values.
        Example: {{"operating plan": "plan operativo", "business review": "revisión de negocio"}}
        
        Do not include explanations or additional text.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content.strip()
        return self._parse_glossary_response(result_text)
    
    def _clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text for analysis"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove speaker indicators (e.g., "Speaker 1:", "John:")
        text = re.sub(r'^[A-Za-z\s]+:\s*', '', text)
        
        # Remove timestamps
        text = re.sub(r'\d{1,2}:\d{2}:\d{2}', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might interfere with analysis
        text = re.sub(r'[^\w\s\-.,!?;:()]', '', text)
        
        return text.strip()
    
    def _truncate_text_intelligently(self, text: str) -> str:
        """Truncate text at sentence boundaries to stay within character limit"""
        if len(text) <= self.MAX_CONTENT_LENGTH:
            return text
        
        # Find the last sentence boundary within the limit
        truncated = text[:self.MAX_CONTENT_LENGTH]
        
        # Look for sentence endings
        sentence_endings = ['.', '!', '?']
        last_sentence_end = -1
        
        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos
        
        if last_sentence_end > 0:
            # Truncate at the last complete sentence
            return text[:last_sentence_end + 1]
        else:
            # Fall back to word boundary
            last_space = truncated.rfind(' ')
            if last_space > 0:
                return text[:last_space]
            else:
                return truncated
    
    def _parse_excluded_terms_response(self, response_text: str) -> List[str]:
        """Parse the AI response for excluded terms"""
        try:
            # Extract JSON array from response
            import json
            
            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
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
            self.logger.error(f"Error parsing excluded terms response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return []
    
    def _parse_glossary_response(self, response_text: str) -> Dict[str, str]:
        """Parse the AI response for business glossary"""
        try:
            import json
            
            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            # Parse JSON
            glossary = json.loads(cleaned)
            
            # Ensure it's a dict and all values are strings
            if isinstance(glossary, dict):
                return {str(k).strip(): str(v).strip() for k, v in glossary.items() if k and v}
            else:
                self.logger.warning("AI response is not a dictionary format")
                return {}
                
        except Exception as e:
            self.logger.error(f"Error parsing glossary response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            return {}
    
    def validate_api_key(self) -> bool:
        """Validate that the API key is working"""
        try:
            # Make a simple test call
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            self.logger.error(f"API key validation failed: {e}")
            return False 