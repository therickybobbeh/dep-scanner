"""
Tests for PackageLockV1Parser
"""
import pytest
import json
from backend.core.resolver.parsers.javascript.package_lock_v1 import PackageLockV1Parser
from backend.core.resolver.base import ParseError
from backend.tests.fixtures.package_lock_samples import (
    PACKAGE_LOCK_V1,
    MALFORMED_PACKAGE_LOCK
)


class TestPackageLockV1Parser:
    
    @pytest.fixture
    def parser(self):
        return PackageLockV1Parser()
    
    @pytest.mark.asyncio
    async def test_parse_package_lock_v1(self, parser):
        """Test parsing package-lock.json v1 format"""
        content = json.dumps(PACKAGE_LOCK_V1)
        deps = await parser.parse(content)
        
        # Should extract both direct and transitive dependencies
        assert len(deps) >= 6  # express, lodash, jest + transitive deps
        
        # Find direct dependencies (top-level in dependencies section)
        direct_deps = [dep for dep in deps if dep.is_direct]
        transitive_deps = [dep for dep in deps if not dep.is_direct]
        
        assert len(direct_deps) >= 3  # express, lodash, jest
        assert len(transitive_deps) >= 3  # accepts, mime-types, etc.
        
        # Verify express (direct dependency)
        express_dep = next((d for d in deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.version == "4.18.2"
        assert express_dep.is_direct is True
        assert express_dep.is_dev is False
        assert express_dep.ecosystem == "npm"
        assert express_dep.path == ["express"]
        
        # Verify lodash (direct dependency)
        lodash_dep = next((d for d in deps if d.name == "lodash"), None)
        assert lodash_dep is not None
        assert lodash_dep.version == "4.17.21"
        assert lodash_dep.is_direct is True
        assert lodash_dep.is_dev is False
        
        # Verify jest (dev dependency)
        jest_dep = next((d for d in deps if d.name == "jest"), None)
        assert jest_dep is not None
        assert jest_dep.version == "29.7.0"
        assert jest_dep.is_direct is True
        assert jest_dep.is_dev is True
        
        # Verify transitive dependencies
        accepts_dep = next((d for d in deps if d.name == "accepts"), None)
        assert accepts_dep is not None
        assert accepts_dep.version == "1.3.8"
        assert accepts_dep.is_direct is False
        assert "express" in accepts_dep.path  # Should show dependency path
        assert "accepts" in accepts_dep.path
        
        # Verify nested transitive dependency
        mime_types_dep = next((d for d in deps if d.name == "mime-types"), None)
        assert mime_types_dep is not None
        assert mime_types_dep.version == "2.1.35"
        assert mime_types_dep.is_direct is False
        # Should be nested under accepts
        assert len(mime_types_dep.path) >= 2
        
        # Verify mime-db (deeply nested)
        mime_db_dep = next((d for d in deps if d.name == "mime-db"), None)
        assert mime_db_dep is not None
        assert mime_db_dep.version == "1.52.0"
        assert mime_db_dep.is_direct is False
        # Should have longest path
        assert len(mime_db_dep.path) >= 2
    
    @pytest.mark.asyncio
    async def test_dependency_path_tracking(self, parser):
        """Test that dependency paths are correctly tracked"""
        content = json.dumps(PACKAGE_LOCK_V1)
        deps = await parser.parse(content)
        
        # Check specific path structures
        accepts_dep = next((d for d in deps if d.name == "accepts"), None)
        assert accepts_dep is not None
        # accepts is a direct dependency of express
        assert accepts_dep.path == ["express", "accepts"]
        
        mime_types_dep = next((d for d in deps if d.name == "mime-types"), None)
        assert mime_types_dep is not None
        # mime-types should be under accepts
        expected_path = ["express", "accepts", "mime-types"]
        assert mime_types_dep.path == expected_path
        
        negotiator_dep = next((d for d in deps if d.name == "negotiator"), None)
        assert negotiator_dep is not None
        # negotiator should be direct child of accepts
        assert negotiator_dep.path == ["express", "accepts", "negotiator"]
    
    @pytest.mark.asyncio
    async def test_dev_dependency_detection(self, parser):
        """Test that dev dependencies are properly detected"""
        content = json.dumps(PACKAGE_LOCK_V1)
        deps = await parser.parse(content)
        
        dev_deps = [dep for dep in deps if dep.is_dev]
        prod_deps = [dep for dep in deps if not dep.is_dev]
        
        # Jest should be marked as dev
        jest_dep = next((d for d in deps if d.name == "jest"), None)
        assert jest_dep is not None
        assert jest_dep.is_dev is True
        
        # Express and its dependencies should not be dev
        express_dep = next((d for d in deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.is_dev is False
        
        # Transitive deps of prod deps should not be dev
        accepts_dep = next((d for d in deps if d.name == "accepts"), None)
        assert accepts_dep is not None
        assert accepts_dep.is_dev is False
    
    @pytest.mark.asyncio
    async def test_lockfile_version_validation(self, parser):
        """Test that only v1 lockfiles are accepted"""
        # Test v1 lockfile (should work)
        v1_lock = {"lockfileVersion": 1, "dependencies": {}}
        content = json.dumps(v1_lock)
        deps = await parser.parse(content)
        assert isinstance(deps, list)
        
        # Test v2 lockfile (should raise error)
        v2_lock = {"lockfileVersion": 2, "packages": {}}
        content = json.dumps(v2_lock)
        with pytest.raises(ParseError) as exc_info:
            await parser.parse(content)
        assert "v1" in str(exc_info.value) or "version 1" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_malformed_lockfile(self, parser):
        """Test handling of malformed lockfile"""
        with pytest.raises(ParseError):
            await parser.parse("invalid json")
        
        # Test missing dependencies section
        content = json.dumps(MALFORMED_PACKAGE_LOCK)
        with pytest.raises(ParseError):
            await parser.parse(content)
    
    def test_extract_nested_dependencies(self, parser):
        """Test extraction of nested dependencies from v1 format"""
        nested_deps = {
            "express": {
                "version": "4.18.2",
                "dependencies": {
                    "accepts": {
                        "version": "1.3.8",
                        "dependencies": {
                            "mime-types": {
                                "version": "2.1.35"
                            }
                        }
                    }
                }
            }
        }
        
        result = parser._extract_dependencies_recursive(nested_deps, ["root"])
        
        # Should extract all levels
        names = [dep.name for dep in result]
        assert "express" in names
        assert "accepts" in names
        assert "mime-types" in names
        
        # Verify paths
        express_dep = next((d for d in result if d.name == "express"), None)
        assert express_dep.path == ["root", "express"]
        
        accepts_dep = next((d for d in result if d.name == "accepts"), None)
        assert accepts_dep.path == ["root", "express", "accepts"]
        
        mime_types_dep = next((d for d in result if d.name == "mime-types"), None)
        assert mime_types_dep.path == ["root", "express", "accepts", "mime-types"]
    
    def test_parser_format_support(self, parser):
        """Test parser format identification"""
        assert parser.can_parse("package-lock.json")
        assert not parser.can_parse("package.json")
        assert not parser.can_parse("yarn.lock")
    
    def test_transitive_dependency_support(self, parser):
        """Test that parser correctly identifies transitive support"""
        assert parser.supports_transitive_dependencies()
    
    @pytest.mark.asyncio
    async def test_empty_dependencies_section(self, parser):
        """Test handling of empty dependencies section"""
        lock_data = {
            "name": "test",
            "version": "1.0.0",
            "lockfileVersion": 1,
            "dependencies": {}
        }
        
        content = json.dumps(lock_data)
        deps = await parser.parse(content)
        
        assert len(deps) == 0
    
    @pytest.mark.asyncio
    async def test_dependency_deduplication(self, parser):
        """Test that duplicate dependencies are handled correctly"""
        # In v1, nested deps can appear multiple times if they have same version
        # Parser should handle this gracefully
        content = json.dumps(PACKAGE_LOCK_V1)
        deps = await parser.parse(content)
        
        # Check that each package appears only once at each path
        dep_paths = [(dep.name, tuple(dep.path)) for dep in deps]
        assert len(dep_paths) == len(set(dep_paths)), "Duplicate dependencies found"
    
    def test_version_extraction(self, parser):
        """Test version extraction from dependency entries"""
        dep_entry = {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
            "integrity": "sha512-..."
        }
        
        version = parser._extract_version(dep_entry)
        assert version == "4.18.2"
        
        # Test missing version
        invalid_entry = {"resolved": "https://registry.npmjs.org/test"}
        version = parser._extract_version(invalid_entry)
        assert version is None