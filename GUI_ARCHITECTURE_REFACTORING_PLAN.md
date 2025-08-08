# SRT Translator GUI Architecture Refactoring Plan

## Problem Statement

The SRT Translator GUI is experiencing critical bugs due to improper use of environment variables for runtime state management. The application was designed for CLI-first architecture but the GUI was implemented by bolting environment variable updates onto the existing CLI code path, creating timing dependencies and state management issues.

### Current Issues

1. **Language Selection Bug**: Translation uses all 12 languages instead of user-selected languages
2. **Termbase Lookup Bug**: Translation worker cannot find AI-generated termbase for selected languages
3. **State Management Inconsistency**: GUI displays correct data but backend processes cannot access it
4. **Thread Safety Issues**: Background worker threads updating GUI without proper Qt signaling
5. **State Fragmentation**: Configuration scattered across multiple components without single source of truth

### Root Cause Analysis

The GUI incorrectly uses environment variables as a crude form of inter-process communication:

```
User Action → UI Updates Environment Variables → Worker Reads Environment Variables → Translation
```

This creates:
- **Timing dependencies**: Environment variables read at import time vs runtime updates
- **Thread safety issues**: Multiple threads modifying global state
- **Debugging difficulties**: Impossible to trace state flow
- **Architectural mismatch**: CLI patterns forced into GUI context
- **State fragmentation**: No single source of truth for configuration

## Current Architecture (Broken)

### GUI Flow
```
User selects languages → UI updates TARGET_LANGUAGES env var → TranslationWorker updates env var again → srt_core reads env var at import time → Uses wrong languages
```

### Termbase Flow  
```
AI generates termbase (language codes) → Settings manager stores termbase → GUI editor displays correctly → TranslationWorker calls get_termbase(language_names) → Lookup fails
```

### State Management Flow (Broken)
```
GUI Widgets ↔ Environment Variables ↔ SettingsManager ↔ TranslationWorker ↔ srt_core
(No single source of truth, state scattered across components)
```

## Proposed Solution

### Target Architecture (Correct)

#### GUI Flow
```
User selects languages → UI maintains internal state → Pass state directly to TranslationWorker → Pass to translation functions as parameters
```

#### Termbase Flow
```
AI generates termbase → Settings manager stores termbase → GUI loads termbase → TranslationWorker receives termbase directly → Translation functions receive termbase as parameter
```

#### State Management Flow (Fixed)
```
SettingsManager (Single Source of Truth)
    ↓
GUI Widgets (Read/Write via SettingsManager)
    ↓
TranslationWorker (Receives state from SettingsManager)
    ↓
SRTTranslator (Receives all config as parameters)
```

### Key Principles

1. **No environment variables for runtime GUI state**
2. **Direct parameter passing between components**
3. **Clear separation between GUI and CLI code paths**
4. **Environment variables only for startup configuration and CLI mode**
5. **SettingsManager as single source of truth for all GUI state**
6. **Thread-safe communication via Qt signals/slots**
7. **Structured logging with session context for debugging**
8. **Immutable state objects with validation for reliability**

## Detailed Implementation Plan

### Phase 1: Foundation (Critical) - State Management and Thread Safety

#### Files to Modify

**1. `gui/settings_manager.py`**
- **Function**: Add state management as single source of truth
- **Change**: Implement centralized state management with thread-safe access
- **Risk**: Medium - changes core state management
- **Test**: Verify state consistency across all components

**2. `gui/workers/translation_worker.py`**
- **Function**: `run()` method and thread communication
- **Change**: Use Qt signals for all GUI updates, receive state from SettingsManager
- **Risk**: Medium - changes thread communication patterns
- **Test**: Verify thread safety and proper GUI updates

**3. `srt_core/main.py` ✅ COMPLETED**
- **Function**: `translate_srt_files()`
- **Change**: ✅ Added `target_languages` parameter with default fallback to environment variable
- **Risk**: Low - maintains backward compatibility for CLI
- **Test**: Verify CLI still works, GUI passes correct languages

**4. `gui/main_window.py`**
- **Function**: Language selection and state synchronization
- **Change**: Update language selection to use SettingsManager as single source of truth
- **Risk**: Low - improves state management
- **Test**: Verify language selection persists and syncs correctly

#### Code Changes Required

```python
# gui/settings_manager.py
class SettingsManager:
    def __init__(self):
        self._current_target_languages = {}
        self._current_dnt_terms = []
        self._current_termbase = {}
        self._lock = threading.Lock()
    
    def get_current_target_languages(self) -> Dict[str, str]:
        """Get current language selection from UI state (thread-safe)"""
        with self._lock:
            return self._current_target_languages.copy()
    
    def update_target_languages(self, languages: Dict[str, str]):
        """Update both UI state and persistent storage (thread-safe)"""
        with self._lock:
            self._current_target_languages = languages.copy()
        self.save_target_languages(languages)
    
    def get_current_dnt_terms(self) -> List[str]:
        """Get current DNT terms (thread-safe)"""
        with self._lock:
            return self._current_dnt_terms.copy()
    
    def get_current_termbase(self) -> Dict[str, Dict[str, str]]:
        """Get current termbase (thread-safe)"""
        with self._lock:
            return self._current_termbase.copy()

# gui/workers/translation_worker.py
class TranslationWorker(QThread):
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings_manager = settings_manager
        self.session_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"translation.{self.session_id}")
    
    def run(self):
        try:
            # Get state from single source of truth
            config_state = self.settings_manager.get_current_state()
            
            # Log translation session start
            self.logger.info(f"Starting translation session {self.session_id}")
            self.logger.info(f"Target languages: {list(config_state.target_languages.keys())}")
            self.logger.info(f"DNT terms count: {len(config_state.dnt_terms)}")
            self.logger.info(f"Termbase languages: {list(config_state.termbase.keys())}")
            
            # Emit progress via signal (thread-safe)
            self.progress_updated.emit(f"Starting translation to {len(config_state.target_languages)} languages")
            
            # Call translation with direct parameters
            results = translate_srt_files(
                file_paths=self.selected_files,
                target_languages=config_state.target_languages
            )
            
            # Emit completion via signal
            self.translation_completed.emit(results)
            
        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)

# srt_core/main.py
def translate_srt_files(file_paths=None, target_languages=None):
    """Translate SRT files. If target_languages is None, use environment variable."""
    if target_languages is None:
        target_languages = TARGET_LANGUAGES  # Fallback for CLI
    
    # Log language configuration information
    logging.info(f"Source language: {SOURCE_LANG}")
    logging.info(f"Target languages: {len(target_languages)} languages configured")
    if len(target_languages) <= 10:
        logging.info(f"Languages: {', '.join(target_languages.keys())}")
    else:
        popular_langs = language_config.get_popular_languages()
        logging.info(f"Popular languages: {', '.join(popular_langs)}")
        logging.info(f"Total available languages: {len(target_languages)}")
    
    # Use target_languages parameter instead of global TARGET_LANGUAGES
    for lang_name, lang_code in target_languages.items():
        # ... rest of function unchanged
```

### Phase 2: Core Translation (Medium Risk) - Termbase and Error Handling

#### Files to Modify

**1. `gui/config_manager.py`**
- **Function**: `get_termbase()`
- **Change**: Add language name to code mapping logic with proper error handling
- **Risk**: Medium - changes lookup behavior
- **Test**: Verify termbase found for both language names and codes

**2. `gui/workers/translation_worker.py`**
- **Function**: `setup_ai_configuration()`
- **Change**: Pass termbase directly to translation functions instead of writing to file
- **Risk**: Medium - changes how termbase is provided to translation
- **Test**: Verify termbase is used correctly during translation

**3. `srt_core/translator/translator.py`**
- **Function**: `SRTTranslator.__init__()` and translation methods
- **Change**: Accept termbase and DNT terms as parameters with dependency injection
- **Risk**: Medium - changes public API
- **Test**: Verify translation quality with direct parameters

#### Code Changes Required

```python
# gui/config_manager.py
def get_termbase(self, target_language: str) -> Dict[str, str]:
    """Get termbase for a specific language (name or code)."""
    # Try direct lookup first
    _, ai_termbase = self.settings_manager.load_ai_config()
    if target_language in ai_termbase:
        self.logger.info(f"Using AI-generated termbase for {target_language}")
        return ai_termbase[target_language]
    
    # Try language name to code mapping
    try:
        from srt_core.config.language_config import language_config
        all_languages = language_config.get_all_languages()
        
        for code, lang_info in all_languages.items():
            if lang_info.get('name') == target_language:
                if code in ai_termbase:
                    self.logger.info(f"Using AI-generated termbase for {target_language} (code: {code})")
                    return ai_termbase[code]
    except Exception as e:
        self.logger.debug(f"Error checking language mapping: {e}")
        pass
    
    # Priority 2: Manual termbase.json fallback
    manual_termbase = self._load_termbase_from_file()
    if target_language in manual_termbase and manual_termbase[target_language]:
        self.logger.info(f"Using termbase from file for {target_language}")
        return manual_termbase[target_language]

    # Priority 3: Built-in defaults
    if target_language in self.DEFAULT_TERMBASE:
        self.logger.info(f"Using default termbase for {target_language}")
        return self.DEFAULT_TERMBASE[target_language].copy()

    # No termbase available for this language
    self.logger.warning(f"No termbase available for {target_language}")
    return {}

# srt_core/translator/translator.py
class SRTTranslator:
    def __init__(self, source_lang='en', dnt_terms=None, termbase=None, logger=None):
        self.source_lang = source_lang
        self.dnt_terms = dnt_terms or []
        self.termbase = termbase or {}
        self.logger = logger or logging.getLogger(__name__)
    
    def translate_file(self, input_filepath, output_filepath, target_lang, 
                      dnt_terms=None, termbase=None):
        # Use passed parameters or fall back to instance variables
        dnt_terms = dnt_terms or self.dnt_terms
        termbase = termbase or self.termbase
        
        self.logger.info(f"Translating {input_filepath} to {target_lang}")
        self.logger.info(f"Using {len(dnt_terms)} DNT terms and {len(termbase)} termbase entries")
        
        # ... rest of method
```

### Phase 3: Clean Architecture (Critical) - Environment Variable Elimination and Config Resolver

#### Files to Modify

**1. `srt_core/config/translation_config.py` (NEW FILE)**
- **Function**: Create configuration abstraction layer
- **Change**: Implement `TranslationConfig` dataclass and builder functions
- **Risk**: Medium - new module, but isolated functionality
- **Test**: Verify configuration builders work correctly

**2. `srt_core/config/config_resolver.py` (NEW FILE)**
- **Function**: Create dedicated config resolver for CLI mode
- **Change**: Centralize all environment variable lookups for CLI mode only
- **Risk**: Medium - new module, but isolated functionality
- **Test**: Verify CLI mode works correctly with new resolver

**3. `srt_core/translator/translator.py`**
- **Function**: Remove all environment variable lookups
- **Change**: Accept all configuration as explicit parameters
- **Risk**: High - major API change
- **Test**: Verify GUI and CLI both work with explicit parameters

**4. `srt_core/main.py`**
- **Function**: `translate_srt_files()` and CLI entry point
- **Change**: Use config resolver for CLI mode, explicit parameters for GUI
- **Risk**: Medium - changes CLI behavior
- **Test**: Verify CLI compatibility and GUI parameter passing

**5. `gui/workers/translation_worker.py`**
- **Function**: `prepare_translation_environment()`
- **Change**: Remove environment variable updates, pass configuration directly
- **Risk**: High - major architectural change
- **Test**: Verify all configuration is passed correctly

**6. `srt_core/config/settings.py`**
- **Function**: Deprecate environment variable functions
- **Change**: Keep for backward compatibility but mark as deprecated
- **Risk**: Low - maintains backward compatibility
- **Test**: Verify CLI still works, GUI uses parameters

**7. `srt_core/translator/srt_parser.py`**
- **Function**: Remove any environment variable dependencies
- **Change**: Accept configuration as explicit parameters
- **Risk**: Medium - changes parsing behavior
- **Test**: Verify parsing works with injected configuration

**8. `srt_core/translator/fixer.py`**
- **Function**: Remove any environment variable dependencies
- **Change**: Accept configuration as explicit parameters
- **Risk**: Medium - changes fixing behavior
- **Test**: Verify fixing works with injected configuration

**9. `srt_core/translator/term_handler.py`**
- **Function**: Remove any environment variable dependencies
- **Change**: Accept configuration as explicit parameters
- **Risk**: Medium - changes term handling behavior
- **Test**: Verify term handling works with injected configuration

#### Code Changes Required

```python
# srt_core/config/translation_config.py (NEW FILE)
"""Configuration abstraction layer for translation system"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import os

@dataclass
class TranslationConfig:
    """Immutable translation configuration with validation"""
    target_languages: Dict[str, str]
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    source_lang: str = 'en'
    output_directory: str = 'translated_srt_files'
    api_key: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration integrity"""
        if not self.target_languages:
            raise ValueError("At least one target language required")
        if not isinstance(self.dnt_terms, list):
            raise ValueError("dnt_terms must be a list")
        if not isinstance(self.termbase, dict):
            raise ValueError("termbase must be a dictionary")

def build_config_from_gui(settings_manager) -> TranslationConfig:
    """Build configuration from GUI settings manager"""
    return TranslationConfig(
        target_languages=settings_manager.get_current_target_languages(),
        dnt_terms=settings_manager.get_current_dnt_terms(),
        termbase=settings_manager.get_current_termbase(),
        api_key=settings_manager.get_api_key()
    )

def build_config_from_cli(env_file_path: Optional[str] = None) -> TranslationConfig:
    """Build configuration from CLI environment variables"""
    # Load from environment variables
    target_languages_str = os.getenv('TARGET_LANGUAGES', '{}')
    dnt_terms_str = os.getenv('DNT_TERMS', '[]')
    termbase_str = os.getenv('TERMBASE', '{}')
    
    try:
        target_languages = json.loads(target_languages_str)
        dnt_terms = json.loads(dnt_terms_str)
        termbase = json.loads(termbase_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid environment variable format: {e}")
    
    return TranslationConfig(
        target_languages=target_languages,
        dnt_terms=dnt_terms,
        termbase=termbase,
        source_lang=os.getenv('SOURCE_LANG', 'en'),
        output_directory=os.getenv('OUTPUT_DIRECTORY', 'translated_srt_files'),
        api_key=os.getenv('OPENAI_API_KEY')
    )

# srt_core/config/config_resolver.py (NEW FILE)
"""Configuration resolver for CLI mode - centralizes all environment variable lookups"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class CLIConfig:
    """Configuration for CLI mode loaded from environment variables"""
    target_languages: Dict[str, str]
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    api_key: str
    output_directory: str
    source_lang: str
    source_dir: str
    
    @classmethod
    def from_environment(cls) -> 'CLIConfig':
        """Load configuration from environment variables (CLI mode only)"""
        # Validate required environment variables
        required_vars = ['OPENAI_API_KEY', 'TARGET_LANGUAGES', 'SOURCE_LANG']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {missing_vars}")
        
        # Load target languages from environment
        target_languages_str = os.getenv('TARGET_LANGUAGES', '{}')
        try:
            import json
            target_languages = json.loads(target_languages_str)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid TARGET_LANGUAGES format: {target_languages_str}")
        
        # Load DNT terms from environment
        dnt_terms_str = os.getenv('DNT_TERMS', '[]')
        try:
            dnt_terms = json.loads(dnt_terms_str)
        except json.JSONDecodeError:
            logging.warning(f"Invalid DNT_TERMS format, using empty list: {dnt_terms_str}")
            dnt_terms = []
        
        # Load termbase from environment (if available)
        termbase_str = os.getenv('TERMBASE', '{}')
        try:
            termbase = json.loads(termbase_str)
        except json.JSONDecodeError:
            logging.warning(f"Invalid TERMBASE format, using empty dict: {termbase_str}")
            termbase = {}
        
        return cls(
            target_languages=target_languages,
            dnt_terms=dnt_terms,
            termbase=termbase,
            api_key=os.getenv('OPENAI_API_KEY'),
            output_directory=os.getenv('OUTPUT_DIRECTORY', 'translated_srt_files'),
            source_lang=os.getenv('SOURCE_LANG', 'en'),
            source_dir=os.getenv('SOURCE_DIR', 'original_captions')
        )

class ConfigResolver:
    """Resolves configuration for different modes (CLI vs GUI)"""
    
    @staticmethod
    def get_cli_config() -> CLIConfig:
        """Get configuration for CLI mode from environment variables"""
        return CLIConfig.from_environment()
    
    @staticmethod
    def is_cli_mode() -> bool:
        """Determine if running in CLI mode"""
        return os.getenv('GUI_MODE') != 'true'
    
    @staticmethod
    def validate_cli_config(config: CLIConfig) -> List[str]:
        """Validate CLI configuration and return list of issues"""
        issues = []
        
        if not config.target_languages:
            issues.append("No target languages configured")
        
        if not config.api_key:
            issues.append("No OpenAI API key configured")
        
        if not os.path.exists(config.source_dir):
            issues.append(f"Source directory does not exist: {config.source_dir}")
        
        return issues

# srt_core/translator/translator.py
class SRTTranslator:
    def __init__(self, config: TranslationConfig):
        """Initialize with explicit configuration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Validate configuration
        if not config.api_key:
            raise ValueError("API key required for translation")
    
    def translate_file(self, input_filepath: str, output_filepath: str, target_lang: str):
        """Translate file using configuration"""
        self.logger.info(f"Translating {input_filepath} to {target_lang}")
        self.logger.info(f"Using {len(self.config.dnt_terms)} DNT terms")
        self.logger.info(f"Using termbase with {len(self.config.termbase)} languages")
        
        # Use self.config.target_languages, self.config.dnt_terms, etc.
        # No environment variable lookups anywhere

# srt_core/main.py
from srt_core.config.translation_config import TranslationConfig, build_config_from_cli

def translate_srt_files(file_paths=None, config: TranslationConfig = None):
    """Translate SRT files with explicit configuration."""
    
    if config is None:
        # CLI mode: build configuration from environment
        config = build_config_from_cli()
    
    # Log configuration information
    logging.info(f"Source language: {config.source_lang}")
    logging.info(f"Target languages: {len(config.target_languages)} languages configured")
    if len(config.target_languages) <= 10:
        logging.info(f"Languages: {', '.join(config.target_languages.keys())}")
    
    # Use configuration for translation
    for lang_name, lang_code in config.target_languages.items():
        # ... rest of function using config

# gui/workers/translation_worker.py
def run(self):
    try:
        # Build configuration from GUI state
        config = build_config_from_gui(self.settings_manager)
        
        # Pass configuration to translation
        results = translate_srt_files(
            file_paths=self.selected_files,
            config=config
        )
        
        self.translation_completed.emit(results)
    except Exception as e:
        self.error_occurred.emit(str(e))
```

## Risk Assessment

### High Risk Changes
1. **Eliminating environment variable dependencies**: Could break CLI mode if not handled carefully
2. **Changing TranslationWorker architecture**: Major refactoring of core translation flow
3. **Creating ConfigResolver module**: New architectural component that must be properly integrated
4. **Comprehensive environment variable audit**: Risk of missing `os.getenv()` calls in core modules

### Risk Mitigation Strategy

**For Environment Variable Removal:**
1. **Comprehensive Audit**: Use static analysis tools to find all `os.getenv()` calls
2. **Gradual Migration**: Remove environment variables one module at a time
3. **Dual Mode Support**: Keep environment variable fallbacks during transition
4. **Extensive Testing**: Test both CLI and GUI modes after each change
5. **Rollback Plan**: Keep environment variable code as fallback until fully tested

### Medium Risk Changes  
1. **Modifying termbase lookup logic**: Could affect translation quality if mapping fails
2. **Changing SRTTranslator API**: Could break existing integrations
3. **Implementing centralized state management**: Could introduce new bugs if not properly synchronized
4. **Adding thread safety**: Could introduce deadlocks or race conditions if not properly implemented
5. **Removing environment variable lookups from translator.py**: Could break existing CLI usage patterns

### Low Risk Changes
1. **Adding parameters to translate_srt_files()**: Backward compatible
2. **Adding fallback logic to config_manager**: Maintains existing behavior
3. **Adding structured logging**: Improves debugging without affecting functionality

## Test Plan

### Unit Tests
1. **State Management Test**
   - Test SettingsManager thread safety
   - Test state consistency across components
   - Test state persistence and restoration

2. **Thread Safety Test**
   - Test TranslationWorker signal emission
   - Test GUI updates from background threads
   - Test concurrent state access

3. **Language Selection Test**
   - Select 3 languages in GUI
   - Start translation
   - Verify only 3 languages are processed
   - Verify correct language codes are used
   - **Test with names only** (e.g. "French") — verify it normalizes to "fr"
   - **Test with mixed inputs** ("German": "de", "Japanese": "ja") — verify consistent output
   - **Test with invalid language name** — verify warning is logged and language is skipped

4. **Termbase Lookup Test**
   - Generate AI termbase
   - Verify GUI displays termbase correctly
   - Start translation
   - Verify termbase is found for all selected languages
   - Verify termbase is used during translation

5. **CLI Compatibility Test**
   - Set environment variables
   - Run CLI translation
   - Verify CLI still works correctly
   - Verify no regression in CLI functionality

6. **Environment Variable Isolation Test**
   - Test that GUI mode never reads environment variables
   - Test that CLI mode uses ConfigResolver correctly
   - Test that all modules accept explicit parameters
   - Test that no `os.getenv()` calls exist in GUI code paths

### Integration Tests
1. **End-to-End GUI Test**
   - Select files, languages, generate AI config
   - Start translation
   - Verify all components work together
   - Verify translation quality is maintained

2. **State Persistence Test**
   - Generate AI config
   - Close and reopen GUI
   - Verify AI config is still available
   - Verify termbase editor shows correct data

3. **Error Handling Test**
   - Test translation with missing termbase
   - Test translation with network errors
   - Test translation with invalid language codes
   - Verify proper error messages in GUI

### Performance Tests
1. **Translation Speed Test**
   - Compare translation speed before and after changes
   - Verify no significant performance regression

2. **Memory Usage Test**
   - Monitor memory usage during translation
   - Verify no memory leaks from new architecture

3. **Thread Safety Test**
   - Test concurrent translation sessions
   - Test rapid language selection changes
   - Test GUI responsiveness during translation

## Success Criteria

1. **Language Selection**: Translation uses exactly the languages selected in GUI
2. **Termbase Access**: Translation worker can access AI-generated termbase for all selected languages
3. **CLI Compatibility**: CLI mode continues to work without changes
4. **Performance**: No significant performance regression
5. **User Experience**: No visible changes to GUI functionality
6. **Thread Safety**: No crashes or race conditions during translation
7. **State Consistency**: All components use same state source
8. **Error Handling**: Clear error messages for all failure scenarios
9. **Debugging**: Structured logs enable easy problem diagnosis

## Rollback Plan

If issues arise:
1. **Immediate rollback**: Revert to current environment variable approach
2. **Partial rollback**: Keep language selection fix, revert termbase changes
3. **Gradual rollout**: Implement changes in phases with testing between each phase
4. **State management rollback**: Revert to environment variable state management if centralized approach fails

## Timeline Estimate

- **Phase 1 (Foundation)**: 3-4 days (increased due to state management and thread safety)
- **Phase 2 (Core Translation)**: 2-3 days  
- **Phase 3 (Clean Architecture)**: 3-5 days
- **Testing and Validation**: 3-4 days (increased due to thread safety testing)
- **Total**: 11-16 days

## Next Steps

1. **Review and approve this plan**
2. **Implement Phase 1** (critical foundation)
3. **Test Phase 1 thoroughly** (especially thread safety)
4. **Implement Phase 2** if Phase 1 is successful
5. **Consider Phase 3** based on Phase 2 results

## Simplified Architectural Recommendations

Based on the principle of **simplicity and reliability**, the following recommendations have been evaluated and prioritized:

### ✅ **RECOMMENDED: Language Normalization (Centralized in Config)**

**Why this is essential:**
- **Prevents mismatches** between "Japanese" vs "ja" across translation, termbase, logging, and output directories
- **Eliminates silent translation skips** and lookup failures
- **Removes duplicated normalization logic** across the pipeline
- **Ensures consistency** everywhere language identifiers are used

**Updated Implementation:**
Centralize normalization in the `TranslationConfig` dataclass:

```python
# srt_core/config/translation_config.py

from srt_core.config.language_config import language_config

@dataclass
class TranslationConfig:
    target_languages: Dict[str, str]  # language_name or code → code
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    source_lang: str = 'en'
    output_directory: str = 'translated_srt_files'
    api_key: Optional[str] = None
    logger: Optional[logging.Logger] = None

    def __post_init__(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        # Normalize all target_languages to language codes once
        normalized = {}
        for name_or_code, code in self.target_languages.items():
            norm_code = language_config.normalize_to_code(name_or_code)
            if norm_code:
                normalized[name_or_code] = norm_code
            else:
                self.logger.warning(f"Unrecognized language identifier: {name_or_code}")
        self.target_languages = normalized

        if not self.target_languages:
            raise ValueError("At least one valid target language required")
```

Add this utility method inside `language_config` if not already present:

```python
# srt_core/config/language_config.py

def normalize_to_code(identifier: str) -> Optional[str]:
    """Normalize language name or code to standard ISO code"""
    name_map = get_language_names()  # e.g., {'ja': 'Japanese'}
    reversed_map = {v.lower(): k for k, v in name_map.items()}
    if identifier.lower() in reversed_map:
        return reversed_map[identifier.lower()]
    if identifier in name_map:
        return identifier
    return None
```

**Benefits of This Approach:**
- **All components** (GUI, CLI, translator) now receive language codes only — consistent everywhere
- **Termbase lookups, logs, filenames, translation prompts** will be correct
- **Bug risk eliminated** from inconsistent dictionary keys or naming mismatches
- **Single point of normalization** - no scattered logic throughout codebase
- **Validation at config creation** - catch issues early with clear error messages

**Impact:** Centralized fix that eliminates bugs and ensures consistency.

### **🟢 Minor Engineering Suggestions (Optional)**

These are minor improvements that enhance reliability and debugging without changing the core architecture:

#### **1. Normalize source_lang in TranslationConfig**

**Why:** Prevents errors during prompt construction when source language is inconsistent.

**Implementation:**
```python
def __post_init__(self):
    if self.logger is None:
        self.logger = logging.getLogger(__name__)

    # Normalize source language
    self.source_lang = language_config.normalize_to_code(self.source_lang) or self.source_lang

    # Normalize all target_languages to language codes once
    normalized = {}
    for name_or_code, code in self.target_languages.items():
        norm_code = language_config.normalize_to_code(name_or_code)
        if norm_code:
            normalized[name_or_code] = norm_code
        else:
            self.logger.warning(f"Unrecognized language identifier: {name_or_code}")
    self.target_languages = normalized

    if not self.target_languages:
        raise ValueError("At least one valid target language required")
```

#### **2. Log TranslationConfig on Construction**

**Why:** Makes debugging translation failures easier by providing clear configuration summary.

**Implementation:**
```python
def to_log_string(self):
    """Return a concise string representation for logging"""
    return f"Languages: {list(self.target_languages.values())}, DNT: {len(self.dnt_terms)}, Termbase: {list(self.termbase.keys())}"

def __post_init__(self):
    # ... existing normalization logic ...
    
    # Log configuration summary
    self.logger.info(f"TranslationConfig created: {self.to_log_string()}")
```

#### **3. Assert GUI never uses ConfigResolver**

**Why:** Defensive programming to prevent accidental mixing of GUI and CLI code paths.

**Implementation:**
```python
def build_config_from_gui(settings_manager) -> TranslationConfig:
    """Build configuration from GUI settings manager"""
    # Defensive check to prevent CLI/GUI code path mixing
    assert os.getenv("GUI_MODE") != "false", "build_config_from_gui() should never run in CLI mode"
    
    return TranslationConfig(
        target_languages=settings_manager.get_current_target_languages(),
        dnt_terms=settings_manager.get_current_dnt_terms(),
        termbase=settings_manager.get_current_termbase(),
        api_key=settings_manager.get_api_key()
    )
```

**Impact:** These are minor enhancements that improve reliability and debugging without changing the core architecture.

### ✅ **RECOMMENDED: Logger Injection (Phase 1 Priority)**

**Why it's good:**
- **Fixes real debugging problems** - you can't control logging in tests
- **Makes testing simpler** - no more global logger state
- **Improves reliability** - better error tracking and debugging
- **Minimal complexity** - just pass logger as parameter

**Implementation:**
```python
# Updated TranslationConfig with injected logger
@dataclass
class TranslationConfig:
    target_languages: Dict[str, str]
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    logger: Optional[logging.Logger] = None  # Simple injection
    
    def __post_init__(self):
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

# Usage in SRTTranslator
class SRTTranslator:
    def __init__(self, config: TranslationConfig):
        self.config = config
        self.logger = config.logger  # Use injected logger
```

**Impact:** Simple change that improves reliability.

### ❌ **NOT RECOMMENDED: TranslationController Layer (Overengineering)**

**Why it's overengineering:**
- **Adds complexity** without solving a real problem
- **Current `translate_srt_files()` works fine** - it's not broken
- **"Orchestration concerns"** are minimal in this simple app
- **File batching, retry logic, progress tracking** are already handled adequately
- **Headless testing/future web integration** are hypothetical future needs

**Impact:** Unnecessary abstraction that adds complexity without benefits.

### **Revised Implementation Priority:**

#### **Phase 1 (Essential):**
1. **Language Normalization** - Fixes real bugs, simple utility
2. **Logger Injection** - Improves debugging, minimal complexity
3. **State Management** - Fixes core architectural issues
4. **Thread Safety** - Prevents race conditions

#### **Phase 2 (Important):**
1. **Termbase Lookup Fixes** - Improves reliability
2. **Error Handling** - Better user experience
3. **Dependency Injection** - Cleaner architecture

#### **Phase 3 (Clean Architecture):**
1. **Environment Variable Elimination** - Removes architectural flaws
2. **Configuration Abstraction** - Unified configuration handling

### **Why This Approach is Better:**

#### **Simplicity:**
- **Keep what works** (`translate_srt_files()`)
- **Add only what fixes real problems**
- **No unnecessary abstractions**

#### **Reliability:**
- **Language normalization** prevents termbase lookup failures
- **Logger injection** improves debugging and testing
- **No new complexity** that could introduce bugs

#### **Maintainability:**
- **Fewer moving parts** = fewer things that can break
- **Clear, simple code** = easier to understand and modify
- **Focused on real problems** = not solving hypothetical issues

## Technical Details

### Current Bug Locations

1. **Language Selection Bug**:
   - `srt_core/config/settings.py` line ~50: TARGET_LANGUAGES read at import time
   - `gui/workers/translation_worker.py` line ~140: Environment variable updated after import
   - `srt_core/main.py` line ~70: Uses global TARGET_LANGUAGES instead of passed parameter

2. **Termbase Lookup Bug**:
   - `gui/config_manager.py` line ~90: get_termbase() looks for language names
   - `gui/ai_config.py` line ~540: AI generates termbase with language codes
   - `gui/workers/translation_worker.py` line ~175: Calls get_termbase() with language names

3. **Thread Safety Issues**:
   - `gui/workers/translation_worker.py`: Direct GUI updates from background thread
   - `gui/settings_manager.py`: No thread-safe state access
   - `gui/main_window.py`: No proper signal/slot communication

### Data Flow Analysis

#### Current (Broken) Flow:
```
GUI Language Selection → Environment Variable → TranslationWorker → Environment Variable → srt_core → Global Variable
```

#### Proposed (Fixed) Flow:
```
GUI Language Selection → SettingsManager → TranslationWorker → Direct Parameter → srt_core → Function Parameter
```

### Environment Variable Usage Audit

**Current Environment Variables Used in GUI Runtime:**
- `TARGET_LANGUAGES`: Should be eliminated for GUI runtime
- `DNT_TERMS`: Should be eliminated for GUI runtime  
- `OPENAI_API_KEY`: Keep (essential for API calls)
- `OUTPUT_DIRECTORY`: Keep (file system path)
- `GUI_MODE`: Keep (indicates GUI vs CLI mode)

**Environment Variables to Keep:**
- All startup configuration
- CLI mode configuration
- System paths and API keys

#### Comprehensive Environment Variable Audit

**Files Requiring Environment Variable Removal:**

1. **`srt_core/translator/translator.py`**
   - `os.getenv('TARGET_LANGUAGES')` → Pass as parameter
   - `os.getenv('DNT_TERMS')` → Pass as parameter
   - `os.getenv('TERMBASE')` → Pass as parameter

2. **`srt_core/translator/srt_parser.py`**
   - `os.getenv('SOURCE_LANG')` → Pass as parameter
   - Any language-specific parsing logic → Inject configuration

3. **`srt_core/translator/fixer.py`**
   - `os.getenv('TARGET_LANG')` → Pass as parameter
   - `os.getenv('DNT_TERMS')` → Pass as parameter

4. **`srt_core/translator/term_handler.py`**
   - `os.getenv('TERMBASE')` → Pass as parameter
   - `os.getenv('DNT_TERMS')` → Pass as parameter

5. **`srt_core/main.py`**
   - `os.getenv('TARGET_LANGUAGES')` → Use ConfigResolver for CLI
   - `os.getenv('SOURCE_LANG')` → Use ConfigResolver for CLI
   - `os.getenv('OUTPUT_DIRECTORY')` → Use ConfigResolver for CLI

6. **`gui/workers/translation_worker.py`**
   - `os.environ['TARGET_LANGUAGES']` → Remove entirely
   - `os.environ['DNT_TERMS']` → Remove entirely
   - `os.environ['TERMBASE']` → Remove entirely

**Benefits of Complete Environment Variable Removal:**

1. **Easier Testing**: No need to mock environment variables
2. **Portability**: Works across different GUI frameworks
3. **Concurrent Safety**: No shared global state
4. **Debugging**: Clear parameter flow
5. **Maintainability**: Explicit dependencies

### State Management Architecture

#### Benefits of Configuration Abstraction Layer

The `TranslationConfig` abstraction provides several critical advantages:

1. **Unified Configuration Interface**: Both GUI and CLI use the same configuration object
2. **Explicit Dependencies**: All configuration passed explicitly, no hidden dependencies
3. **Validation**: Configuration validated at creation time with clear error messages
4. **Framework Independence**: Core logic works with any GUI framework
5. **Testing**: Easy to create test configurations without mocking
6. **Debugging**: Clear configuration flow from source to usage
7. **Maintainability**: Single configuration object to modify and extend

#### Benefits of ConfigResolver Pattern

The dedicated `ConfigResolver` module provides several critical advantages:

1. **Explicit Mode Separation**: Clear distinction between CLI and GUI modes
2. **Environment Variable Isolation**: All env-var lookups centralized in one place
3. **Validation**: CLI configuration validated before use
4. **Error Prevention**: GUI calls cannot accidentally use environment variables
5. **Testing**: Easy to mock CLI configuration for testing
6. **Debugging**: Clear logging of which configuration source is used
7. **Maintainability**: Single place to modify environment variable handling

#### Benefits of Complete Environment Variable Removal

Removing all GUI-time environment variable dependencies provides:

1. **Easier Testing**: No need to mock environment variables in unit tests
2. **Portability**: Works across different GUI frameworks (Qt, Tkinter, etc.)
3. **Concurrent Safety**: No shared global state between multiple GUI instances
4. **Debugging**: Clear parameter flow from GUI to core modules
5. **Maintainability**: Explicit dependencies make code easier to understand
6. **Stability**: Eliminates timing dependencies and race conditions
7. **Framework Independence**: Core logic can be used with any GUI framework

#### Benefits of ConfigState Dataclass

The `ConfigState` dataclass provides several critical advantages for a robust application:

1. **Type Safety**: All state fields are strongly typed, preventing runtime errors
2. **Validation**: `__post_init__` validates state integrity on creation
3. **Immutability**: State changes create new objects, preventing accidental mutations
4. **Serialization**: Built-in `to_dict()` and `from_dict()` methods for persistence
5. **Testing**: Easy to create test fixtures with known state
6. **Debugging**: Clear representation of state in logs and debuggers
7. **Documentation**: Self-documenting structure with type hints

#### SettingsManager as Single Source of Truth
```python
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import threading
import json

@dataclass
class ConfigState:
    """Immutable configuration state with validation"""
    target_languages: Dict[str, str]  # language_name -> language_code
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]  # language_code -> {term -> translation}
    output_directory: Optional[str] = None
    api_key: Optional[str] = None
    
    def __post_init__(self):
        """Validate state after initialization"""
        if not isinstance(self.target_languages, dict):
            raise ValueError("target_languages must be a dictionary")
        if not isinstance(self.dnt_terms, list):
            raise ValueError("dnt_terms must be a list")
        if not isinstance(self.termbase, dict):
            raise ValueError("termbase must be a dictionary")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConfigState':
        """Create from dictionary with validation"""
        return cls(**data)
    
    def copy(self) -> 'ConfigState':
        """Create a deep copy of the state"""
        return ConfigState(
            target_languages=self.target_languages.copy(),
            dnt_terms=self.dnt_terms.copy(),
            termbase={k: v.copy() for k, v in self.termbase.items()},
            output_directory=self.output_directory,
            api_key=self.api_key
        )

class SettingsManager:
    def __init__(self):
        self._state = ConfigState(
            target_languages={},
            dnt_terms=[],
            termbase={}
        )
        self._lock = threading.Lock()
    
    def get_current_state(self) -> ConfigState:
        """Get current state (thread-safe)"""
        with self._lock:
            return self._state.copy()
    
    def update_state(self, new_state: ConfigState):
        """Update state (thread-safe)"""
        with self._lock:
            self._state = new_state
        self._persist_state(new_state)
    
    def update_target_languages(self, languages: Dict[str, str]):
        """Update target languages (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.target_languages = languages.copy()
            self._state = new_state
        self._persist_state(self._state)
    
    def update_dnt_terms(self, dnt_terms: List[str]):
        """Update DNT terms (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.dnt_terms = dnt_terms.copy()
            self._state = new_state
        self._persist_state(self._state)
    
    def update_termbase(self, termbase: Dict[str, Dict[str, str]]):
        """Update termbase (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.termbase = {k: v.copy() for k, v in termbase.items()}
            self._state = new_state
        self._persist_state(self._state)
    
    def _persist_state(self, state: ConfigState):
        """Persist state to storage"""
        try:
            state_dict = state.to_dict()
            # Remove sensitive data before persistence
            if 'api_key' in state_dict:
                del state_dict['api_key']
            # Save to QSettings or file
            self._save_to_storage(state_dict)
        except Exception as e:
            logging.error(f"Failed to persist state: {e}")
    
    def _load_from_storage(self) -> ConfigState:
        """Load state from storage"""
        try:
            data = self._load_from_storage()
            return ConfigState.from_dict(data)
        except Exception as e:
            logging.warning(f"Failed to load state, using defaults: {e}")
            return ConfigState(target_languages={}, dnt_terms=[], termbase={})
```

#### Thread-Safe Communication
```python
class TranslationWorker(QThread):
    # All GUI communication via signals
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def run(self):
        # Never call GUI methods directly
        # Always use signals for communication
```

## Implementation Checklist

### Phase 1 Checklist
- [ ] Implement SettingsManager as single source of truth
- [ ] Add thread-safe state access with locks
- [ ] Implement Qt signal/slot communication in TranslationWorker
- [x] Modify `translate_srt_files()` to accept target_languages parameter
- [ ] Update TranslationWorker to pass target_languages directly
- [ ] **Implement Language Normalization** - Centralized in TranslationConfig dataclass
- [ ] **Implement Logger Injection** - Pass logger as parameter instead of global
- [ ] Add structured logging with session context
- [ ] Test language selection with 3 languages
- [ ] Test language selection with 12 languages
- [ ] Test thread safety with concurrent operations
- [ ] Verify CLI compatibility
- [ ] Update documentation

### Phase 2 Checklist
- [ ] Add language name to code mapping in config_manager
- [ ] Implement dependency injection for SRTTranslator
- [ ] Add comprehensive error handling and reporting
- [ ] Test termbase lookup with language names
- [ ] Test termbase lookup with language codes
- [ ] Verify termbase is used during translation
- [ ] Test with AI-generated termbase
- [ ] Test with manual termbase
- [ ] Test error scenarios (missing termbase, network errors)
- [ ] **Verify Language Normalization works correctly** - Test TranslationConfig normalization and validation
- [ ] **Verify Logger Injection works correctly** - Test logging in both GUI and CLI modes

### Phase 3 Checklist
- [ ] Create TranslationConfig abstraction layer
- [ ] Create ConfigResolver module for CLI configuration
- [ ] Audit all `os.getenv()` calls across core modules
- [ ] Remove all environment variable lookups from translator.py
- [ ] Remove all environment variable lookups from srt_parser.py
- [ ] Remove all environment variable lookups from fixer.py
- [ ] Remove all environment variable lookups from term_handler.py
- [ ] Update SRTTranslator to accept TranslationConfig only
- [ ] Modify translate_srt_files() to use configuration abstraction
- [ ] Remove environment variable updates from TranslationWorker
- [ ] Update all translation function calls to use configuration objects
- [ ] Verify no `os.getenv()` calls exist in GUI code paths
- [ ] Test CLI mode with configuration abstraction
- [ ] Test GUI mode with configuration abstraction
- [ ] Test complete GUI workflow
- [ ] Performance testing
- [ ] Memory usage testing
- [ ] Full regression testing
- [ ] Thread safety stress testing
- [ ] Environment variable isolation testing
- [ ] **🟢 Optional: Normalize source_lang in TranslationConfig** - Prevent prompt construction errors
- [ ] **🟢 Optional: Add TranslationConfig logging** - Improve debugging capabilities
- [ ] **🟢 Optional: Add GUI/CLI mode assertion** - Defensive programming against code path mixing

## Conclusion

This refactoring plan addresses the fundamental architectural issues causing the current bugs while maintaining backward compatibility and improving the overall code quality. The phased approach minimizes risk while providing immediate benefits.

The key insight is that GUI applications should not rely on environment variables for runtime state management. Environment variables are appropriate for CLI applications and startup configuration, but GUI state should be managed through direct parameter passing and internal state management.

By implementing this plan, we will:
1. Fix the immediate bugs affecting user experience
2. Improve code maintainability and debugging capabilities
3. Create a cleaner separation between GUI and CLI architectures
4. Establish better patterns for future development
5. Ensure thread safety and state consistency
6. Provide robust error handling and debugging capabilities 