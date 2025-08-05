from dotenv import load_dotenv
from srt_core import main

# Load environment variables for CLI mode
load_dotenv()

if __name__ == "__main__":
    main.translate_srt_files()