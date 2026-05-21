# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow these steps:

### 🚨 **DO NOT** create a public GitHub issue for security vulnerabilities

### ✅ **DO** report security issues privately:

1. **Email**: Send details to [your-email@example.com] (replace with your actual email)
2. **Subject**: Use "SECURITY VULNERABILITY: [brief description]"
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### 🔒 **What happens next:**

1. **Acknowledgment**: You'll receive an acknowledgment within 48 hours
2. **Investigation**: Our security team will investigate the issue
3. **Fix Development**: We'll develop and test a fix
4. **Release**: A security patch will be released
5. **Credit**: You'll be credited in the security advisory (if desired)

### 🛡️ **Security Measures in Place:**

- **CodeQL Analysis**: Automated security scanning on every commit
- **Dependabot**: Automatic dependency vulnerability monitoring
- **Security Headers**: Protection against common web vulnerabilities
- **Input Validation**: Comprehensive input sanitization
- **API Key Handling**: OpenAI API keys are stored locally in app settings (plaintext, not encrypted), never written to logs or batch artifacts, and never transmitted anywhere except to OpenAI's API over HTTPS. See the GUI manual's "API Key Storage" section for the full data-handling description.

### 📋 **Security Checklist for Contributors:**

- [ ] No hardcoded secrets or API keys
- [ ] Input validation on all user inputs
- [ ] Proper error handling (no information disclosure)
- [ ] Use of secure defaults
- [ ] Regular dependency updates

### 🔍 **Security Tools Used:**

- **Static Analysis**: CodeQL, Pylint, MyPy
- **Dependency Scanning**: Dependabot, Safety
- **Code Quality**: Black, isort, Flake8
- **Testing**: Pytest with security-focused tests

## Security Best Practices

### For Users:
- Keep your API keys secure and never share them
- Use the latest version of the application
- Report any suspicious behavior immediately

### For Contributors:
- Follow secure coding practices
- Never commit secrets or sensitive data
- Use the provided security tools and workflows

## Contact

- **Security Issues**: [your-email@example.com]
- **General Issues**: Use GitHub Issues
- **Discussions**: Use GitHub Discussions

Thank you for helping keep our community secure! 🛡️
