# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

### Changed
- Replaced print() statements with proper logging in CLI
- Updated CI workflow to use unified package structure
- Enhanced security scanning with pip-audit integration
- **BREAKING CHANGE**: CLI configuration policy updated - OS environment variables are now ignored for all settings except OPENAI_API_KEY
- **BREAKING CHANGE**: CLI now reads configuration from .env files only (OS env ignored for non-API key settings)
- Repository root reorganized for better maintainability

### Fixed
- SRT writer edge case for empty output directories
- Package structure inconsistencies
- Entry point configuration

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
