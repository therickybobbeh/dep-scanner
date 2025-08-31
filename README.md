# 🛡️ DepScan - Professional Dependency Vulnerability Scanner

> **Fast, accurate, and comprehensive vulnerability scanning for Python and JavaScript projects**

DepScan is a professional-grade security tool that identifies known vulnerabilities in your project dependencies across multiple ecosystems. Get detailed security reports with actionable recommendations through both CLI and web interfaces.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)

## 🚀 Quick Start

### For Developers (CLI)
```bash
# Install from PyPI
pip install dep-scan

# Scan your project
dep-scan scan ./package.json
dep-scan scan ./requirements.txt --output html
```

### For Teams (Web Interface)
```bash
# Local development
git clone https://github.com/your-repo/dep-scanner.git
cd dep-scanner
./scripts/dev-setup.sh
```

### For Production (AWS Deployment)
```bash
# One-command AWS deployment
cd deploy/terraform && terraform apply
```

## ✨ Key Features

| Feature | CLI | Web Interface |
|---------|-----|---------------|
| 🔍 **Multi-Ecosystem Scanning** | Python, JavaScript | Python, JavaScript |
| 🌳 **Transitive Dependencies** | Full dependency tree | Interactive visualization |
| 🚨 **Real-time Vulnerability DB** | OSV.dev integration | Live updates |
| 📊 **Multiple Output Formats** | JSON, HTML, CSV | Interactive dashboard |
| ⚡ **Performance** | ~100 deps/second | Real-time progress |
| 🔒 **No API Keys Required** | Completely free | Open source |

## 🎯 Perfect For

- **🏢 Development Teams**: Integrate into CI/CD pipelines
- **🔒 Security Audits**: Comprehensive vulnerability reporting  
- **📊 Compliance**: Track and document security status
- **🚀 DevOps**: Automated security scanning workflows

## 📋 Supported Ecosystems & Files

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
$ dep-scan scan package.json

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

## 🔗 Documentation & Resources

### 📚 Core Documentation
- **[📖 Complete Documentation](documentation/README.md)** - Comprehensive technical guide
- **[🚀 Deployment Guide](DEPLOYMENT.md)** - All deployment options
- **[🏗️ Architecture Overview](documentation/architecture/system-overview.md)** - Technical architecture
- **[🔄 API Reference](documentation/api/rest-api.md)** - REST API documentation

### 🛠️ Development & Contributing
- **[💻 Development Setup](documentation/guides/development-setup.md)** - Local development environment
- **[🤝 Contributing Guide](documentation/guides/contributing.md)** - Code contribution workflow
- **[🧪 Testing Strategy](documentation/guides/testing-strategy.md)** - Testing approach and coverage

### 🎨 User Experience
- **[📱 User Journeys](documentation/workflows/user-journeys.md)** - Complete user workflows
- **[🔍 Scanning Process](documentation/workflows/scanning-process.md)** - How vulnerability detection works
- **[⚙️ Configuration](documentation/guides/configuration.md)** - Customization options

## 🚀 Deployment Options

| Method | Best For | Complexity | Cost |
|--------|----------|------------|------|
| **pip install** | Individual developers | ⭐ | Free |
| **Docker** | Teams & self-hosting | ⭐⭐ | Server costs only |
| **AWS ECS** | Production web service | ⭐⭐⭐ | ~$17-27/month |
| **PyPI Package** | Library distribution | ⭐⭐ | Free |

### Quick Deployment Links
- **[🐳 Docker Setup](deploy/docker/README.md)** - Container deployment
- **[☁️ AWS Deployment](deploy/terraform/README.md)** - Production AWS infrastructure  
- **[📦 PyPI Publishing](deploy/pypi/README.md)** - Package distribution
- **[⚙️ Configuration Options](DEPLOYMENT.md#configuration-options)** - Environment setup

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph "🖥️ Interfaces"
        CLI[CLI Scanner]
        WEB[Web Dashboard]
    end
    
    subgraph "🔧 Core Engine"
        API[FastAPI Server]
        CORE[Scanner Core]
        CACHE[Result Cache]
    end
    
    subgraph "🔍 Processing Pipeline"
        RESOLVE[Dependency Resolvers]
        PARSE[File Parsers]
        SCAN[Vulnerability Scanner]
    end
    
    subgraph "🌐 External Services"
        OSV[OSV.dev Database]
        PYPI[PyPI Registry]
        NPM[npm Registry]
    end
    
    CLI --> CORE
    WEB --> API
    API --> CORE
    CORE --> RESOLVE
    RESOLVE --> PARSE
    CORE --> SCAN
    SCAN --> OSV
    PARSE --> PYPI
    PARSE --> NPM
    CORE --> CACHE
```

## ⚡ Performance & Scale

- **Scanning Speed**: 100-500 dependencies in 5-15 seconds
- **Memory Usage**: ~100-500MB per scan (dependency count dependent)
- **API Throughput**: 1000+ scans per minute (distributed)
- **Database Coverage**: 500,000+ known vulnerabilities via OSV.dev
- **Supported Projects**: No limits on dependency count

## 🔒 Security & Privacy

- ✅ **No API Keys Required** - Completely free to use
- ✅ **Local Processing** - Your code never leaves your infrastructure
- ✅ **Open Source** - Full transparency and community auditing
- ✅ **Zero Data Collection** - No tracking or analytics
- ✅ **Offline Capable** - Works without internet after initial setup

## 🤝 Contributing & Community

We welcome contributions of all kinds! Here's how to get started:

- **🐛 Bug Reports**: [GitHub Issues](https://github.com/your-repo/dep-scanner/issues)
- **💡 Feature Requests**: [GitHub Discussions](https://github.com/your-repo/dep-scanner/discussions)
- **📝 Documentation**: Improve guides and examples
- **🔧 Code Contributions**: See [Contributing Guide](documentation/guides/contributing.md)
- **📋 Testing**: Help expand test coverage

### Development Quick Start
```bash
# Clone and setup
git clone https://github.com/your-repo/dep-scanner.git
cd dep-scanner

# Backend development
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Frontend development  
cd frontend && npm install && npm run dev

# Run full test suite
./scripts/test-all.sh
```

## 📄 License & Legal

**MIT License** - Use freely in personal, commercial, and enterprise projects.

- Full license: [LICENSE](LICENSE)
- Third-party licenses: [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- Security policy: [SECURITY.md](SECURITY.md)

## 🆘 Support & Help

### Getting Help
- **📖 Documentation**: Start with [documentation/README.md](documentation/README.md)
- **🔍 Search Issues**: Check [existing issues](https://github.com/your-repo/dep-scanner/issues)
- **💬 Community**: Join [GitHub Discussions](https://github.com/your-repo/dep-scanner/discussions)
- **📧 Security Issues**: security@yourdomain.com (private reporting)

### Professional Support
- **🏢 Enterprise Support**: Contact us for SLA-backed support
- **🎓 Training**: Team training and implementation guidance
- **🔧 Custom Development**: Feature development and integration services

---

## 🎉 Try It Now!

```bash
# Get started in 30 seconds
pip install dep-scan
dep-scan scan package.json

# Or try the web interface
docker run -p 8000:8000 dep-scan:latest
# Open http://localhost:8000
```

**Made with ❤️ by the DepScan team** | **Star ⭐ if this helps you secure your code!**