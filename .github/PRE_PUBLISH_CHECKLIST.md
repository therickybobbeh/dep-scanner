# 📋 Pre-Publish Checklist

Complete this checklist before publishing to PyPI to ensure a smooth release.

## 📦 Package Preparation

- [ ] **Version Updated**: Updated version in `pyproject.toml`
- [ ] **Changelog**: Updated CHANGELOG.md or release notes
- [ ] **README**: Updated installation instructions and examples
- [ ] **Dependencies**: Verified all dependencies are correct and up-to-date
- [ ] **License**: Confirmed license file is present and correct
- [ ] **Author Info**: Verified author and maintainer information

## 🧪 Testing

- [ ] **Local Tests**: All tests pass locally
- [ ] **Build Test**: Package builds without errors (`make build`)
- [ ] **Installation Test**: Package installs correctly (`make test-package`)
- [ ] **CLI Test**: Command-line interface works (`dep-scan --help`)
- [ ] **Functionality Test**: Core scanning features work
- [ ] **Cross-platform**: Tested on different operating systems (if possible)

## 🔧 Technical Checks

- [ ] **Entry Points**: CLI entry point is correctly configured
- [ ] **Package Structure**: All necessary files are included
- [ ] **Import Paths**: All imports work correctly after installation
- [ ] **Dependencies Conflicts**: No dependency conflicts with common packages
- [ ] **Security**: No secrets or sensitive data in package

## 📚 Documentation

- [ ] **Installation Guide**: Clear pip install instructions
- [ ] **Usage Examples**: Working examples in README
- [ ] **API Documentation**: If applicable, API docs are current
- [ ] **Troubleshooting**: Common issues and solutions documented

## 🔐 Security

- [ ] **Secrets Scan**: No API keys, passwords, or tokens in code
- [ ] **Dependencies**: All dependencies are from trusted sources
- [ ] **Vulnerabilities**: No known vulnerabilities in dependencies
- [ ] **Code Review**: Code has been reviewed for security issues

## 🚀 Publishing Setup

- [ ] **PyPI Account**: Accounts created on PyPI and TestPyPI
- [ ] **2FA Enabled**: Two-factor authentication enabled
- [ ] **Trusted Publishing**: GitHub trusted publishing configured (or API tokens set)
- [ ] **GitHub Environments**: Repository environments configured
- [ ] **Workflow Permissions**: GitHub Actions have necessary permissions

## 🎯 Release Process

- [ ] **TestPyPI First**: Plan to test on TestPyPI before PyPI
- [ ] **Version Tag**: Prepared to create appropriate version tag
- [ ] **Release Notes**: Prepared release notes highlighting changes
- [ ] **Rollback Plan**: Know how to yank a release if needed

## ✅ Final Verification

Before clicking "publish":

- [ ] **Double-check Version**: Confirm version number is correct and not already used
- [ ] **Test Install**: Can install previous version from PyPI
- [ ] **Backup**: Have a backup of working code
- [ ] **Team Notice**: If applicable, team is aware of the release

## 🚨 Emergency Procedures

If something goes wrong:

- [ ] **Yank Release**: Know how to yank a problematic release
  ```bash
  # Remove from PyPI (marks as yanked but keeps for existing installs)
  pip install twine
  # Contact PyPI support for complete removal if needed
  ```

- [ ] **Fix Forward**: Prepare to quickly release a patch version
- [ ] **Communication**: Plan to notify users of issues via GitHub/documentation

## 📞 Support Contacts

- [ ] **PyPI Support**: Know how to contact PyPI support if needed
- [ ] **GitHub Support**: Know how to get help with GitHub Actions
- [ ] **Community**: Prepared to handle user issues and questions

---

## 🎉 Ready to Publish!

When all items are checked:

1. **For TestPyPI**: Run `make publish-test` or trigger GitHub workflow with "TestPyPI only"
2. **For PyPI**: Create a release or run `make publish-prod`
3. **Monitor**: Watch the GitHub Actions workflow and test results
4. **Verify**: Test installation from PyPI after successful publish
5. **Announce**: Share the release with your community

## 📝 Post-Publish Tasks

After successful publication:

- [ ] **Test Installation**: `pip install dep-scan` works
- [ ] **Update Documentation**: Add PyPI badges to README
- [ ] **Social Media**: Announce the release (if desired)
- [ ] **Monitor Issues**: Watch for user reports or issues
- [ ] **Plan Next Release**: Consider what's next for the project

---

**Remember**: It's better to delay a release to fix issues than to publish a broken package!