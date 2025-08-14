import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from srt_translator.core.translator.fixer import SRTFixer

#!/usr/bin/env python3
"""
Standalone script to run the SRT fixer on existing translated files.
This script can be run independently to fix issues in already-translated SRT files.
"""

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)

# Add parent directory to path so we can import srt_translator module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


load_dotenv()


def run_fixer_only(log_file_path=None, output_directory=None):
    """Run only the fixer on existing translation files"""

    if not log_file_path:
        logger.error("Error: No log file specified. Please provide a log file path.")
        logger.error("Usage: python run_fixer_only.py --log-file <path_to_log_file>")
        return

    if not os.path.exists(log_file_path):
        logger.error(f"Error: Log file not found: {log_file_path}")
        return

    # Use provided output directory or default
    translations_dir = output_directory or "translated_srt_files"

    logger.info(f"Using log file: {log_file_path}")
    logger.info(f"Using translations directory: {translations_dir}")

    # Run the fixer with default aggressiveness
    fixer = SRTFixer(log_file_path, translations_dir)
    fixer.parse_log_file()

    if fixer.issues or fixer.phantoms:
        logger.info(
            f"Found {len(fixer.issues)} regular issues and {len(fixer.phantoms)} phantom placeholders to fix"
        )
        fixer.fix_srt_files(aggressiveness=0.75)  # Default aggressiveness
    else:
        logger.info("No issues found in log file")

    fixer.report_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run SRT fixer on existing translation files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_fixer_only.py --log-file path/to/log/file.log
  python scripts/run_fixer_only.py --log-file path/to/log/file.log --output-dir path/to/translations
        """,
    )

    parser.add_argument(
        "--log-file",
        required=True,
        help="Path to the log file containing translation issues",
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory containing translated files (defaults to configured output directory)",
    )

    args = parser.parse_args()

    run_fixer_only(log_file_path=args.log_file, output_directory=args.output_dir)
