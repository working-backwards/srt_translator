# Documentation Audit (2026-02-06)

## Status: Restructure Complete

The documentation has been reorganized into audience-separated folders.

### What Changed

- **Deleted:** 4 obsolete files
- **Merged:** 2 security docs → 1
- **Moved:** 16 files to new locations
- **Created:** 2 new index files

## Summary

- **Files reviewed:** 22 (in `docs/`, excluding `docs/design/`)
- **Keep:** 15
- **Delete:** 4
- **Merge:** 2 → 1
- **Rename:** 2

---

## GitHub Standards Compliance

### Root-Level Files (GitHub-recognized) ✅

| File | Status | Notes |
|------|--------|-------|
| `README.md` | ✅ Correct | Repo homepage |
| `LICENSE` | ✅ Correct | MIT license |
| `CONTRIBUTING.md` | ✅ Correct | Linked on PRs/issues |
| `CODE_OF_CONDUCT.md` | ✅ Correct | Community Profile |
| `SUPPORT.md` | ✅ Correct | Community Profile |
| `CHANGELOG.md` | ✅ Correct | Not GitHub-special but good practice |

### .github/ Folder ✅

| File | Status | Notes |
|------|--------|-------|
| `SECURITY.md` | ✅ Correct | Shows in Security tab (vulnerability reporting) |
| `dependabot.yml` | ✅ Correct | Dependency updates |
| `PULL_REQUEST_TEMPLATE.md` | ✅ Correct | PR template |
| `ISSUE_TEMPLATE/` | ✅ Correct | Issue templates |
| `workflows/` | ✅ Correct | GitHub Actions |
| `release-drafter.yml` | ✅ Correct | Release automation |
| `branch-protection.md` | ⚠️ Info only | Documentation, not GitHub-recognized |

### Key Finding

Two security-related files exist with **different purposes** (resolved):
- `.github/SECURITY.md` → Vulnerability reporting policy (GitHub-recognized)
- `docs/user-guide/executable-safety.md` → Executable distribution safety (renamed from SECURITY.md)

---

## Full Audit Table

| File | Purpose | Audience | Status | Recommendation | Notes |
|------|---------|----------|--------|----------------|-------|
| ARCHITECTURE.md | High-level architecture + evaluation subsystem | Dev | Current | Keep | Good overview |
| arch-translator.md | Translator core (batching, retries, DNT) | Dev | Duplicate | **Delete** | Nearly identical to translation_architecture.md |
| translation_architecture.md | Translator core (more detailed) | Dev | Current | Keep | Superset of arch-translator.md |
| CI_GUARDRAILS_SETUP.md | CI guardrails setup | Dev | Current | Keep | |
| CODING_STANDARDS.md | Coding standards | Dev | Current | Keep | Not GitHub-special, move to developer/ |
| CREATOR_GUIDE.md | Understanding ai_config, reports | Creator | Current | Keep | Good companion to GUI manual |
| Customizing Your Termbase.md | Advanced termbase workflow with AI | Creator | Current | Keep | Untracked - needs commit |
| DEPENDENCY_INJECTION_REFACTOR.md | DI refactor history | Dev | Historical | **Delete** | Internal dev notes, not reference |
| GITHUB_SECURITY_SETUP.md | GitHub security setup | Dev | Current | **Merge** | Combine with SECURITY_QUICK_REFERENCE.md |
| GUI_USER_MANUAL.md | Comprehensive GUI guide | Creator | Current | Keep | Primary user doc |
| index.md | mkdocs landing page | Both | Current | Keep | Entry point |
| INSTALLATION.md | Installation guide | Both | Current | Keep | |
| POST_TRANSLATION_WORKFLOW.md | Post-translation pipeline details | Dev | Current | Keep | Very detailed, useful for devs |
| QUALITY_HARDENING.md | Quality features explanation | Both | Current | Keep | |
| quickstart.md | Quick start for GUI | Creator | Current | Keep | Good onboarding |
| reports.md | Evaluation reports overview | Both | Current | Keep | |
| SECURITY.md | Executable distribution safety | Creator | Current | **Rename** | → executable-safety.md (clarify purpose) |
| SECURITY_QUICK_REFERENCE.md | GitHub security quick ref | Dev | Current | **Merge** | Redundant with GITHUB_SECURITY_SETUP.md |
| STANDARDIZED_OUTPUT_IMPLEMENTATION.md | Standardized output internals | Dev | Historical | **Delete** | Implementation notes, not reference |
| TECHNICAL_FLOW_EXAMPLE.md | Translation flow example | Dev | Current | Keep | Good for understanding system |
| TERMINOLOGY_SYSTEM.md | Terminology system docs | Both | Current | Keep | |
| UNIFIED_REPORTS.md | Report format overview | Dev | Superseded | **Delete** | v2 is the complete spec |
| UNIFIED_REPORTS - v2.md | Complete report spec | Dev | Current | **Keep & Rename** | Rename to unified-reports.md |

---

## Actions Summary

### Delete (5 files)
1. `arch-translator.md` - duplicate of translation_architecture.md
2. `DEPENDENCY_INJECTION_REFACTOR.md` - historical implementation notes
3. `STANDARDIZED_OUTPUT_IMPLEMENTATION.md` - historical implementation notes
4. `UNIFIED_REPORTS.md` - superseded by v2
5. `UNIFIED_REPORTS - v2.md` - content merged into post-translation.md

### Rename (1 file)
1. `SECURITY.md` → `user-guide/executable-safety.md`

### Merge (2 → 1)
- `GITHUB_SECURITY_SETUP.md` + `SECURITY_QUICK_REFERENCE.md` → `developer/github-security.md`

---

## Restructure Plan

### New Folder Structure

```
docs/
├── index.md                              # Landing page (both audiences)
│
├── getting-started/                      # Shared entry points
│   ├── installation.md                   # ← INSTALLATION.md
│   └── quickstart.md                     # ← quickstart.md
│
├── user-guide/                           # Creator docs (non-technical)
│   ├── index.md                          # NEW: User guide overview
│   ├── gui-manual.md                     # ← GUI_USER_MANUAL.md
│   ├── creator-guide.md                  # ← CREATOR_GUIDE.md
│   ├── customizing-termbase.md           # ← Customizing Your Termbase.md
│   ├── terminology.md                    # ← TERMINOLOGY_SYSTEM.md
│   ├── quality-features.md               # ← QUALITY_HARDENING.md
│   ├── reports.md                        # ← reports.md
│   └── executable-safety.md              # ← SECURITY.md (renamed)
│
├── developer/                            # Developer docs
│   ├── index.md                          # NEW: Developer overview
│   ├── architecture.md                   # ← ARCHITECTURE.md
│   ├── translation-core.md               # ← translation_architecture.md
│   ├── technical-flow.md                 # ← TECHNICAL_FLOW_EXAMPLE.md
│   ├── post-translation.md               # ← POST_TRANSLATION_WORKFLOW.md
│   ├── unified-reports.md                # ← UNIFIED_REPORTS - v2.md
│   ├── coding-standards.md               # ← CODING_STANDARDS.md
│   ├── ci-guardrails.md                  # ← CI_GUARDRAILS_SETUP.md
│   └── github-security.md                # ← GITHUB_SECURITY_SETUP.md + SECURITY_QUICK_REFERENCE.md (merged)
│
└── design/                               # Keep as-is (internal reference)
    └── ...
```

### File Movement Map

| Current Location | New Location |
|------------------|--------------|
| `index.md` | `index.md` (no change) |
| `INSTALLATION.md` | `getting-started/installation.md` |
| `quickstart.md` | `getting-started/quickstart.md` |
| `GUI_USER_MANUAL.md` | `user-guide/gui-manual.md` |
| `CREATOR_GUIDE.md` | `user-guide/creator-guide.md` |
| `Customizing Your Termbase.md` | `user-guide/customizing-termbase.md` |
| `TERMINOLOGY_SYSTEM.md` | `user-guide/terminology.md` |
| `QUALITY_HARDENING.md` | `user-guide/quality-features.md` |
| `reports.md` | `user-guide/reports.md` |
| `SECURITY.md` | `user-guide/executable-safety.md` |
| `ARCHITECTURE.md` | `developer/architecture.md` |
| `translation_architecture.md` | `developer/translation-core.md` |
| `TECHNICAL_FLOW_EXAMPLE.md` | `developer/technical-flow.md` |
| `POST_TRANSLATION_WORKFLOW.md` | `developer/post-translation.md` |
| `UNIFIED_REPORTS - v2.md` | `developer/unified-reports.md` |
| `CODING_STANDARDS.md` | `developer/coding-standards.md` |
| `CI_GUARDRAILS_SETUP.md` | `developer/ci-guardrails.md` |
| `GITHUB_SECURITY_SETUP.md` | `developer/github-security.md` (merge) |
| `SECURITY_QUICK_REFERENCE.md` | (merged into above) |

### New Files to Create

| File | Purpose |
|------|---------|
| `user-guide/index.md` | Overview for creators: "Start here if you downloaded the app" |
| `developer/index.md` | Overview for developers: "Start here if you're contributing" |

---

## Updated mkdocs.yml

```yaml
site_name: SRT Translator
site_description: Free MIT-licensed SRT translation tool for creators and developers
site_url: https://workingbackwards.github.io/srt_translator/
repo_url: https://github.com/workingbackwards/srt_translator

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - content.code.copy
    - search.suggest
    - search.highlight
  palette:
    - media: "(prefers-color-scheme: light)"
      primary: indigo
      accent: indigo
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo

markdown_extensions:
  - admonition
  - toc:
      permalink: true
  - codehilite

nav:
  - Home: index.md

  - Getting Started:
      - Installation: getting-started/installation.md
      - Quick Start: getting-started/quickstart.md

  - User Guide:
      - Overview: user-guide/index.md
      - GUI Manual: user-guide/gui-manual.md
      - For Creators: user-guide/creator-guide.md
      - Custom Termbases: user-guide/customizing-termbase.md
      - Terminology System: user-guide/terminology.md
      - Quality Features: user-guide/quality-features.md
      - Understanding Reports: user-guide/reports.md
      - Executable Safety: user-guide/executable-safety.md

  - Developer Guide:
      - Overview: developer/index.md
      - Architecture: developer/architecture.md
      - Translation Core: developer/translation-core.md
      - Technical Flow: developer/technical-flow.md
      - Post-Translation: developer/post-translation.md
      - Report Format: developer/unified-reports.md
      - Coding Standards: developer/coding-standards.md
      - CI Guardrails: developer/ci-guardrails.md
      - GitHub Security: developer/github-security.md

extra:
  social:
    - icon: simple/github
      link: https://github.com/workingbackwards/srt_translator
```

---

## Execution Order

- [x] **Create folders:** `getting-started/`, `user-guide/`, `developer/`
- [x] **Create new index files:** `user-guide/index.md`, `developer/index.md`
- [x] **Move and rename files** (used `git mv` to preserve history)
- [x] **Merge security docs** into `developer/github-security.md`
- [x] **Delete obsolete files**
- [x] **Update `mkdocs.yml`**
- [x] **Update internal links** in all docs
- [ ] **Check accuracy** against codebase
- [ ] **Test with `mkdocs serve`**
- [ ] **Commit and push**
