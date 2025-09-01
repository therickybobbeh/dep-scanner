# Contributing to DepScan

Thank you for your interest in contributing to DepScan! We welcome contributions of all kinds, from bug reports to feature implementations.

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (required)
- **Node.js 18+** (for frontend development)
- **Docker** (optional, for containerized development)
- **Git** (for version control)

### Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/therickybobbeh/dep-scanner.git
cd socketTest

# 2. Backend setup
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Frontend setup (if working on web interface)
cd ../frontend
npm install

# 4. Run tests to verify setup
cd ../backend
pytest
```

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- **Search existing issues** first to avoid duplicates
- **Use the bug report template** when creating issues
- **Provide clear reproduction steps**
- **Include environment details** (OS, Python version, etc.)

### 💡 Feature Requests
- **Check existing discussions** and issues first
- **Use GitHub Discussions** for feature ideas
- **Provide clear use cases** and benefits
- **Consider implementation complexity**

### 📝 Documentation
- **Fix typos** and unclear instructions
- **Add examples** and use cases
- **Improve API documentation**
- **Translate documentation** (future)

### 🔧 Code Contributions
- **Start with good first issues** labeled as such
- **Follow the development workflow** below
- **Write tests** for new functionality
- **Update documentation** as needed

## 🔄 Development Workflow

### 1. Before You Start
```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/therickybobbeh/dep-scanner.git
cd socketTest

# Add upstream remote
git remote add upstream https://github.com/therickybobbeh/dep-scanner.git
```

### 2. Create a Feature Branch
```bash
# Update your main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
# Or for bug fixes:
git checkout -b fix/bug-description
```

### 3. Development Process
```bash
# Make your changes
# Test your changes
pytest                          # Run backend tests
cd frontend && npm test         # Run frontend tests (if applicable)

# Format and lint code
black backend/                  # Format Python code
isort backend/                  # Sort imports
flake8 backend/                 # Lint Python code
mypy backend/                   # Type checking
```

### 4. Commit Your Changes
```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "feat: add vulnerability severity filtering

- Add support for filtering by severity levels
- Update CLI arguments and web interface
- Add tests for severity filtering
- Update documentation"

# Follow conventional commit format:
# feat: new feature
# fix: bug fix
# docs: documentation changes
# test: adding tests
# refactor: code refactoring
# style: formatting changes
```

### 5. Submit Pull Request
```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Use the PR template and fill out all sections
```

## 📋 Code Standards

### Python Code Style
```bash
# We use these tools (automatically run in CI):
black backend/          # Code formatting
isort backend/          # Import sorting  
flake8 backend/         # Linting
mypy backend/           # Type checking
bandit backend/         # Security linting
```

**Key Guidelines:**
- **Type hints** required for all functions
- **Docstrings** for public APIs
- **Error handling** for external API calls
- **Input validation** using Pydantic models
- **Tests** for all new functionality

### Frontend Code Style (if applicable)
```bash
# TypeScript/React standards
npm run lint            # ESLint
npm run type-check      # TypeScript checking
npm run format          # Prettier formatting
```

### Commit Message Format
```
type(scope): brief description

Longer description if needed explaining what changed and why.

- List specific changes
- Reference issues: Fixes #123
- Breaking changes: BREAKING CHANGE: description
```

## 🧪 Testing

### Running Tests
```bash
# Backend tests
cd backend
pytest                          # All tests
pytest tests/test_scanner.py    # Specific test file
pytest -v                       # Verbose output
pytest -x                       # Stop at first failure

# Frontend tests (if applicable)
cd frontend
npm test                        # All tests
npm run test:coverage          # With coverage report

# Integration tests
pytest tests/test_integration.py -v
```

### Writing Tests
```python
# Test file structure: tests/test_[module].py
def test_scan_python_requirements():
    """Test scanning a simple requirements.txt file."""
    # Arrange
    requirements_content = "requests==2.28.0\n"
    
    # Act
    result = scan_requirements(requirements_content)
    
    # Assert
    assert result.total_dependencies > 0
    assert "requests" in [dep.name for dep in result.dependencies]
```

**Testing Guidelines:**
- **Unit tests** for core functionality
- **Integration tests** for external APIs
- **Mock external services** to avoid rate limits
- **Test error conditions** and edge cases
- **Maintain test coverage** above 80%

## 🏗️ Project Structure

```
socketTest/
├── backend/                    # Python backend
│   ├── cli/                   # CLI implementation
│   ├── core/                  # Core scanning logic
│   ├── web/                   # Web API
│   └── tests/                 # Backend tests
├── frontend/                  # React frontend
│   ├── src/                   # Source code
│   └── tests/                 # Frontend tests
├── deploy/                    # Deployment scripts
│   ├── terraform/             # AWS infrastructure
│   └── docker/                # Docker configurations
├── .github/                   # GitHub workflows
└── docs/                      # Additional documentation
```

## 🔒 Security Considerations

### Reporting Security Issues
- **Do NOT** create public issues for security vulnerabilities
- **Email** the maintainers privately
- **Follow** the [Security Policy](SECURITY.md)

### Code Security
- **No hardcoded secrets** or credentials
- **Input validation** for all user inputs
- **Secure dependencies** (regularly updated)
- **Container security** for Docker images

## 📖 Documentation

### Code Documentation
```python
def scan_dependencies(file_path: str, options: ScanOptions) -> ScanResult:
    """Scan dependency file for vulnerabilities.
    
    Args:
        file_path: Path to dependency file (requirements.txt, package.json)
        options: Scanning configuration options
        
    Returns:
        ScanResult containing vulnerabilities and metadata
        
    Raises:
        FileNotFoundError: If dependency file doesn't exist
        ValidationError: If file format is invalid
    """
```

### README Updates
- **Keep installation instructions current**
- **Update feature lists** when adding functionality
- **Add examples** for new CLI options
- **Update deployment guides** for infrastructure changes

## 🎉 Recognition

Contributors will be recognized in:
- **GitHub Contributors** list
- **Release notes** for significant contributions
- **Documentation credits** for major improvements
- **Special mentions** in project communications

## ❓ Getting Help

### Where to Ask Questions
- **GitHub Discussions**: General questions and ideas
- **GitHub Issues**: Bug reports and feature requests  
- **Code Reviews**: Specific implementation feedback

### Response Times
- **Issues**: Within 48 hours
- **Pull Requests**: Within 1 week
- **Discussions**: Best effort, community-driven

## 📋 Pull Request Checklist

Before submitting your PR, ensure:

- [ ] **Tests pass**: All existing and new tests pass
- [ ] **Code is formatted**: Black, isort, flake8 all pass
- [ ] **Type checking**: MyPy passes with no errors
- [ ] **Documentation updated**: README, docstrings, etc.
- [ ] **Security check**: Bandit passes
- [ ] **Commit messages**: Follow conventional format
- [ ] **PR description**: Clear description of changes
- [ ] **Issue linked**: References related issues
- [ ] **Breaking changes**: Documented if applicable

## 🚀 Release Process

### Versioning
We use [Semantic Versioning](https://semver.org/):
- **Major (1.0.0)**: Breaking changes
- **Minor (1.1.0)**: New features, backward compatible
- **Patch (1.0.1)**: Bug fixes

### Release Timeline
- **Patch releases**: As needed for critical bugs
- **Minor releases**: Monthly for new features
- **Major releases**: When significant breaking changes accumulate

---

**Thank you for contributing to DepScan!** 🛡️

*Your contributions help make dependency scanning more accessible and secure for everyone.*