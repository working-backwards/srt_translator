# SRT Translator Coding Standards

## 🚨 CRITICAL ARCHITECTURE RULES (NEVER VIOLATE)

### **1. CORE ENGINE ISOLATION**
- **Core engine (`srt_translator/core/`) NEVER imports from GUI or CLI modules**
- **Core engine ONLY reads from `TranslationConfig` objects passed as parameters**
- **Core engine NEVER accesses environment variables, global settings, or file paths**
- **Core engine NEVER calls `logging.basicConfig()` or configures logging**

### **2. LOGGING ARCHITECTURE**
- **ONLY configure logging in entry points**: `cli/app.py`, `gui/app.py`, `__main__.py`
- **Library modules get loggers and emit, but NEVER call `basicConfig()` or log on import**
- **This prevents duplicate handlers, noisy logs, and surprises for library consumers**

### **3. CONFIGURATION FLOW**
```
CLI/GUI → Load config from files/env → Create TranslationConfig → Pass to Core Engine
     ↑           ↑                           ↑                    ↑
  Entry point  I/O layer              Data object          Pure functions
```

## 🐍 Python Code Standards

### **Logging (CRITICAL)**
- **NEVER use `print()` statements in production code**
- **ALWAYS use proper logging**: `import logging; logger = logging.getLogger(__name__)`
- **Use appropriate levels**: `logger.info()`, `logger.warning()`, `logger.error()`, `logger.debug()`

### **Code Style**
- Follow PEP 8 standards
- Use type hints where appropriate
- Include docstrings for all functions and classes
- Use f-strings for string formatting

## 🏗️ Project Structure
- Maintain existing package structure: `srt_translator.{core,cli,gui}`
- Follow established import patterns
- Use relative imports within packages when appropriate

## 🚨 Error Handling
- Use proper exception handling with logging
- Log errors with context information
- Provide user-friendly error messages in GUI/CLI

## 📦 Dependencies
- Minimize external dependencies
- Use standard library when possible
- Document any new dependencies added

## 🧪 Testing
- Write tests for new functionality
- Use pytest framework
- Aim for high test coverage
- Use logging in tests for better debugging

## 🔒 Security
- Never log sensitive information (API keys, passwords)
- Use environment variables ONLY for OpenAI API key
- Validate all user inputs
- Follow security best practices

## 📚 Documentation
- Update docstrings when modifying functions
- Keep README and other docs current
- Document any breaking changes

## ⚡ Performance
- Use lazy loading for heavy dependencies
- Optimize for memory usage in large file processing
- Profile performance-critical sections

## 💻 Platform Compatibility
- Ensure code works on Windows, macOS, and Linux
- Use platform-agnostic path handling
- Test on Python 3.9-3.12

## 🧠 Remember
- **Logging over print() statements**
- **Core engine isolation - NEVER import GUI/CLI modules**
- **Configuration objects only - NEVER global settings**
- **Follow existing patterns in the codebase**
- **Write tests for new functionality**
- **Document changes clearly**

## 🚨 CRITICAL REMINDER
When working with the core engine (`srt_translator/core/`):
1. **NEVER import from GUI or CLI modules**
2. **NEVER use environment variables (except OpenAI key)**
3. **NEVER use hardcoded defaults**
4. **ONLY read from TranslationConfig objects**
5. **If you need a configurable parameter, add it to TranslationConfig class**

Violating these rules will break the app's architecture and introduce fragility. The core engine must remain pure and only consume the configuration objects passed to it.
