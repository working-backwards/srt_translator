Absolutely — here’s the detailed, **single-source-of-truth spec** you asked for, written so you (and Cursor) can implement and verify it without ambiguity. I’ve based it on the files you shared (`compiler.py`, `report.py`, `presenters/eval_html/build.py`, `main_window.py`, `translation_worker.py`, `app.py`, plus recent `report_v1.json`, `eval_report.json`, `eval_report.md/html`). Where I’m missing full code (several files were truncated), I explicitly flag what to confirm before coding.

---

# Unified Evaluation & Reporting Spec (v1)

## 1) Desired Unified Reporting Generation and Evaluation

### 1.1 Goals

* **Single authoritative data model**: `report_v1.json` is the only input the **presenters** (MD + HTML) read.
* **Deterministic, fail-fast**: If required files/keys are missing, the pipeline fails with a clear error; no partial artifacts.
* **One-pass orchestration**: No double-builds and no presenters reading evaluator internals.
* **Same content, two formats**: MD and HTML convey the same decisions, punch list, KPIs, file statuses, and lexicon summaries.

### 1.2 End-to-end pipeline (GUI & CLI)

#### 1) Translation finishes

* Translation writes translated SRTs to the batch directory.
* Then runs the **SRT fixer**.

#### 2) Run the evaluator

* **Input:** batch root (includes translated SRTs) and `artifacts/ai_config.json`.
* **Output:** `artifacts/eval_report.json` (strict v1 shape – see §2.4).

#### 3) Compile the unified report

* **Input:** `artifacts/eval_report.json` and `artifacts/ai_config.json`.
* **Compiler:** `srt_translator/report/compiler.py`.
* **Output:** `artifacts/report_v1.json` (the *only* source for presenters).

#### 4) Render reports (presenters)

* **MD presenter**: reads only `report_v1.json`, writes `artifacts/eval_report.md`.
* **HTML presenter**: reads only `report_v1.json`, writes `artifacts/eval_report.html`.

#### 5) GUI integration

* GUI should:

  * Call evaluator → compiler → presenters in this exact order.
  * **Do not** call the HTML presenter a second time after the orchestrator has already run it (no double-build).
  * After success, show buttons/links to open `eval_report.html` and `eval_report.md`.
  * Log the four paths: `eval_report.json`, `report_v1.json`, `eval_report.md`, `eval_report.html`.

#### 6) CLI integration

* CLI `eval` path calls the same orchestration (evaluator → compiler → presenters), writing into `artifacts/`.
* Optional flag `--report html|md|both|none` should still be respected, but when `html` or `md` are requested, the presenter still reads only `report_v1.json`.

### 1.3 File locations (mandatory)

* `artifacts/ai_config.json` (authoritative)
* `artifacts/eval_report.json` (evaluator output)
* `artifacts/report_v1.json` (compiler output; canonical for presenters)
* `artifacts/eval_report.md` (MD presenter)
* `artifacts/eval_report.html` (HTML presenter)

> **Important:** There must be **no lookups** for `ai_config.json` in the batch root. Presenters and compiler never read evaluator internals directly, only `report_v1.json`.

---

## 2) The Report: Sections, Definitions, and Schema

### 2.1 Sections (both MD and HTML, same content/order)

1. **Decision Banner + One-liner**

   * **Pass** ✅ “Everything looks great. Your translated files are ready to use.”
   * **Review** ⚠️ “We found {E} errors and {W} warnings. Fix the items in the Punch List below.”
   * **Fail** ❌ “We found {E} errors that must be fixed before publishing.”

2. **Punch List** (actionable items for creators, grouped)

   * **Errors** (blocking)
   * **Warnings** (non-blocking)
   * Each item:

     * File, language, cue/subtitle index (or range)
     * Short description (human-friendly)
     * **Suggested fix** (plain-language steps)
     * **Context** blocks (source ±2, target ±2) when relevant

3. **File Status by Language**

   * Table: Language → per-file status (✅ Ready | ⚠️ Review | ❌ Blocked) with counts and totals.

4. **KPI Summary**

   * Files total, Languages total, Issues total, Per-type counts (e.g., missing translation, placeholder mismatch, untranslated after DNT, timing fail, parity issue), plus any % metrics you currently emit (normalized formatting).

5. **Lexicons**

   * **DNT Terms**: count; show up to N items; “None” when empty.
   * **Termbases**: per language counts; show up to N example entries; “None” or “No violations found” as appropriate.

6. (Optional) **Appendices**

   * Full listings (if you want a deeper drill-down for power users later).

### 2.2 Error/Warning taxonomy

| Code                     | Level   | Description (creator-facing)                                       | Suggested Fix (plain language)                                                                                                                                    |
| ------------------------ | ------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `missing_translation`    | Warning | Target cue is empty with empty neighbors and substantial source (≥12 chars). | Copy the **target** and **source** contexts below into your AI assistant; ask to translate target → source language; compare with source; merge/adjust as needed. |
| `timing_fail`            | Error   | Subtitle timing overlaps or exceeds limits.                        | Use your subtitle editor to adjust timing so cues don’t overlap and respect duration limits.                                                                      |
| `parity_issue`           | Warning | Target length/pace mismatches source (may hurt readability).       | Rephrase target to a similar idea density and line breaks; keep critical terms consistent with termbase.                                                          |
| `placeholder_mismatch`   | Error   | Placeholder indices mismatched between source and target.          | Fix the placeholder indices to match source numbering; then regenerate the cue translation if needed.                                                             |
| `termbase_violation`     | Warning | A term should use the canonical translation but doesn’t.           | Replace with the canonical translation from the termbase; re-read for fluency.                                                                                    |

> You can expand this list as needed; the key is **consistent classification** and a **creator-friendly suggested fix**.

### 2.3 `report_v1.json` (authoritative schema)

**Top-level shape:**

```json
{
  "version": "1.0.0",
  "decision": "pass | review | fail",
  "one_liner": "string",
  "totals": {
    "files_total": 0,
    "languages_total": 0,
    "issues_total": 0
  },
  "kpis": {
    "issue_counts": {
      "missing_translation": 0,
      "timing_fail": 0,
      "parity_issue": 0,
      "placeholder_mismatch": 0,
      "termbase_violation": 0
    },
    "other_metrics": {
      "...": "numbers or strings as needed"
    }
  },
  "file_status": {
    "ar": { "File A.srt": "ready|review|blocked", "File B.srt": "..." },
    "ja": { "File A.srt": "..." }
  },
  "sections": {
    "errors": [
      {
        "type": "placeholder_mismatch",
        "language": "ar",
        "file": "File A.srt",
        "cue": 103,
        "message": "Placeholder index mismatch",
        "suggested_fix": "Update target placeholders to match source indices.",
        "context": {
          "source": { "prev2": "...", "current": "...", "next2": "..." },
          "target": { "prev2": "...", "current": "", "next2": "..." }
        }
      }
    ],
    "warnings": [
      {
        "type": "missing_translation",
        "language": "ar",
        "file": "File A.srt",
        "cue": 294,
        "message": "Target cue empty but translation likely present nearby.",
        "suggested_fix": "Copy target+source contexts to your AI assistant...",
        "context": { ... }
      }
    ]
  },
  "lexicons": {
    "dnt": { "count": 14, "examples": ["DMAIC", "Weekly Business Review", "..."] },
    "termbase": {
      "ar": { "count": 23, "examples": ["input metrics", "customer experience", "..."] },
      "ja": { "count": 23, "examples": ["...", "..."] }
    }
  }
}
```

**Determinism rules:**

* Sort language codes ascending.
* Sort filenames ascending.
* When lists are unordered semantically (DNT, examples), sort ascending.
* Normalize numbers (e.g., whole numbers, 1 decimal for percentages).

### 2.4 `eval_report.json` (strict evaluator output)

* Minimal rollup the **compiler** needs to produce `report_v1.json`. It **does not** contain suggested-fix prose.
* Must include counts per error code, per-language/per-file issue arrays with enough data to produce the punch list.
* **Required top-level keys** (strict):

  * `files_total`, `languages_total`, `issues_total`
  * `issue_counts` (by code)
  * `per_language` → `{ lang: { files: { path: { issues: [ { type, cue, … }, … ] } } }`
* The exact shape can be narrower than `report_v1.json`, but **never** broader; the compiler owns enrichment/mapping.

---

## 3) Variations: GUI vs CLI

* **Same orchestration**: evaluator → compiler → presenters.
* **GUI**:

  * After success, it **does not** call any presenter again (no double HTML build).
  * Emits paths (log + UI buttons) to the four artifacts.
* **CLI**:

  * Same outputs to `artifacts/`.
  * `--report` flag controls whether the presenters are called, but presenters still read only `report_v1.json`.

---

## 4) Source Tree (all files involved)

> ✅ = provided/uploaded by you (some truncated); 🔍 = please confirm full content before coding

* **Evaluator orchestration & writers**

  * 🔍 `srt_translator/eval/report.py` (writes `eval_report.json`; orchestrates compiler & presenters; writes MD/HTML)
  * 🔍 `srt_translator/eval/runner.py` (or wherever evaluator core lives) — produces in-memory rollup for `_write_json_report`
  * 🔍 `srt_translator/core/main.py` (calls evaluator and SRT fixer)

* **Compiler (authoritative)**

  * ✅ `srt_translator/report/compiler.py` (reads `eval_report.json` + `ai_config.json` → writes `report_v1.json` only)

* **Presenters**

  * ✅ `srt_translator/presenters/eval_html/build.py` (reads `report_v1.json` → writes `eval_report.html`)
  * 🔍 `srt_translator/presenters/md/build.py` (if not present, create) (reads `report_v1.json` → writes `eval_report.md`)

* **GUI**

  * ✅ `srt_translator/gui/main_window.py` (post-translation hook; must not double-call HTML presenter)
  * ✅ `srt_translator/gui/workers/translation_worker.py` (orchestrates evaluator → compiler → presenters)
  * 🔍 `srt_translator/gui/ui/ai_config_section.py` (for DNT/termbase gen UX)

* **CLI**

  * ✅ `srt_translator/cli.py` or `srt_translator/app.py` (invoke the same orchestration)

* **Schema / utils**

  * ✅ `srt_translator/report/schema.py` (if you keep a typed schema / dataclass / TypedDict)
  * ✅ `srt_translator/report/tools.py` (helpers used by compiler/presenters)
  * ✅ `srt_translator/report/assemble.py` (if used; otherwise remove)

* **Tests**

  * `tests/test_eval_system.py` (end-to-end orchestration)
  * `tests/test_report_compiler.py` (compiler unit tests)
  * `tests/test_presenters_html.py`, `tests/test_presenters_md.py` (rendering sanity)
  * Fixtures:

    * `tests/fixtures/eval_report_min.json`
    * `tests/fixtures/ai_config_min.json`
    * `tests/fixtures/report_v1_expected.json` (small)

---

## 5) Translation batch `artifacts/` structure

```
translation-batch-YYYYMMDD_HHMMSS_/
├─ originals/                       # (if you keep originals)
├─ translations/                    # per-language output SRTs
└─ _artifacts/
   ├─ ai_config.json                # authoritative lexicon/config
   ├─ eval_report.json              # evaluator output (strict v1)
   ├─ report_v1.json                # compiler output (authoritative for presenters)
   ├─ eval_report.md                # presenter (MD)
   ├─ eval_report.html              # presenter (HTML)
   └─ logs/                         # optional, if you keep per-step logs
```

> Nothing reads files from outside `_artifacts/` during evaluation/reporting. No copying from batch root.

---

## 6) Gaps vs. this Spec (what to change)

> These are based on your logs and the partial code you shared. Please confirm the marked areas before editing.

1. **Double HTML build (must remove)**

   * Logs show: “Generated HTML report …” (presenter) **and then** GUI tries to build HTML again and fails on mismatched keys.
   * **Fix:** In `gui/main_window.py` (and/or `gui/workers/translation_worker.py`), **only** call presenters from the orchestrator (`eval/report.py`). **Remove any second call** to `presenters/eval_html/build.py` in GUI post-hook.

2. **Presenters must read `report_v1.json` only**

   * Your new HTML presenter already expects compiled keys like `decision`, `kpis`, `file_status`, `lexicons`.
   * **Fix:** Ensure HTML and MD presenters both take **only** `report_v1.json`. Remove any paths that pass `eval_report.json` to a presenter.

3. **Compiler must populate Punch List**

   * Your last `report_v1.json` snippet had `"sections": { "errors": [], "warnings": [] }`. That’s why HTML showed no Punch List.
   * **Fix:** In `report/compiler.py`, **map each issue** from `eval_report.json` into Errors or Warnings, convert missing\_translation → Warning, and attach creator-friendly `suggested_fix` + context when available. Sort deterministically.

4. **Evaluator output strictness**

   * Earlier failures were from missing keys (`files_total`, `languages_total`, `issues_total`).
   * **Fix:** Ensure `eval_report.json` includes minimal required keys for the compiler. Do **not** put presenter prose in this file.

5. **AI config location (no root fallbacks)**

   * Logs showed attempts to copy `ai_config.json` from batch root.
   * **Fix:** Remove fallback logic; always read `artifacts/ai_config.json`. If not found, fail-fast.

6. **GUI orchestration order**

   * Ensure sequence is strictly: `write_evaluator_json()` → `compile_report()` → `write_md()` → `write_html()`.
   * GUI should only **announce** finished artifact paths; it should not call presenters again.

7. **Tests**

   * Update fixtures and tests to this flow:

     * Use a **valid** `eval_report.json` (strict) + `ai_config.json` fixture.
     * Unit-test **compiler** → assert expected `report_v1.json`.
     * Unit-test **presenters** → read that `report_v1.json` and assert key strings exist (“Punch List”, decisions, counts).
     * E2E orchestrator test → assert all four artifacts are created, and that `report_v1.json.sections.errors` (or warnings) contain at least one item for a known failing cue.

---

## What I still need to review (please share if you want me to verify before code changes)

* **Full content** (not truncated) of:

  * `srt_translator/eval/report.py`
  * `srt_translator/report/compiler.py`
  * `srt_translator/presenters/eval_html/build.py`
  * `srt_translator/presenters/md/build.py` (if it doesn’t exist yet, we’ll create it)
  * `srt_translator/gui/main_window.py` (section after evaluation completes — the path that currently double-calls HTML)
  * `srt_translator/gui/workers/translation_worker.py` (the `run()` orchestration)

With those, I can produce Cursor-ready PR packets that:

* Remove the double-call entirely
* Enforce the single-source flow
* Populate Punch List deterministically
* Make MD and HTML show the same content
* Delete legacy paths and fallbacks
* Update/align tests & fixtures

If you’d like, I can draft the exact commit sequence (packetized) next, but I wanted to give you the full, traceable spec first so we’re finally converging.
