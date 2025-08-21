# Terminology System - SRT Translator

## Overview

The SRT Translator uses an intelligent terminology system that combines **Do Not Translate (DNT) terms** with **AI-generated termbase** to ensure consistent, high-quality translations while preserving important technical and brand terms.

## Key Features

### 🚫 **Do Not Translate (DNT) Terms**
- **Hard-Preserve Terms**: Always kept in original language (acronyms, tech codes, product names)
- **Soft-Preserve Terms**: Kept unless overridden by termbase
- **Automatic Filtering**: Numeric and number-like terms are automatically filtered out
- **Smart Detection**: Identifies acronyms, CamelCase, and technical patterns

### 📚 **AI-Generated Termbase**
- **Script Validation**: Ensures translations use proper writing systems for each language
- **Confidence Filtering**: Only accepts translations with confidence ≥0.90
- **Identity Prevention**: Rejects translations that are identical to source terms
- **Context-Aware**: Analyzes transcript content to identify key terminology

### 🔄 **Precedence System**
- **Termbase → DNT**: Termbase translations take precedence over DNT terms
- **Hard-Preserve Exception**: Acronyms and tech codes always remain untranslated
- **Conflict Resolution**: Automatic handling of overlapping terms

## How It Works

### 1. **DNT Generation**
```
Transcript Analysis → AI Identifies Terms → Hard-Preserve Filtering → Final DNT List
```

**Example DNT Terms:**
- ✅ **Hard-Preserve**: `API`, `GPU`, `NASA`, `Adobe Premiere`
- ❌ **Filtered Out**: `300ms`, `6.7`, `2024`, `$99.99`

### 2. **Termbase Generation**
```
Transcript Analysis → AI Extracts 30 Key Terms → Script Validation → Confidence Filtering → Final Termbase
```

**Termbase Entry Format:**
```json
{
  "source": "machine learning",
  "target": "机器学习",
  "language": "zh-Hans",
  "category": "technical",
  "confidence": 0.95
}
```

### 3. **Script Validation**
The system validates that translations use the correct writing system:

- **Chinese (Simplified)**: Must contain CJK characters (一, 二, 三...)
- **Japanese**: Must contain Hiragana (あ, い, う...), Katakana (ア, イ, ウ...), or CJK
- **Arabic**: Must contain Arabic script (ا, ب, ت...)
- **Latin Languages**: No script restrictions (default behavior)

### 4. **Precedence Application**
```
Input: DNT=["machine learning", "API"], Termbase={"machine learning": "机器学习"}
Result: Effective DNT=["API"] (machine learning overridden by termbase)
```

## Configuration

### Language Script Configuration
The system automatically detects script requirements from `languages.json`:

```json
{
  "zh-Hans": {
    "script": "cjk",
    "script_blocks": ["CJK"]
  },
  "ja": {
    "script": "japanese", 
    "script_blocks": ["Hiragana", "Katakana", "CJK"]
  }
}
```

### DNT Filtering Rules
- **Always Keep**: Acronyms (API, GPU, NASA)
- **Always Keep**: Tech product names (Adobe Premiere, Vivaldi)
- **Always Keep**: CamelCase terms (MachineLearning, DeepNeural)
- **Filter Out**: Pure numbers (300, 6.7, 2024)
- **Filter Out**: Number-like patterns (300ms, $99.99, 6.7%)

## Usage Examples

### GUI Usage
1. **Generate Translation Settings**: AI analyzes your transcript and creates DNT + termbase
2. **Edit Settings**: Review and modify AI-generated terminology
3. **Translate**: System automatically applies terminology rules

### CLI Usage
```bash
# Generate terminology from transcript
srtx-cli --generate-terminology input.srt

# Translate with custom terminology
srtx-cli --dnt-terms dnt.json --termbase termbase.json input.srt
```

### Programmatic Usage
```python
from srt_translator.core.terminology_utils import build_effective_dnt
from srt_translator.core.translator.term_handler import TermHandler

# Build effective DNT with precedence
effective_dnt = build_effective_dnt(dnt_terms, termbase)

# Create term handler
handler = TermHandler(dnt_terms, termbase, target_lang="es")
effective_dnt = handler.get_effective_dnt()
stats = handler.get_dnt_precedence_stats()
```

## Quality Metrics

### DNT Preservation Rate
- **Target**: ≥90% of DNT terms preserved
- **Measurement**: Count of preserved terms / total DNT terms
- **Hard-Preserve**: Always 100% preserved

### Termbase Usage
- **Accepted Translations**: High-confidence, script-valid translations
- **Rejected Reasons**: Low confidence, script mismatch, identity
- **Quality Score**: Percentage of accepted vs. total generated

### Script Validation Success
- **Target**: 100% script compliance
- **Measurement**: Script-valid translations / total translations
- **Fallback**: Latin languages have no script restrictions

## Troubleshooting

### Common Issues

**DNT Terms Not Preserved**
- Check if terms are in termbase (they override soft-preserve DNT)
- Verify terms meet hard-preserve criteria
- Check for numeric filtering

**Script Validation Failures**
- Ensure language has proper script configuration in `languages.json`
- Check if AI is generating wrong-script translations
- Verify Unicode block definitions

**Low Termbase Acceptance**
- Check confidence thresholds (default: 0.90)
- Review script validation results
- Verify transcript content quality

### Debug Information
The system provides detailed logging for troubleshooting:
- DNT filtering results
- Termbase acceptance/rejection reasons
- Script validation details
- Precedence application statistics

## Best Practices

### For Content Creators
1. **Review AI-generated terminology** before translation
2. **Add important brand names** to DNT if not detected
3. **Verify technical terms** in termbase for accuracy
4. **Test with small samples** before full translation

### For Developers
1. **Use script validation** for all AI-generated content
2. **Implement confidence thresholds** for quality control
3. **Log precedence decisions** for debugging
4. **Cache language configurations** for performance

## Technical Details

### Architecture
- **Terminology Utils**: Core filtering and validation logic
- **Language Config**: Script and language metadata
- **Term Handler**: DNT replacement and restoration
- **AI Config**: AI-powered terminology generation

### Performance
- **Lazy Loading**: Language configurations loaded on demand
- **Caching**: Script specifications cached in memory
- **Efficient Validation**: Unicode block lookups optimized
- **Batch Processing**: Multiple terms processed simultaneously

### Extensibility
- **Custom Scripts**: Add new writing systems via Unicode blocks
- **Filtering Rules**: Extend DNT filtering logic
- **Validation Methods**: Custom script validation functions
- **Precedence Rules**: Modify termbase/DNT priority

## Future Enhancements

- **Multi-script Support**: Languages with mixed writing systems
- **Context-Aware DNT**: Dynamic DNT based on content type
- **Quality Learning**: Improve filtering based on user feedback
- **Script Detection**: Automatic script identification for unknown text
