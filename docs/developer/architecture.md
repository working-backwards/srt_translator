# SRT Translator Architecture

This document describes the high-level architecture of the SRT Translator project.

## Overview

The SRT Translator is designed with a clean separation between:
- **Core Translation Engine**: Pure functions that process SRT files
- **Interface Layers**: CLI and GUI that collect configuration and drive the core
- **Evaluation System**: Post-processing analysis of translation quality

## Core Architecture

### Translation Pipeline
```
CLI/GUI → TranslationConfig → Core Engine → Batch Output
     ↑           ↑              ↑            ↑
  Collects    Contains      Processes    Creates
  params      ALL params    SRT files    batch dir
```

### Configuration Flow
- **Entry points** (CLI/GUI) collect user preferences and environment data
- **TranslationConfig** object contains all runtime configuration
- **Core engine** reads only from TranslationConfig - no global state
- **Batch output** includes frozen configuration snapshot in `ai_config.json`

## Evaluation Subsystem (v1.0)

### Purpose
The evaluation subsystem provides post-translation quality analysis and reporting. It operates independently of the translation process, reading only batch artifacts to ensure reproducibility.

### Input Contract
The evaluator reads **only** files on disk from the batch directory:

**REQUIRED inputs:**
- `batch_root/artifacts/ai_config.json` - Schema-versioned configuration snapshot
- `batch_root/originals/` - Source SRT files
- `batch_root/<lang>/` - Translated SRT files for each target language (e.g., `batch_root/es/`, `batch_root/fr/`)

**OPTIONAL inputs (inside ai_config.json):**
- `dnt_terms` - Batch-wide "Do Not Translate" terms list
- `termbase` - Per-language termbase mappings (source → target)

### Required vs Optional Policy
- **Required inputs missing/invalid** → ERROR and STOP evaluation. No fallbacks.
- **Optional inputs missing/empty** → INFO log and CONTINUE evaluation. Report coverage explicitly.

### Data Normalization
The evaluator normalizes the `ai_config.json` shape to internal formats:

```python
# Input (ai_config.json)
{
  "dnt_terms": ["Operating Plan", "Module"],
  "termbase": {
    "es": {"Operating Plan": "Plan Operativo"},
    "fr": {"Module": "Module"}
  }
}

# Normalized (internal)
{
  "dnt_terms": ["Operating Plan", "Module"],
  "termbase": {
    "es": [{"source": "Operating Plan", "target": "Plan Operativo"}],
    "fr": [{"source": "Module", "target": "Module"}]
  }
}
```

### Artifacts for Audit Only
Any files under `artifacts/<lang>/` (e.g., `dnt_summary.json`, `termbase_summary.json`) are **derived outputs for auditing only**. The evaluator never requires nor prefers these files as inputs.

### Reporting Requirements
The `eval_report.json` MUST include:
- `config_source: "ai_config.json"` - Source of configuration data
- `dnt_coverage: "present"|"none"` - Whether DNT terms were available
- `termbase_coverage: "full"|"partial"|"none"` - Coverage across target languages
- `termbase_entry_counts: {"es": 5, "fr": 3}` - Per-language entry counts

### Logging Requirements
All evaluation logs (INFO/ERROR) MUST appear in:
- **Console output** - For real-time monitoring
- **Batch log file** - For permanent record and debugging

This ensures that coverage decisions and evaluation results are captured in the same log file as the translation process.

### Independence from TranslationConfig
The evaluator **MUST NOT** import or depend on `TranslationConfig` objects. It reads only batch artifacts to ensure:
- **Reproducibility**: Evaluation can be re-run on old batches
- **Decoupling**: Changes to translation config don't affect evaluation
- **Auditability**: Complete configuration snapshot preserved in batch

## Quality Assurance

### Translation Quality
- Character-per-second (CPS) analysis
- Placeholder consistency checks
- DNT term coverage analysis
- Termbase collision detection

### Batch Validation
- File structure verification
- Configuration completeness checks
- Artifact generation validation

## Security Considerations

### Configuration Isolation
- CLI reads API key from environment or .env file
- GUI stores API key in local app settings via QSettings (`IniFormat`, plaintext); the SRT Translator does not use OS credential storage
- All translation configuration frozen in batch artifacts
- No external API calls during evaluation

### Data Handling
- SRT content processed in memory during translation
- Translated files written to batch output directory
- API key persisted locally (not included in batch artifacts)
