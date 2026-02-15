# Contributing to SRT Translator

Thank you for your interest in contributing to SRT Translator! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- OpenAI API key (for testing translation features)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/srt_translator.git
   cd srt_translator
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/srt_translator.git
   ```

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install in development mode with all dev dependencies
pip install -e ".[dev]"
```

### 3. Environment Configuration

Copy the example environment file and configure your API key:

```bash
cp env_example .env
# Edit .env with your OpenAI API key and other settings
```

### 4. Verify Installation

```bash
# Test CLI
srt-cli --version

# Test GUI
srtx

# Run tests
pytest
```

## Contributing Guidelines

### Types of Contributions

We welcome various types of contributions:

- **Bug Reports**: Report bugs and issues
- **Feature Requests**: Suggest new features
- **Code Contributions**: Fix bugs, implement features
- **Documentation**: Improve docs, add examples
- **Testing**: Add tests, improve test coverage
- **Localization**: Add new language support

### Before You Start

1. **Check existing issues** to avoid duplicates
2. **Discuss major changes** in an issue before implementing
3. **Keep changes focused** - one feature/fix per pull request
4. **Test thoroughly** before submitting

### Issue Guidelines

When creating an issue:

- Use the appropriate issue template
- Provide clear, reproducible steps
- Include relevant system information
- Add screenshots for GUI issues
- Check if it's already reported

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Import sorting**: Use `isort` with Black profile
- **Type hints**: Use type hints for public APIs
- **Docstrings**: Use Google-style docstrings

### Automated Formatting

- Run Ruff locally (fixes what it can, flags what matters):
  ```bash
  ruff check --select E,F,I,B,TID,G,ARG,UP --fix .
  ```
  - `G` forbids f-strings/formatting in logger calls.
  - `ARG` flags unused function parameters (prefix with `_` if required by an interface).
  - `UP` keeps syntax modern (pyupgrade).

# Type checking
mypy srt_translator/

# Security scanning
bandit -r srt_translator/
safety check --full-report

### Pre-commit Hooks

Install pre-commit hooks for automatic formatting and quality checks:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Run on all files initially
```

The pre-commit hooks will automatically:
- Format code with Ruff
- Fix linting issues (including G/ARG/UP rules)
- Run type checking
- Scan for security issues (Bandit + Safety)
- Ensure consistent code quality across all commits

## Evaluation System Guardrails

### Core Principle
The evaluation system must be **completely independent** of the translation runtime. It reads only batch artifacts to ensure reproducibility and decoupling.

### Critical Rules (NEVER VIOLATE)

#### ❌ FORBIDDEN
- **Do NOT import or pass `TranslationConfig` objects into evaluation code**
- **Do NOT depend on runtime state or environment variables**
- **Do NOT create fallbacks to legacy summary files**

#### ✅ REQUIRED
- **Evaluation must be reproducible from batch folder alone**
- **Read only from `ai_config.json` and SRT files on disk**
- **Any new evaluation checks must document the exact `ai_config.json` keys they consume**

### Implementation Requirements

#### Input Sources
- **Primary**: `batch_root/ai_config.json` (configuration snapshot)
- **Required**: `batch_root/originals/` and `batch_root/targets/<lang>/` (SRT files)
- **Optional**: DNT terms and termbases inside `ai_config.json`

#### Data Normalization
- **DNT terms**: `dnt_terms: [str, ...]` → list of strings
- **Termbases**: `termbase: {lang: {src: tgt}}` → per-language list of {source, target} pairs

#### Error Handling
- **Required inputs missing** → ERROR and STOP evaluation
- **Optional inputs missing** → INFO log and CONTINUE evaluation

### Why These Rules Matter
- **Reproducibility**: Evaluation can be re-run on old batches
- **Decoupling**: Changes to translation config don't affect evaluation
- **Auditability**: Complete configuration snapshot preserved in batch
- **Debugging**: Evaluation failures are clearly traceable to missing files

### Testing the Rules
When adding evaluation functionality, ensure:
- [ ] No imports from `srt_translator.core.config.models`
- [ ] No dependency on `TranslationConfig` objects
- [ ] All inputs read from batch directory files
- [ ] Clear documentation of required `ai_config.json` keys
- [ ] Tests pass with only batch artifacts (no runtime config)

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=srt_translator --cov-report=html

# Run specific test file
pytest tests/test_specific.py

# Run with verbose output
pytest -v
```

### Test Guidelines

- **Test coverage**: Aim for 70%+ coverage
- **Test isolation**: Each test should be independent
- **Mock external services**: Don't make real API calls in tests
- **Test edge cases**: Include error conditions and boundary cases
- **Use fixtures**: Leverage pytest fixtures for common setup

### Adding New Tests

When adding new functionality:

1. Write tests first (TDD approach)
2. Test both success and failure cases
3. Test edge cases and error conditions
4. Ensure tests are fast and reliable

## Submitting Changes

### Commit Guidelines

Use conventional commit messages:

```
type(scope): description

feat(cli): add --version flag
fix(gui): resolve asset loading issue
docs(readme): update installation instructions
test(core): add edge case tests for SRT parser
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Process

1. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the guidelines above

3. **Test thoroughly**:
   ```bash
   pytest
   ruff check --select E,F,I,B,TID,G,ARG,UP --fix .
   ```

4. **Commit your changes** with clear messages

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a pull request**:
   - Use the PR template
   - Describe changes clearly
   - Link related issues
   - Request review from maintainers

### PR Review Process

- **Code review**: All PRs require review
- **CI checks**: Must pass all automated checks
- **Test coverage**: Should maintain or improve coverage
- **Documentation**: Update docs for new features

## Release Process

### Release Candidates

1. **Create release branch** from `develop`
2. **Update version** in `srt_translator/__init__.py`
3. **Run full test suite** on all supported platforms
4. **Create release candidate** tag
5. **Test installation** from PyPI test index

### Final Release

1. **Merge to main** after RC testing
2. **Create release tag** (e.g., `v1.0.0`)
3. **Build and publish** to PyPI
4. **Update changelog** with release notes
5. **Announce release** to community

## Getting Help

If you need help:

- **Check documentation**: README, INSTALLATION.md, etc.
- **Search issues**: Look for similar problems
- **Ask questions**: Create an issue with the "question" label
- **Join discussions**: Participate in issue comments

## Recognition

Contributors are recognized in:

- **README.md**: Major contributors
- **CHANGELOG.md**: Individual contributions
- **GitHub contributors**: Automatic recognition
- **Release notes**: Feature and fix acknowledgments

Thank you for contributing to SRT Translator! 🚀
