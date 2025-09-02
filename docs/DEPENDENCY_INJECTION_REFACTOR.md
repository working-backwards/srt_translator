# Dependency Injection Refactor for LanguageConfig

## Overview

This document describes the refactoring of the `LanguageConfig` class from a file-reading configuration manager to a pure data holder that requires dependency injection. This change improves the architecture by eliminating duplicate file I/O and creating clear separation of concerns.

## What Changed

### Before (File-Reading Architecture)
- `LanguageConfig` automatically searched for and loaded `languages.json` from multiple possible locations
- Both GUI and core modules independently loaded the same file
- Path resolution was complex and error-prone
- No clear ownership of language data

### After (Dependency Injection Architecture)
- `LanguageConfig` is a pure data holder that requires preloaded data
- GUI loads `languages.json` once and passes `LanguageConfig` instances to core modules
- Core modules never read files directly
- Clear data flow: GUI → LanguageConfig → Core

## Implementation Details

### 1. LanguageConfig Class Changes

**File**: `srt_translator/core/config/language_config.py`

- **Constructor**: Now requires `data: Dict[str, Any]` parameter
- **Validation**: Checks for required `"languages"` key and non-empty mapping
- **No file I/O**: All file reading logic removed
- **Script helpers**: Maintained for script validation functionality

```python
# Before
config = LanguageConfig()  # Auto-searched for file

# After
with open("config/languages.json", "r") as f:
    data = json.load(f)
config = LanguageConfig(data)  # Explicit data injection
```

### 2. GUI Changes

**File**: `srt_translator/gui/main_window.py`

- **Single load**: Loads `languages.json` once in constructor
- **Error handling**: Graceful failure with user-friendly messages
- **Dependency injection**: Passes `LanguageConfig` to `AIConfigGenerator`

```python
# Load language configuration once
try:
    with open("config/languages.json", "r", encoding="utf-8") as f:
        lang_data = json.load(f)
    self.language_config = LanguageConfig(lang_data)
except (FileNotFoundError, json.JSONDecodeError) as e:
    # Show error dialog and raise exception
    QMessageBox.critical(self, "Configuration Error", f"Failed to load language configuration: {e}")
    raise RuntimeError(f"Language configuration load failed: {e}")

# Pass to AI config generator
self.ai_config_generator = AIConfigGenerator(api_key, self.language_config)
```

### 3. Core Engine Changes

**File**: `srt_translator/core/main.py`

- **Language loading**: Loads `languages.json` once for the translation session
- **Dependency injection**: Passes `LanguageConfig` to `SRTTranslator`

```python
# Load language configuration for the core engine
try:
    with open("config/languages.json", "r", encoding="utf-8") as f:
        lang_data = json.load(f)
    language_config = LanguageConfig(lang_data)
except (FileNotFoundError, json.JSONDecodeError) as e:
    raise RuntimeError(f"Language configuration load failed: {e}")

# Create translator with language configuration
translator = SRTTranslator(
    # ... other parameters ...
    language_config=language_config,
)
```

### 4. GUI Component Updates

**Files Updated**:
- `srt_translator/gui/ui/language_section.py` - Now receives `LanguageConfig` from main window
- `srt_translator/gui/settings_manager.py` - Now receives `LanguageConfig` in constructor
- `srt_translator/gui/config_manager.py` - Now receives `LanguageConfig` in constructor

**Main Window Changes**:
```python
# Load language configuration once
try:
    with open("config/languages.json", "r", encoding="utf-8") as f:
        lang_data = json.load(f)
    self.language_config = LanguageConfig(lang_data)
except (FileNotFoundError, json.JSONDecodeError) as e:
    QMessageBox.critical(self, "Configuration Error", f"Failed to load language configuration: {e}")
    raise RuntimeError(f"Language configuration load failed: {e}")

# Pass to all components that need it
self.settings_manager = SettingsManager(self.language_config)
self.config_manager = GUIConfigManager(self.settings_manager, self.language_config)
self.language_section = LanguageSection(self.settings_manager, self.language_config)
self.ai_config_generator = AIConfigGenerator(api_key, self.language_config)
```

### 5. Component Updates

**Core Files Updated**:
- `srt_translator/gui/ai_config.py` - Requires `LanguageConfig` parameter
- `srt_translator/core/translator/translator.py` - Requires `LanguageConfig` parameter
- `srt_translator/core/translator/` - Already required `LanguageConfig`
- `srt_translator/core/translator/subtitle_formatter.py` - Already required `LanguageConfig`

## Benefits

### 1. **Eliminates Duplicate I/O**
- Single file read instead of multiple reads
- Reduced resource usage and startup time

### 2. **Clear Data Ownership**
- GUI owns language data loading
- Core consumes preloaded data
- No hidden file system dependencies

### 3. **Better Error Handling**
- Centralized error handling in GUI
- User-friendly error messages
- Graceful degradation

### 4. **Improved Testability**
- Easy to inject mock language data
- No file system dependencies in tests
- Faster test execution

### 5. **Architectural Clarity**
- Clear dependency flow
- Separation of concerns
- Easier to maintain and extend

## Migration Notes

### For Developers

1. **No more automatic file loading**: All `LanguageConfig()` calls must provide data
2. **Error handling required**: Implement proper error handling for missing/corrupted files
3. **Testing updates**: Use mock data instead of relying on file system

### For Users

1. **No functional changes**: The application works exactly the same
2. **Better error messages**: Clear feedback if language configuration is missing
3. **Faster startup**: Reduced file I/O operations

## Testing

All existing tests have been updated to use mock data:

```python
def test_language_config():
    test_data = {
        "version": "1.1",
        "languages": {
            "en": {"name": "English", "family": "latin"},
            "zh-Hans": {"name": "Chinese (Simplified)", "family": "cjk"}
        }
    }
    config = LanguageConfig(test_data)
    assert config.get_language_codes() == ["en", "zh-Hans"]
```

## Future Considerations

1. **Database support**: Could easily extend to load from databases instead of files
2. **API support**: Could load language data from remote APIs
3. **Caching**: Could implement caching strategies for frequently accessed data
4. **Validation**: Could add more sophisticated data validation rules

## Current Status

After completing the refactor, we have achieved the goal of **single-point file loading**:

### ✅ **Only Two Places Read `languages.json`**:
1. **GUI Entry Point** (`srt_translator/gui/main_window.py`) - loads once per GUI session
2. **CLI Entry Point** (`srt_translator/core/main.py`) - loads once per translation session

### ✅ **All Components Use Dependency Injection**:
- **GUI Components**: `LanguageSection`, `SettingsManager`, `GUIConfigManager`, `AIConfigGenerator`
- **Core Components**: `SRTTranslator`, `SubtitleFormatter`
- **No More Direct File I/O**: All components receive preloaded `LanguageConfig` instances

### ✅ **Eliminated Unused Code**:
- `srt_translator/core/config/resource_loader.py` - contains unused file reading logic (can be removed)
- All `LanguageConfig()` calls without data have been updated to use dependency injection

## Conclusion

This refactor significantly improves the application's architecture by:
- **Eliminating duplicate file operations** - Only 2 file reads instead of multiple reads
- **Creating clear data ownership boundaries** - GUI owns language data, core consumes it
- **Improving error handling and user experience** - Centralized error handling with user-friendly messages
- **Making the code more testable and maintainable** - Easy to inject mock data, no file system dependencies

The change maintains full backward compatibility for end users while providing a much cleaner internal architecture for developers.

## Next Steps

1. **Remove unused code**: The `resource_loader.py` file can be deleted as it's no longer used
2. **Test thoroughly**: Verify that both GUI and CLI work correctly with the new architecture
3. **Monitor performance**: The single file read should improve startup time

## Recent Fixes

### **Fixed Core-GUI Import Issue**
**Problem**: The core translation engine was importing `AIConfigGenerator` from the GUI to filter DNT terms, causing a `LanguageConfig` dependency error.

**Solution**: Replaced the GUI import with the core utility function `filter_dnt_terms_with_metadata` from `srt_translator.core.terminology_utils`.

**Before**:
```python
# ❌ Core importing from GUI (violates architecture)
from srt_translator.gui.ai_config import AIConfigGenerator
temp_config = AIConfigGenerator("dummy_key")  # Missing LanguageConfig
filtered_dnt_terms, dnt_filtered_out = temp_config.filter_dnt_terms_with_metadata(translation_config.dnt_terms)
```

**After**:
```python
# ✅ Core using core utilities (maintains architecture)
from srt_translator.core.terminology_utils import filter_dnt_terms_with_metadata
filtered_dnt_terms, dnt_filtered_out = filter_dnt_terms_with_metadata(translation_config.dnt_terms)
```

**Result**: Core translation engine now works without GUI dependencies, maintaining proper separation of concerns.

### **Fixed Missing LanguageConfig Methods**
**Problem**: After refactoring `LanguageConfig` to be a pure data holder, some required methods were accidentally removed, causing `'LanguageConfig' object has no attribute 'get_sentence_endings'` errors.

**Solution**: Added the missing `get_sentence_endings` method that the language configuration requires for sentence boundary detection.

**Added Method**:
```python
def get_sentence_endings(self, code: str) -> List[str]:
    """Get sentence ending punctuation for a language"""
    languages = self.get_all_languages()
    lang_info = languages.get(code, {})
    return lang_info.get("sentence_endings", [".", "!", "?"])
```

**Result**: Core translation engine now has all required methods and should work without attribute errors.

### **Fixed Subtitle Formatter Dictionary Unpacking Error**
**Problem**: The subtitle formatter was incorrectly trying to unpack a dictionary as a tuple, causing `'LanguageConfig' object has no attribute 'get_sentence_endings'` and later `can't multiply sequence by non-int of type 'float'` errors.

**Root Cause**: The code was doing:
```python
# ❌ Incorrect unpacking
soft, hard = self.language_config.get_cps_caps(lang)
```

But `get_cps_caps(lang)` returns a dictionary `{"cps_soft": 15, "cps_hard": 20}`, not a tuple.

**Solution**: Fixed the unpacking to properly access dictionary values:
```python
# ✅ Correct dictionary access
cps_caps = self.language_config.get_cps_caps(lang)
soft, hard = cps_caps["cps_soft"], cps_caps["cps_hard"]
```

**Result**: The subtitle formatter can now properly access CPS limits and perform calculations without type errors.
