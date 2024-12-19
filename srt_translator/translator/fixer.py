import os
import re
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class PlaceholderIssue:
    timestamp: str
    language: str
    original_term: str
    placeholder: str
    original_context: str
    translated_context: str

class SRTFixer:
    def __init__(self, log_file: str, translations_dir: str):
        self.log_file = log_file
        self.translations_dir = translations_dir
        self.issues = []
        self.fixed_count = 0

    def parse_log_file(self):
        """Parse the log file and extract placeholder issues"""
        if not os.path.exists(self.log_file):
            print(f"Log file {self.log_file} does not exist. Skipping fixing step.")
            return

        with open(self.log_file, 'r', encoding='utf-8') as f:
            content = f.read()

        entries = content.split('=' * 50)

        for entry in entries:
            if 'PLACEHOLDER POSITION MISMATCH' not in entry:
                continue

            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', entry)
            language_match = re.search(r'Language: (.+?)(?:\n|$)', entry)
            original_term_match = re.search(r'Original Term: (.+?)(?:\n|$)', entry)
            placeholder_match = re.search(r'Placeholder: (.+?)(?:\n|$)', entry)
            original_context_match = re.search(r'Original Context: (.+?)(?:\n|$)', entry)
            translated_context_match = re.search(r'Translated Context: (.+?)(?:\n|$)', entry)

            if all([timestamp_match, language_match, original_term_match, 
                   placeholder_match, original_context_match, translated_context_match]):
                issue = PlaceholderIssue(
                    timestamp=timestamp_match.group(1),
                    language=language_match.group(1).strip(),
                    original_term=original_term_match.group(1).strip(),
                    placeholder=placeholder_match.group(1).strip(),
                    original_context=original_context_match.group(1).strip(),
                    translated_context=translated_context_match.group(1).strip()
                )
                self.issues.append(issue)

    def fix_srt_files(self, aggressiveness: float):
        """Process and fix all SRT files in the translations directory"""
        for lang_dir in os.listdir(self.translations_dir):
            lang_path = os.path.join(self.translations_dir, lang_dir)
            if not os.path.isdir(lang_path):
                continue

            language_issues = [
                issue for issue in self.issues 
                if self._should_fix_issue(issue, aggressiveness)
            ]

            for filename in os.listdir(lang_path):
                if not filename.endswith('.srt'):
                    continue

                file_path = os.path.join(lang_path, filename)
                self._fix_srt_file(file_path, language_issues)

    def _fix_srt_file(self, file_path: str, issues: List[PlaceholderIssue]):
        """Fix a single SRT file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        backup_path = file_path + '.bak'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

        fixed_content = content
        for issue in issues:
            if issue.placeholder in fixed_content:
                fixed_content = fixed_content.replace(issue.placeholder, issue.original_term)
                self.fixed_count += 1

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

    def _should_fix_issue(self, issue: PlaceholderIssue, aggressiveness: float) -> bool:
        """Decide if an issue should be fixed based on aggressiveness level"""
        if aggressiveness >= 0.75 and "does not match its original context" in issue.translated_context:
            return True
        if aggressiveness >= 0.5 and "missing" in issue.translated_context:
            return True
        return False

    def report_status(self):
        print(f"Total issues found: {len(self.issues)}")
        print(f"Total placeholders fixed: {self.fixed_count}")
