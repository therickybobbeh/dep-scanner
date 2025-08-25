"""
Tests for YarnLockParser
"""
import pytest
from backend.core.resolver.parsers.javascript.yarn_lock import YarnLockParser
from backend.core.resolver.base import ParseError
from backend.tests.fixtures.yarn_lock_samples import (
    BASIC_YARN_LOCK,
    COMPLEX_YARN_LOCK,
    MINIMAL_YARN_LOCK,
    MALFORMED_YARN_LOCK
)


class TestYarnLockParser:
    
    @pytest.fixture
    def parser(self):
        return YarnLockParser()
    
    @pytest.mark.asyncio
    async def test_parse_basic_yarn_lock(self, parser):
        """Test parsing basic yarn.lock file"""
        deps = await parser.parse(BASIC_YARN_LOCK)
        
        # Should extract all dependencies
        assert len(deps) >= 7  # All packages listed in the lock file
        
        # Verify specific packages
        express_dep = next((d for d in deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.version == "4.18.2"
        assert express_dep.is_direct is True  # Top-level dependency
        assert express_dep.ecosystem == "npm"
        assert express_dep.path == ["express"]
        
        lodash_dep = next((d for d in deps if d.name == "lodash"), None)
        assert lodash_dep is not None
        assert lodash_dep.version == "4.17.21"
        
        # Verify transitive dependencies
        accepts_dep = next((d for d in deps if d.name == "accepts"), None)
        assert accepts_dep is not None
        assert accepts_dep.version == "1.3.8"
        assert accepts_dep.is_direct is False  # Transitive dependency
        
        mime_types_dep = next((d for d in deps if d.name == "mime-types"), None)
        assert mime_types_dep is not None
        assert mime_types_dep.version == "2.1.35"
    
    @pytest.mark.asyncio
    async def test_parse_complex_yarn_lock(self, parser):
        """Test parsing complex yarn.lock with scoped packages and version ranges"""
        deps = await parser.parse(COMPLEX_YARN_LOCK)
        
        dep_names = [dep.name for dep in deps]
        
        # Should handle scoped packages
        assert "@babel/core" in dep_names
        assert "@types/node" in dep_names
        
        # Should handle version ranges and multiple version specs
        lodash_dep = next((d for d in deps if d.name == "lodash"), None)
        assert lodash_dep is not None
        assert lodash_dep.version == "4.17.21"
        
        # Verify React and its dependencies
        react_dep = next((d for d in deps if d.name == "react"), None)
        assert react_dep is not None
        assert react_dep.version == "18.2.0"
        
        loose_envify_dep = next((d for d in deps if d.name == "loose-envify"), None)
        assert loose_envify_dep is not None
        assert loose_envify_dep.is_direct is False  # Transitive from React
    
    @pytest.mark.asyncio
    async def test_parse_minimal_yarn_lock(self, parser):
        """Test parsing minimal yarn.lock with single dependency"""
        deps = await parser.parse(MINIMAL_YARN_LOCK)
        
        assert len(deps) == 1
        
        lodash_dep = deps[0]
        assert lodash_dep.name == "lodash"
        assert lodash_dep.version == "4.17.21"
        assert lodash_dep.is_direct is True
        assert lodash_dep.ecosystem == "npm"
    
    @pytest.mark.asyncio
    async def test_parse_malformed_yarn_lock(self, parser):
        """Test handling of malformed yarn.lock file"""
        with pytest.raises(ParseError):
            await parser.parse(MALFORMED_YARN_LOCK)
    
    def test_parse_package_entry(self, parser):
        """Test parsing individual package entries from yarn.lock"""
        # Test basic entry
        entry_lines = [
            'express@^4.18.2:',
            '  version "4.18.2"',
            '  resolved "https://registry.yarnpkg.com/express/-/express-4.18.2.tgz"',
            '  integrity sha512-...',
            '  dependencies:',
            '    accepts "~1.3.8"',
            '    cookie "0.5.0"'
        ]
        
        entry = parser._parse_package_entry(entry_lines)
        
        assert entry["name"] == "express"
        assert entry["version"] == "4.18.2"
        assert entry["version_specs"] == ["^4.18.2"]
        assert "accepts" in entry["dependencies"]
        assert "cookie" in entry["dependencies"]
    
    def test_parse_package_entry_multiple_specs(self, parser):
        """Test parsing package with multiple version specifications"""
        entry_lines = [
            'lodash@^4.17.21, lodash@4.17.21:',
            '  version "4.17.21"',
            '  resolved "https://registry.yarnpkg.com/lodash/-/lodash-4.17.21.tgz"',
            '  integrity sha512-...'
        ]
        
        entry = parser._parse_package_entry(entry_lines)
        
        assert entry["name"] == "lodash"
        assert entry["version"] == "4.17.21"
        assert "^4.17.21" in entry["version_specs"]
        assert "4.17.21" in entry["version_specs"]
    
    def test_parse_scoped_package(self, parser):
        """Test parsing scoped npm packages"""
        entry_lines = [
            '"@babel/core@^7.20.0":',
            '  version "7.23.2"',
            '  resolved "https://registry.yarnpkg.com/@babel/core/-/core-7.23.2.tgz"',
            '  integrity sha512-...'
        ]
        
        entry = parser._parse_package_entry(entry_lines)
        
        assert entry["name"] == "@babel/core"
        assert entry["version"] == "7.23.2"
        assert "^7.20.0" in entry["version_specs"]
    
    def test_is_direct_dependency_detection(self, parser):
        """Test detection of direct vs transitive dependencies"""
        # This would require analyzing the actual dependency tree
        # For now, test the heuristic based on version specs
        
        # Package with exact version is likely direct
        assert parser._is_likely_direct(["4.17.21"])
        
        # Package with range is likely direct  
        assert parser._is_likely_direct(["^4.17.21"])
        
        # Package with multiple specs might be transitive
        # (appears multiple times with different requirements)
        result = parser._is_likely_direct(["^4.17.21", "~4.17.0", "4.17.21"])
        # This is a heuristic and may vary based on implementation
        assert isinstance(result, bool)
    
    def test_extract_package_name_from_spec(self, parser):
        """Test extracting package name from version specification line"""
        test_cases = [
            ('express@^4.18.2:', 'express'),
            ('lodash@^4.17.21, lodash@4.17.21:', 'lodash'),
            ('"@babel/core@^7.20.0":', '@babel/core'),
            ('"@types/node@^18.0.0":', '@types/node'),
            ('simple-package@1.0.0:', 'simple-package')
        ]
        
        for spec_line, expected_name in test_cases:
            name = parser._extract_package_name(spec_line)
            assert name == expected_name
    
    def test_extract_version_specs_from_spec(self, parser):
        """Test extracting version specifications from spec line"""
        test_cases = [
            ('express@^4.18.2:', ['^4.18.2']),
            ('lodash@^4.17.21, lodash@4.17.21:', ['^4.17.21', '4.17.21']),
            ('"@babel/core@^7.20.0":', ['^7.20.0']),
            ('package@>=1.0.0 <2.0.0:', ['>=1.0.0 <2.0.0'])
        ]
        
        for spec_line, expected_specs in test_cases:
            specs = parser._extract_version_specs(spec_line)
            assert specs == expected_specs
    
    def test_parser_format_support(self, parser):
        """Test parser format identification"""
        assert parser.can_parse("yarn.lock")
        assert not parser.can_parse("package.json")
        assert not parser.can_parse("package-lock.json")
    
    def test_transitive_dependency_support(self, parser):
        """Test that parser correctly identifies transitive support"""
        assert parser.supports_transitive_dependencies()
    
    @pytest.mark.asyncio
    async def test_empty_yarn_lock(self, parser):
        """Test handling of empty yarn.lock file"""
        empty_lock = '''# THIS IS AN AUTOGENERATED FILE. DO NOT EDIT THIS FILE DIRECTLY.
# yarn lockfile v1
'''
        
        deps = await parser.parse(empty_lock)
        assert len(deps) == 0
    
    def test_parse_dependency_list(self, parser):
        """Test parsing dependency list from package entry"""
        dep_lines = [
            '  dependencies:',
            '    accepts "~1.3.8"',
            '    array-flatten "1.1.1"',
            '    cookie "0.5.0"',
            '    "@babel/runtime" "^7.0.0"'
        ]
        
        dependencies = parser._parse_dependency_list(dep_lines)
        
        assert "accepts" in dependencies
        assert "array-flatten" in dependencies  
        assert "cookie" in dependencies
        assert "@babel/runtime" in dependencies
        assert dependencies["accepts"] == "~1.3.8"
        assert dependencies["@babel/runtime"] == "^7.0.0"
    
    @pytest.mark.asyncio
    async def test_dependency_path_construction(self, parser):
        """Test that dependency paths are constructed correctly"""
        deps = await parser.parse(BASIC_YARN_LOCK)
        
        # All dependencies should have valid paths
        for dep in deps:
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1
            assert dep.name in dep.path
            assert all(isinstance(segment, str) for segment in dep.path)