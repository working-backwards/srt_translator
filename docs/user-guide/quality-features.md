# Quality Hardening Features

## Overview

The SRT Translator includes advanced quality hardening features that automatically improve translation results by filtering problematic content and enforcing consistency rules. These features work transparently in the background to ensure high-quality, professional translations.

## Key Features

### 1. Automatic DNT Term Filtering

**Problem**: Numeric and number-like terms in DNT lists can prevent proper localization.

**Example**:
- **Before**: "300 milliseconds" in DNT → stays as "300 milliseconds" in all languages
- **After**: "300 milliseconds" filtered out → becomes "300毫秒" in Chinese, "300 milisegundos" in Spanish

**What Gets Filtered**:
- Pure numbers: "300", "6.7", "2025"
- Number-like patterns: "300 milliseconds", "6.7 seconds", "2025 Q1"
- Time formats: "1:30", "2:45"
- Percentages: "15%", "25.5%"
- Currency: "$50", "€100"

**Benefits**:
- Better localization of numeric content
- Improved readability in target languages
- Maintains important non-numeric DNT terms (brands, names, acronyms)

### 2. DNT/Termbase Precedence

**Problem**: Conflicts between DNT terms and termbase entries can cause inconsistent behavior.

**Solution**: The system uses intelligent precedence based on term type:

- **Hard-preserve terms** (acronyms, tech codes like "API", "GPU", "NASA") always remain untranslated
- **Soft-preserve terms** can be overridden by termbase entries when a translation is specified

**Example**:
- **Hard-preserve DNT term**: "API" → always stays "API" (termbase cannot override)
- **Soft-preserve DNT term**: "machine learning" with termbase entry "机器学习" → uses termbase translation
- **DNT-only term**: "S-Team" with no termbase entry → stays untranslated

**Benefits**:
- Consistent behavior across all languages
- Flexibility to translate domain terms while protecting technical codes
- Clear hierarchy: Hard-preserve DNT > Termbase > Soft-preserve DNT > Default translation

### 3. Relevant Termbase Injection

**Problem**: Injecting all termbase entries can cause AI hallucinations and reduce relevance.

**Solution**: Only inject termbase entries that are actually present in the current subtitle text.

**Example**:
- **Full termbase**: 50 terms across all business domains
- **Current subtitle**: Only contains 15 relevant terms
- **Result**: Only 15 relevant terms are injected, improving translation quality

**Benefits**:
- Reduced AI hallucinations
- More focused and relevant translations
- Better performance and cost efficiency

### 4. Termbase Size Capping

**Problem**: Very large termbases can overwhelm the AI and reduce translation quality.

**Solution**: Automatic capping at 30 terms per language, prioritizing important terms.

**Benefits**:
- Consistent translation quality
- Predictable API costs
- Focus on most important terminology

## Technical Implementation

### DNT Term Processing

```python
def filter_dnt_terms(self, dnt_terms: List[str]) -> List[str]:
    """Filter DNT terms to exclude numeric and number-like items"""
    filtered_terms = []
    for term in dnt_terms:
        if not self._is_pure_number(term) and not self._is_number_like(term):
            filtered_terms.append(term)
    return filtered_terms
```

### Tolerant Matching

```python
def _compile_tolerant_patterns(self):
    """Compile regex patterns for tolerant matching of Latin keys"""
    for term in self.dnt_terms:
        if self._is_latin_text(term):
            # Handle space/hyphen variations and possessives
            base_term = re.sub(r'[\s\-]+', r'[\s\-]+', re.escape(term))
            possessive_pattern = f"{base_term}['s]?"
            self.tolerant_patterns[term] = re.compile(possessive_pattern, re.IGNORECASE)
```


## Output Transparency

### Enhanced Output Files

The quality hardening features provide complete transparency through enhanced output files:

**`dnt_terms.json`**:
```json
{
  "description": "DNT terms processing summary",
  "user_provided": {
    "description": "Original DNT terms as provided by user",
    "terms": ["S-Team", "300 milliseconds", "2025", "API"],
    "count": 4
  },
  "filtered_for_translation": {
    "description": "DNT terms actually used during translation",
    "terms": ["S-Team", "API"],
    "count": 2,
    "filtered_out": ["300 milliseconds (filtered: numeric/number-like)", "2025 (filtered: numeric/number-like)"],
    "filtering_reason": "Removed numeric and number-like terms for better localization"
  }
}
```

**`termbase.json`**:
```json
{
  "description": "Termbase processing summary",
  "user_provided": {
    "description": "Original termbase as provided by user",
    "languages": { "es": {...}, "zh": {...} }
  },
  "filtered_for_translation": {
    "description": "Termbase actually used during translation",
    "languages": { "es": {...}, "zh": {...} },
    "collisions_removed": {
      "es": {
        "filtered_out": ["S-Team"],
        "reason": "DNT collision"
      }
    },
    "filtering_reason": "Removed termbase entries that conflict with DNT terms"
  }
}
```

**`manifest.json`**:
```json
{
  "processing_summary": {
    "dnt_terms": {
      "provided": 4,
      "used": 2,
      "filtered": 2
    },
    "termbase": {
      "provided_entries": 25,
      "used_entries": 22,
      "collisions_resolved": 3
    },
    "quality_improvements": [
      "Numeric DNT terms automatically filtered",
      "DNT precedence enforced over termbase",
      "Relevant-only termbase injection"
    ]
  }
}
```

## Configuration

### Automatic vs. Manual

**Automatic (Recommended)**:
- Quality hardening features are enabled by default
- No configuration required
- Best results for most users

**Manual Control** (Future Enhancement):
- Option to disable specific filtering rules
- Custom filtering thresholds
- Manual override for specific terms

## Best Practices

### DNT Term Management

1. **Focus on Brand/Name Terms**: Use DNT for company names, product names, technical acronyms
2. **Avoid Numeric Content**: Let numeric terms be translated for better localization
3. **Regular Review**: Periodically review DNT terms to ensure they're still needed

### Termbase Management

1. **Quality Over Quantity**: Focus on important, frequently-used terms
2. **Language-Specific**: Consider cultural and linguistic differences
3. **Regular Updates**: Update termbase as your content evolves

### Monitoring Quality

1. **Review Enhanced Output**: Check the processing summaries after each translation
2. **Monitor Filtering Results**: Ensure the filtering is working as expected
3. **Track Improvements**: Use the transparency features to validate quality gains

## Troubleshooting

### Common Issues

**DNT Terms Not Being Preserved**:
- Check if the term is in your DNT list
- Verify the term isn't being filtered as numeric
- Check the enhanced output files for filtering details

**Termbase Entries Not Being Used**:
- Verify the term appears in your source text
- Check for DNT collisions in the enhanced output
- Ensure the termbase is properly configured for the target language

**Unexpected Filtering**:
- Review the enhanced output files for filtering details
- Check the processing summary for counts and reasons
- Verify the filtering rules are working as intended

### Getting Help

1. **Check Enhanced Output Files**: The detailed JSON files contain all the information about what happened
2. **Review Processing Summary**: The manifest.json shows high-level filtering results
3. **Check Logs**: Detailed logs show the step-by-step processing
4. **Contact Support**: If issues persist, the enhanced output files provide all the context needed for troubleshooting

## Future Enhancements

### Planned Features

1. **Custom Filtering Rules**: User-defined filtering criteria
2. **Filtering Analytics**: Historical tracking of filtering effectiveness
3. **Quality Metrics**: Automated quality scoring based on filtering results
4. **Advanced Matching**: More sophisticated pattern matching for complex terms

### Contributing

The quality hardening features are designed to be extensible. If you have ideas for additional filtering rules or quality improvements, please contribute to the project!

## Conclusion

The quality hardening features in the SRT Translator provide automatic, transparent improvements to translation quality while maintaining complete visibility into what's happening. These features work together to ensure professional, consistent translations that respect your brand and terminology while providing the best possible localization for your audience.
