#!/usr/bin/env python3
"""
Validate languages.json to ensure it follows the new single cps_cap format.
This script checks that:
1. All languages have cps_cap (required)
2. No languages have forbidden keys (cps_soft, cps_hard, reflow, no_orphan_end, protected_bigrams)
3. Family defaults are clean
"""

import sys

from srt_translator.config import load_language_catalog

FORBIDDEN_KEYS = {
    "cps_soft",
    "cps_hard",
    "reflow",
    "no_orphan_end",
    "protected_bigrams",
}
REQUIRED_KEYS = {"cps_cap"}


def main():
    # Load config from packaged resources
    config = load_language_catalog()

    languages = config.get("languages", {})
    errors = []

    # Check each language
    for code, meta in languages.items():
        # Must have cps_cap
        missing = [k for k in REQUIRED_KEYS if k not in meta]
        if missing:
            errors.append(f"[{code}] missing required key(s): {', '.join(missing)}")

        # Must not have forbidden keys
        forbidden = [k for k in FORBIDDEN_KEYS if k in meta]
        if forbidden:
            errors.append(f"[{code}] contains forbidden key(s): {', '.join(forbidden)}")

    # Check family_defaults
    family_defaults = config.get("family_defaults", {})
    for family, obj in family_defaults.items():
        for k in list(obj.keys()):
            if k in ("no_orphan_end", "protected_bigrams", "reflow"):
                errors.append(f"[family_defaults.{family}] forbidden key: {k}")

    if errors:
        print("languages.json validation FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("languages.json validation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
