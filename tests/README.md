# SRT Translator Tests

This directory contains the test suite for the SRT Translator application.

## Test Structure

```
tests/
├── __init__.py                 # Makes tests a Python package
├── conftest.py                 # Pytest configuration and fixtures
├── test_ai_config_basic.py     # Basic AI configuration tests
├── test_ai_config_integration.py # Integration tests for AI config system
└── gui/                        # GUI component tests
    ├── __init__.py
    ├── test_business_glossary_editor.py
    ├── test_editors_integration.py
    └── test_dnt_terms_editor.py
```

## Running Tests

### All Tests
```bash
python run_tests.py
```

### GUI Tests Only
```bash
python run_tests.py gui
```

### Using pytest directly
```bash
# All tests
pytest tests/ -v

# GUI tests only
pytest tests/gui/ -v

# Specific test file
pytest tests/test_ai_config_integration.py -v
```

## Test Types

### Unit Tests
- **`test_ai_config_basic.py`**: Basic functionality tests for AI configuration
- **`test_ai_config_integration.py`**: Integration tests for the complete AI config system

### GUI Tests
- **`test_business_glossary_editor.py`**: Tests the business glossary editor widget
- **`test_editors_integration.py`**: Tests the integrated editors dialog
- **`test_dnt_terms_editor.py`**: Tests the DNT terms editor widget

## Notes

- GUI tests are standalone applications that can be run directly
- Unit tests use pytest framework
- All tests are designed to run without external dependencies (except for the core application)
- The `conftest.py` file provides common fixtures and configuration 