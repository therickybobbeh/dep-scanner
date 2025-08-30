# 📦 DepScan PyPI Package Distribution

This directory contains all the tools and documentation needed to package and distribute DepScan as a pip-installable package.

## 🚀 Quick Install (For End Users)

```bash
pip install dep-scan
```

Then use it anywhere:
```bash
dep-scan --help
dep-scan scan ./package.json
```

## 📋 Package Publishing Guide (For Maintainers)

### Prerequisites

1. **PyPI Account**: Create accounts at:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

2. **Install Publishing Tools**:
   ```bash
   pip install build twine keyring
   ```

3. **Configure PyPI Credentials**:
   ```bash
   # Store credentials securely
   python -m keyring set https://upload.pypi.org/legacy/ __token__
   # Enter your PyPI API token when prompted
   
   # For TestPyPI
   python -m keyring set https://test.pypi.org/legacy/ __token__
   # Enter your TestPyPI API token when prompted
   ```

### Publishing Process

#### Step 1: Prepare Release

```bash
# Navigate to project root
cd ../../

# Update version in pyproject.toml
# Edit the version field: version = "1.2.0"

# Update changelog and documentation
# Test the package locally
pip install -e .
dep-scan --version
```

#### Step 2: Build Package

```bash
# Use the build script
./deploy/pypi/build.sh

# Or manually:
python -m build --wheel --sdist
```

#### Step 3: Test on TestPyPI

```bash
# Upload to TestPyPI first
./deploy/pypi/publish.sh test

# Test installation from TestPyPI
./deploy/pypi/test.sh
```

#### Step 4: Publish to PyPI

```bash
# If TestPyPI works, publish to production PyPI
./deploy/pypi/publish.sh prod
```

#### Step 5: Verify Release

```bash
# Test installation from PyPI
pip install --upgrade dep-scan
dep-scan --version

# Create GitHub release
git tag v1.2.0
git push origin v1.2.0
```

## 🛠️ Package Structure

The package is configured in `pyproject.toml` with:

```toml
[project]
name = "dep-scan"
version = "1.0.0"
description = "Professional-grade dependency vulnerability scanner"

[project.scripts]
dep-scan = "backend.cli.main:app"
```

**Key Files:**
- `pyproject.toml` - Modern Python packaging configuration
- `backend/` - Source code for the CLI and API
- `dist/` - Built packages (created during build)
- `*.egg-info/` - Package metadata (created during build)

## 📊 Package Features

When users install via pip, they get:

- **CLI Tool**: `dep-scan` command available globally
- **Multi-ecosystem Support**: Scan NPM and Python dependencies
- **Multiple Output Formats**: JSON, CSV, human-readable
- **No External Dependencies**: Works without npm or pip-tools
- **Fast Scanning**: Concurrent vulnerability checking

## 🔧 Usage Examples

### Basic Scanning
```bash
# Scan package.json
dep-scan scan ./package.json

# Scan Python requirements
dep-scan scan ./requirements.txt

# Scan with specific output format
dep-scan scan ./package.json --output json --file results.json
```

### Advanced Options
```bash
# Exclude dev dependencies
dep-scan scan ./package.json --no-dev

# Filter by severity
dep-scan scan ./requirements.txt --ignore-severity LOW,MEDIUM

# Scan multiple files
dep-scan scan ./package.json ./requirements.txt

# Export to CSV
dep-scan scan ./package.json --output csv --file vulnerabilities.csv
```

### CI/CD Integration
```bash
# Exit with error code on vulnerabilities
dep-scan scan ./package.json --exit-code

# Fail only on HIGH and CRITICAL
dep-scan scan ./package.json --exit-code --ignore-severity LOW,MEDIUM
```

## 🏗️ Development Setup

For contributors who want to develop the package:

```bash
# Clone repository
git clone https://github.com/yourusername/dep-scanner.git
cd dep-scanner

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black backend/
isort backend/
flake8 backend/

# Test package build
./deploy/pypi/build.sh
```

## 📈 Version Management

**Semantic Versioning:**
- `1.0.0` - Major release (breaking changes)
- `1.1.0` - Minor release (new features)
- `1.1.1` - Patch release (bug fixes)

**Release Process:**
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with release notes
3. Test thoroughly with `./deploy/pypi/test.sh`
4. Publish to TestPyPI first
5. If tests pass, publish to PyPI
6. Create GitHub release and tag

## 🔒 Security Considerations

**Package Security:**
- All dependencies pinned with security patches
- Regular security audits with `pip-audit`
- Signed releases with GPG (optional)
- Minimal attack surface (no unnecessary dependencies)

**Credential Security:**
- API tokens stored in system keyring
- Never commit credentials to repository
- Use scoped API tokens for PyPI access
- Rotate tokens regularly

## 🌍 Distribution Channels

**Primary Distribution:**
- [PyPI](https://pypi.org/project/dep-scan/) - `pip install dep-scan`

**Alternative Channels:**
- [Conda Forge](https://conda-forge.org/) - `conda install dep-scan`
- [Homebrew](https://brew.sh/) - `brew install dep-scan`
- [Docker Hub](https://hub.docker.com/) - `docker pull dep-scan`

## 📞 Support & Contributing

**For Package Users:**
- Issues: [GitHub Issues](https://github.com/yourusername/dep-scanner/issues)
- Documentation: [GitHub Wiki](https://github.com/yourusername/dep-scanner/wiki)
- Examples: [Examples Directory](https://github.com/yourusername/dep-scanner/tree/main/examples)

**For Contributors:**
- Development Guide: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- Code of Conduct: [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md)
- Security Policy: [SECURITY.md](../../SECURITY.md)

## 🔄 Automated Publishing

For automated releases, consider setting up GitHub Actions:

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install build twine
    - run: python -m build
    - run: twine upload dist/*
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
```

This ensures consistent, automated releases whenever you create a GitHub release.