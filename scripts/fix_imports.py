#!/usr/bin/env python3
"""
Script to fix import order issues (E402 errors) in the project.
"""

import logging
from pathlib import Path

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


def fix_imports_in_file(file_path):
    """Fix import order issues in a single file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Pattern to match imports that are not at the top
    # This looks for imports that come after non-import statements
    lines = content.split("\n")
    new_lines = []
    imports_to_move = []
    in_import_section = True

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this is an import statement
        is_import = (
            stripped.startswith("import ")
            or stripped.startswith("from ")
            and " import " in stripped
        )

        # Check if this is a non-import statement (but not empty or comment)
        is_non_import = (
            stripped
            and not stripped.startswith("#")
            and not stripped.startswith('"""')
            and not stripped.startswith("'''")
            and not is_import
        )

        if is_non_import and in_import_section:
            in_import_section = False

        if is_import and not in_import_section:
            # This import needs to be moved to the top
            imports_to_move.append(line)
        else:
            new_lines.append(line)

    if imports_to_move:
        # Find the right place to insert imports (after existing imports)
        insert_index = 0
        for i, line in enumerate(new_lines):
            stripped = line.strip()
            if stripped.startswith("import ") or (
                stripped.startswith("from ") and " import " in stripped
            ):
                insert_index = i + 1
            elif (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                break

        # Insert the moved imports
        new_lines.insert(insert_index, "")
        for import_line in imports_to_move:
            new_lines.insert(insert_index, import_line)
            insert_index += 1

        # Remove the original import lines
        content = "\n".join(new_lines)

        # Write the fixed content back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Fixed imports in {file_path}")
        return True

    return False


def main():
    """Fix import order issues in all files with E402 errors."""
    # Files with known E402 errors
    files_to_fix = [
        "scripts/run_fixer_only.py",
        "srt_translator/core/config/settings.py",
        "srt_translator/core/main.py",
        "srt_translator/core/translator/translator.py",
        "tests/conftest.py",
        "tests/gui/test_termbase_editor.py",
        "tests/gui/test_editors_integration.py",
        "tests/gui/test_dnt_terms_editor.py",
        "tests/test_ai_config_basic.py",
        "tests/test_ai_config_integration.py",
    ]

    fixed_count = 0
    for file_path in files_to_fix:
        if Path(file_path).exists():
            if fix_imports_in_file(file_path):
                fixed_count += 1

    logger.info(f"\nFixed import order issues in {fixed_count} files.")
    logger.info("Run 'flake8 --select E402' to verify the fixes.")


if __name__ == "__main__":
    main()
