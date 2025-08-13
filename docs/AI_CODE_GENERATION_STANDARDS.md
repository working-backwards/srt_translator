# AI Code Generation Standards

This document provides specific guidelines for AI-generated code to ensure consistency with the project's coding standards.

## 🎯 **CRITICAL: Always Follow These Rules**

### 0. Core Engine Architecture (NEVER VIOLATE)

**The core engine (`srt_translator/core/`) must follow strict architecture rules:**

- **NEVER import from global settings modules** (`srt_translator.core.config.settings`)
- **NEVER use `os.environ` or `os.getenv` for configuration**
- **NEVER use hardcoded default values for configurable parameters**
- **ONLY read configuration from `TranslationConfig` objects passed as parameters**
- **ALWAYS require complete `TranslationConfig` objects - no Optional config parameters**
- **CRASH with clear error if `TranslationConfig` is missing required fields**
- **A instance cof Translator can only run one batch at a time**

**Correct data flow:**
```
CLI/GUI → TranslationConfig → Core Engine
     ↑           ↑              ↑
  Collects    Contains      ONLY reads
  params      ALL params    from config
```

**Example of CORRECT pattern:**
```python
def translate_srt_files(file_paths: List[str], config: TranslationConfig):
    batch_size = config.batch_size  # Read from config object
    if not config.api_key:
        raise ValueError("TranslationConfig.api_key is required")
```

### 1. Code Quality Tools (MOST IMPORTANT)

**After making any Python code changes, automatically run the project's code quality tools:**

```bash
# 1. Auto-fix formatting issues
python scripts/fix_formatting.py

# 2. Run all quality checks
python scripts/lint.py
```

**What these tools enforce:**
- **Black**: PEP 8 formatting (88 char line length, consistent style)
- **isort**: Import organization and sorting
- **flake8**: Style and error checking  
- **pylint**: Code quality and best practices
- **mypy**: Type checking (optional but recommended)

**Why this approach:**
- Uses your existing project configuration
- No need to remember individual tool commands
- Automatically enforces project-specific standards
- Consistent with existing team workflow

### 2. Import Order (CRITICAL)

**ALWAYS structure imports in this exact order:**

```python
"""
Module docstring (if needed)
"""

# 1. Standard library imports (alphabetical)
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# 2. Third-party imports (alphabetical)
from dotenv import load_dotenv
import srt

# 3. Local imports (alphabetical)
from srt_core.config.settings import SOURCE_LANG
from srt_core.translator.translator import SRTTranslator

# 4. Empty line
# 5. Code begins here
```

**❌ NEVER put imports after code execution:**
```python
# WRONG - Don't do this!
import logging
logging.basicConfig(level=logging.INFO)

from srt_core.config.settings import SOURCE_LANG  # Import after code!
```

### 2. File Structure Template

**Use this exact structure for every new Python file:**

```python
"""
Brief description of the module.
"""

# Standard library imports
import os
import sys

# Third-party imports
from dotenv import load_dotenv

# Local imports
from .config import settings

# Module-level constants
DEFAULT_CONFIG = "config.json"

# Functions and classes
def main():
    """Main function docstring."""
    pass

class MyClass:
    """Class docstring."""
    
    def __init__(self, param: str):
        """Initialize the class."""
        self.param = param

# Main execution
if __name__ == "__main__":
    main()
```

### 3. Function Signatures

**Always include type hints:**

```python
def process_file(
    file_path: str,
    output_dir: str,
    config: dict[str, any] | None = None,
) -> bool:
    """
    Process a file with the given configuration.
    
    Args:
        file_path: Path to the input file
        output_dir: Directory for output files
        config: Optional configuration dictionary
        
    Returns:
        True if processing succeeded, False otherwise
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If configuration is invalid
    """
    pass
```

### 4. Class Definitions

```python
class FileProcessor:
    """Handles file processing operations."""
    
    def __init__(self, config: dict[str, any] | None = None):
        """
        Initialize the file processor.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
    
    def process(self, file_path: str) -> bool:
        """Process a single file."""
        pass
```

### 5. Error Handling

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

### 6. Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_data(data: list[str]) -> None:
    """Process data with proper logging."""
    logger.info("Processing %d items", len(data))
    
    try:
        # Process data
        logger.debug("Data processed successfully")
    except Exception as e:
        logger.exception("Error processing data")
        raise
```


### 7. String Formatting

**Use f-strings:**

```python
# ✅ Preferred
filename = f"{base_name}_{timestamp}.srt"
message = f"Processing {len(files)} files"

# ✅ For logging (performance)
logger.info("Processing %d files", len(files))

# ❌ Avoid
filename = base_name + "_" + timestamp + ".srt"
```

## 🔧 **Quick Reference for Common Patterns**

### File Operations

```python
from pathlib import Path

def read_file(file_path: str) -> str:
    """Read file content safely."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    return path.read_text(encoding="utf-8")

def write_file(file_path: str, content: str) -> None:
    """Write content to file safely."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

### JSON Operations

```python
import json
from typing import Any

def load_json(file_path: str) -> dict[str, Any]:
    """Load JSON file safely."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")

def save_json(file_path: str, data: dict[str, Any]) -> None:
    """Save data to JSON file safely."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
```

### Testing Template

```python
"""
Tests for the module.
"""

import pytest
from unittest.mock import Mock, patch

from srt_core.translator.translator import SRTTranslator


class TestSRTTranslator:
    """Test cases for SRTTranslator."""
    
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

## 🚨 **Common Mistakes to Avoid**

1. **Imports after code execution**
2. **Missing type hints**
3. **Generic Exception handling**
4. **Hardcoded sensitive information**
5. **Missing docstrings**
6. **Inconsistent string formatting**
7. **No error handling**
8. **Missing logging**

## 📋 **Before Submitting Code**

1. **Check import order** - All imports at top
2. **Add type hints** - Every function and variable
3. **Add docstrings** - All public functions and classes
4. **Use specific exceptions** - Not generic Exception
5. **Add logging** - Info for operations, debug for details
6. **Validate inputs** - Check parameters and environment
7. **Handle errors gracefully** - Proper error messages

## 🎯 **Example: Complete File Template**

```python
"""
Module for processing SRT files.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

from srt_core.config.settings import SOURCE_LANG
from srt_core.translator.translator import SRTTranslator

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_BATCH_SIZE = 5
SUPPORTED_FORMATS = (".srt", ".txt")


class SRTProcessor:
    """Handles SRT file processing operations."""
    
    def __init__(self, config: Dict[str, Any] | None = None):
        """
        Initialize the SRT processor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.translator = SRTTranslator(SOURCE_LANG)
    
    def process_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Process multiple SRT files.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Dictionary with processing results
            
        Raises:
            FileNotFoundError: If any file doesn't exist
            ValueError: If configuration is invalid
        """
        logger.info("Processing %d files", len(file_paths))
        
        results = {
            "processed": 0,
            "failed": 0,
            "errors": []
        }
        
        for file_path in file_paths:
            try:
                self._process_single_file(file_path)
                results["processed"] += 1
            except Exception as e:
                logger.error("Failed to process %s: %s", file_path, e)
                results["failed"] += 1
                results["errors"].append(f"{file_path}: {e}")
        
        logger.info("Processing complete: %d processed, %d failed", 
                   results["processed"], results["failed"])
        return results
    
    def _process_single_file(self, file_path: str) -> None:
        """Process a single SRT file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.debug("Processing file: %s", file_path)
        # Processing logic here


def main():
    """Main function."""
    processor = SRTProcessor()
    # Main logic here


if __name__ == "__main__":
    main()
```

---

**Remember:** These standards ensure code quality, maintainability, and consistency. Always follow them when generating new code! 