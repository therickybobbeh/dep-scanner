# 🤝 Contributing to DepScan

Thank you for your interest in contributing to DepScan! This guide will help you get started with contributing to this dependency vulnerability scanner.

## 🎯 Ways to Contribute

### 🐛 Bug Reports
- Found a bug? [Open an issue](https://github.com/yourusername/depscan/issues)
- Provide clear reproduction steps
- Include system information and error messages
- Check existing issues to avoid duplicates

### ✨ Feature Requests  
- Have an idea for improvement? Share it!
- Explain the use case and benefits
- Consider if it fits the project's scope
- Discuss implementation approach

### 💻 Code Contributions
- Fix bugs or implement features
- Improve documentation
- Add new parser formats
- Enhance test coverage
- Optimize performance

### 📖 Documentation
- Fix typos or improve clarity
- Add examples and use cases
- Create tutorials or guides
- Update outdated information

---

## 🚀 Getting Started

### 1. Fork & Clone

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/yourusername/depscan.git
cd depscan

# Add upstream remote
git remote add upstream https://github.com/original/depscan.git
```

### 2. Development Setup

```bash
# Backend development environment
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Frontend development (if needed)
cd frontend
npm install
npm run dev  # Development server
```

### 3. Verify Setup

```bash
# Run tests to ensure everything works
./run_tests.py

# Try CLI tool
python backend/cli.py scan frontend/ --json test.json

# Start web server
cd backend && python -m uvicorn app.main:app --reload
```

---

## 📋 Development Workflow

### 1. Create Feature Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch  
git checkout -b feature/parser-support-go
# or
git checkout -b fix/memory-leak-large-files
# or  
git checkout -b docs/improve-cli-examples
```

### 2. Make Changes

Follow our [coding standards](#-coding-standards) and write tests for new functionality.

### 3. Test Changes

```bash
# Run complete test suite
./run_tests.py

# Run specific tests
pytest tests/unit/parsers/ -v
pytest tests/integration/ -v

# Check code quality
black backend/  # Format code
isort backend/  # Sort imports
mypy backend/   # Type checking
```

### 4. Commit Changes

Use clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "Add support for Go mod files in dependency resolution"
git commit -m "Fix memory leak when processing large package-lock.json files"
git commit -m "Update CLI documentation with advanced usage examples"

# Follow conventional commits format (optional)
git commit -m "feat(parsers): add Go mod file support"
git commit -m "fix(scanner): resolve memory leak in large file processing"
git commit -m "docs(cli): add advanced usage examples"
```

### 5. Submit Pull Request

```bash
# Push to your fork
git push origin feature/parser-support-go

# Create pull request on GitHub
# Fill out the PR template completely
```

---

## 🧪 Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── parsers/            # Parser-specific tests
│   ├── factories/          # Factory pattern tests  
│   ├── utils/              # Utility class tests
│   └── services/           # Service layer tests
├── integration/            # Integration tests
│   └── test_end_to_end.py  # Full workflow tests
└── fixtures/               # Test data
    ├── package_samples.py  # Sample dependency files
    └── vulnerability_data.py
```

### Writing Tests

#### Parser Tests Example

```python
import pytest
from backend.app.resolver.parsers.go.go_mod import GoModParser

class TestGoModParser:
    
    @pytest.fixture
    def parser(self):
        return GoModParser()
    
    @pytest.mark.asyncio
    async def test_parse_go_mod(self, parser):
        content = """
        module example.com/myapp
        
        go 1.19
        
        require (
            github.com/gin-gonic/gin v1.9.1
            github.com/stretchr/testify v1.8.4
        )
        """
        
        deps = await parser.parse(content)
        
        assert len(deps) == 2
        gin_dep = next((d for d in deps if d.name == "github.com/gin-gonic/gin"), None)
        assert gin_dep is not None
        assert gin_dep.version == "1.9.1"
        assert gin_dep.ecosystem == "Go"
```

#### Integration Tests Example

```python
@pytest.mark.asyncio
async def test_complete_go_workflow(go_resolver, osv_scanner):
    """Test complete Go dependency scanning workflow"""
    manifest_files = {"go.mod": sample_go_mod, "go.sum": sample_go_sum}
    
    # Resolve dependencies
    deps = await go_resolver.resolve_dependencies(None, manifest_files)
    assert len(deps) > 0
    
    # Scan for vulnerabilities  
    vulnerabilities = await osv_scanner.scan_dependencies(deps)
    assert isinstance(vulnerabilities, list)
    
    # Verify Go ecosystem
    for dep in deps:
        assert dep.ecosystem == "Go"
```

### Test Data

Create realistic test fixtures in `tests/fixtures/`:

```python
# tests/fixtures/go_samples.py
BASIC_GO_MOD = """
module github.com/example/myapp

go 1.19

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/lib/pq v1.10.9
)

require (
    github.com/bytedance/sonic v1.9.1 // indirect
    github.com/gin-contrib/sse v0.1.0 // indirect
)
"""
```

---

## 📝 Coding Standards

### Python Code Style

We use automated tools to maintain consistent code quality:

```bash
# Format code
black backend/
isort backend/

# Type checking
mypy backend/

# Linting  
flake8 backend/
```

#### Key Principles

1. **Type Hints**: Use type hints for all function parameters and return values
```python
def parse_dependencies(content: str, is_dev: bool = False) -> list[Dep]:
    """Parse dependency content and return list of dependencies."""
    pass
```

2. **Docstrings**: Use Google-style docstrings
```python
def resolve_dependencies(self, repo_path: str | None, 
                        manifest_files: dict[str, str] | None = None) -> list[Dep]:
    """
    Resolve dependencies from repository or manifest files.
    
    Args:
        repo_path: Path to repository directory (None if using manifest_files)
        manifest_files: Dict of {filename: content} for uploaded files
        
    Returns:
        List of dependency objects with full transitive resolution when possible
        
    Raises:
        FileNotFoundError: If no supported dependency files found
        ParseError: If parsing fails
    """
```

3. **Error Handling**: Use specific exception types
```python
from .base import ParseError

try:
    data = json.loads(content)
except json.JSONDecodeError as e:
    raise ParseError("go.mod", e) from e
```

4. **Modern Python**: Use Python 3.10+ features
```python
# Use union types
def get_parser(filename: str) -> BaseDependencyParser | None:
    pass

# Use match statements for complex conditionals
match file_extension:
    case ".go":
        return GoModParser()
    case ".py":
        return PythonParser()
    case _:
        return None
```

### TypeScript/React Code Style

For frontend contributions:

```bash
# Format and lint
npm run lint
npm run format

# Type checking
npm run type-check
```

#### Key Principles

1. **TypeScript**: Use strict TypeScript
2. **Components**: Functional components with hooks
3. **Styling**: Tailwind CSS classes
4. **State**: React hooks for local state, context for global state

---

## 🏗️ Architecture Guidelines

### Adding New Parser Support

To add support for a new package manager (e.g., Go modules):

#### 1. Create Parser Class

```python
# backend/app/resolver/parsers/go/go_mod.py
from ...base import BaseDependencyParser, ParseError
from ....models import Dep

class GoModParser(BaseDependencyParser):
    def __init__(self):
        super().__init__(ecosystem="Go")
    
    async def parse(self, content: str) -> list[Dep]:
        """Parse go.mod file content."""
        # Implementation here
        pass
    
    def can_parse(self, filename: str) -> bool:
        return filename == "go.mod"
    
    def supports_transitive_dependencies(self) -> bool:
        return True  # if go.sum provides transitive deps
```

#### 2. Create Factory Support

```python
# Update backend/app/resolver/factories/go_factory.py
class GoParserFactory(FileFormatDetector):
    def get_parser(self, filename: str, content: str) -> BaseDependencyParser:
        if filename == "go.mod":
            return GoModParser()
        elif filename == "go.sum":
            return GoSumParser()
        else:
            raise ValueError(f"Unsupported Go file: {filename}")
```

#### 3. Create Resolver

```python  
# backend/app/resolver/go_resolver.py
class GoResolver:
    def __init__(self):
        self.ecosystem = "Go"
        self.parser_factory = GoParserFactory()
    
    async def resolve_dependencies(self, repo_path: str | None, 
                                 manifest_files: dict[str, str] | None = None) -> list[Dep]:
        # Implementation following existing patterns
        pass
```

#### 4. Add Tests

Create comprehensive tests following existing patterns:
- Unit tests for parser
- Factory tests
- Integration tests
- Test fixtures

#### 5. Update Documentation

- Add to supported formats in README.md
- Update user guides
- Add examples

### Extending OSV Integration

To add support for additional vulnerability databases:

#### 1. Create Scanner Class

```python
# backend/app/scanner/nvd.py
class NVDScanner:
    async def scan_dependencies(self, deps: list[Dep]) -> list[Vuln]:
        """Scan dependencies against NVD database."""
        pass
```

#### 2. Update Scanner Service

```python
# backend/app/services/scan_service.py
class ScanService:
    def __init__(self):
        self.osv_scanner = OSVScanner()
        self.nvd_scanner = NVDScanner()  # Add new scanner
    
    async def scan_vulnerabilities(self, deps: list[Dep]) -> list[Vuln]:
        # Combine results from multiple scanners
        pass
```

---

## 🔄 Review Process

### Pull Request Requirements

- [ ] **Tests**: All new code has corresponding tests
- [ ] **Documentation**: Updated relevant documentation  
- [ ] **Type Hints**: All functions have proper type annotations
- [ ] **Code Quality**: Passes linting and formatting checks
- [ ] **Backwards Compatibility**: Changes don't break existing functionality
- [ ] **Performance**: No significant performance regressions

### Review Checklist

Reviewers will check:

1. **Functionality**: Code works as intended
2. **Tests**: Adequate test coverage and quality
3. **Architecture**: Follows existing patterns and principles
4. **Documentation**: Clear and complete
5. **Performance**: Efficient implementation  
6. **Security**: No security vulnerabilities introduced

### Feedback Process

- Be respectful and constructive
- Explain the reasoning behind feedback
- Suggest specific improvements
- Acknowledge good work
- Iterate until all concerns are addressed

---

## 🎯 Priority Contribution Areas

### High Priority

1. **New Parser Support**
   - Go modules (go.mod, go.sum)
   - Rust Cargo (Cargo.toml, Cargo.lock)
   - Ruby Gems (Gemfile, Gemfile.lock)
   - .NET (packages.config, project.json)

2. **Performance Improvements**
   - Parallel dependency resolution
   - More efficient caching
   - Memory usage optimization
   - Large file handling

3. **Security Enhancements**
   - Additional vulnerability databases
   - SBOM (Software Bill of Materials) export
   - Supply chain risk analysis
   - License compliance checking

### Medium Priority

1. **Web Interface Improvements**
   - Dependency graph visualization
   - Interactive filtering
   - Batch file upload
   - Export options

2. **CLI Enhancements**
   - Configuration file support
   - Plugin system
   - Better error messages
   - Progress indicators

3. **Integration Features**
   - IDE plugins
   - GitHub App
   - CI/CD plugins
   - Slack/Teams notifications

### Low Priority

1. **Developer Experience**
   - Better debugging tools
   - Development Docker setup
   - Code generation tools
   - Documentation improvements

---

## ❓ Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests, questions
- **GitHub Discussions**: General discussion, ideas, help
- **Email**: maintainer@depscan.dev (for sensitive issues)

### Before Asking

1. **Search existing issues** - Your question might already be answered
2. **Check documentation** - Comprehensive guides available
3. **Try latest version** - Issue might already be fixed
4. **Provide context** - Include system info, error messages, steps to reproduce

### Mentorship Program

New contributors can request mentorship:

1. **Find a mentor**: Look for "mentor available" labels on issues
2. **Express interest**: Comment on the issue asking for guidance  
3. **Pair programming**: Schedule video calls for complex features
4. **Code review**: Get detailed feedback on your contributions

---

## 🏆 Recognition

### Contributors

All contributors are recognized in:
- README.md contributors section
- CONTRIBUTORS.md file
- GitHub repository insights
- Release notes for significant contributions

### Maintainers

Active contributors may be invited to become maintainers with:
- Commit access to repository
- Review privileges for pull requests
- Input on project direction and roadmap
- Recognition in project documentation

---

## 📄 License

By contributing to DepScan, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to DepScan! Your efforts help make software development more secure for everyone. 🙏