import logging
import os
from datetime import datetime

from srt_app.config.settings import LOG_DIRECTORY, LOG_MODE


def setup_logging():
    """Configure logging settings for translation issues"""
    os.makedirs(LOG_DIRECTORY, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")

    class HTTPFilter(logging.Filter):
        def filter(self, record):
            if LOG_MODE == "Standard":
                http_keywords = [
                    "http",
                    "https",
                    "request",
                    "response",
                    "api.openai.com",
                ]
                return not any(
                    keyword in record.msg.lower() for keyword in http_keywords
                )
            return True

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler()

    http_filter = HTTPFilter()
    file_handler.addFilter(http_filter)
    console_handler.addFilter(http_filter)

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

    return log_file


def log_placeholder_issue(issue_type, issue_details):
    """Log placeholder issues with a reason description and subtitle number"""
    fixable_status = (
        "Computer-fixable"
        if issue_details.get("fixable", False)
        else "Requires human review"
    )
    reason_description = issue_details.get(
        "reason_description", "No specific reason provided."
    )
    subtitle_number = issue_details.get("subtitle_number", "Unknown")

    logging.warning(
        f"""
    ==================================================
    {issue_type.upper()}:
    File: {issue_details['filename']}
    Subtitle Number: {subtitle_number}
    Language: {issue_details['language']}
    Original Term: {issue_details['original_term']}
    Placeholder: {issue_details['placeholder']}
    Original Context: {issue_details.get('original_context', 'N/A')}
    Translated Context: {issue_details.get('translated_context', 'N/A')}
    Status: {fixable_status}
    Reason: {reason_description}
    ==================================================
    """
    )
