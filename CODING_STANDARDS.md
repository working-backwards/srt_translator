# Coding Standards and Linting Setup

This document describes the code quality tools and standards used in the SRT Translator project.

## Tools Overview

### Code Formatting
- **Black**: Uncompromising code formatter that follows PEP 8
- **isort**: Import sorting and organization
- **Line length**: 88 characters (Black default)

### Linting
- **pylint**: Comprehensive code analysis (configured with sensible defaults)
- **flake8**: Style guide enforcement
- **mypy**: Static type checking (optional but recommended)

## Quick Start

### 1. Install Development Dependencies

```bash
# Install all development tools
pip install -e .[dev]

# Or install individually
pip install black isort pylint flake8 mypy
```

### 2. Configure Cursor (VS Code)

The project includes `.cursor/settings.json` with optimal configuration for:
- Automatic formatting on save
- Import sorting on save
- Real-time linting
- Type checking

### 3. Run Linting

```bash
# Run all linting checks
python scripts/lint.py

# Auto-fix formatting issues
python scripts/fix_formatting.py

# Fix import order issues
python scripts/fix_imports.py
```

## Code Generation Standards

### Import Order Rules

**ALWAYS follow this exact import order:**

1. **Standard library imports** (alphabetical)
2. **Third-party imports** (alphabetical)
3. **Local/application imports** (alphabetical)
4. **Empty line**
5. **Code begins**

```python
# ✅ CORRECT - Standard library first
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Third-party imports
from dotenv import load_dotenv
import srt

# Local imports
from srt_core.config.settings import SOURCE_LANG
from srt_core.translator.translator import SRTTranslator

# Empty line
# Code begins here
load_dotenv()
```

**❌ NEVER do this:**
```python
# Wrong - imports mixed with code
import logging
logging.basicConfig(level=logging.INFO)

from srt_core.config.settings import SOURCE_LANG  # Import after code!
```

### File Structure Standards

**Every Python file should follow this structure:**

```python
"""
Module docstring (if needed)
"""

# 1. Standard library imports
import os
import sys

# 2. Third-party imports
from dotenv import load_dotenv

# 3. Local imports
from .config import settings

# 4. Empty line
# 5. Module-level constants/variables
DEFAULT_CONFIG = "config.json"

# 6. Functions and classes
def main():
    """Function docstring."""
    pass

class MyClass:
    """Class docstring."""
    pass

# 7. Main execution block
if __name__ == "__main__":
    main()
```

### Function and Class Standards

**Function signatures:**
```python
def translate_file(
    input_filepath: str,
    output_filepath: str,
    target_lang: str,
    batch_size: int = 5,
) -> dict[str, any]:
    """
    Translate an SRT file to the target language.
    
    Args:
        input_filepath: Path to input SRT file
        output_filepath: Path to output SRT file
        target_lang: Target language name
        batch_size: Number of subtitles per batch
        
    Returns:
        Dictionary with translation results
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If target language is invalid
    """
    pass
```

**Class definitions:**
```python
class SRTTranslator:
    """Handles SRT file translation using OpenAI API."""
    
    def __init__(self, source_lang: str = "en", api_key: str | None = None):
        """
        Initialize the translator.
        
        Args:
            source_lang: Source language code
            api_key: OpenAI API key (optional, uses env var if not provided)
        """
        self.source_lang = source_lang
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
```

### Error Handling Standards

**Use specific exceptions:**
```python
# ✅ Good
if not os.path.exists(file_path):
    raise FileNotFoundError(f"File not found: {file_path}")

if not api_key:
    raise ValueError("API key is required")

# ❌ Avoid
if not os.path.exists(file_path):
    raise Exception(f"File not found: {file_path}")
```

**Logging standards:**
```python
import logging

logger = logging.getLogger(__name__)

def process_file(file_path: str) -> None:
    """Process a file with proper logging."""
    logger.info("Starting file processing: %s", file_path)
    
    try:
        # Process file
        logger.debug("File processed successfully")
    except FileNotFoundError:
        logger.error("File not found: %s", file_path)
        raise
    except Exception as e:
        logger.exception("Unexpected error processing file: %s", file_path)
        raise
```

### Type Hints

**Always use type hints for:**
- Function parameters
- Function return values
- Class attributes
- Variable assignments (when not obvious)

```python
from typing import Any, Dict, List, Optional

def get_language_config() -> Dict[str, Dict[str, str]]:
    """Get language configuration."""
    return {"en": {"name": "English"}}

def process_files(files: List[str], config: Optional[Dict[str, Any]] = None) -> bool:
    """Process multiple files."""
    pass
```

### String Formatting

**Use f-strings for most cases:**
```python
# ✅ Preferred
filename = f"{base_name}_{timestamp}.srt"
message = f"Processing {len(files)} files"

# ✅ For logging (performance)
logger.info("Processing %d files", len(files))

# ❌ Avoid
filename = base_name + "_" + timestamp + ".srt"
```

### Configuration and Constants

**Use environment variables for configuration:**
```python
import os
from typing import Final

# Constants
DEFAULT_BATCH_SIZE: Final[int] = 5
SUPPORTED_LANGUAGES: Final[tuple[str, ...]] = ("en", "es", "fr")

# Configuration from environment
BATCH_SIZE = int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
```

## Pre-commit Workflow

### Before Committing Code

1. **Run formatting:**
   ```bash
   python scripts/fix_formatting.py
   ```

2. **Run linting:**
   ```bash
   python scripts/lint.py
   ```

3. **Fix any remaining issues manually**

4. **Commit with descriptive message:**
   ```bash
   git add .
   git commit -m "feat: add new translation feature

   - Add support for batch processing
   - Improve error handling
   - Update documentation"
   ```

### IDE Integration

**Cursor/VS Code settings are configured in `.cursor/settings.json`:**
- Format on save with Black
- Sort imports on save with isort
- Real-time linting with pylint and flake8
- Type checking with mypy

## Common Issues and Solutions

### Import Order Issues (E402)

**Problem:** Imports not at top of file
**Solution:** Move all imports to the top, before any code

### Line Length Issues (E501)

**Problem:** Lines longer than 88 characters
**Solution:** Use Black formatter or break lines manually

### Type Checking Issues

**Problem:** Missing type hints
**Solution:** Add type hints to function signatures and variables

### Pylint Issues

**Common disabled warnings:**
- `C0114`: Missing module docstring
- `C0115`: Missing class docstring  
- `C0116`: Missing function docstring
- `R0903`: Too few public methods
- `W0621`: Redefined outer name (common in tests)

## Testing Standards

**Test file structure:**
```python
"""
Tests for the translator module.
"""

import pytest
from unittest.mock import Mock, patch

from srt_core.translator.translator import SRTTranslator


class TestSRTTranslator:
    """Test cases for SRTTranslator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.translator = SRTTranslator("en")
    
    def test_translate_file_success(self):
        """Test successful file translation."""
        # Test implementation
        pass
    
    def test_translate_file_not_found(self):
        """Test translation with missing file."""
        with pytest.raises(FileNotFoundError):
            self.translator.translate_file("nonexistent.srt", "output.srt", "es")
```

## Documentation Standards

**Docstring format (Google style):**
```python
def complex_function(param1: str, param2: int = 10) -> bool:
    """
    Perform a complex operation.
    
    This function does something very important that requires
    detailed explanation.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter (default: 10)
        
    Returns:
        True if operation succeeded, False otherwise
        
    Raises:
        ValueError: If param1 is empty
        RuntimeError: If operation fails
        
    Example:
        >>> result = complex_function("test", 5)
        >>> print(result)
        True
    """
    pass
```

## Performance Guidelines

**Avoid expensive operations in loops:**
```python
# ❌ Bad - expensive operation in loop
for file_path in files:
    content = open(file_path).read()  # File I/O in loop
    process(content)

# ✅ Good - batch operations
contents = [open(f).read() for f in files]  # Single comprehension
for content in contents:
    process(content)
```

**Use generators for large datasets:**
```python
def process_large_file(file_path: str):
    """Process large file line by line."""
    with open(file_path) as f:
        for line in f:
            yield process_line(line)
```

## Security Guidelines

**Never hardcode sensitive information:**
```python
# ❌ Bad
API_KEY = "sk-1234567890abcdef"

# ✅ Good
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("API key not found in environment")
```

**Validate user input:**
```python
def process_user_input(user_data: str) -> str:
    """Process and validate user input."""
    if not user_data or len(user_data) > 1000:
        raise ValueError("Invalid input data")
    
    # Sanitize input
    sanitized = user_data.strip()
    return sanitized
```

---

**Remember:** These standards ensure code quality, maintainability, and consistency across the project. Always run the linting tools before committing code! 