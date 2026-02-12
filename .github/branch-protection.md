# Branch Protection Rules for main/master
# This file documents the required CI checks for merging

## Required Status Checks
- **Stage 0 Guardrails** must pass before merging
  - Runs prompt snapshot tests
  - Blocks merge if tests fail

## What This Protects Against
1. **Accidental prompt modifications** that could change AI behavior
2. **Breaking changes** to the core translation logic
3. **Behavior drift** from the established Stage 0 baseline

## How to Use
1. Create a pull request against main/master
2. The Stage 0 Guardrails workflow will run automatically
3. All checks must pass before the PR can be merged
4. If tests fail, fix the issues and push again

## Local Testing
Before pushing, run locally to ensure CI will pass:
```bash
pytest tests/test_prompts_snapshot.py -q
```
