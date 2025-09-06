# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Unified Report Pipeline**: Single source of truth for report generation using `report_v1.json`
- **Orchestrated Report Generation**: Worker now generates all report formats (JSON, MD, HTML) in one pass
- **Comprehensive Test Coverage**: Added tests to verify orchestrator generates all required files

### Changed
- **GUI Report Handling**: GUI now uses worker-generated reports instead of double-rendering HTML
- **HTML Presenter**: Now reads only from `report_v1.json` (no direct access to `eval_report.json` or `ai_config.json`)
- **Worker Signal Architecture**: Removed `eval_report_ready` signal; report paths now included in `translation_completed` signal

### Removed
- **Legacy Double HTML Rendering**: Eliminated duplicate HTML generation in GUI
- **Batch-Root ai_config Fallbacks**: Standardized on `_artifacts/ai_config.json` as single source of truth
- **Unused Signal**: Removed `eval_report_ready` signal from translation worker

### Fixed
- **Report Consistency**: Ensures HTML and Markdown reports are always generated from the same compiled data
- **Performance**: Eliminates redundant file I/O and processing in GUI
- **Architecture**: Cleaner separation between worker (generates) and GUI (displays) responsibilities

### Added
- Comprehensive CI/CD pipeline with Python 3.9-3.12 matrix
- Cross-platform testing (Ubuntu, macOS, Windows)
- Automated release artifact generation
- CLI --version flag
- Structured logging throughout CLI
- CONTRIBUTING.md with development guidelines
- CODE_OF_CONDUCT.md for community standards
- RELEASE.md with release process documentation
- CHANGELOG.md for change tracking
- Safe upper bounds on all critical dependencies
- Organized repository structure with docs/ and examples/ folders
- **Quality Hardening**: Automatic filtering of numeric DNT terms for better localization
- **DNT Precedence**: Automatic resolution of conflicts between DNT terms and termbase entries
- **Relevant Termbase Injection**: Only injects termbase entries present in current batch text
- **Enhanced Output Format**: Complete transparency into what was provided vs. what was used during translation
- **Processing Summaries**: Detailed logs showing filtering results and quality improvements applied
- **Translation Quality Improvements**: Major enhancement to address "quality cliff" issues
  - **Progressive Shrinking**: Intelligent batch size reduction that preserves translation context and quality
  - **No-Orphans Protection**: Language-aware subtitle reflow that prevents orphaned function words
  - **Language-Specific Configuration**: Support for customizing orphan prevention rules per language
  - **Family Defaults**: Sensible defaults for unconfigured languages with safe fallbacks
- **Policy-Driven Language Configuration**: New policy system in `languages.json` for per-language batch sizes and apostrophe handling
  - **Policy Defaults**: Centralized configuration with sensible defaults for all languages
  - **Per-Language Overrides**: Support for language-specific batch sizes (e.g., TR/AZ use batch_size=4 for stability)
  - **Apostrophe Policy**: Configurable handling of apostrophes after DNT placeholders per language
- **Policy-Aware Apostrophe Validation**: Enhanced placeholder validation that respects language-specific apostrophe policies
  - **TR/AZ Support**: Turkish and Azerbaijani can now use apostrophes after DNT placeholders without validation errors
  - **Smart Normalization**: Apostrophes are normalized during validation when allowed by policy
  - **Policy-Driven Logging**: Log level and content adjusts based on apostrophe policy (info vs. warning)
- **Per-Language Policy Injection**: Complete policy system implementation with automatic loading and validation
  - **CLI Integration**: CLI now loads language policies from `languages.json` and validates required keys
  - **GUI Integration**: GUI translation worker loads policies and passes them to core engine
  - **API Enhancement**: TranslationConfig now supports language policies and optional batch sizes
  - **Core Orchestration**: Core engine uses per-language batch sizes and logs policy configuration
  - **Policy Validation**: System validates that all required policy keys exist before translation
  - **Architecture Cleanup**: Removed all direct file I/O from core modules, enforcing dependency injection pattern
  - **Simplified Batch Size Configuration**: Removed confusing `None` batch_size flags, system now uses sensible defaults with per-language overrides
  - **Core Language Policies Support**: Added language_policies field to core TranslationConfig for proper policy injection

### Changed
- Replaced print() statements with proper logging in CLI
- Updated CI workflow to use unified package structure
- Enhanced security scanning with pip-audit integration
- **BREAKING CHANGE**: CLI configuration policy updated - OS environment variables are now ignored for all settings except OPENAI_API_KEY
- **BREAKING CHANGE**: CLI now reads configuration from .env files only (OS env ignored for non-API key settings)
- Repository root reorganized for better maintainability
- **Enhanced TermHandler**: Added tolerant matching for Latin terms (space/hyphen variations, possessives)
- **Improved AI Config**: Added numeric filtering functions and enhanced DNT processing
- **Enhanced Translator**: Added untranslated content detection with micro-context retry mechanism
- **Batch Translation Logic**: Replaced immediate fallback to individual translation with progressive shrinking
- **Reflow Engine**: Enhanced with language-aware orphan rebalancing for better subtitle quality
- **Language Configuration**: Extended `languages.json` with orphan prevention rules and family defaults
- **Language Configuration Version**: Updated `languages.json` from version 1.2 to 1.3 with new policy structure
- **Batch Size Configuration**: Batch sizes are now configured per-language instead of globally, with TR/AZ using size 4 for stability

### Fixed
- SRT writer edge case for empty output directories
- Package structure inconsistencies
- Entry point configuration
- **DNT Term Filtering**: Fixed issue where numeric DNT terms were blocking proper localization
- **Termbase Collisions**: Resolved conflicts between DNT terms and termbase entries
- **Output Transparency**: Fixed lack of visibility into what filtering was applied during translation

### Technical Details
- Progressive shrinking tries smaller sub-batches (e.g., 5→3+2) before falling back to individual translation
- No-orphans protection works across all language families (Latin, CJK, Cyrillic, RTL, Indic)
- Configuration-driven approach allows easy tuning without code changes
- Safe implementation with comprehensive error handling and logging

### Impact
- **Quality**: Eliminates quality cliff when batch translation fails
- **Context**: Preserves natural language flow and context in subtitles
- **Languages**: Improves subtitle quality across all supported languages
- **Performance**: Minimal overhead with significant quality benefits

## [1.0.0] - 2025-01-27

### Added
- Unified package structure with `srt_translator.{core,cli,gui}` subpackages
- CLI entry point with full .env file support
- GUI entry point with PySide6 integration
- Core translation engine with OpenAI integration
- SRT file parsing and writing capabilities
- Multi-language translation support
- Termbase management system
- Batch processing capabilities
- Logging and error handling infrastructure

### Changed
- Refactored from flat layout to organized subpackages
- Updated all internal imports to use new structure
- Modernized packaging with pyproject.toml
- Removed legacy setup.py

### Fixed
- Package installation and import issues
- Entry point configuration
- Asset loading in GUI
- Environment variable handling

## [0.1.0] - 2024-12-01

### Added
- Initial SRT translation functionality
- Basic CLI interface
- Simple GUI with PySide6
- OpenAI API integration
- Basic SRT file handling

### Changed
- Experimental development version

### Fixed
- Basic functionality implementation

---

## Release Notes

### Version 1.0.0
This release candidate represents a major milestone in the SRT Translator project. We've completely restructured the codebase to use a modern, organized package structure that makes the project more maintainable and easier to contribute to.

**Key Improvements:**
- **Unified Package Structure**: All functionality is now organized into logical subpackages (`core`, `cli`, `gui`)
- **Modern Packaging**: Uses `pyproject.toml` instead of `setup.py` for better dependency management
- **Enhanced CLI**: Full .env file support and improved error handling
- **Improved GUI**: Better asset loading and PySide6 integration
- **Better Testing**: Comprehensive test suite with improved coverage

**Breaking Changes:**
- Package import paths have changed from `srt_core.*` to `srt_translator.core.*`
- CLI entry point is now `srt-cli` instead of `run_cli.py`
- GUI entry point is now `srtx` instead of `run_gui.py`

**Migration Guide:**
If you're upgrading from a previous version:
1. Uninstall the old package: `pip uninstall srt-translator`
2. Install the new version: `pip install -e .`
3. Update any scripts to use the new console scripts:
   - Use `srtx` instead of `python run_gui.py`
   - Use `srt-cli` instead of `python run_cli.py`
4. Update import statements if you're using the package programmatically

**Configuration Changes (Breaking):**
- CLI now reads configuration from `.env` files only
- OS environment variables are ignored for all settings except `OPENAI_API_KEY`
- To migrate: Copy `examples/env_example` to `.env` and edit with your values
- API key can still be set via OS environment variable (overrides .env)

### Version 0.1.0
This was the initial experimental release with basic functionality. It served as a proof of concept and foundation for the current version.

---

## Contributing

To add entries to this changelog:

1. **Follow the format**: Use the categories above (Added, Changed, Fixed, etc.)
2. **Be specific**: Describe what changed and why it matters
3. **Link issues**: Reference issue numbers when relevant
4. **User focus**: Write for users, not developers
5. **Keep it current**: Update this file with each release

## Types of Changes

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** in case of vulnerabilities

---

*This changelog is maintained by the SRT Translator development team.*
