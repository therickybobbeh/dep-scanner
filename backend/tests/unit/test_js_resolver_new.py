"""
Updated tests for JavaScript resolver using new modular architecture
"""
import pytest
import json
from backend.core.resolver.js_resolver import JavaScriptResolver
from backend.core.models import Dep
from backend.tests.fixtures.package_json_samples import (
    BASIC_PACKAGE_JSON,
    COMPLEX_PACKAGE_JSON,
    MINIMAL_PACKAGE_JSON
)
from backend.tests.fixtures.package_lock_samples import (
    PACKAGE_LOCK_V1,
    PACKAGE_LOCK_V2,
    PACKAGE_LOCK_V3
)
from backend.tests.fixtures.yarn_lock_samples import (
    BASIC_YARN_LOCK,
    COMPLEX_YARN_LOCK
)


class TestJavaScriptResolverNew:
    
    @pytest.fixture
    def js_resolver(self):
        return JavaScriptResolver()
    
    # Test new architecture methods
    
    @pytest.mark.asyncio
    async def test_resolve_from_package_json_only(self, js_resolver):
        """Test resolving dependencies from package.json only (direct dependencies)"""
        manifest_files = {"package.json": json.dumps(BASIC_PACKAGE_JSON)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should extract all dependencies but mark as direct only
        assert len(deps) == 5  # 3 prod + 2 dev
        
        # All should be direct dependencies (no transitive resolution for package.json)
        direct_deps = [dep for dep in deps if dep.is_direct]
        assert len(direct_deps) == 5
        
        # Verify specific packages
        dep_names = [dep.name for dep in deps]
        assert "express" in dep_names
        assert "lodash" in dep_names
        assert "axios" in dep_names
        assert "jest" in dep_names
        assert "typescript" in dep_names
        
        # Verify dev dependency detection
        dev_deps = [dep for dep in deps if dep.is_dev]
        assert len(dev_deps) == 2
        dev_names = [dep.name for dep in dev_deps]
        assert "jest" in dev_names
        assert "typescript" in dev_names
    
    @pytest.mark.asyncio
    async def test_resolve_from_package_lock_v1(self, js_resolver):
        """Test resolving from package-lock.json v1 (transitive dependencies)"""
        manifest_files = {"package-lock.json": json.dumps(PACKAGE_LOCK_V1)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should extract both direct and transitive dependencies
        assert len(deps) >= 6
        
        # Should have both direct and transitive dependencies
        direct_deps = [dep for dep in deps if dep.is_direct]
        transitive_deps = [dep for dep in deps if not dep.is_direct]
        assert len(direct_deps) >= 3
        assert len(transitive_deps) >= 3
        
        # Verify transitive dependencies have proper paths
        transitive_dep = next((d for d in transitive_deps if d.name == "accepts"), None)
        assert transitive_dep is not None
        assert len(transitive_dep.path) > 1  # Should show dependency chain
    
    @pytest.mark.asyncio
    async def test_resolve_from_package_lock_v2(self, js_resolver):
        """Test resolving from package-lock.json v2+ format"""
        manifest_files = {"package-lock.json": json.dumps(PACKAGE_LOCK_V2)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should handle v2 format correctly
        assert len(deps) >= 3
        
        # Verify all deps have correct ecosystem
        for dep in deps:
            assert dep.ecosystem == "npm"
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1
    
    @pytest.mark.asyncio
    async def test_resolve_from_yarn_lock(self, js_resolver):
        """Test resolving from yarn.lock file"""
        manifest_files = {"yarn.lock": BASIC_YARN_LOCK}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should extract dependencies from yarn.lock
        assert len(deps) >= 3
        
        dep_names = [dep.name for dep in deps]
        assert "express" in dep_names
        assert "lodash" in dep_names
    
    @pytest.mark.asyncio  
    async def test_priority_order_lockfile_over_manifest(self, js_resolver):
        """Test that lockfiles take priority over manifests"""
        # Provide both package.json and package-lock.json
        manifest_files = {
            "package.json": json.dumps(BASIC_PACKAGE_JSON),
            "package-lock.json": json.dumps(PACKAGE_LOCK_V1)
        }
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should use package-lock.json (which provides transitive deps)
        transitive_deps = [dep for dep in deps if not dep.is_direct]
        assert len(transitive_deps) > 0, "Should use lockfile which provides transitive deps"
    
    # Test transitive dependency detection capabilities
    
    def test_can_resolve_transitive_dependencies(self, js_resolver):
        """Test transitive dependency capability detection for different formats"""
        # Lockfiles support transitive dependencies
        assert js_resolver.can_resolve_transitive_dependencies("package-lock.json") is True
        assert js_resolver.can_resolve_transitive_dependencies("yarn.lock") is True
        
        # Manifests don't support transitive dependencies
        assert js_resolver.can_resolve_transitive_dependencies("package.json") is False
    
    def test_get_resolution_info(self, js_resolver):
        """Test resolution information for different formats"""
        # Test package-lock.json info
        lock_info = js_resolver.get_resolution_info("package-lock.json")
        assert lock_info["transitive_resolution"] is True
        assert lock_info["deterministic_versions"] is True
        assert "NPM lockfile" in lock_info["description"]
        
        # Test yarn.lock info
        yarn_info = js_resolver.get_resolution_info("yarn.lock")
        assert yarn_info["transitive_resolution"] is True
        assert yarn_info["deterministic_versions"] is True
        assert "Yarn lockfile" in yarn_info["description"]
        
        # Test package.json info
        manifest_info = js_resolver.get_resolution_info("package.json")
        assert manifest_info["transitive_resolution"] is False
        assert manifest_info["deterministic_versions"] is False
        assert "NPM manifest" in manifest_info["description"]
        
        # Test unknown format
        unknown_info = js_resolver.get_resolution_info("unknown.txt")
        assert unknown_info["transitive_resolution"] is False
        assert unknown_info["format"] == "unknown"
    
    def test_get_supported_formats(self, js_resolver):
        """Test that all supported formats are listed"""
        formats = js_resolver.get_supported_formats()
        
        assert "package.json" in formats
        assert "package-lock.json" in formats
        assert "yarn.lock" in formats
        
        # Should be a reasonable number of formats
        assert len(formats) >= 3
        assert len(formats) <= 10  # Not too many
    
    # Test error handling
    
    @pytest.mark.asyncio
    async def test_no_manifest_files_error(self, js_resolver):
        """Test error when no manifest files provided"""
        with pytest.raises(ValueError) as exc_info:
            await js_resolver.resolve_dependencies(None, None)
        
        assert "Either repo_path or manifest_files must be provided" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_manifest_files_error(self, js_resolver):
        """Test error when empty manifest files provided"""
        with pytest.raises(ValueError) as exc_info:
            await js_resolver.resolve_dependencies(None, {})
        
        assert "No manifest files provided" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_unsupported_format_fallback(self, js_resolver):
        """Test behavior with unsupported file formats"""
        manifest_files = {"unsupported.txt": "some content"}
        
        # Should either raise an error or return empty list
        try:
            deps = await js_resolver.resolve_dependencies(None, manifest_files)
            assert isinstance(deps, list)
        except Exception as e:
            # Error is acceptable for unsupported formats
            assert "manifest files" in str(e).lower() or "format" in str(e).lower()
    
    # Test repository-based resolution
    
    @pytest.mark.asyncio
    async def test_resolve_from_repository_no_files(self, js_resolver, tmp_path):
        """Test repository resolution when no dependency files exist"""
        # Create empty directory
        empty_repo = tmp_path / "empty_repo"
        empty_repo.mkdir()
        
        with pytest.raises(FileNotFoundError) as exc_info:
            await js_resolver.resolve_dependencies(str(empty_repo))
        
        assert "No JavaScript dependency files found" in str(exc_info.value)
    
    # Test complex scenarios
    
    @pytest.mark.asyncio
    async def test_complex_package_json_with_various_deps(self, js_resolver):
        """Test complex package.json with various dependency types"""
        manifest_files = {"package.json": json.dumps(COMPLEX_PACKAGE_JSON)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should handle various dependency types
        dep_names = [dep.name for dep in deps]
        
        # Should include regular dependencies
        assert "react" in dep_names
        assert "lodash" in dep_names
        assert "moment" in dep_names
        assert "chalk" in dep_names
        
        # Should include scoped packages
        assert "@babel/core" in dep_names
        
        # Should include dev dependencies
        assert "@types/node" in dep_names
        assert "eslint" in dep_names
    
    @pytest.mark.asyncio
    async def test_version_cleaning_and_validation(self, js_resolver):
        """Test that versions are properly cleaned and validated"""
        manifest_files = {"package.json": json.dumps(BASIC_PACKAGE_JSON)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # All dependencies should have clean versions
        for dep in deps:
            assert dep.version is not None
            assert isinstance(dep.version, str)
            assert len(dep.version) > 0
            # Should not contain version prefixes like ^, ~, >=
            assert not any(prefix in dep.version for prefix in ["^", "~", ">=", "<=", "*"])
    
    @pytest.mark.asyncio
    async def test_ecosystem_consistency(self, js_resolver):
        """Test that all dependencies have consistent ecosystem"""
        manifest_files = {"package.json": json.dumps(BASIC_PACKAGE_JSON)}
        
        deps = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # All JavaScript dependencies should have npm ecosystem
        for dep in deps:
            assert dep.ecosystem == "npm"
    
    def test_resolver_ecosystem_property(self, js_resolver):
        """Test that resolver has correct ecosystem"""
        assert js_resolver.ecosystem == "npm"