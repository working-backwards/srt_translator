# utils/logging_setup.py

import os
import logging
from datetime import datetime
from ..config.settings import LOG_MODE

def setup_logging():
    """Configure logging settings for translation issues"""
    log_dir = 'translation_logs'
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'translation_issues_{timestamp}.log')
    
    class HTTPFilter(logging.Filter):
        def filter(self, record):
            if LOG_MODE == 'Standard':
                http_keywords = ['http', 'https', 'request', 'response', 'api.openai.com']
                return not any(keyword in record.msg.lower() for keyword in http_keywords)
            return True

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    console_handler = logging.StreamHandler()
    
    http_filter = HTTPFilter()
    file_handler.addFilter(http_filter)
    console_handler.addFilter(http_filter)
    
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
    
    return log_file

def log_placeholder_issue(issue_type, data):
    """Log placeholder-related issues"""
    if issue_type == 'missing_placeholder':
        logging.warning(
            f"\nPLACEHOLDER MISSING:"
            f"\nFile: {data['filename']}"
            f"\nLanguage: {data['language']}"
            f"\nOriginal Term: {data['original_term']}"
            f"\nPlaceholder: {data['placeholder']}"
            f"\nOriginal Text: {data['original_text']}"
            f"\nTranslated Text: {data['translated_text']}"
            f"\n{'='*50}"
        )
    elif issue_type == 'position_mismatch':
        logging.warning(
            f"\nPLACEHOLDER POSITION MISMATCH:"
            f"\nFile: {data['filename']}"
            f"\nLanguage: {data['language']}"
            f"\nOriginal Term: {data['original_term']}"
            f"\nPlaceholder: {data['placeholder']}"
            f"\nOriginal Context: {data['original_context']}"
            f"\nTranslated Context: {data['translated_context']}"
            f"\n{'='*50}"
        )