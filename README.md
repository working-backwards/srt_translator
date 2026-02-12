# SRT Translator

## Overview

The **SRT Translator** is a tool that uses AI to translate subtitle files while preserving important terms like names, brands, and technical terms. Perfect for content creators who want to reach international audiences.

### Who is this for?

**Content creators:**
- YouTubers and podcasters expanding to global audiences
- Course creators offering multilingual educational content
- Business professionals localizing training videos

**What you need to know:**
- Basic computer skills (no programming required)
- An OpenAI API key (~$0.01 per hour of video per language)
- Subtitle files in .srt format

**Developers** looking to contribute or extend the tool — see the [Developer Guide](docs/developer/index.md).

---

## Creator Workflow (Recommended)

1. **Create AI Config** — generate DNT & Termbase from the start of your material (put intros and term-dense files first).
2. **Translate** — choose target languages.
3. **Evaluate** — open `eval_report.html` and follow the "What to do next".

See [Creator Guide](docs/user-guide/creator-guide.md) for the full workflow and plain-language guidance.

---

## Quick Start (5 minutes)

### For GUI Users (Recommended for most users)
- Download the latest release for your platform from [GitHub Releases](https://github.com/working-backwards/srt_translator/releases) (.exe for Windows, .dmg for macOS)
- Double-click to run the app (macOS: drag .dmg to Applications)
- Open **API Configuration** in the app and paste your OpenAI API key
- Add your `.srt` files and click **Translate All Files**

See [Installation Guide](docs/user-guide/installation.md) for platform-specific details.

### For CLI Users

See [Developer Setup](docs/developer/setup.md) for cloning the repository, creating a virtual environment, and configuring the CLI.

---

## Features

- **Multi-language translation**: Translate to 80 languages at once
- **Preserve important terms**: Keep names, brands, and technical terms untranslated using Do-Not-Translate (DNT) lists
- **Consistent terminology**: AI-generated, language-specific termbases ensure key terms are translated consistently
- **Tone control**: Choose casual, neutral, or formal register — with automatic language-specific adjustments (e.g., honorifics in Japanese, pronoun selection in Chinese)
- **Maintains timing**: Subtitle timing and formatting stay intact with deterministic subtitle-based formatting
- **Automatic error fixing**: Intelligently fixes common translation issues with progressive retry and batch-size reduction
- **Quality evaluation**: Automatic post-translation assessment with configurable thresholds and HTML/Markdown reports
- **AI-powered setup**: Automatically generate DNT terms and termbases by analyzing a few representative subtitle files

See [Quality Features](docs/user-guide/quality-features.md) and [Terminology System](docs/user-guide/terminology.md) for details.

---

## Configuration

### GUI Users

1. Enter your API key in **Settings > API Configuration**
2. Select target languages using checkboxes or search
3. Browse and select your `.srt` files
4. Optionally click **Generate Translation Settings** to auto-create DNT terms and a termbase
5. Click **Translate All Files**

See [GUI Manual](docs/user-guide/gui-manual.md) for the complete interface guide.

### CLI Configuration

1. Copy the example configuration: `cp examples/env_example .env`
2. Edit `.env` with your values:

```bash
# Required
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}

# Optional
DNT_TERMS=["YourName", "YourCompany", "YourProduct"]
OUTPUT_DIRECTORY=translated_srt_files
INPUT_DIRECTORY=original_captions
TONE=neutral
```

CLI flags:
```bash
srtx-cli --tone formal          # Override tone
srtx-cli --report html          # Generate evaluation report (html, md, both, none)
srtx-cli --debug                # Enable debug logging
```

> **Note:** The CLI reads configuration from `.env` files only. OS environment variables are ignored for all settings except `OPENAI_API_KEY`.

See [Custom Termbases](docs/user-guide/customizing-termbase.md) for termbase setup.

---

## Output Structure

Each translation session creates a batch directory:

```
translated_srt_files/
└── translation-batch-20250810_111157-0700/
    ├── manifest.json                    # Batch metadata
    ├── artifacts/                       # Evaluation and config artifacts
    │   ├── ai_config.json              # DNT terms and termbase used
    │   ├── eval_report.html            # Open this to review translation quality
    │   ├── eval_report.md              # Markdown version
    │   └── es/                         # Per-language audit snapshots
    ├── ES/                              # Spanish translations
    │   └── video1 - ES.srt
    └── FR/                              # French translations
        └── video1 - FR.srt
```

See [Understanding Reports](docs/user-guide/reports.md) for how to read evaluation output.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key not found" | Verify the key is active at [OpenAI](https://platform.openai.com/api-keys) |
| Translation quality issues | Review and adjust DNT terms and termbase; check logs |
| Windows security warnings | Right-click > Properties > Unblock (normal for open-source software) |

Log files are created inside each batch directory as `translation_issues_<timestamp>.log`.

**Long runs on macOS:** Prevent sleep during multi-hour jobs by enabling "Prevent automatic sleeping when the display is off" in System Settings > Battery, or run `caffeinate -imsu srtx` from Terminal.

---

## FAQ

**Q: Do I need to edit my .srt files first?**
A: No, just place them in the input folder as-is.

**Q: Can I translate to multiple languages at once?**
A: Yes! Select multiple target languages in the interface.

**Q: What if some terms get translated that shouldn't be?**
A: Add them to your DNT terms list and re-run the translation.

**Q: How accurate are the translations?**
A: Very good for most content. Review important videos before publishing.

**Q: Is my content secure?**
A: Yes, only subtitle text is sent to OpenAI. Your video files stay local.

---

## Documentation

- **[User Guide](docs/user-guide/index.md)** — Installation, GUI manual, creator workflow, terminology, reports
- **[Developer Guide](docs/developer/index.md)** — Setup, architecture, translation core, CI/CD, contributing

Full documentation is also available at [working-backwards.github.io/srt_translator](https://working-backwards.github.io/srt_translator/).

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

We use pre-commit hooks to ensure code quality. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions.

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For issues and feature requests, please use the [GitHub Issues page](https://github.com/working-backwards/srt_translator/issues).
