import logging
import os
from datetime import datetime

from srt_core.config.settings import LOG_DIRECTORY, LOG_MODE


def setup_logging():
    """Configure logging settings exactly once and return active log file path.

    This function is idempotent and does not rely on logging.basicConfig(), so it
    works even if logging was already initialized elsewhere. It will:
      - Reuse an existing FileHandler that points to our LOG_DIRECTORY if present
      - Otherwise add a new FileHandler and a StreamHandler to the root logger
    """
    os.makedirs(LOG_DIRECTORY, exist_ok=True)

    root_logger = logging.getLogger()

    # If there is already a FileHandler writing into our log directory, reuse it
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            try:
                handler_path = os.path.abspath(handler.baseFilename)
                if os.path.commonpath([handler_path, os.path.abspath(LOG_DIRECTORY)]) == os.path.abspath(LOG_DIRECTORY):
                    return handler.baseFilename
            except Exception:
                continue

    # No existing handler → create a new timestamped file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")

    class HTTPFilter(logging.Filter):
        def filter(self, record):
            if LOG_MODE == "Standard":
                msg = str(record.msg).lower()
                http_keywords = ["http", "https", "request", "response", "api.openai.com"]
                return not any(keyword in msg for keyword in http_keywords)
            return True

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(HTTPFilter())

    # Add a console handler if one isn't already present
    has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_stream:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(HTTPFilter())
        root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    # Suppress verbose HTTP logs from dependencies
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

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
