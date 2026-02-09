# Installation (Content Creators)

This guide covers installation for **content creators** who want to use the SRT Translator application.

## Download & Run (Recommended)

**No Python installation required.**

1. **Download the release package** for your platform:
   - Windows: `SRT-Translator-v1.0.0-windows.zip`
   - macOS: `SRT-Translator-v1.0.0-mac.dmg`
   - Linux: `SRT-Translator-v1.0.0-linux.zip`

2. **Extract/Install**:
   - **Windows**: Extract the zip to a folder
   - **macOS**: Open the .dmg and drag to Applications
   - **Linux**: Extract the zip to a folder

3. **Run the application**: Double-click `SRT-Translator`

4. **Enter your API key** in the app's API Configuration section

## Getting an OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key (starts with `sk-`)
5. Copy and paste it into the app

## System Requirements

### Minimum
- **OS**: Windows 10+, macOS 10.14+, or Linux
- **RAM**: 4GB
- **Storage**: 500MB free
- **Internet**: Required for API calls

### Recommended
- **RAM**: 8GB+
- **Internet**: Stable broadband

## macOS: Prevent Sleep for Long Runs

For multi-hour translation jobs:

**Option 1: System Settings**
1. Go to **System Settings** → **Battery**
2. Disable **Low Power Mode**
3. Enable **"Prevent automatic sleeping when the display is off"**

**Option 2: Terminal** (if comfortable with command line)
```bash
caffeinate -imsu /Applications/SRT-Translator.app/Contents/MacOS/SRT-Translator
```

## Troubleshooting

**"OpenAI API key not found"**
- Make sure you entered the key in the API Configuration section
- Verify the key is active in your OpenAI account

**Security warnings (Windows)**
- This is normal for open-source software
- Right-click → Properties → Unblock if needed

**Security warnings (macOS)**
- Right-click the app → Open (first time only)
- Or: System Settings → Privacy & Security → Open Anyway

**App won't start**
- Ensure you have enough disk space
- Try re-downloading the release

---

For developers who want to install from source, see the [Developer Setup](../developer/setup.md) guide.
