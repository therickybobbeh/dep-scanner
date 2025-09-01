# TestPyPI Publishing Setup Guide

This document explains how to set up and use the GitHub workflows for publishing the `multi-vuln-scanner` CLI tool to TestPyPI.

> **Note**: We currently only publish to TestPyPI for testing and validation. Production PyPI publishing will be enabled in the future after thorough testing.

## 🔧 Prerequisites

### 1. TestPyPI Account Setup
1. Create an account on [TestPyPI](https://test.pypi.org)
2. Enable 2FA on your TestPyPI account (required for trusted publishing)
3. *(Optional for future)* Create a [PyPI](https://pypi.org) account when ready for production publishing

### 2. GitHub Repository Setup

#### Configure Trusted Publishing (Recommended)
Trusted publishing allows GitHub Actions to publish to TestPyPI without storing API tokens.

**For TestPyPI:**
1. Go to https://test.pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI project name**: `multi-vuln-scanner`
   - **Owner**: Your GitHub username
   - **Repository name**: Your repository name
   - **Workflow name**: `pypi-publish.yml`
   - **Environment name**: `testpypi`

**For Production PyPI (Future Use):**
When ready for production publishing, you'll need to:
1. Go to https://pypi.org/manage/account/publishing/
2. Repeat the same process with:
   - **Environment name**: `pypi`

#### Alternative: API Token Setup
If you prefer API tokens over trusted publishing:

1. Generate API token for TestPyPI:
   - TestPyPI: https://test.pypi.org/manage/account/token/

2. Add secret to your GitHub repository:
   - Go to Settings → Secrets and variables → Actions
   - Add secret: `TESTPYPI_API_TOKEN` with your TestPyPI token

3. Modify the workflow to use the token instead of trusted publishing

*(For future production use, you'll also need a PyPI token)*

### 3. GitHub Environments Setup

1. Go to Settings → Environments in your repository
2. Create the TestPyPI environment:
   - **testpypi**: For TestPyPI publishing

*(The **pypi** environment will be created later when production publishing is enabled)*

## 🚀 Usage

### Manual Testing (Recommended First)

Test the workflow manually before setting up automatic publishing:

1. Go to Actions → Publish to TestPyPI
2. Click "Run workflow"
3. Click "Run workflow" to start

This will:
- ✅ Build and test the package
- ✅ Publish to TestPyPI
- ✅ Test installation from TestPyPI
- ✅ Run cross-platform compatibility tests

### Automatic Publishing

The workflow automatically triggers on:

1. **GitHub Releases**: When you create a release
2. **Version Tags**: When you push tags like `v1.0.1`

#### Creating a Release:
```bash
# Tag the release
git tag v1.0.1
git push origin v1.0.1

# Or create through GitHub web interface
# Go to Releases → Create a new release
```

### Publishing Flow

1. **Build & Test**: Package is built and tested locally
2. **TestPyPI Publishing**: Package is published to TestPyPI
3. **Installation Verification**: Installation from TestPyPI is tested
4. **Multi-platform Testing**: Verified on Windows, macOS, Linux via separate workflow

*(Production PyPI publishing will be added to this flow in the future)*

## 📦 Package Information

- **Package Name**: `multi-vuln-scanner`
- **TestPyPI URL**: https://test.pypi.org/project/multi-vuln-scanner/
- **Current Installation**: `pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner`
- **Future PyPI URL**: https://pypi.org/project/multi-vuln-scanner/ *(when production publishing is enabled)*

## 🔍 Troubleshooting

### Common Issues

1. **Build Failures**
   - Check `pyproject.toml` syntax
   - Ensure all required files are included
   - Run `python -m build` locally to test

2. **Import Errors After Installation**
   - Verify package structure in `pyproject.toml`
   - Check `[project.scripts]` entry point
   - Test local wheel: `pip install dist/*.whl`

3. **Publishing Failures**
   - Verify trusted publishing configuration
   - Check environment names match exactly
   - Ensure version number hasn't been published before

4. **Test Failures**
   - Dependencies missing from `pyproject.toml`
   - CLI entry point not working
   - Core functionality broken

### Debug Commands

```bash
# Local build testing
python -m build
twine check dist/*
pip install dist/*.whl
dep-scan --help

# Test from TestPyPI (current method)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner

# Check package contents
python -c "import zipfile; zipfile.ZipFile('dist/multi_vuln_scanner-*.whl').printdir()"
```

## 🔄 Workflow Files

- **`pypi-publish.yml`**: TestPyPI publishing workflow (production PyPI disabled)
- **`test-pypi-package.yml`**: Cross-platform installation testing from TestPyPI
- **`build-verify.yml`**: Build verification on commits and PRs

## ⚙️ Customization

### Version Management

The package version is defined in `pyproject.toml`:
```toml
[project]
version = "1.0.1"
```

For automatic versioning, consider using tools like:
- `setuptools-scm` for git-based versioning
- `bump2version` for semantic versioning

### Package Metadata

Update these fields in `pyproject.toml`:
```toml
[project]
name = "multi-vuln-scanner"
description = "Your description"
authors = [{name = "Your Name", email = "your.email@example.com"}]

[project.urls]
Homepage = "https://github.com/your-username/your-repo"
Repository = "https://github.com/your-username/your-repo.git"
```

## 📋 Checklist for First TestPyPI Release

- [ ] Configure trusted publishing on TestPyPI
- [ ] Set up GitHub `testpypi` environment
- [ ] Update package metadata in `pyproject.toml`
- [ ] Test manual workflow run
- [ ] Verify installation from TestPyPI works
- [ ] Create first release/tag to trigger automatic publishing
- [ ] Monitor cross-platform compatibility tests
- [ ] Update documentation with TestPyPI installation instructions
- [ ] *(Future)* Set up production PyPI when ready

## 🎯 Next Steps

After successful TestPyPI setup:

1. **Documentation**: Add TestPyPI installation instructions to main README
2. **Testing**: Thoroughly test package installation and functionality from TestPyPI
3. **Badges**: Add TestPyPI version badge (optional)
4. **Automation**: Set up automatic version bumping
5. **Production Planning**: Prepare for eventual PyPI production publishing
6. **Monitoring**: Set up notifications for failed TestPyPI publications