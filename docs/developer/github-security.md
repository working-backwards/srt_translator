# GitHub Security Setup Guide

This guide walks you through setting up comprehensive security features for your SRT Translator repository using GitHub's built-in security tools.

## Quick Reference

| Feature | Purpose | Frequency | Location |
|---------|---------|-----------|----------|
| **CodeQL** | Security vulnerability detection | Every push/PR | Security tab |
| **Dependabot** | Dependency vulnerability monitoring | Weekly (Monday 9 AM) | Security tab |
| **Security Workflows** | Automated security checks | Every push/PR | Actions tab |
| **Security Policy** | Vulnerability reporting guidelines | Always | Security tab |

### Key Configuration Files

- `.github/workflows/codeql-analysis.yml` - CodeQL scanning
- `.github/workflows/security-and-quality.yml` - Security pipeline
- `.github/dependabot.yml` - Dependency updates
- `.github/SECURITY.md` - Security policy

---

## What We're Setting Up

1. **GitHub Code Scanning (CodeQL)** - Automated security vulnerability detection
2. **GitHub Dependabot** - Automatic dependency vulnerability monitoring
3. **Security and Quality Workflows** - Comprehensive CI/CD security pipeline
4. **Security Policy** - Clear vulnerability reporting guidelines

## Branch Strategy

**Use the `develop` branch for these security enhancements:**

- **develop** - Active development, security improvements, testing
- **main** - Stable, production-ready code (keep clean)

This follows Git Flow and gives you a safety net while implementing security features.

## Step-by-Step Setup

### 1. Push Your Changes to GitHub

First, commit and push the new security files to your `develop` branch:

```bash
# Make sure you're on the develop branch
git checkout develop

# Add the new security files
git add .github/
git add pyproject.toml

# Commit with a descriptive message
git commit -m "feat: Add comprehensive GitHub security features

- Add CodeQL workflow for automated security scanning
- Add Dependabot configuration for dependency monitoring
- Add security and quality CI/CD pipeline
- Add security policy and reporting guidelines
- Update dependencies with security tools"

# Push to GitHub
git push origin develop
```

### 2. Enable GitHub Code Scanning

1. Go to your repository on GitHub
2. Click the "Security" tab
3. Click "Set up code scanning"
4. Choose "CodeQL Analysis"
5. Select "Default" setup
6. Click "Enable CodeQL"

GitHub will automatically:
- Create the workflow file (we already have it)
- Run the first scan
- Set up automated scanning on every push/PR

### 3. Enable GitHub Dependabot

1. Go to your repository on GitHub
2. Click the "Security" tab
3. Click "Dependabot" in the left sidebar
4. Click "Enable Dependabot"
5. Configure alerts (optional but recommended)

### 4. Review and Customize

#### CodeQL Configuration
The workflow will automatically:
- Scan Python code for security vulnerabilities
- Detect dead code and quality issues
- Run on every push to `main`/`develop`
- Run on every pull request
- Schedule weekly scans

#### Dependabot Configuration
- **Weekly updates** every Monday at 9 AM
- **Security-focused** updates prioritized
- **Automatic PR creation** for vulnerable packages
- **Grouped updates** to reduce PR noise

## What You'll See

### Security Tab
- **Code scanning alerts** from CodeQL
- **Dependabot alerts** for vulnerable dependencies
- **Security advisories** and policy information

### Actions Tab
- **CodeQL Analysis** workflow runs
- **Security and Quality Checks** workflow runs
- **Detailed reports** and artifacts

### Pull Requests
- **Security check results** displayed
- **Dependency update PRs** from Dependabot
- **Blocking** of PRs with security issues (configurable)

## Security Features in Action

### Automated Scanning
- **Every commit** triggers security analysis
- **Pull requests** get security reviews
- **Weekly scheduled** scans catch new vulnerabilities

### Dependency Monitoring
- **Real-time alerts** for new vulnerabilities
- **Automatic updates** via Dependabot PRs
- **Security-focused** dependency management

### Code Quality
- **Formatting checks** with Black
- **Import sorting** with isort
- **Linting** with Pylint, Flake8
- **Type checking** with MyPy
- **Security linting** with Bandit

## Monitoring and Maintenance

### Daily Checklist
- [ ] Check GitHub Security tab for new alerts
- [ ] Review any failed workflow runs
- [ ] Check Dependabot for new PRs

### Weekly
- Review Dependabot PRs
- Check scheduled security scans
- Review dependency update reports

### Monthly
- Review security policy effectiveness
- Update security tools and configurations
- Analyze security metrics and trends

## Responding to Security Issues

### CodeQL Alerts
1. Review the alert in the Security tab
2. Understand the vulnerability and its impact
3. Fix the issue in your code
4. Test the fix thoroughly
5. Push the fix to trigger a new scan

### Dependabot Alerts
1. Review the vulnerability details
2. Test the update in your environment
3. Merge the PR if tests pass
4. Monitor for any issues after deployment

### Security Policy Violations
1. Follow the reporting process in `.github/SECURITY.md`
2. Investigate the reported issue
3. Develop and test a fix
4. Deploy the fix following security best practices

### Emergency Response

If a security vulnerability is found:
1. **DO NOT** create a public issue
2. **Email** security details privately
3. **Fix** in develop branch
4. **Test** thoroughly
5. **Merge** to main after verification

## Customization Options

### CodeQL Queries
You can customize security rules by:
- Adding custom queries
- Enabling security-extended rules
- Configuring language-specific settings

### Dependabot Settings
Customize update behavior:
- Change update frequency
- Set specific version constraints
- Configure grouping strategies
- Set review requirements

### Workflow Triggers
Modify when workflows run:
- Change branch triggers
- Adjust schedule timing
- Add manual triggers
- Configure path filters

## Benefits

### Immediate
- **Security visibility** across your codebase
- **Automated vulnerability detection**
- **Dependency security monitoring**

### Short-term (1-2 weeks)
- **Reduced security debt**
- **Improved code quality**
- **Faster security issue identification**

### Long-term (1-3 months)
- **Proactive security posture**
- **Reduced vulnerability exposure**
- **Improved development workflow**
- **Better dependency management**

## Troubleshooting

### Common Issues

#### Workflow Failures
- Check Python version compatibility
- Verify dependency installation
- Review error logs in Actions tab

#### CodeQL Scan Issues
- Ensure Python code is properly structured
- Check for build configuration issues
- Verify language detection

#### Dependabot Not Working
- Check repository permissions
- Verify configuration file syntax
- Ensure dependencies are properly specified

### Getting Help
- **GitHub Documentation**: [CodeQL](https://docs.github.com/en/code-security/code-scanning/automatically-scanning-your-code-for-vulnerabilities-and-errors/about-code-scanning-with-codeql)
- **Dependabot Docs**: [Dependabot](https://docs.github.com/en/code-security/dependabot)
- **GitHub Support**: Available for GitHub Pro/Team accounts

## Additional Resources

- [GitHub Security Best Practices](https://docs.github.com/en/github/getting-started-with-github/learning-about-github/github-security)
- [Python Security Tools](https://python-security.readthedocs.io/)
- [OWASP Security Guidelines](https://owasp.org/)
- [GitHub Advanced Security](https://github.com/features/security)
