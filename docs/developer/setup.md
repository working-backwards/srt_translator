# Developer Setup

This guide covers installation for **developers** who want to work with the source code or contribute to the project.

## Prerequisites

- **Python 3.11+**
- **Git**
- **pip**

## Installation from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/working-backwards/srt_translator.git
   cd srt_translator
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install the package**:
   ```bash
   # CLI only (lightweight)
   pip install -e .

   # With GUI support
   pip install -e '.[gui]'

   # With development dependencies (testing, linting)
   pip install -e '.[dev]'

   # Everything
   pip install -e '.[gui,dev]'
   ```

4. **Configure environment**:
   ```bash
   cp examples/env_example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

5. **Run the application**:
   ```bash
   srtx        # GUI
   srtx-cli    # CLI
   ```

## Building Executables

To create standalone executables with PyInstaller:

```bash
pip install pyinstaller
```

**Quick Build (Recommended):**
```bash
python scripts/build_gui.py
```

**Manual Build:**

- **Windows**:
  ```bash
  pyinstaller --noconsole --name SRT-Translator \
    --add-data "srt_translator/config/languages.json;srt_translator/config" \
    srt_translator/gui/main_window.py
  ```

- **macOS**:
  ```bash
  pyinstaller --windowed --name SRT-Translator \
    --add-data "srt_translator/config/languages.json:srt_translator/config" \
    srt_translator/gui/main_window.py
  ```

- **Linux**:
  ```bash
  pyinstaller --windowed --name SRT-Translator \
    --add-data "srt_translator/config/languages.json:srt_translator/config" \
    srt_translator/gui/main_window.py
  ```

Output is created in `dist/`.

**Note**: The `--add-data` syntax uses `;` on Windows and `:` on macOS/Linux.

## macOS Rebuilding

- **Rebuild Terminal binary** (fast):
  ```bash
  rm -rf dist/SRT-Translator build
  pyinstaller build_specs/srt_translator_gui.spec --noconfirm --clean
  ```

- **Rebuild Finder app** (.app bundle):
  ```bash
  rm -rf dist/SRT-Translator.app build
  pyinstaller --windowed --name SRT-Translator \
    --clean --noconfirm \
    --add-data "srt_translator/config/languages.json:srt_translator/config" \
    srt_translator/gui/main_window.py
  open dist/SRT-Translator.app
  ```

## Running Tests

```bash
python -m pytest tests/
```

## Build Scripts

All build and utility scripts are in `scripts/`:

```
scripts/
├── build_gui.py          # PyInstaller wrapper for GUI executable
├── build_release.py      # Standard Python package building
├── smoke_test.py         # Testing utilities
└── lint.py               # Linting utilities
```

## CLI/GUI Architecture

The SRT Translator has clean separation between CLI and GUI:

- **CLI (`srtx-cli`)**: Lightweight, works on headless servers
- **GUI (`srtx`)**: Full graphical interface, requires PySide6
- **Core Engine**: Shared translation logic used by both

```
srt_translator/
├── core/           # Pure translation logic (no GUI/CLI dependencies)
├── cli/            # CLI-specific code
├── gui/            # GUI-specific code
└── config/         # Configuration files
```

## CLI Model Configuration

For CLI runs (`srtx-cli`):

- **API key** comes from `OPENAI_API_KEY` (OS environment wins over `.env`).
- **Translation model** is controlled by the `.env` key:

  ```bash
  OPENAI_TRANSLATION_MODEL=gpt-4o-mini
  ```

  If unset, the CLI uses `DEFAULT_TRANSLATION_MODEL` from `srt_translator/core/constants.py`.

- The **generation/configuration model** (used for DNT + termbase generation) is a
  code-level choice driven by:

  - `DEFAULT_GENERATION_MODEL` in `srt_translator/core/constants.py`
  - Per-model capabilities in `srt_translator/config/model_config.json`

  CLI code does not override or reference a separate configuration model; that remains
  the responsibility of the AI-config pipeline (currently GUI-only).

## Troubleshooting

**"Module not found" errors**
- Ensure you ran `pip install -e .`
- Check you're in the correct virtual environment

**zsh: no matches found: .[dev]**
- Quote the extras: `pip install -e '.[dev]'`

**GUI doesn't start**
- Verify PySide6: `pip install PySide6`
- Check display server on Linux

---

For contributing guidelines, see [CONTRIBUTING.md](https://github.com/working-backwards/srt_translator/blob/main/CONTRIBUTING.md).
