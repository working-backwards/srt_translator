"""
Validation Utilities
Input validation functions for the GUI
"""

import logging
import webbrowser

from PySide6.QtWidgets import QMessageBox


def validate_translation_inputs(
    api_key: str, selected_files: list[str], target_languages: list[str]
) -> tuple[bool, str]:
    """
    Validate translation inputs

    Returns:
        tuple: (is_valid, error_message)
    """
    logging.debug("API key loaded: %s", "Yes" if api_key else "No")

    if not api_key:
        return False, "Please enter your OpenAI API key."

    logging.debug("Selected files: %s", len(selected_files))
    if not selected_files:
        return False, "Please select at least one SRT file to translate."

    logging.debug("Target languages: %s", target_languages)
    if not target_languages:
        return False, "Please select at least one target language."

    return True, ""


def show_validation_error(parent, title: str, message: str):
    """Show validation error message"""
    QMessageBox.warning(parent, title, message)


def show_translation_results(parent, results: dict, *, on_open_folder=None, on_retry_failed=None):
    """Show translation completion results dialog.

    Lists the languages that succeeded and the languages that failed (grouped
    by error type), and surfaces two action buttons per the plan's mock:
    [Open Output Folder] and (when applicable) [Retry Failed Languages].
    """
    success_count = results.get("completed", 0)
    error_count = results.get("failed", 0)
    total_files = results.get("total_files", 0)
    output_directory = results.get("output_directory", "translated_srt_files")
    failed_languages = results.get("failed_languages", [])
    successful_languages = results.get("successful_languages", [])

    logging.info(
        "Success count: %s (languages), Error count: %s, Total files: %s",
        success_count,
        error_count,
        total_files,
    )

    success_codes = [item.get("code", "?") for item in successful_languages]
    success_line = (
        f"Successfully translated {len(success_codes)} languages: "
        f"{', '.join(success_codes)}"
        if success_codes
        else "Successfully translated 0 languages"
    )

    if failed_languages:
        failed_groups: dict[str, list[str]] = {}
        for item in failed_languages:
            code = item.get("code", "?")
            err = item.get("error_type", "error")
            failed_groups.setdefault(err, []).append(code)
        failed_lines = [
            f"  - {', '.join(codes)} ({err})" for err, codes in failed_groups.items()
        ]
        body = (
            f"Translation complete with errors.\n\n"
            f"{success_line}\n\n"
            f"Failed {len(failed_languages)} languages:\n"
            + "\n".join(failed_lines)
            + f"\n\nOutput so far is in '{output_directory}'."
        )
        title = "Translation Complete with Errors"
        icon = QMessageBox.Warning
    else:
        body = (
            f"Translation complete.\n\n"
            f"{success_line}\n\n"
            f"Output files are available in '{output_directory}'."
        )
        title = "Translation Complete"
        icon = QMessageBox.Information

    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(body)

    open_folder_btn = None
    if on_open_folder is not None:
        open_folder_btn = box.addButton("Open Output Folder", QMessageBox.ActionRole)

    retry_btn = None
    if failed_languages and on_retry_failed is not None:
        # Only offer retry when something is recoverable (transient error_type).
        retryable = {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError"}
        if any(item.get("error_type") in retryable for item in failed_languages):
            retry_btn = box.addButton("Retry Failed Languages", QMessageBox.ActionRole)

    ok_btn = box.addButton(QMessageBox.Ok)
    box.setDefaultButton(retry_btn if retry_btn is not None else ok_btn)
    box.exec()

    clicked = box.clickedButton()
    if clicked is open_folder_btn and on_open_folder is not None:
        on_open_folder(output_directory)
    elif clicked is retry_btn and on_retry_failed is not None:
        on_retry_failed()


def show_translation_error(parent, details: dict, *, on_open_settings=None, on_retry=None):
    """Show a classifier-aware translation error dialog.

    Accepts the dict produced by `gui.utils.error_classifier.get_error_details`
    (`title` / `message` / `suggestion` / `recoverable` / `action_kind`).
    Renders a single primary action button, plus OK.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning if details.get("recoverable") else QMessageBox.Critical)
    box.setWindowTitle(details.get("title", "Translation Error"))
    box.setText(details.get("message", "An error occurred during translation."))
    suggestion = details.get("suggestion")
    if suggestion:
        box.setInformativeText(suggestion)

    action_kind = details.get("action_kind", "ok")
    primary = None
    if action_kind == "open_settings" and on_open_settings is not None:
        primary = box.addButton("Open Settings", QMessageBox.ActionRole)
    elif action_kind == "open_url":
        primary = box.addButton("Open platform.openai.com", QMessageBox.ActionRole)
    elif action_kind == "wait_retry" and on_retry is not None:
        primary = box.addButton("Wait and Retry", QMessageBox.ActionRole)
    elif action_kind == "cancel_retry" and on_retry is not None:
        primary = box.addButton("Retry", QMessageBox.ActionRole)
    elif action_kind == "retry" and on_retry is not None:
        primary = box.addButton("Retry", QMessageBox.ActionRole)

    # For cancel_retry the secondary button is labeled "Cancel" to make the
    # decision explicit; otherwise OK is fine because there's nothing to cancel.
    if action_kind == "cancel_retry":
        secondary = box.addButton("Cancel", QMessageBox.RejectRole)
    else:
        secondary = box.addButton(QMessageBox.Ok)

    default_button = primary or secondary

    if default_button is not None:
        box.setDefaultButton(default_button)
    box.exec()

    clicked = box.clickedButton()
    if clicked is primary and primary is not None:
        if action_kind == "open_settings":
            on_open_settings()
        elif action_kind == "open_url":
            url = details.get("action_url", "")
            if url:
                webbrowser.open(url)
        elif action_kind in ("wait_retry", "cancel_retry", "retry"):
            on_retry()
