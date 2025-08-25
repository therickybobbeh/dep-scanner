"""
Tests for RequirementsParser
"""
import pytest
from backend.core.resolver.parsers.python.requirements import RequirementsParser
from backend.core.resolver.base import ParseError
from backend.tests.fixtures.python_samples import (
    BASIC_REQUIREMENTS_TXT,
    COMPLEX_REQUIREMENTS_TXT
)


class TestRequirementsParser:
    
    @pytest.fixture
    def parser(self):
        return RequirementsParser()
    
    @pytest.mark.asyncio
    async def test_parse_basic_requirements(self, parser):
        """Test parsing basic requirements.txt file"""
        deps = await parser.parse(BASIC_REQUIREMENTS_TXT)
        
        # Should extract all valid requirements
        assert len(deps) >= 5
        
        # Verify specific packages
        flask_dep = next((d for d in deps if d.name == "flask"), None)
        assert flask_dep is not None
        assert flask_dep.version == "2.3.2"
        assert flask_dep.is_direct is True
        assert flask_dep.is_dev is False
        assert flask_dep.ecosystem == "PyPI"
        assert flask_dep.path == ["flask"]
        
        requests_dep = next((d for d in deps if d.name == "requests"), None)
        assert requests_dep is not None
        assert requests_dep.version == "2.28.0"  # Should clean >=2.28.0 to 2.28.0
        
        numpy_dep = next((d for d in deps if d.name == "numpy"), None)
        assert numpy_dep is not None
        assert numpy_dep.version == "1.24.0"  # Should clean ~=1.24.0 to 1.24.0
        
        click_dep = next((d for d in deps if d.name == "click"), None)
        assert click_dep is not None
        assert click_dep.version == "8.1.3"
        
        werkzeug_dep = next((d for d in deps if d.name == "werkzeug"), None)
        assert werkzeug_dep is not None
        assert werkzeug_dep.version == "2.3.6"
    
    @pytest.mark.asyncio
    async def test_parse_complex_requirements(self, parser):
        """Test parsing complex requirements.txt with various formats"""
        deps = await parser.parse(COMPLEX_REQUIREMENTS_TXT)
        
        dep_names = [dep.name for dep in deps]
        
        # Should include standard packages
        assert "django" in dep_names
        assert "psycopg2-binary" in dep_names
        assert "redis" in dep_names
        assert "celery" in dep_names
        assert "pytest" in dep_names
        assert "black" in dep_names
        assert "isort" in dep_names
        assert "mypy" in dep_names
        assert "urllib3" in dep_names
        
        # Should exclude git and local dependencies
        assert "custom-package" not in dep_names
        
        # Verify version handling
        django_dep = next((d for d in deps if d.name == "django"), None)
        assert django_dep.version == "4.2.1"
        
        # Verify complex version specs
        redis_dep = next((d for d in deps if d.name == "redis"), None)
        assert redis_dep.version == "4.0.0"  # Should extract from >=4.0.0,<5.0.0
        
        # Verify extras handling
        celery_dep = next((d for d in deps if d.name == "celery"), None)
        assert celery_dep.version == "5.2.7"
    
    def test_parse_requirement_line(self, parser):
        """Test parsing individual requirement lines"""
        test_cases = [
            ("Flask==2.3.2", ("flask", "2.3.2")),
            ("requests>=2.28.0", ("requests", "2.28.0")),
            ("numpy~=1.24.0", ("numpy", "1.24.0")),
            ("Django>=4.2.0,<5.0.0", ("django", "4.2.0")),
            ("celery[redis]==5.2.7", ("celery", "5.2.7")),
            ("package-with-dashes==1.0.0", ("package-with-dashes", "1.0.0")),
            ("UPPERCASE==1.0.0", ("uppercase", "1.0.0")),  # Should normalize to lowercase
            ("", None),  # Empty line
            ("# comment", None),  # Comment
            ("-e ./local", None),  # Editable install
            ("git+https://github.com/user/repo.git", None),  # Git URL
            ("https://example.com/package.tar.gz", None),  # HTTP URL
        ]
        
        for line, expected in test_cases:
            result = parser._parse_requirement_line(line)
            assert result == expected
    
    def test_clean_package_name(self, parser):
        """Test package name cleaning and normalization"""
        test_cases = [
            ("Flask", "flask"),
            ("DJANGO", "django"),
            ("package-with-dashes", "package-with-dashes"),
            ("package_with_underscores", "package_with_underscores"),
            ("Package.With.Dots", "package.with.dots"),
            ("123numeric", "123numeric"),
            ("", ""),
        ]
        
        for name, expected in test_cases:
            result = parser._clean_package_name(name)
            assert result == expected
    
    def test_extract_version_from_spec(self, parser):
        """Test version extraction from various version specifications"""
        test_cases = [
            ("==2.3.2", "2.3.2"),
            (">=2.28.0", "2.28.0"),
            ("~=1.24.0", "1.24.0"),
            ("<=3.0.0", "3.0.0"),
            (">1.0.0", "1.0.0"),
            ("<2.0.0", "2.0.0"),
            (">=2.0.0,<3.0.0", "2.0.0"),
            (">=2.0.0,<=2.5.0", "2.0.0"),
            ("*", None),
            ("", None),
            ("latest", None),
            ("dev", None),
        ]
        
        for spec, expected in test_cases:
            result = parser._extract_version(spec)
            if expected is None:
                assert result is None or result == ""
            else:
                assert result == expected
    
    def test_is_valid_requirement_line(self, parser):
        """Test validation of requirement lines"""
        valid_lines = [
            "Flask==2.3.2",
            "requests>=2.28.0",
            "numpy~=1.24.0",
            "celery[redis]==5.2.7",
            "package-with-dashes>=1.0.0"
        ]
        
        invalid_lines = [
            "",  # Empty
            "   ",  # Whitespace only
            "# This is a comment",
            "-e ./local-package",
            "git+https://github.com/user/repo.git",
            "https://example.com/package.tar.gz",
            "-r other-requirements.txt",
            "--index-url https://pypi.org/simple/",
            "-f https://download.pytorch.org/whl/torch_stable.html"
        ]
        
        for line in valid_lines:
            assert parser._is_valid_requirement_line(line), f"Should be valid: {line}"
        
        for line in invalid_lines:
            assert not parser._is_valid_requirement_line(line), f"Should be invalid: {line}"
    
    def test_detect_dev_requirements(self, parser):
        """Test detection of dev requirements files"""
        dev_files = [
            "dev-requirements.txt",
            "requirements-dev.txt",
            "test-requirements.txt",
            "requirements-test.txt",
            "requirements/dev.txt",
            "requirements/test.txt"
        ]
        
        prod_files = [
            "requirements.txt",
            "requirements/base.txt",
            "requirements/prod.txt",
            "requirements/production.txt"
        ]
        
        for filename in dev_files:
            assert parser.detect_dev_requirements(filename), f"Should be dev: {filename}"
        
        for filename in prod_files:
            assert not parser.detect_dev_requirements(filename), f"Should be prod: {filename}"
    
    @pytest.mark.asyncio
    async def test_parse_dev_requirements(self, parser):
        """Test parsing dev requirements with is_dev flag"""
        deps = await parser.parse(BASIC_REQUIREMENTS_TXT, is_dev=True)
        
        # All dependencies should be marked as dev
        for dep in deps:
            assert dep.is_dev is True
    
    @pytest.mark.asyncio
    async def test_parse_empty_requirements(self, parser):
        """Test parsing empty requirements file"""
        empty_content = "\n# Just comments\n\n# More comments\n"
        deps = await parser.parse(empty_content)
        
        assert len(deps) == 0
    
    @pytest.mark.asyncio
    async def test_parse_malformed_requirements(self, parser):
        """Test handling of malformed requirements"""
        malformed_content = """
        Flask==
        ==2.3.2
        invalid-spec
        package-name-only
        """
        
        # Should not raise error, but may skip invalid entries
        deps = await parser.parse(malformed_content)
        assert isinstance(deps, list)
        # May have 0 deps if all are invalid, or some valid ones
    
    def test_parser_format_support(self, parser):
        """Test parser format identification"""
        assert parser.can_parse("requirements.txt")
        assert parser.can_parse("dev-requirements.txt")
        assert parser.can_parse("test-requirements.txt")
        assert not parser.can_parse("pyproject.toml")
        assert not parser.can_parse("poetry.lock")
        assert not parser.can_parse("Pipfile")
    
    def test_transitive_dependency_support(self, parser):
        """Test that parser correctly identifies no transitive support"""
        assert not parser.supports_transitive_dependencies()
    
    @pytest.mark.asyncio
    async def test_whitespace_handling(self, parser):
        """Test handling of whitespace in requirements"""
        content_with_whitespace = """
        
            Flask==2.3.2   
        
            requests>=2.28.0   # With comment
        
        """
        
        deps = await parser.parse(content_with_whitespace)
        
        assert len(deps) == 2
        dep_names = [dep.name for dep in deps]
        assert "flask" in dep_names
        assert "requests" in dep_names
    
    @pytest.mark.asyncio
    async def test_comment_handling(self, parser):
        """Test handling of comments in requirements"""
        content_with_comments = """
# Production dependencies
Flask==2.3.2  # Web framework
requests>=2.28.0  # HTTP library

# Development dependencies  
pytest>=7.0.0  # Testing framework
"""
        
        deps = await parser.parse(content_with_comments)
        
        assert len(deps) == 3
        dep_names = [dep.name for dep in deps]
        assert "flask" in dep_names
        assert "requests" in dep_names  
        assert "pytest" in dep_names