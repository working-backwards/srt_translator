# SRT Translator

## Overview

The **SRT Translator** is a tool that uses AI to translate subtitle files while preserving important terms like names, brands, and technical terms. Perfect for content creators who want to reach international audiences.

### Who is this for?

**Perfect for:**
- **Content creators** translating videos for international viewers
- **YouTubers and podcasters** expanding to global audiences
- **Course creators** offering multilingual educational content
- **Business professionals** localizing training videos

**What you need to know:**
- Basic computer skills (no programming required)
- An OpenAI API key (costs ~$0.01-0.05 per minute of video)
- Subtitle files in .srt format

---

## Quick Start (5 minutes)

### Option 1: Download Executable (Recommended for Content Creators)

1. **Download** the executable for your platform
2. **Run the application** (Windows may show security warnings - this is normal for free software)
3. **Enter your OpenAI API key** in the API Configuration section
4. **Select target languages** (Spanish, French, German, etc.)
5. **Add your .srt files** and click "Translate All Files"

### Option 2: Install from Source (For Developers)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/working-backwards/srt_translator.git
   cd srt_translator
   ```

2. **Install and run:**
   ```bash
   pip install -e .
   python run_gui.py
   ```

---

## Features

- **Multi-language Translation**: Translate to multiple languages at once
- **Preserve Important Terms**: Keep names, brands, and technical terms untranslated
- **Maintains Timing**: Subtitle timing and formatting stay intact
- **Automatic Error Fixing**: Intelligently fixes common translation issues
- **Professional Results**: High-quality translations suitable for public content

---

## Installation

### For Content Creators (Executable)

1. **Download** the latest release for your platform
2. **Extract** the files to a folder
3. **Run** the executable
4. **Follow** the on-screen setup instructions

**Note**: Windows may show security warnings because this is free, open-source software. This is normal and safe.

### For Developers (Source Code)

1. **Clone the repository**
2. **Create virtual environment**: `python -m venv venv`
3. **Activate environment**: 
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. **Install**: `pip install -e .`
5. **Run**: `python run_gui.py`

---

## Basic Configuration

### 1. API Key Setup
- Get an OpenAI API key from [OpenAI's website](https://platform.openai.com/api-keys)
- Enter it in the GUI's API Configuration section
- Test the connection to verify it works

### 2. Target Languages
- Select which languages you want to translate to
- Popular choices: Spanish, French, German, Japanese, Chinese
- You can select multiple languages at once

### 3. Do Not Translate (DNT) Terms (Optional)
- Add names, brands, or technical terms that shouldn't be translated
- Examples: Your name, company name, product names, technical acronyms

### 4. AI-Generated Translation Settings (Recommended)
To improve translation quality, the SRT Translator app supports two professional tools: Do Not Translate (DNT) terms and a Termbase—and both can be created for you automatically using AI. DNT terms are names, acronyms, or product references (like "Amazon" or "ROI") that should remain in the original language. The Termbase is a glossary that ensures consistent translations for important business or technical terms, such as "operating plan" or "input metrics." Creating these lists is easy: just upload a few representative subtitle files and click "Generate Translation Settings." The app analyzes your content and uses AI to suggest DNT terms and generate a Termbase for each selected language. While optional, these tools are highly recommended for videos that contain brand names, industry jargon, or educational content—helping ensure your translations are clear, accurate, and consistent across all languages.

---

## Usage

### Step-by-Step Process

1. **Prepare your .srt files**
   - Place subtitle files in the input folder
   - Supported format: .srt files

2. **Configure settings**
   - Enter your API key
   - Select target languages
   - Add any DNT terms to preserve

3. **Start translation**
   - Click "Translate All Files"
   - Monitor progress in the interface
   - Check logs for any issues

4. **Find your results**
   - Translated files appear in language-specific folders
   - Each language gets its own subfolder
   - Original timing and formatting preserved

### Example Output Structure
```
translated_srt_files/
├── ES/                    # Spanish translations
│   └── video1 - ES.srt
├── FR/                    # French translations
│   └── video1 - FR.srt
└── DE/                    # German translations
    └── video1 - DE.srt
```

---

## Cost Estimation

**Typical costs:**
- **Short video (5-10 minutes)**: $0.05-0.15
- **Medium video (20-30 minutes)**: $0.20-0.50
- **Long video (60+ minutes)**: $0.50-1.50

**Factors affecting cost:**
- Length of video
- Number of languages
- Complexity of content
- Number of subtitles

**Tips to reduce costs:**
- Remove unnecessary subtitles before translation
- Use fewer target languages initially
- Test with a short video first

---

## Troubleshooting

### Common Issues

**"API key not found"**
- Check that you entered the API key correctly
- Verify the key is active in your OpenAI account

**"Source directory does not exist"**
- Create the input folder: `mkdir original_captions`
- Place your .srt files in this folder

**Translation quality issues**
- Review and adjust your DNT terms list
- Check the logs for specific issues
- Try translating to fewer languages first

**Security warnings (Windows)**
- This is normal for free, open-source software
- Right-click → Properties → Unblock if needed
- The software is safe to run

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

**Q: Can I use this on Windows/Mac/Linux?**
A: Yes, the tool works on all major platforms.

**Q: Is my content secure?**
A: Yes, only subtitle text is sent to OpenAI. Your video files stay local.

---

## Advanced Configuration

### Environment Variables (For Advanced Users)

If you're installing from source, you can configure these settings:

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `TARGET_LANGUAGES`: Dictionary of target languages

**Optional:**
- `DNT_TERMS`: Comma-separated list of DNT terms
- `SOURCE_LANG`: Source language (default: en)
- `OPENAI_MODEL`: AI model to use (default: gpt-4o-mini)
- `AGGRESSIVENESS`: Auto-fix level 0-1 (default: 0.75)

### Example Configuration
```bash
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}
DNT_TERMS=YourName,YourCompany,YourProduct
SOURCE_LANG=en
```

---

## Supported Languages

**Popular Languages (12):**
- Spanish, French, German, Italian
- Portuguese (Brazil), Chinese (Simplified)
- Japanese, Korean, Arabic, Hindi
- Russian, Dutch

**Total Available:** 78 languages including regional variants

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For issues and feature requests, please use the [GitHub issues page](https://github.com/working-backwards/srt_translator/issues).
