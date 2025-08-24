"""
Tests for PackageJsonParser
"""
import pytest
import json
from backend.app.resolver.parsers.javascript.package_json import PackageJsonParser
from backend.app.resolver.base import ParseError
from tests.fixtures.package_json_samples import (
    BASIC_PACKAGE_JSON,
    COMPLEX_PACKAGE_JSON,
    MINIMAL_PACKAGE_JSON,
    MALFORMED_PACKAGE_JSON
)


class TestPackageJsonParser:
    
    @pytest.fixture
    def parser(self):
        return PackageJsonParser()
    
    @pytest.mark.asyncio
    async def test_parse_basic_package_json(self, parser):
        """Test parsing a basic package.json with prod and dev dependencies"""
        content = json.dumps(BASIC_PACKAGE_JSON)
        deps = await parser.parse(content)
        
        # Should extract all dependencies
        assert len(deps) == 5  # 3 prod + 2 dev
        
        # Verify production dependencies
        prod_deps = [dep for dep in deps if not dep.is_dev]
        assert len(prod_deps) == 3
        
        express_dep = next((d for d in prod_deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.version == "4.18.2"  # Should clean ^4.18.2 to 4.18.2
        assert express_dep.is_direct is True
        assert express_dep.is_dev is False
        assert express_dep.ecosystem == "npm"
        assert express_dep.path == ["express"]
        
        lodash_dep = next((d for d in prod_deps if d.name == "lodash"), None)
        assert lodash_dep is not None
        assert lodash_dep.version == "4.17.21"
        assert lodash_dep.is_direct is True
        
        axios_dep = next((d for d in prod_deps if d.name == "axios"), None)
        assert axios_dep is not None
        assert axios_dep.version == "1.6.0"  # Should clean ~1.6.0 to 1.6.0
        
        # Verify dev dependencies
        dev_deps = [dep for dep in deps if dep.is_dev]
        assert len(dev_deps) == 2
        
        jest_dep = next((d for d in dev_deps if d.name == "jest"), None)
        assert jest_dep is not None
        assert jest_dep.version == "29.0.0"  # Should clean ^29.0.0 to 29.0.0
        assert jest_dep.is_direct is True
        assert jest_dep.is_dev is True
        
        ts_dep = next((d for d in dev_deps if d.name == "typescript"), None)
        assert ts_dep is not None
        assert ts_dep.version == "5.0.4"
    
    @pytest.mark.asyncio
    async def test_parse_complex_package_json(self, parser):
        """Test parsing complex package.json with various dependency types"""
        content = json.dumps(COMPLEX_PACKAGE_JSON)
        deps = await parser.parse(content)
        
        # Should extract only valid semver dependencies
        dep_names = [dep.name for dep in deps]
        
        # Should include normal dependencies
        assert "react" in dep_names
        assert "lodash" in dep_names
        assert "moment" in dep_names
        assert "chalk" in dep_names
        assert "@babel/core" in dep_names  # Scoped package
        
        # Should include dev dependencies
        assert "@types/node" in dep_names
        assert "eslint" in dep_names
        
        # Should exclude git and file dependencies (not valid semver)
        assert "git-package" not in dep_names
        assert "local-package" not in dep_names
        
        # Verify version cleaning
        react_dep = next((d for d in deps if d.name == "react"), None)
        assert react_dep.version == "18.2.0"  # Cleaned from ^18.2.0
        
        moment_dep = next((d for d in deps if d.name == "moment"), None)
        assert moment_dep.version == "2.29.0"  # Cleaned from >=2.29.0
        
        chalk_dep = next((d for d in deps if d.name == "chalk"), None)
        assert chalk_dep.version == "4.1.0"  # Cleaned from ~4.1.0
        
        # Check that prettier with "*" version is handled
        prettier_dep = next((d for d in deps if d.name == "prettier"), None)
        if prettier_dep:  # Might be filtered out due to wildcard version
            assert prettier_dep.version is not None
    
    @pytest.mark.asyncio
    async def test_parse_minimal_package_json(self, parser):
        """Test parsing minimal package.json with no dependencies"""
        content = json.dumps(MINIMAL_PACKAGE_JSON)
        deps = await parser.parse(content)
        
        assert len(deps) == 0
    
    @pytest.mark.asyncio
    async def test_parse_malformed_json(self, parser):
        """Test handling of malformed JSON"""
        with pytest.raises(ParseError) as exc_info:
            await parser.parse("invalid json content")
        
        assert "Failed to parse package.json" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_parse_missing_dependencies_field(self, parser):
        """Test parsing package.json without dependencies field"""
        content = json.dumps({"name": "test", "version": "1.0.0"})
        deps = await parser.parse(content)
        
        assert len(deps) == 0
    
    def test_clean_version_specs(self, parser):
        """Test version specification cleaning"""
        test_cases = [
            ("4.18.2", "4.18.2"),
            ("^4.18.2", "4.18.2"),
            ("~4.18.2", "4.18.2"),
            (">=4.18.2", "4.18.2"),
            ("<=4.18.2", "4.18.2"),
            ("4.18.2 - 4.19.0", "4.18.2"),
            ("4.18.*", "4.18.0"),
            ("4.*", "4.0.0"),
            ("*", None),  # Should return None for wildcard
            ("", None),   # Should return None for empty
            ("latest", None),  # Should return None for non-semver
            ("git+https://github.com/user/repo.git", None)  # Git URLs
        ]
        
        for version_spec, expected in test_cases:
            result = parser.version_cleaner.clean_version(version_spec)
            if expected is None:
                assert result is None or result == ""
            else:
                assert result == expected
    
    def test_is_valid_package_name(self, parser):
        """Test package name validation"""
        valid_names = [
            "express",
            "lodash",
            "@babel/core",
            "@types/node",
            "my-package",
            "package.name"
        ]
        
        invalid_names = [
            "",
            "UPPERCASE",  # npm packages are lowercase
            "package with spaces",
            "package/name",  # Invalid character
            ".leadingdot",
            "trailing.",
            "_underscore_start"
        ]
        
        for name in valid_names:
            assert parser._is_valid_package_name(name), f"Should be valid: {name}"
        
        for name in invalid_names:
            assert not parser._is_valid_package_name(name), f"Should be invalid: {name}"
    
    @pytest.mark.asyncio
    async def test_dependency_extraction_order(self, parser):
        """Test that dependencies are extracted in consistent order"""
        content = json.dumps(BASIC_PACKAGE_JSON)
        deps1 = await parser.parse(content)
        deps2 = await parser.parse(content)
        
        # Should return dependencies in same order
        names1 = [dep.name for dep in deps1]
        names2 = [dep.name for dep in deps2]
        assert names1 == names2
    
    def test_parser_format_support(self, parser):
        """Test parser format identification"""
        assert parser.can_parse("package.json")
        assert not parser.can_parse("package-lock.json")
        assert not parser.can_parse("yarn.lock")
        assert not parser.can_parse("requirements.txt")
    
    def test_transitive_dependency_support(self, parser):
        """Test that parser correctly identifies no transitive support"""
        assert not parser.supports_transitive_dependencies()
        
    @pytest.mark.asyncio
    async def test_empty_dependency_sections(self, parser):
        """Test handling of empty dependency sections"""
        package_json = {
            "name": "test",
            "version": "1.0.0",
            "dependencies": {},
            "devDependencies": {},
            "peerDependencies": {},
            "optionalDependencies": {}
        }
        
        content = json.dumps(package_json)
        deps = await parser.parse(content)
        
        assert len(deps) == 0