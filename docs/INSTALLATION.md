# SRT Translator Installation Guide

This guide covers two installation methods for the SRT Translator application.

## 🚀 Quick Start (Content Creators)

**For users who want to run the application without installing Python or dependencies.**

### Method 1: Download Executables (Recommended)

1. **Download the release package** for your platform:
   - Windows: `SRT-Translator-v1.0.0-windows.zip`
   - macOS: `SRT-Translator-v1.0.0-darwin.zip`
   - Linux: `SRT-Translator-v1.0.0-linux.zip`

2. **Extract the package** to a folder on your computer

3. **Configure your API key**:
   - Copy `examples/env_example` to `.env`:
  - **Windows/Linux/macOS:** `cp examples/env_example .env`
  - **Windows (PowerShell):** `Copy-Item examples/env_example .env`
- Edit `.env` and add your OpenAI API key:
     ```
     OPENAI_API_KEY=your_api_key_here
     ```

4. **Run the application**:
   - **GUI Version**: Double-click `SRT-Translator-GUI`
   - **CLI Version**: Run `SRT-Translator-CLI` from command line

5. **Add your subtitle files** to the `original_captions` folder

6. **Start translating!**

### Method 2: Build Your Own Executables

If you want to create executables from source:

1. **Install Python 3.9+** and pip
2. **Clone the repository**:
   ```bash
   git clone https://github.com/working-backwards/srt_translator.git
   cd srt_translator
   ```
3. **Install dependencies**:
   ```bash
   pip install -e '.[dev]'
   ```
4. **Build executables (PyInstaller quick path)**:
   - Windows:
     ```bash
     pyinstaller --noconsole --name SRT-Translator \
       --add-data "srt_translator/core/config/languages.json;srt_translator/core/config" \
       srt_translator/gui/main_window.py
     ```
   - macOS:
     ```bash
      # Build a Finder app (.app bundle)
      pyinstaller --windowed --name SRT-Translator \
        --add-data "srt_translator/core/config/languages.json:srt_translator/core/config" \
        srt_translator/gui/main_window.py
      
      # Build/update only the single-file console-launchable binary
      # (uses the provided .spec and places output in dist/SRT-Translator)
      pyinstaller build_specs/srt_translator_gui.spec --noconfirm --clean
     ```
   - Linux:
     ```bash
     pyinstaller --windowed --name SRT-Translator \
       --add-data "srt_translator/core/config/languages.json:config" \
       srt_translator/gui/main_window.py
     ```
5. **Find executables** in the `dist/` folder

## 🔧 Advanced Installation (Developers)

**For users who want to work with the source code or contribute to the project.**

### Prerequisites

- **Python 3.9 or higher**
- **Git** (for cloning the repository)
- **pip** (Python package installer)

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/srt_translator.git
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
   # Install with development dependencies (note the quotes for zsh)
   pip install -e '.[dev]'
   
   # Or install without dev dependencies
   pip install -e .
   ```

4. **Configure your environment**:
   ```bash
   # Copy the example configuration
   cp examples/env_example .env
   
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application**:
   ```bash
   # GUI version
   srtx
   
   # CLI version
   srt-cli
   ```

### macOS: Prevent Sleep for Long Runs

For multi‑hour jobs, use `caffeinate` to keep the system awake while allowing the display to sleep:

```bash
caffeinate -imsu srtx
## 🔁 Rebuilding (macOS)

Use these depending on what you need to refresh:

- Rebuild only the Terminal binary (fast, single file):
  ```bash
  rm -rf dist/SRT-Translator build
  pyinstaller build_specs/srt_translator_gui.spec --noconfirm --clean
  ```

- Rebuild a fresh Finder app (.app bundle):
  ```bash
  rm -rf dist/SRT-Translator.app build
       pyinstaller --windowed --name SRT-Translator \
       --clean --noconfirm \
       --add-data "srt_translator/core/config/languages.json:srt_translator/core/config" \
       srt_translator/gui/main_window.py
  # Open it
  open dist/SRT-Translator.app
  ```

- Quick local test without packaging:
   ```bash
   srtx
   ```

```

Flags:
- `-i` prevent idle sleep, `-m` prevent disk sleep, `-s` prevent system sleep on AC, `-u` user activity. Omit `-d` so the display may turn off.

## 📋 System Requirements

### Minimum Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Memory**: 4GB RAM
- **Storage**: 500MB free space
- **Internet**: Required for translation API calls

### Recommended Requirements

- **Operating System**: Latest stable version
- **Memory**: 8GB RAM or more
- **Storage**: 1GB free space
- **Internet**: Stable broadband connection

## 🔑 API Key Setup

### Getting an OpenAI API Key

1. **Visit** [OpenAI Platform](https://platform.openai.com/)
2. **Sign up** or log in to your account
3. **Navigate** to API Keys section
4. **Create** a new API key
5. **Copy** the key (it starts with `sk-`)

### Configuring the API Key

**For Executable Users:**
1. Copy `examples/env_example` to `.env`:
   - **Windows/Linux/macOS:** `cp examples/env_example .env`
   - **Windows (PowerShell):** `Copy-Item examples/env_example .env`
2. Edit `.env` and add: `OPENAI_API_KEY=your_key_here`

**For Source Code Users:**
1. Copy `examples/env_example` to `.env`:
   - **Windows/Linux/macOS:** `cp examples/env_example .env`
   - **Windows (PowerShell):** `Copy-Item examples/env_example .env`
2. Edit `.env` and add: `OPENAI_API_KEY=your_key_here`

## 🧪 Testing the Installation

### Test the GUI

1. **Run the GUI**:
   ```bash
   srtx
   ```

2. **Verify the interface loads** without errors

3. **Check that language selection** shows available languages

### Test the CLI

1. **Create a test file**:
   ```bash
   echo "1\n00:00:01,000 --> 00:00:04,000\nHello world\n" > test.srt
   ```

2. **Run translation**:
   ```bash
   srt-cli
   ```

3. **Check output** in `translated_srt_files/` directory

## 🚨 Troubleshooting

### Common Issues

**"OpenAI API key not found"**
- Make sure you've created a `.env` file
- Verify the API key is correctly formatted
- Check that the file is in the project root

**"Source directory does not exist"**
- Create the `original_captions` directory
- Place your `.srt` files in this directory

**"Module not found" errors**
- Make sure you've installed dependencies: `pip install -e .`
- Check that you're in the correct virtual environment

**zsh: no matches found: .[dev]**
- zsh treats `[]` as globbing characters. Quote the extras spec: run `pip install -e '.[dev]'` (or escape the brackets: `pip install -e .\[dev\]`).

**GUI doesn't start**
- Verify PySide6 is installed: `pip install PySide6`
- Check for display/display server issues on Linux

**Executable is too large**
- This is normal for PyInstaller executables
- They include Python runtime and all dependencies
- Typical size: 50-100MB

### Getting Help

1. **Check the logs** in `translation_logs/` directory
2. **Review the README.md** for detailed information
3. **Open an issue** on GitHub with:
   - Your operating system and version
   - Python version
   - Error messages
   - Steps to reproduce the issue

## 📦 Distribution Options

### For Content Creators

- **Download executables** from GitHub releases
- **No Python installation required**
- **Self-contained packages**

### For Advanced Users

- **Clone repository** and install from source
- **Modify code** as needed
- **Contribute** to the project

### For Organizations

- **Build custom executables** for your environment
- **Deploy via internal distribution** systems
- **Customize configuration** for your needs

## 🔄 Updates

### Updating Executables

1. **Download** the latest release package
2. **Replace** old executables with new ones
3. **Keep** your `.env` configuration file

### Updating Source Code

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Update dependencies**:
   ```bash
   pip install -e '.[dev]'
   ```

3. **Test the installation**:
   ```bash
   # Test the console scripts
   srtx --help
   srt-cli --help
   
   # Run tests if available
   python -m pytest tests/  # or your test command
   ```

---

**Need help?** Check the [README.md](README.md) for detailed usage instructions or open an issue on GitHub. 