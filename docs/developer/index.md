# Developer Guide

Welcome to the SRT Translator Developer Guide. This section is for **developers** who want to understand the codebase, contribute, or extend the application.

## Getting Started

1. **[Setup](setup.md)** - Set up your development environment
2. **[Coding Standards](coding-standards.md)** - Code style and conventions

## Architecture

- **[Architecture Overview](architecture.md)** - High-level system design and evaluation subsystem
- **[Translation Core](translation-core.md)** - Batching, retries, DNT handling
- **[Technical Flow](technical-flow.md)** - Step-by-step translation flow example
- **[Post-Translation](post-translation.md)** - Post-translation pipeline details

## Reports & Evaluation

- **[Post-Translation Pipeline](post-translation.md)** - Evaluation workflow and report generation

## Testing & QA

- **[Testing a Clean / First-Run State](testing-clean-state.md)** - Reset settings to reproduce the new-user experience of a built `.exe`/`.dmg`

## CI/CD & Security

- **[CI Guardrails](ci-guardrails.md)** - Continuous integration setup
- **[GitHub Security](github-security.md)** - CodeQL, Dependabot, and security workflows

## Contributing

Before submitting a PR, please review:

1. [CONTRIBUTING.md](https://github.com/working-backwards/srt_translator/blob/main/CONTRIBUTING.md) - Contribution guidelines
2. [Coding Standards](coding-standards.md) - Code style requirements
3. [CI Guardrails](ci-guardrails.md) - What checks your PR must pass
