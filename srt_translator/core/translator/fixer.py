import logging
import re
from pathlib import Path

import srt

# Get logger for this module
logger = logging.getLogger(__name__)


class SRTFixer:
    def __init__(self, log_file: str, translations_dir: str):
        self.log_file = log_file
        self.translations_dir = translations_dir

    def scan_and_fix_placeholders(self, *, batch_dir: Path, dnt_terms: list[str], dry_run: bool = False) -> dict:
        """
        Scan and fix placeholder issues in translated SRT files.

        Args:
            batch_dir: Path to the batch directory containing translated files
            dnt_terms: List of DNT terms for replacement
            dry_run: If True, only report what would be changed without writing files

        Returns:
            Dict with summary statistics
        """
        # Discover all translated SRT files under batch_dir
        srt_files = self._discover_srt_files(batch_dir)

        # Track statistics
        files_changed = 0
        tokens_replaced = 0
        tokens_removed = 0
        unknown_indices = 0

        logger.info("Scanning %s SRT files for placeholder issues...", len(srt_files))

        for file_path in srt_files:
            file_stats = self._process_single_file(file_path, dnt_terms, dry_run)

            if file_stats["changed"]:
                files_changed += 1
                tokens_replaced += file_stats["tokens_replaced"]
                tokens_removed += file_stats["tokens_removed"]
                unknown_indices += file_stats["unknown_indices"]

        # Log summary
        self._log_summary(
            len(srt_files),
            files_changed,
            tokens_replaced,
            tokens_removed,
            unknown_indices,
            dry_run,
        )

        return {
            "files_scanned": len(srt_files),
            "files_changed": files_changed,
            "tokens_replaced": tokens_replaced,
            "tokens_removed": tokens_removed,
            "unknown_indices": unknown_indices,
        }

    def _discover_srt_files(self, batch_dir: Path) -> list[Path]:
        """Discover all translated SRT files under batch_dir."""
        srt_files = []

        # Look for language subdirectories
        for lang_dir in batch_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith("."):
                # Find .srt files in each language directory
                for srt_file in lang_dir.glob("*.srt"):
                    if srt_file.is_file():
                        srt_files.append(srt_file)

        return srt_files

    def _process_single_file(self, file_path: Path, dnt_terms: list[str], dry_run: bool) -> dict:
        """Process a single SRT file for placeholder issues."""
        try:
            # Read the file
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Parse subtitles
            subtitles = list(srt.parse(content))

            # Track changes
            changes = []
            tokens_replaced = 0
            tokens_removed = 0
            unknown_indices = 0

            # Process each subtitle
            for subtitle in subtitles:
                subtitle_changes = self._process_subtitle_content(subtitle.content, dnt_terms)

                if subtitle_changes["new_content"] != subtitle.content:
                    changes.append(
                        {
                            "subtitle": subtitle,
                            "old_content": subtitle.content,
                            "new_content": subtitle_changes["new_content"],
                            "tokens_replaced": subtitle_changes["tokens_replaced"],
                            "tokens_removed": subtitle_changes["tokens_removed"],
                            "unknown_indices": subtitle_changes["unknown_indices"],
                        }
                    )

                    tokens_replaced += subtitle_changes["tokens_replaced"]
                    tokens_removed += subtitle_changes["tokens_removed"]
                    unknown_indices += subtitle_changes["unknown_indices"]

            # Apply changes if any
            if changes and not dry_run:
                self._apply_changes(file_path, subtitles, changes)

            return {
                "changed": len(changes) > 0,
                "tokens_replaced": tokens_replaced,
                "tokens_removed": tokens_removed,
                "unknown_indices": unknown_indices,
            }

        except Exception as e:
            logger.error("Error processing %s: %s", file_path, e)
            return {
                "changed": False,
                "tokens_replaced": 0,
                "tokens_removed": 0,
                "unknown_indices": 0,
            }

    def _process_subtitle_content(self, content: str, dnt_terms: list[str]) -> dict:
        """Process subtitle content for placeholder issues."""
        # Define character classes for Unicode variants
        UNDERSCORE_CLASS = r"[_\uFF3F]"  # ASCII underscore and fullwidth underscore
        ZERO_WIDTH_CLASS = r"[\u200B\u200C\u200D\uFEFF]"  # ZWSP/ZWNJ/ZWJ/BOM

        # Build comprehensive placeholder pattern with named groups
        placeholder_pattern = re.compile(
            UNDERSCORE_CLASS
            + "{2}"  # Two leading underscores
            + r"DNT"  # DNT
            + ZERO_WIDTH_CLASS
            + "*"  # Optional zero-width chars
            + UNDERSCORE_CLASS
            + "?"  # Optional underscore
            + ZERO_WIDTH_CLASS
            + "*"  # Optional zero-width chars
            + r"TERM"  # TERM
            + UNDERSCORE_CLASS  # One underscore before index
            + r"(?P<idx>\d+)"  # Named group for index
            + UNDERSCORE_CLASS
            + "{2}"  # Two trailing underscores
            + r"(?P<tail>[\"'`,.:;!?\)\]}"
            "''»«）］】，。！？：；…]*)"  # Named group for trailing punctuation
        )

        matches = list(placeholder_pattern.finditer(content))

        # Sort matches in reverse order to avoid index shifting during replacement
        matches.sort(key=lambda m: m.start(), reverse=True)

        new_content = content
        tokens_replaced = 0
        tokens_removed = 0
        unknown_indices = 0

        for match in matches:
            index_str = match.group("idx")
            tail = match.group("tail")

            try:
                index = int(index_str)

                # If index is in range, replace with DNT term + tail
                if 0 <= index < len(dnt_terms):
                    replacement = dnt_terms[index] + tail
                    new_content = new_content[: match.start()] + replacement + new_content[match.end() :]
                    tokens_replaced += 1
                else:
                    # Remove the placeholder but keep punctuation
                    replacement = tail
                    new_content = new_content[: match.start()] + replacement + new_content[match.end() :]
                    tokens_removed += 1
                    unknown_indices += 1

            except ValueError:
                # Invalid index, remove the placeholder but keep punctuation
                replacement = tail
                new_content = new_content[: match.start()] + replacement + new_content[match.end() :]
                tokens_removed += 1
                unknown_indices += 1

        return {
            "new_content": new_content,
            "tokens_replaced": tokens_replaced,
            "tokens_removed": tokens_removed,
            "unknown_indices": unknown_indices,
        }

    def _apply_changes(self, file_path: Path, subtitles: list[srt.Subtitle], changes: list[dict]):
        """Apply changes to the SRT file with backup."""
        # Create backup
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        if not backup_path.exists():
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(original_content)

        # Apply changes to subtitles
        for change in changes:
            change["subtitle"].content = change["new_content"]

        # Write updated file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(srt.compose(subtitles))

        logger.info("Updated %s (backup: %s)", file_path, backup_path)

    def _log_summary(
        self,
        files_scanned: int,
        files_changed: int,
        tokens_replaced: int,
        tokens_removed: int,
        unknown_indices: int,
        dry_run: bool,
    ):
        """Log summary of the fixing process."""
        logger.info("=" * 60)
        logger.info("SRT Fixer Status Report")
        logger.info("=" * 60)
        logger.info("Files scanned: %s, Files changed: %s", files_scanned, files_changed)
        logger.info("Tokens replaced: %s (mapped to DNT terms)", tokens_replaced)
        logger.info("Tokens removed: %s (unmappable/invalid index)", tokens_removed)

        if unknown_indices > 0:
            logger.info("Unknown indices encountered: %s", unknown_indices)

        if dry_run and (tokens_replaced > 0 or tokens_removed > 0):
            logger.info("Dry-run: changes were NOT written")
