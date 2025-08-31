# CI Guardrails Setup Guide

This guide explains how to set up the Stage 0 guardrails in GitHub to prevent accidental changes to the translator behavior.

## Overview

The Stage 0 Guardrails workflow runs two critical checks:
1. **Stage 0 Tests**: Ensures prompt snapshots and parity tests pass unchanged
2. **Prompt Integrity Check**: Detects any modifications to prompt strings in `translator.py`

## Setup Steps

### 1. Enable the Workflow

The workflow file `.github/workflows/stage0-guardrails.yml` is already created and will run automatically on:
- Pull requests to `main`/`master`
- Direct pushes to `main`/`master`

### 2. Configure Branch Protection

1. Go to your GitHub repository
2. Navigate to **Settings** → **Branches**
3. Click **Add rule** for the `main` branch
4. Configure the following:

#### Basic Settings
- **Branch name pattern**: `main` (or `master`)
- ✅ **Require a pull request before merging**
- ✅ **Require approvals**: Set to at least 1
- ✅ **Dismiss stale PR approvals when new commits are pushed**

#### Status Checks
- ✅ **Require status checks to pass before merging**
- ✅ **Require branches to be up to date before merging**
- In the search box, type: `Stage 0 Guardrails`
- Select the workflow when it appears

#### Additional Settings
- ✅ **Restrict pushes that create files that match the specified pattern**
- ✅ **Require linear history** (optional, but recommended)

### 3. Test the Setup

1. Create a test branch
2. Make a small change to `translator.py`
3. Create a PR against `main`
4. Verify the Stage 0 Guardrails workflow runs
5. Verify the PR cannot be merged until the workflow passes

## What Happens When Guardrails Fail

### Stage 0 Tests Fail
- The workflow will show which specific test failed
- Check the test output for details
- Fix the issue and push again
- The workflow will re-run automatically

### Prompt String Changes Detected
- The workflow will fail with a message about changes in `translator.py`
- Review the changes to ensure they don't modify AI prompts
- If changes are intentional and safe, you may need to update the Stage 0 tests
- If changes are accidental, revert them

## Local Testing

Before pushing, run the guardrails locally:

```bash
# Run Stage 0 tests
pytest tests/test_prompts_snapshot.py -q
pytest tests/test_parity_io.py -q

# Check for prompt changes (if you have the base commit)
git diff --exit-code -w -- srt_translator/core/translator/translator.py <base-commit>
```

## Troubleshooting

### Workflow Not Appearing in Status Checks
- Ensure the workflow file is in the correct location: `.github/workflows/`
- Check that the workflow has run at least once
- Verify the workflow file syntax is correct

### Tests Passing Locally but Failing in CI
- Check Python version compatibility
- Verify all dependencies are installed in CI
- Check for environment-specific issues

### False Positives in Prompt Check
- The `-w` flag ignores whitespace changes
- Only actual content changes will trigger failures
- Review the git diff output to understand what changed

## Maintenance

### Updating Stage 0 Tests
If you need to modify the Stage 0 tests (e.g., after intentional prompt changes):
1. Update the test files
2. Ensure they pass locally
3. Push and verify CI passes
4. Update this documentation if needed

### Workflow Updates
The workflow file can be updated as needed, but ensure:
- Stage 0 tests continue to run
- Prompt integrity check remains in place
- All existing protections are maintained
