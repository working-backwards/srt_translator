#!/usr/bin/env python3
"""
Utility functions for merging user-provided termbase and DNT terms with AI-generated ones.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request


def merge_dnt_terms(
    ai_generated: list[str], user_provided: list[str] | None = None
) -> list[str]:
    """
    Merge AI-generated DNT terms with user-provided DNT terms.
    
    Strategy:
    - User-provided terms take precedence (added first)
    - AI-generated terms are added if not already present (case-insensitive)
    - Returns sorted, deduplicated list
    
    Args:
        ai_generated: List of AI-generated DNT terms
        user_provided: Optional list of user-provided DNT terms
        
    Returns:
        Merged and deduplicated list of DNT terms
    """
    if not user_provided:
        return sorted(set(ai_generated), key=str.lower)
    
    # Start with user-provided terms (they take precedence)
    merged = []
    seen_lower = set()
    
    # Add user-provided terms first
    for term in user_provided:
        if term and term.strip():
            term_clean = term.strip()
            term_lower = term_clean.lower()
            if term_lower not in seen_lower:
                merged.append(term_clean)
                seen_lower.add(term_lower)
    
    # Add AI-generated terms that aren't duplicates
    for term in ai_generated:
        if term and term.strip():
            term_clean = term.strip()
            term_lower = term_clean.lower()
            if term_lower not in seen_lower:
                merged.append(term_clean)
                seen_lower.add(term_lower)
    
    return sorted(merged, key=str.lower)


def merge_termbase(
    ai_generated: dict[str, dict[str, str]],
    user_provided: dict[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, str]]:
    """
    Merge AI-generated termbase with user-provided termbase.
    
    Strategy:
    - For each language, user-provided entries take precedence
    - AI-generated entries are added if the source term doesn't exist in user termbase
    - User-provided translations override AI-generated ones for the same source term
    
    Args:
        ai_generated: AI-generated termbase {lang_code: {source_term: translation}}
        user_provided: Optional user-provided termbase {lang_code: {source_term: translation}}
        
    Returns:
        Merged termbase dictionary
    """
    if not user_provided:
        return ai_generated.copy()
    
    merged = {}
    
    # Get all unique language codes from both sources
    all_languages = set(ai_generated.keys()) | set(user_provided.keys())
    
    for lang_code in all_languages:
        user_tb = user_provided.get(lang_code, {})
        ai_tb = ai_generated.get(lang_code, {})
        
        # Start with user-provided entries (they take precedence)
        merged_tb = user_tb.copy()
        
        # Add AI-generated entries that don't conflict
        for source_term, translation in ai_tb.items():
            if source_term and translation:
                source_clean = source_term.strip()
                # User-provided takes precedence, so only add if not present
                if source_clean not in merged_tb:
                    merged_tb[source_clean] = translation.strip()
        
        if merged_tb:
            merged[lang_code] = merged_tb
    
    return merged


def load_termbase_from_file(file_path: str, logger: logging.Logger | None = None) -> dict[str, dict[str, str]]:
    """
    Load termbase from a JSON file.
    
    Expected format:
    {
      "lang_code": {
        "source_term": "translation",
        ...
      },
      ...
    }
    
    Args:
        file_path: Path to termbase JSON file
        logger: Optional logger for error reporting
        
    Returns:
        Termbase dictionary, or empty dict if loading fails
    """
    log = logger or logging.getLogger(__name__)
    
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            log.error("Termbase file must contain a JSON object, got %s", type(data).__name__)
            return {}
        
        # Validate structure: each value should be a dict
        validated = {}
        for lang_code, term_map in data.items():
            if isinstance(term_map, dict):
                # Ensure all values are strings
                validated[lang_code] = {
                    str(k).strip(): str(v).strip()
                    for k, v in term_map.items()
                    if k and v
                }
            else:
                log.warning("Skipping invalid termbase entry for language %s: expected dict, got %s", lang_code, type(term_map).__name__)
        
        log.info("Loaded termbase from %s: %s languages, %s total entries", 
                 file_path, len(validated), sum(len(tb) for tb in validated.values()))
        return validated
        
    except FileNotFoundError:
        log.error("Termbase file not found: %s", file_path)
        return {}
    except json.JSONDecodeError as e:
        log.error("Invalid JSON in termbase file %s: %s", file_path, e)
        return {}
    except Exception as e:
        log.error("Error loading termbase from %s: %s", file_path, e)
        return {}


def load_dnt_terms_from_file(file_path: str, logger: logging.Logger | None = None) -> list[str]:
    """
    Load DNT terms from a JSON file or text file.
    
    Supports:
    - JSON array: ["term1", "term2", ...]
    - Text file: one term per line
    
    Args:
        file_path: Path to DNT terms file
        logger: Optional logger for error reporting
        
    Returns:
        List of DNT terms, or empty list if loading fails
    """
    log = logger or logging.getLogger(__name__)
    
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()
        
        # Try JSON first
        try:
            data = json.loads(content)
            if isinstance(data, list):
                terms = [str(term).strip() for term in data if term]
                log.info("Loaded %s DNT terms from JSON file %s", len(terms), file_path)
                return terms
            else:
                log.warning("JSON file does not contain an array, trying as text file")
        except json.JSONDecodeError:
            # Not JSON, treat as text file
            pass
        
        # Treat as text file (one term per line)
        terms = []
        for line in content.split("\n"):
            term = line.strip()
            if term and not term.startswith("#"):  # Ignore comment lines
                terms.append(term)
        
        log.info("Loaded %s DNT terms from text file %s", len(terms), file_path)
        return terms
        
    except FileNotFoundError:
        log.error("DNT terms file not found: %s", file_path)
        return []
    except Exception as e:
        log.error("Error loading DNT terms from %s: %s", file_path, e)
        return []


def fetch_termbase_from_url(url: str, logger: logging.Logger | None = None, timeout: int = 30) -> dict[str, dict[str, str]]:
    """
    Fetch termbase from a URL.
    
    Args:
        url: URL to fetch termbase JSON from
        logger: Optional logger for error reporting
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Termbase dictionary, or empty dict if fetching fails
    """
    log = logger or logging.getLogger(__name__)
    
    if not url or not url.strip():
        log.error("Empty URL provided for termbase fetch")
        return {}
    
    try:
        # Validate URL format
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            log.error("Invalid URL format: %s", url)
            return {}
        
        log.info("Fetching termbase from URL: %s", url)
        
        # Create request with timeout
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "SRT-Translator/1.0")
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                log.error("HTTP error %s when fetching termbase from %s", response.status, url)
                return {}
            
            # Read and decode response
            content = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            text = content.decode(encoding)
            
            # Parse JSON
            data = json.loads(text)
            
            if not isinstance(data, dict):
                log.error("Termbase URL must return a JSON object, got %s", type(data).__name__)
                return {}
            
            # Validate structure: each value should be a dict
            validated = {}
            for lang_code, term_map in data.items():
                if isinstance(term_map, dict):
                    # Ensure all values are strings
                    validated[lang_code] = {
                        str(k).strip(): str(v).strip()
                        for k, v in term_map.items()
                        if k and v
                    }
                else:
                    log.warning("Skipping invalid termbase entry for language %s: expected dict, got %s", lang_code, type(term_map).__name__)
            
            log.info("Fetched termbase from URL: %s languages, %s total entries", 
                     len(validated), sum(len(tb) for tb in validated.values()))
            return validated
            
    except urllib.error.URLError as e:
        log.error("Network error fetching termbase from %s: %s", url, e)
        return {}
    except urllib.error.HTTPError as e:
        log.error("HTTP error %s fetching termbase from %s: %s", e.code, url, e)
        return {}
    except json.JSONDecodeError as e:
        log.error("Invalid JSON in termbase response from %s: %s", url, e)
        return {}
    except Exception as e:
        log.error("Error fetching termbase from %s: %s", url, e)
        return {}


def fetch_dnt_terms_from_url(url: str, logger: logging.Logger | None = None, timeout: int = 30) -> list[str]:
    """
    Fetch DNT terms from a URL.
    
    Supports:
    - JSON array: ["term1", "term2", ...]
    - Text file: one term per line
    
    Args:
        url: URL to fetch DNT terms from
        logger: Optional logger for error reporting
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        List of DNT terms, or empty list if fetching fails
    """
    log = logger or logging.getLogger(__name__)
    
    if not url or not url.strip():
        log.error("Empty URL provided for DNT terms fetch")
        return []
    
    try:
        # Validate URL format
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            log.error("Invalid URL format: %s", url)
            return []
        
        log.info("Fetching DNT terms from URL: %s", url)
        
        # Create request with timeout
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "SRT-Translator/1.0")
        
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                log.error("HTTP error %s when fetching DNT terms from %s", response.status, url)
                return []
            
            # Read and decode response
            content = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            text = content.decode(encoding).strip()
            
            # Try JSON first
            try:
                data = json.loads(text)
                if isinstance(data, list):
                    terms = [str(term).strip() for term in data if term]
                    log.info("Fetched %s DNT terms from JSON URL", len(terms))
                    return terms
                else:
                    log.warning("JSON URL does not contain an array, trying as text")
            except json.JSONDecodeError:
                # Not JSON, treat as text file
                pass
            
            # Treat as text file (one term per line)
            terms = []
            for line in text.split("\n"):
                term = line.strip()
                if term and not term.startswith("#"):  # Ignore comment lines
                    terms.append(term)
            
            log.info("Fetched %s DNT terms from text URL", len(terms))
            return terms
            
    except urllib.error.URLError as e:
        log.error("Network error fetching DNT terms from %s: %s", url, e)
        return []
    except urllib.error.HTTPError as e:
        log.error("HTTP error %s fetching DNT terms from %s: %s", e.code, url, e)
        return []
    except Exception as e:
        log.error("Error fetching DNT terms from %s: %s", url, e)
        return []

