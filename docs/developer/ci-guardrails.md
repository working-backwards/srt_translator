# CI Guardrails

This document explains the Stage 0 guardrails that protect the translator from accidental regressions.

## Why These Guardrails Exist

AI prompts are the most critical code in this application. A small, unintended change can:

- Silently break translations across all languages
- Introduce subtle quality regressions that only appear in production
- Cause inconsistent behavior that's hard to diagnose
- Violate the "byte-for-byte identical" output guarantee the codebase depends on

The guardrails catch these problems before they reach the main branch.

## How the Guardrails Work

The Stage 0 workflow runs prompt snapshot tests on every PR to main/master.

### Prompt Snapshot Tests

These tests capture the exact output of each prompt and compare it against a known-good "golden" snapshot. If a prompt change alters the output in any way, the test fails.

This catches:
- Intentional changes that need review
- Accidental edits (typos, whitespace, formatting)
- Regressions from refactoring

## Making Changes

Changes to prompts or translator code are allowed as long as:

1. All tests pass (or snapshots are intentionally updated)
2. A reviewer approves the PR

### Changing a Prompt

1. Create a feature branch
2. Edit the prompt file in `srt_translator/prompts/`
3. Run tests locally—they will fail (this is expected)
4. Update the snapshots:
   ```bash
   pytest tests/test_prompts_snapshot.py --snapshot-update
   ```
5. Verify tests now pass:
   ```bash
   pytest tests/test_prompts_snapshot.py -q
   ```
6. In your PR description, explain:
   - What changed and why
   - Which languages or scenarios are affected
   - How you verified the new behavior

Reviewers can examine the snapshot diff to evaluate whether the change is appropriate.

### Changing Translator Code

The same process applies to `translator.py` or other translator code. Make your changes, ensure the snapshot tests pass, and document the change in your PR.

## Local Testing

Before pushing, run the guardrails locally:

```bash
pytest tests/test_prompts_snapshot.py -q
```

## GitHub Setup

### Enable the Workflow

The workflow file `.github/workflows/stage0-guardrails.yml` runs automatically on:
- Pull requests to `main`/`master`
- Direct pushes to `main`/`master`

### Configure Branch Protection

1. Go to **Settings** → **Branches**
2. Add a rule for `main`:
   - **Require a pull request before merging**
   - **Require approvals**: At least 1
   - **Require status checks to pass**: Select `Stage 0 Guardrails`

## Troubleshooting

### Tests Pass Locally but Fail in CI

- Check Python version compatibility
- Verify all dependencies are installed in CI
- Check for environment-specific issues (line endings, locale)

### Snapshot Differences You Don't Understand

Run with verbose output to see the exact diff:

```bash
pytest tests/test_prompts_snapshot.py -v
```
