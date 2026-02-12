# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
