# SRT Translator — Coding Standards (Python 3.11+)

This document is the single source of truth for code and repository standards. It supersedes older/AI‑specific guidance.

---

## 1) Architecture (NEVER VIOLATE)

### Core Engine Isolation
- Core engine (`srt_translator/core/`) **never** imports from GUI/CLI modules.
- Core engine **only** reads configuration from `TranslationConfig` objects passed as parameters.
- Core engine **never** reads environment variables, global settings modules, or file paths directly.
- Core engine **never** configures logging (no `basicConfig()`); it only obtains a module logger and emits.

### Configuration Flow
```
CLI/GUI → load config → create TranslationConfig → pass to Core Engine
     ↑           ↑               ↑                        ↑
  entry pt     I/O layer    data object               pure funcs
```

### Single‑File Translator Rule
A `Translator` instance can run **only one file at a time**. Starting a second file while one is running must fail fast with a clear error (e.g., `RuntimeError("translation in progress")`). This constraint must be enforced by tests.

---

## 2) Logging (CRITICAL - NEVER VIOLATE)

### One-Rule Policy
**Only the app boundary (GUI worker or CLI main) configures logging. Every core module must use the logger it is passed and must never create handlers, call `basicConfig`, or log to the root/default logger.**

### Implementation Rules
- **Core modules**: Must require a logger parameter; no fallback to `logging.getLogger(__name__)`
- **Entry points only**: Configure logging in `cli/app.py`, `gui/app.py`, `__main__.py`
- **No side logs**: Core code never creates handlers, calls `basicConfig()`, or writes separate log files
- **Unified logging**: One run log per execution, funneled through the app's logging system

### Forbidden Patterns in Core Code
```python
# ❌ FORBIDDEN - Fallback to default logger
logger = logger or logging.getLogger(__name__)

# ❌ FORBIDDEN - Creating handlers
logger.addHandler(logging.FileHandler(...))

# ❌ FORBIDDEN - Global logging config
logging.basicConfig(...)

# ❌ FORBIDDEN - Root logger usage
logging.info(...)
```

### Required Pattern in Core Code
```python
# ✅ REQUIRED - Require injected logger
def __init__(self, *, logger: logging.Logger, ...):
    if logger is None:
        raise ValueError("Logger is required; no fallback allowed.")
    self.logger = logger.getChild("module.name")
```

---

## 3) Style & Patterns

### Imports (order)
1) Standard library  
2) Third‑party  
3) Local package imports  
(no imports after code execution)

### Type hints & docstrings
- Public functions/classes are fully typed.
- Concise docstrings (one‑liner + key args/returns).

### Exceptions
- Raise specific exceptions (`FileNotFoundError`, `ValueError`, etc.); avoid bare `Exception`.

### Strings
- Prefer f‑strings for general formatting.
- For logging, use parameterized messages:
  ```python
  logger.info("Processing %d files", len(files))
  ```

### Dependencies
- Prefer the standard library; keep third‑party deps minimal and justified in PRs.

---

## 4) Testing & Security

### Testing
- Use **pytest**.
- Write tests for new behavior and bug fixes.

### Security
- Never log secrets (API keys/tokens).
- Validate inputs; avoid command injection and unsafe file operations.

---

## 5) Tooling & Local Checks (Python 3.11+)

We use **pre‑commit**, **Ruff**, and **MyPy**.

**One‑time setup**
```bash
pip install -U pre-commit ruff mypy
pre-commit install
```

**Run checks locally**
```bash
ruff check .
ruff format .
mypy srt_translator
pre-commit run --all-files
pytest -q
```

**Security scanning (optional but recommended)**
```bash
# Check for dependency vulnerabilities
safety check --full-report

# Scan for common security issues in code
bandit -r srt_translator
```

---

## 6) Platforms & Versions

- Python: **3.11+** (3.11, 3.12, 3.13 when stable)
- OS: Windows, macOS, Linux

---

## 7) Before You Submit (Checklist)

- [ ] Imports organized; none after code execution  
- [ ] Type hints & docstrings updated  
- [ ] Specific exceptions (no bare `Exception`)  
- [ ] Logging used; no `print()`  
- [ ] Inputs validated; no secrets logged  
- [ ] `ruff check .` and `ruff format .` clean  
- [ ] `mypy srt_translator` passes (or justified ignores)  
- [ ] `pytest -q` passes (incl. single‑file test)