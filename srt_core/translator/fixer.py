import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

import srt

from srt_core.translator.srt_parser import SRTParser


@dataclass
class PlaceholderIssue:
    timestamp: str
    language: str
    original_term: str
    placeholder: str
    original_context: str
    translated_context: str


@dataclass
class PhantomPlaceholder:
    timestamp: str
    language: str
    filename: str
    subtitle_number: str
    phantom_placeholder: str
    original_text: str
    translated_text: str


class SRTFixer:
    def __init__(self, log_file: str, translations_dir: str):
        self.log_file = log_file
        self.translations_dir = translations_dir
        self.issues = []
        self.phantoms = []
        self.fixed_count = 0
        self.phantom_fixed_count = 0
        self.dnt_terms_fixed_count = 0
        self.parser = SRTParser()

    def parse_log_file(self):
        """Parse the log file and extract placeholder issues and phantom placeholders"""
        if not os.path.exists(self.log_file):
            print(f"Log file {self.log_file} does not exist. Skipping fixing step.")
            return

        with open(self.log_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by the separator, but keep separators for better parsing
        entries = content.split("=" * 50)

        for entry in entries:
            # Parse regular placeholder issues
            if "POSITION_MISMATCH" in entry:
                self._parse_placeholder_issue(entry)
            # Parse phantom placeholders
            if "PHANTOM PLACEHOLDER DETECTED" in entry:
                self._parse_phantom_placeholder(entry)

    def _parse_placeholder_issue(self, entry):
        """Parse regular placeholder position mismatch issues"""
        timestamp_match = re.search(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", entry
        )
        language_match = re.search(r"Language: (.+?)(?:\n|$)", entry)
        original_term_match = re.search(r"Original Term: (.+?)(?:\n|$)", entry)
        placeholder_match = re.search(r"Placeholder: (.+?)(?:\n|$)", entry)
        original_context_match = re.search(r"Original Context: (.+?)(?:\n|$)", entry)
        translated_context_match = re.search(
            r"Translated Context: (.+?)(?:\n|$)", entry
        )

        if all(
            [
                timestamp_match,
                language_match,
                original_term_match,
                placeholder_match,
                original_context_match,
                translated_context_match,
            ]
        ):
            issue = PlaceholderIssue(
                timestamp=timestamp_match.group(1),
                language=language_match.group(1).strip(),
                original_term=original_term_match.group(1).strip(),
                placeholder=placeholder_match.group(1).strip(),
                original_context=original_context_match.group(1).strip(),
                translated_context=translated_context_match.group(1).strip(),
            )
            self.issues.append(issue)

    def _parse_phantom_placeholder(self, entry):
        """Parse phantom placeholder issues.

        Supports both the legacy format (with "Subtitle Number", "Original Text",
        and "Translated Text") and the newer batch format:

            File: <name>.srt
            Batch: <n> (subtitles X-Y)
            Language: <code>
            Phantom Placeholder: __DNT_TERM_0__
        """
        # Optional timestamp
        timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", entry)

        # Common fields
        language_match = re.search(r"Language: (.+?)(?:\n|$)", entry)
        filename_match = re.search(r"File: (.+?)(?:\n|$)", entry)
        phantom_match = re.search(r"Phantom Placeholder: (.+?)(?:\n|$)", entry)

        # Legacy optional fields
        subtitle_match_legacy = re.search(r"Subtitle Number: (.+?)(?:\n|$)", entry)
        original_text_match = re.search(r"Original Text: (.+?)(?:\n|$)", entry)
        translated_text_match = re.search(r"Translated Text: (.+?)(?:\n|$)", entry)

        # New batch-format optional fields
        batch_match = re.search(r"Batch:\s*(\d+)\s*\(subtitles\s*([0-9]+)-([0-9]+)\)", entry)

        if not (language_match and filename_match and phantom_match):
            return

        # Derive a subtitle identifier for bookkeeping (not strictly used in fixing)
        if subtitle_match_legacy:
            subtitle_identifier = subtitle_match_legacy.group(1).strip()
        elif batch_match:
            # e.g., "batch_22_subs_123-127"
            subtitle_identifier = f"batch_{batch_match.group(1)}_subs_{batch_match.group(2)}-{batch_match.group(3)}"
        else:
            subtitle_identifier = "unknown"

        phantom = PhantomPlaceholder(
            timestamp=timestamp_match.group(1) if timestamp_match else "unknown",
            language=language_match.group(1).strip(),
            filename=filename_match.group(1).strip(),
            subtitle_number=subtitle_identifier,
            phantom_placeholder=phantom_match.group(1).strip(),
            original_text=original_text_match.group(1).strip() if original_text_match else "",
            translated_text=translated_text_match.group(1).strip() if translated_text_match else "",
        )
        self.phantoms.append(phantom)

    def fix_srt_files(self, aggressiveness: float):
        """Process and fix all SRT files in the translations directory"""
        # Create a mapping from full language names to language codes
        from srt_core.config.settings import TARGET_LANGUAGES

        # Create reverse mapping: "Vietnamese" -> "VI", "Indonesian" -> "ID"
        lang_name_to_code = {}
        for lang_name, lang_code in TARGET_LANGUAGES.items():
            lang_name_to_code[lang_name] = lang_code

        print(f"Language mapping: {lang_name_to_code}")

        # Only process language directories that correspond to TARGET_LANGUAGES
        target_language_codes = set(code.upper() for code in TARGET_LANGUAGES.values())

        for lang_dir in os.listdir(self.translations_dir):
            lang_path = os.path.join(self.translations_dir, lang_dir)
            if not os.path.isdir(lang_path):
                continue

            # Skip directories that don't correspond to languages being translated in this session
            if lang_dir not in target_language_codes:
                continue

            print(f"Processing language directory: {lang_dir}")

            # Get regular issues for this language that should be fixed based on aggressiveness
            language_issues = [
                issue
                for issue in self.issues
                if lang_name_to_code.get(issue.language, issue.language) == lang_dir
                and self._should_fix_issue(issue, aggressiveness)
            ]

            # Get all phantom placeholders for this language (always fix these)
            # Match both by language code (VI) and full name (Vietnamese)
            language_phantoms = [
                phantom
                for phantom in self.phantoms
                if lang_name_to_code.get(phantom.language, phantom.language) == lang_dir
                or phantom.language == lang_dir
            ]

            print(f"  Found {len(language_phantoms)} phantoms for {lang_dir}")
            if language_phantoms:
                print(f"  Phantom languages: {[p.language for p in language_phantoms]}")

            for filename in os.listdir(lang_path):
                if not filename.endswith(".srt"):
                    continue

                file_path = os.path.join(lang_path, filename)
                print(f"  Processing file: {filename}")

                # Fix regular issues
                self._fix_srt_file_regular_issues(file_path, language_issues)

                # Fix phantom placeholders (always)
                self._fix_srt_file_phantoms(file_path, language_phantoms, filename)

    def fix_specific_srt_files(self, file_paths: List[str], aggressiveness: float):
        """Process and fix only the specified SRT files"""
        # Create a mapping from full language names to language codes
        from srt_core.config.settings import TARGET_LANGUAGES

        # Create reverse mapping: "Vietnamese" -> "VI", "Indonesian" -> "ID"
        lang_name_to_code = {}
        for lang_name, lang_code in TARGET_LANGUAGES.items():
            lang_name_to_code[lang_name] = lang_code

        print(f"Language mapping: {lang_name_to_code}")

        # Process only the specified files
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            # Extract language directory and filename from the full path
            lang_dir = os.path.basename(os.path.dirname(file_path))
            filename = os.path.basename(file_path)

            print(f"Processing specific file: {filename} in {lang_dir}")

            # Get regular issues for this language that should be fixed based on aggressiveness
            language_issues = [
                issue
                for issue in self.issues
                if lang_name_to_code.get(issue.language, issue.language) == lang_dir
                and self._should_fix_issue(issue, aggressiveness)
            ]

            # Get all phantom placeholders for this language (always fix these)
            # Match both by language code (VI) and full name (Vietnamese)
            language_phantoms = [
                phantom
                for phantom in self.phantoms
                if lang_name_to_code.get(phantom.language, phantom.language) == lang_dir
                or phantom.language == lang_dir
            ]

            print(f"  Found {len(language_phantoms)} phantoms for {lang_dir}")

            # Fix regular issues
            self._fix_srt_file_regular_issues(file_path, language_issues)

            # Fix phantom placeholders (always)
            self._fix_srt_file_phantoms(file_path, language_phantoms, filename)

    def _fix_srt_file_regular_issues(
        self, file_path: str, issues: List[PlaceholderIssue]
    ):
        """Fix regular placeholder issues in a single SRT file using srt package"""
        if not issues:
            return

        subtitles = self.parser.parse_file(file_path)
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(srt.compose(subtitles))

        changed = False
        for issue in issues:
            for subtitle in subtitles:
                if issue.placeholder in subtitle.content:
                    subtitle.content = subtitle.content.replace(
                        issue.placeholder, issue.original_term
                    )
                    self.fixed_count += 1
                    changed = True

        if changed:
            self.parser.write_file(file_path, subtitles)

    def _fix_srt_file_phantoms(
        self, file_path: str, phantoms: List[PhantomPlaceholder], filename: str
    ):
        """Fix phantom placeholders in a single SRT file using srt package"""
        if not phantoms:
            return

        # Extract base filename without language suffix for matching
        base_filename = filename
        if " - " in filename:
            parts = filename.split(" - ")
            if len(parts) == 2 and parts[1].endswith(".srt"):
                base_filename = parts[0] + ".srt"

        # Filter phantoms for this specific file
        file_phantoms = [p for p in phantoms if p.filename == base_filename]
        if not file_phantoms:
            print(f"    No phantoms found for {base_filename}")
            return

        subtitles = self.parser.parse_file(file_path)
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(srt.compose(subtitles))

        changed = False
        unique_phantoms = set(phantom.phantom_placeholder for phantom in file_phantoms)
        for subtitle in subtitles:
            for phantom_placeholder in unique_phantoms:
                if phantom_placeholder in subtitle.content:
                    count = subtitle.content.count(phantom_placeholder)
                    subtitle.content = subtitle.content.replace(phantom_placeholder, "")
                    self.phantom_fixed_count += count
                    changed = True

        if changed:
            self.parser.write_file(file_path, subtitles)

    def _fix_dnt_term_placeholders(self, file_path: str):
        """Fix DNT_TERM placeholders that weren't properly restored during translation"""
        if not os.path.exists(file_path):
            return 0

        subtitles = self.parser.parse_file(file_path)
        backup_path = file_path + ".bak"
        if not os.path.exists(backup_path):
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(srt.compose(subtitles))

        changed = False
        dnt_terms_fixed = 0

        # Pattern to match DNT_TERM placeholders
        dnt_pattern = r'__DNT_TERM_\d+__'
        
        for subtitle in subtitles:
            if re.search(dnt_pattern, subtitle.content):
                # Find all DNT_TERM placeholders in this subtitle
                placeholders = re.findall(dnt_pattern, subtitle.content)
                
                for placeholder in placeholders:
                    # Extract the number from the placeholder
                    match = re.search(r'__DNT_TERM_(\d+)__', placeholder)
                    if match:
                        term_number = int(match.group(1))
                        
                        # Try to find the original term from the DNT terms list
                        # Since we don't have the original term map, we'll remove the placeholder
                        # This is better than leaving the placeholder in the text
                        subtitle.content = subtitle.content.replace(placeholder, "")
                        dnt_terms_fixed += 1
                        changed = True
                        
                        print(f"    Fixed DNT_TERM placeholder {placeholder} in subtitle {subtitle.index}")

        if changed:
            self.parser.write_file(file_path, subtitles)
            print(f"  Fixed {dnt_terms_fixed} DNT_TERM placeholders in {os.path.basename(file_path)}")
            self.dnt_terms_fixed_count += dnt_terms_fixed

        return dnt_terms_fixed

    def _should_fix_issue(self, issue: PlaceholderIssue, aggressiveness: float) -> bool:
        """Decide if a regular issue should be fixed based on aggressiveness level"""
        return (
            aggressiveness >= 0.75
            and "does not match its original context" in issue.translated_context
        ) or (aggressiveness >= 0.5 and "missing" in issue.translated_context)

    def report_status(self):
        print(f"Total regular issues found: {len(self.issues)}")
        print(f"Total phantom placeholders found: {len(self.phantoms)}")
        print(f"Regular placeholders fixed: {self.fixed_count}")
        print(f"Phantom placeholders removed: {self.phantom_fixed_count}")
        print(f"DNT_TERM placeholders removed: {self.dnt_terms_fixed_count}")
        if self.phantoms:
            print("\nPhantom placeholders detected and removed:")
            for phantom in self.phantoms:
                print(
                    f"  - {phantom.filename}, subtitle {phantom.subtitle_number}: {phantom.phantom_placeholder}"
                )
