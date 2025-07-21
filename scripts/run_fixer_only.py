import glob
import os
import sys

# Add parent directory to path so we can import srt module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from srt.config.settings import FIX_AGGRESSIVENESS, LOG_DIRECTORY, OUTPUT_BASE_DIR
from srt.translator.fixer import SRTFixer

load_dotenv()


def run_fixer_only():
    """Run only the fixer on existing translation files"""

    # Find the most recent log file
    log_files = glob.glob(os.path.join(LOG_DIRECTORY, "translation_issues_*.log"))
    if not log_files:
        print(f"No log files found in {LOG_DIRECTORY}")
        print("Make sure you've run translations at least once.")
        return

    # Get the most recent log file
    latest_log = max(log_files, key=os.path.getctime)
    print(f"Using log file: {latest_log}")

    # Run the fixer
    fixer = SRTFixer(latest_log, OUTPUT_BASE_DIR)
    fixer.parse_log_file()

    if fixer.issues or fixer.phantoms:
        print(
            f"Found {len(fixer.issues)} regular issues and {len(fixer.phantoms)} phantom placeholders to fix"
        )
        fixer.fix_srt_files(aggressiveness=FIX_AGGRESSIVENESS)
    else:
        print("No issues found in log file")

    fixer.report_status()


if __name__ == "__main__":
    run_fixer_only()
