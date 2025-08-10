# Security Quick Reference

## 🚀 Quick Setup Commands

```bash
# Switch to develop branch
git checkout develop

# Add security files
git add .github/ pyproject.toml GITHUB_SECURITY_SETUP.md SECURITY_QUICK_REFERENCE.md

# Commit security setup
git commit -m "feat: Add comprehensive GitHub security features"

# Push to GitHub
git push origin develop
```

## 🛡️ Security Features Overview

| Feature | Purpose | Frequency | Location |
|---------|---------|-----------|----------|
| **CodeQL** | Security vulnerability detection | Every push/PR | Security tab |
| **Dependabot** | Dependency vulnerability monitoring | Weekly (Monday 9 AM) | Security tab |
| **Security Workflows** | Automated security checks | Every push/PR | Actions tab |
| **Security Policy** | Vulnerability reporting guidelines | Always | Security tab |

## 🔍 What to Check Daily

- [ ] **Security tab** for new alerts
- [ ] **Actions tab** for failed workflows
- [ ] **Dependabot** for new PRs

## 🔧 Key Configuration Files

- `.github/workflows/codeql-analysis.yml` - CodeQL scanning
- `.github/workflows/security-and-quality.yml` - Security pipeline
- `.github/dependabot.yml` - Dependency updates
- `.github/SECURITY.md` - Security policy

## 📊 Security Metrics

- **CodeQL scans**: Automated on every commit
- **Dependency updates**: Weekly automated PRs
- **Code quality**: Black, isort, Pylint, MyPy, Flake8
- **Security tools**: Safety, Bandit, pip-tools

## 🚨 Emergency Response

### Security Vulnerability Found
1. **DO NOT** create public issue
2. **Email** security details privately
3. **Fix** in develop branch
4. **Test** thoroughly
5. **Merge** to main after verification

### Failed Security Checks
1. Check **Actions tab** for error details
2. Fix **code issues** locally
3. Push **fixes** to trigger new scan
4. Verify **all checks pass**

## 🌿 Branch Strategy

- **develop** → Active development, security improvements
- **main** → Stable, production-ready code
- **feature branches** → Individual security fixes

## 📅 Maintenance Schedule

- **Daily**: Check alerts and workflow status
- **Weekly**: Review Dependabot PRs
- **Monthly**: Update security tools and policies

---

**Need help?** See `GITHUB_SECURITY_SETUP.md` for detailed instructions!
