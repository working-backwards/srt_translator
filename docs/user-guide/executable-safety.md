# Security Documentation

## Overview

This document explains the security measures implemented to protect sensitive data when building and distributing the SRT Translator executable.

## What Gets Excluded from the Executable

The build process **explicitly excludes** the following sensitive files and directories:

### 🔒 Sensitive Configuration Files
- `.env` - Contains API keys and personal configuration
- `.env.local`, `.env.production`, `.env.development` - Environment-specific configs
- `termbase.json` - User-specific translation data

### 📁 User Content Directories
- `original_captions/` - User's original subtitle files
- `translated_srt_files/` - User's translated subtitle files
- `translation_logs/` - User-specific translation logs

### 📄 Optional Configuration Files
- `translation_prompt.txt` - Custom translation prompts
- `translation_prompt.example` - Example prompt file

### 🗂️ Development and Cache Files
- `__pycache__/` - Python cache files
- `*.pyc`, `*.pyo`, `*.pyd` - Compiled Python files
- `.pytest_cache/` - Test cache
- `.coverage`, `htmlcov/` - Test coverage files
- `venv/`, `.venv/`, `env/` - Virtual environments

## What Gets Included

Only the following **safe, non-sensitive** files are included:

### ✅ Required Application Files
- `config/languages.json` - Language definitions (no sensitive data)
- `examples/env_example` - Template file (no real API keys)

### ✅ Application Code
- All Python source code
- Required dependencies
- GUI assets and styles

## Security Verification

### Automatic Verification
The build process includes automatic security verification that:
1. Checks if sensitive files are accidentally included
2. Scans for API key patterns in the executable
3. Reports any security issues found

### Manual Verification
You can run the security check manually:
```bash
python scripts/verify_security.py
```

This will:
- Analyze the executable for sensitive content
- Report any security issues found
- Confirm the executable is safe to distribute

## Why This Approach Works

### ✅ GUI Independence
The GUI application is designed to work **without** a `.env` file:
- Uses built-in default values for all settings
- Allows users to configure API keys through the interface
- Stores user preferences locally (not in the executable)

### ✅ Three-Tier Configuration System
1. **AI-generated config** (stored in GUI settings)
2. **Manual .env file** (optional fallback)
3. **Built-in defaults** (always available)

### ✅ User Privacy
- No personal data bundled with the executable
- Users can safely share the executable
- Each user configures their own API keys

## Best Practices for Distribution

### ✅ Safe to Distribute
- The executable itself (after security verification)
- `examples/env_example` file (template only)
- `QUICK_START.md` (installation instructions)

### ❌ Never Distribute
- Any `.env` file with real API keys
- `termbase.json` with personal translations
- User content directories
- Development files

## Troubleshooting

### If Security Check Fails
1. **Do not distribute** the executable
2. **Rebuild** with the updated security settings
3. **Run verification** again before distribution

### Common Issues
- **False positives**: Some antivirus software may flag PyInstaller executables
- **Missing files**: Ensure all required files are present
- **Permission errors**: Run as administrator if needed

## Security Checklist

Before distributing your executable:

- [ ] Security verification passed
- [ ] No `.env` files included
- [ ] No user content included
- [ ] No API keys detected
- [ ] Only safe template files included
- [ ] Executable works without sensitive files

## Support

If you encounter security issues:
1. Check this documentation
2. Run the security verification script
3. Review the build configuration
4. Contact the development team if needed
