# 🛡️ Multi-Vuln-Scanner - Professional Dependency Vulnerability Scanner

> **Fast, accurate, and comprehensive vulnerability scanning for Python and JavaScript projects**

Multi-Vuln-Scanner is a professional-grade security tool that identifies known vulnerabilities in your project dependencies across multiple ecosystems. Get detailed security reports with actionable recommendations through both CLI and web interfaces.

[![TestPyPI](https://img.shields.io/badge/TestPyPI-v1.0.0-blue)](https://test.pypi.org/project/multi-vuln-scanner/1.0.0/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 🚀 Quick Start

### Install from TestPyPI

```bash
# Install latest version
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner

# Install specific version
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner==1.0.0
```

### Use the Scanner

```bash
# Scan JavaScript projects
multi-vuln-scanner scan ./package.json
dep-scan scan ./package.json  # Backward compatible

# Scan Python projects
multi-vuln-scanner scan ./requirements.txt
multi-vuln-scanner scan ./requirements.txt --output html

# Scan entire directory
multi-vuln-scanner scan . --verbose
```

## ✨ Key Features

- 🔍 **Multi-Ecosystem Scanning** - Python and JavaScript support
- 🌳 **Transitive Dependencies** - Complete dependency tree analysis
- 🚨 **Real-time Vulnerability DB** - OSV.dev integration
- 📊 **Multiple Output Formats** - JSON, HTML, CSV
- ⚡ **High Performance** - ~100 dependencies/second
- 🔒 **No API Keys Required** - Completely free
- 🛠️ **CLI & Web Interface** - Use standalone or with web dashboard

## 📋 Supported File Types

### Python
- `requirements.txt` - Direct and resolved dependencies
- `poetry.lock` - Poetry lockfile with exact versions
- `Pipfile.lock` - Pipenv lockfile format
- `pyproject.toml` - Modern Python project configuration

### JavaScript/Node.js  
- `package.json` - npm/yarn dependencies
- `package-lock.json` - npm lockfile with full tree
- `yarn.lock` - Yarn lockfile format

## 📊 Example Output

```bash
$ multi-vuln-scanner scan package.json

🛡️ DepScan Security Report
═══════════════════════════════════════════

📦 Scanned: 847 dependencies (23 direct, 824 transitive)
🚨 Found: 12 vulnerabilities across 8 packages

Critical Issues (2):
├── axios@0.19.0 → CVE-2021-3749 (CVSS: 9.8)
└── node-fetch@1.7.3 → CVE-2020-15168 (CVSS: 9.1)

High Issues (4):
├── lodash@4.17.11 → CVE-2020-8203 (CVSS: 7.4)
├── minimist@1.2.0 → CVE-2020-7598 (CVSS: 7.3)
└── ... 2 more

📄 Full Report: ./scan-results/vulnerabilities.html
⏱️ Scan completed in 8.3 seconds
```

## 🔒 Security & Privacy

- ✅ **No API Keys Required** - Completely free to use
- ✅ **Local Processing** - Your code never leaves your infrastructure
- ✅ **Open Source** - Full transparency and community auditing
- ✅ **Zero Data Collection** - No tracking or analytics
- ✅ **Offline Capable** - Works without internet after initial setup

## ⚡ Performance

- **Scanning Speed**: 100-500 dependencies in 5-15 seconds
- **Memory Usage**: ~100-500MB per scan (dependency count dependent)
- **Database Coverage**: 500,000+ known vulnerabilities via OSV.dev
- **Supported Projects**: No limits on dependency count

## 🔗 Links & Resources

- **Repository**: https://github.com/therickybobbeh/multi-vuln-scanner
- **Documentation**: https://github.com/therickybobbeh/multi-vuln-scanner/tree/main/docs
- **Issues**: https://github.com/therickybobbeh/multi-vuln-scanner/issues
- **Changelog**: https://github.com/therickybobbeh/multi-vuln-scanner/releases

## 📄 License

MIT License - Use freely in personal, commercial, and enterprise projects.

---

**Made with ❤️ by the DepScan team** | **Star ⭐ if this helps you secure your code!**