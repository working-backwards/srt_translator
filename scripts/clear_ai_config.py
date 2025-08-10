#!/usr/bin/env python3
"""
Simple script to clear AI-generated configuration from the GUI settings.
Run this from the project root directory.
"""

import sys
import os

# Add the project root to the path (scripts/ is one level down)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    try:
        from gui.settings_manager import SettingsManager

        print("Clearing AI-generated configuration...")
        settings_manager = SettingsManager()

        # Check what's currently stored
        dnt_terms, termbase = settings_manager.load_ai_config()
        print(
            f"Current AI config: {len(dnt_terms)} DNT terms, {len(termbase)} languages in termbase"
        )

        # Clear the AI configuration
        settings_manager.clear_ai_config()

        # Verify it's cleared
        dnt_terms, termbase = settings_manager.load_ai_config()
        print(
            f"After clearing: {len(dnt_terms)} DNT terms, {len(termbase)} languages in termbase"
        )

        print("✅ AI configuration cleared successfully!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the project root directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
