# Current Session Context

**Last Updated**: 2026-01-29
**Branch**: feature/termbase-customization-doc
**Worktree**: romantic-neumann
**Active Tool**: TBD (user will decide after design review)

---

## Active Task

**Extract AI Prompts into Centralized Module** - Medium priority maintainability improvement

**Status**: Design Review

**Design**: `docs/design/JIRA_PROMPT_EXTRACTION.md`

**Approach**: Centralized Prompt Module — pure Python functions in `srt_translator/prompts/` package. No templates, no new dependencies. GUI prompt editing rejected due to fragility/support cost.

**Scope**: All 11 AI prompts across 4 source files (translator.py, diagnostics.py, language_detection.py, ai_config.py). API key validation test prompt excluded (health check, not an AI prompt).

---

## Implementation Plan

### Completed
- ✅ Prompt inventory: all 11 prompts catalogued with file paths, line numbers, and function signatures
- ✅ Design decision: centralized prompt module (pure Python functions)
- ✅ JIRA ticket created: `docs/design/JIRA_PROMPT_EXTRACTION.md`

### Pending Design Review
- ⏳ Create `srt_translator/prompts/` package (`__init__.py`)
- ⏳ Extract language detection prompt → `prompts/detection.py`
- ⏳ Extract translation prompts (3) → `prompts/translation.py`
- ⏳ Extract diagnostic prompts (3) → `prompts/diagnostics.py`
- ⏳ Extract config generation prompts (4) → `prompts/config.py`
- ⏳ Update call sites in `translator.py`, `diagnostics.py`, `language_detection.py`, `ai_config.py`
- ⏳ Snapshot tests for byte-for-byte prompt output verification
- ⏳ Run `pytest` and `ruff check .` — all green

---

## Recent Work History

### Extract AI Prompts (2026-01-29) - Design Review
- ✅ JIRA ticket created: `docs/design/JIRA_PROMPT_EXTRACTION.md`
- ⏳ Awaiting design review before implementation

### Qt Signal Handler Warning (2026-01-25) - In Progress
- ✅ JIRA ticket created: `docs/design/JIRA_SIGNAL_HANDLER_CLEANUP.md`
- ⏳ Implementation assigned to Cursor (Option B2: debug log-once)
- File to modify: `srt_translator/gui/main_window.py:540-546`

### DNT Corruption Bug (2026-01-25) - Completed/Handed Off
- ✅ Root cause analysis completed
- ✅ Defense-in-depth solution designed (3-layer validation)
- ✅ JIRA tickets created and shared with other developer
- 🔄 Implementation in progress by other developer

---

## Key Learnings / Architecture Notes

### QSettings Behavior (Critical Knowledge)
**Keep this section - it's useful for future work**

- **Type Preservation**: QSettings serializes Python objects faithfully
- **No Schema Validation**: QSettings doesn't validate data structure
- **Platform Differences**: Binary Registry (Windows) vs text plist (Mac) vs INI (Linux)
- **Persistence**: Corrupted data persists until explicitly cleared or overwritten

**Lesson**: Always validate data types when loading from QSettings, especially after Clear/Regenerate workflows.

### Prompt Extraction Design Notes
- 11 prompts across 4 files: `translator.py` (4), `diagnostics.py` (2), `language_detection.py` (1), `ai_config.py` (4)
- `ai_config.py` prompts use user-role only (no system prompts), unlike translation prompts which use system+user
- Most complex prompt: two-pass termbase in `ai_config.py` (lines 389-477) with 3 conditional blocks (`src_hint`, `soft_block`, `pass1_goal`/`pass2_goal`)
- Key risk: conditional logic (strict mode, tone hints, Chinese-specific, source-language hints, soft-alignment) must be preserved exactly
- **Decision**: `_render_items_for_prompt()` stays on translator class; prompt builders receive pre-rendered strings only
- **Decision**: No `helpers.py` — add only if a second shared helper emerges during implementation
- `json.dumps(ensure_ascii=False)` calls in config prompts must be preserved identically
- Snapshot tests only for this refactor; property tests deferred to future ticket

---

## Critical Files for Current Task

### Design Document
- `docs/design/JIRA_PROMPT_EXTRACTION.md` - Full specification with prompt inventory and implementation plan

### Files to Create
- `srt_translator/prompts/__init__.py`
- `srt_translator/prompts/translation.py`
- `srt_translator/prompts/diagnostics.py`
- `srt_translator/prompts/detection.py`
- `srt_translator/prompts/config.py`

### Files to Modify
- `srt_translator/core/services/language_detection.py` — replace inline prompt (lines 33-46)
- `srt_translator/core/translator/translator.py` — replace 4 inline prompts
- `srt_translator/core/translator/diagnostics.py` — move/replace 2 prompt functions
- `srt_translator/gui/ai_config.py` — replace 4 inline prompts; remove conditional block construction that moves into prompt builders

---

## Recent Changes (From This Session)

### New Files Created
- `.ai/prompts.md` - Prompt journal for tracking effective AI interactions
- `.ai/context.md` - This file
- `.ai/QUICK_START.md` - Quick reference guide
- `.ai/SETUP_COMPLETE.md` - Setup verification
- `.ai/AI_WORKFLOW_GUIDE.md` - Complete workflow documentation for reuse
- `docs/design/README.md` - Design docs organization
- `docs/design/JIRA_SIGNAL_HANDLER_CLEANUP.md` - Signal handler bug specification
- `docs/design/JIRA_PROMPT_EXTRACTION.md` - Prompt extraction design specification

---

## Notes for Other AI Tools

### If Using Cursor
1. Read this context file first
2. Follow `.cursorrules` for code standards (logging, architecture rules)
3. Run `ruff check .` before committing

### If Using ChatGPT
1. Copy relevant sections from this file for context
2. Use for high-level strategy discussion, not codebase-specific implementation
3. Good for: reviewing design approach, suggesting alternatives, writing docs

---

## Session Continuity

**How to Resume Work Later**:
1. Read this file top to bottom
2. Read `docs/design/JIRA_PROMPT_EXTRACTION.md` for current task details
3. Check Implementation Plan section for current status
4. Update "Last Updated" and "Active Tool" fields when starting new session

**Before Switching Tools**:
1. Update "Implementation Plan" section with current progress
2. Add any new findings to "Key Learnings" section
3. Note any blockers in "Questions / Blockers" section
4. Update "Last Updated" and "Active Tool" fields
