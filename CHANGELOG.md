# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **API key storage documentation corrected.** Prior versions of the GUI manual and architecture docs described the OpenAI API key as being held in "secure storage" via QSettings. This was inaccurate: the key has always been stored as local plaintext in the app's settings file (QSettings `IniFormat`), and that has not changed. Documentation and a new in-app disclosure label now describe storage accurately. If you previously relied on the old claim, no action is required — but if you want stronger protection, rotate the key and use OS-level account protections on the machine running the app.

### Added
- **First-run API key onboarding.** On first launch (when no key is stored), a focused "Welcome to SRT Translator" modal prompts for the OpenAI API key — with a rationale, a "Get an API key" link, a "Test Connection" check, the local-plaintext storage disclosure, and inline validation. This replaces the previous experience where a new user had to discover the requirement by hitting a downstream "No API Key" error and hunt for the settings gear. The key can still be edited later via the gear/Settings dialog.
- In-app disclosure label adjacent to the API key input field, stating that the key is stored locally and unencrypted, with a pointer to rotate at platform.openai.com if exposed.
- Regression tests (`tests/test_api_key_audit.py`) that fail if any code path leaks the API key into log output or batch artifacts.

## [1.0.0] - 2025-02-12

Initial public release of SRT Translator.

### Features
- **Multi-language translation** of SRT subtitle files using OpenAI (gpt-4o-mini)
- **GUI application** (PySide6) with file browser, language selection, and API configuration
- **CLI interface** (`srtx-cli`) with `.env`-based configuration
- **Do-Not-Translate (DNT) lists** to preserve names, brands, and technical terms
- **AI-generated termbases** with per-language translations for consistent terminology
- **Tone control** (casual, neutral, formal) with language-specific adjustments
- **Automatic evaluation** with HTML and Markdown quality reports
- **Subtitle-based processing** that preserves original timing and formatting
- **Progressive retry** with batch-size reduction for reliable translations
- **80 supported languages** including regional variants
