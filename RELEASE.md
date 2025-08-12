# Release Process

This document outlines the release process for SRT Translator, including how to create release candidates, final releases, and manage the release lifecycle.

## Release Types

### Release Candidates (RC)
- **Purpose**: Testing and validation before final release
- **Versioning**: `1.0.0rc1`, `1.0.0rc2`, etc.
- **Audience**: Developers, testers, early adopters
- **Distribution**: GitHub releases, PyPI test index

### Final Releases
- **Purpose**: Production-ready releases for end users
- **Versioning**: `1.0.0`, `1.1.0`, `2.0.0`, etc.
- **Audience**: All users
- **Distribution**: GitHub releases, PyPI main index

## Release Schedule

### Major Releases (X.0.0)
- **Frequency**: Every 6-12 months
- **Scope**: New features, breaking changes, major refactoring
- **Process**: Full RC cycle with extended testing

### Minor Releases (X.Y.0)
- **Frequency**: Every 2-4 months
- **Scope**: New features, improvements, bug fixes
- **Process**: RC cycle with focused testing

### Patch Releases (X.Y.Z)
- **Frequency**: As needed (bug fixes, security patches)
- **Scope**: Bug fixes, security updates, minor improvements
- **Process**: Direct release (no RC) for critical fixes

## Pre-Release Checklist

### Code Quality
- [ ] All tests pass on all supported platforms
- [ ] Test coverage ≥ 70%
- [ ] Code formatting passes (Black, isort)
- [ ] Linting passes (Pylint, Flake8)
- [ ] Type checking passes (MyPy)
- [ ] Security scans pass (Bandit, Safety)

### Documentation
- [ ] README.md updated
- [ ] CHANGELOG.md updated
- [ ] Installation instructions verified
- [ ] API documentation current
- [ ] User manual updated

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Smoke tests pass on all platforms
- [ ] GUI functionality verified
- [ ] CLI functionality verified
- [ ] Cross-platform compatibility verified

### Dependencies
- [ ] Dependencies updated to latest stable versions
- [ ] Security vulnerabilities checked
- [ ] License compatibility verified
- [ ] Build dependencies current

## Release Candidate Process

### 1. Create Release Branch
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0rc1
```

### 2. Update Version
Update version in `srt_translator/__init__.py`:
```python
__version__ = "1.0.0rc1"
```

### 3. Update pyproject.toml
```toml
[project]
version = "1.0.0rc1"
```

### 4. Run Full Test Suite
```bash
# Install in development mode
pip install -e ".[dev]"

# Run all tests with coverage
pytest --cov=srt_translator --cov-report=html

# Run linting and formatting checks
black --check srt_translator/ tests/
isort --check-only srt_translator/ tests/
pylint srt_translator/
flake8 srt_translator/
mypy srt_translator/
```

### 5. Test Installation
```bash
# Build package
python -m build

# Test installation
pip install dist/*.whl

# Verify entry points work
srt-cli --version
srtx --help
```

### 6. Create RC Tag
```bash
git add .
git commit -m "chore: prepare release candidate v1.0.0rc1"
git tag -a v1.0.0rc1 -m "Release Candidate v1.0.0rc1"
git push origin release/v1.0.0rc1
git push origin v1.0.0rc1
```

### 7. Create GitHub Release
- Go to GitHub Releases page
- Create new release from tag `v1.0.0rc1`
- Mark as pre-release
- Upload build artifacts
- Add release notes

### 8. Test RC Installation
```bash
# Test from PyPI test index
pip install --index-url https://test.pypi.org/simple/ srt-translator==1.0.0rc1

# Verify functionality
srt-cli --version
```

## Final Release Process

### 1. Merge to Main
```bash
git checkout main
git merge release/v1.0.0rc1
git push origin main
```

### 2. Update Version for Final Release
```python
__version__ = "1.0.0"
```

### 3. Create Final Release Tag
```bash
git add .
git commit -m "chore: prepare final release v1.0.0"
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 4. Build and Publish
```bash
# Build package
python -m build

# Check package
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

### 5. Create GitHub Release
- Create release from tag `v1.0.0`
- Upload build artifacts
- Add comprehensive release notes
- Link to changelog

### 6. Post-Release Tasks
- [ ] Update develop branch with version bump
- [ ] Announce release to community
- [ ] Monitor for issues
- [ ] Plan next release cycle

## Release Automation

### GitHub Actions
The CI/CD pipeline automatically:
- Runs tests on all supported platforms
- Builds packages on release tags
- Uploads artifacts to GitHub releases
- Performs security scans

### Manual Steps
Some steps still require manual intervention:
- Version number updates
- Release notes writing
- PyPI uploads
- Community announcements

## Release Notes Guidelines

### Structure
```markdown
# SRT Translator v1.0.0

## What's New
- Major new features
- Significant improvements

## Changes
- New features
- Bug fixes
- Improvements
- Deprecations

## Breaking Changes
- API changes
- Configuration changes
- Migration guide

## Contributors
- List of contributors
- Special thanks
```

### Content Guidelines
- **Clear and concise**: Explain what changed and why
- **User-focused**: Emphasize user benefits
- **Technical details**: Include relevant technical information
- **Migration notes**: Explain how to upgrade
- **Examples**: Provide usage examples for new features

## Rollback Plan

### If RC Issues Found
1. **Immediate**: Remove RC tag and release
2. **Investigation**: Identify and fix issues
3. **New RC**: Create new RC with fixes
4. **Extended testing**: Additional validation period

### If Final Release Issues Found
1. **Hotfix**: Create patch release immediately
2. **Communication**: Notify users of issues
3. **Documentation**: Update known issues
4. **Recovery**: Plan and execute recovery steps

## Quality Gates

### Release Candidate Gates
- [ ] All automated tests pass
- [ ] Manual testing completed
- [ ] Security scans pass
- [ ] Performance benchmarks met
- [ ] Documentation updated

### Final Release Gates
- [ ] RC testing completed successfully
- [ ] No critical issues reported
- [ ] All quality checks pass
- [ ] Release notes complete
- [ ] Build artifacts verified

## Support and Maintenance

### Release Support
- **Current release**: Full support, bug fixes
- **Previous release**: Security fixes only
- **Older releases**: No support

### Security Updates
- Critical security issues: Immediate patch release
- Non-critical issues: Next scheduled release
- Security advisories: Published promptly

## Contact and Resources

### Release Team
- **Release Manager**: [Name/Contact]
- **QA Lead**: [Name/Contact]
- **DevOps**: [Name/Contact]

### Resources
- [Release Planning](link-to-planning-doc)
- [Testing Guidelines](link-to-testing-doc)
- [Deployment Guide](link-to-deployment-doc)
- [Rollback Procedures](link-to-rollback-doc)

---

*This document should be updated with each release to reflect current processes and lessons learned.*
