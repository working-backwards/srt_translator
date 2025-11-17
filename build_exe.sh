#!/usr/bin/env bash

# Detect OS
OS="$(uname)"
echo "Detected OS: $OS"

# Project root (absolute path)
ROOT="$(pwd)"

# Set environment variables (matching your required format)
export LANGUAGE_CONFIG="$ROOT/srt_translator/config/languages.json"
export TRANSLATION_RUBRIC="$ROOT/srt_translator/config/translation_rubric.yaml"

echo "LANGUAGE_CONFIG=$LANGUAGE_CONFIG"
echo "TRANSLATION_RUBRIC=$TRANSLATION_RUBRIC"

# PyInstaller add-data syntax (platform specific)
if [[ "$OS" == "Darwin" ]]; then
    SEP=":"       # macOS/Linux
else
    SEP=";"       # Windows
fi

# Final PyInstaller command
pyinstaller --clean --onefile srt_translator/gui/app.py --name SRTTranslator \
    --add-data "${LANGUAGE_CONFIG}${SEP}srt_translator/config" \
    --add-data "${TRANSLATION_RUBRIC}${SEP}srt_translator/config"

echo "✅ Build complete → dist/SRTTranslator"
