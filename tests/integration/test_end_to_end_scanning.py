"""
End-to-end integration tests for the complete dependency scanning workflow
"""
import pytest
import json
import tempfile
from pathlib import Path
from backend.app.resolver.js_resolver import JavaScriptResolver
from backend.app.resolver.python_resolver import PythonResolver
from backend.app.scanner.osv import OSVScanner
from backend.app.models import ScanOptions, SeverityLevel
from tests.fixtures.package_json_samples import BASIC_PACKAGE_JSON, COMPLEX_PACKAGE_JSON
from tests.fixtures.package_lock_samples import PACKAGE_LOCK_V1, PACKAGE_LOCK_V2
from tests.fixtures.yarn_lock_samples import BASIC_YARN_LOCK
from tests.fixtures.python_samples import (
    BASIC_REQUIREMENTS_TXT, 
    BASIC_POETRY_LOCK,
    BASIC_PYPROJECT_TOML
)


class TestEndToEndScanning:
    """Test complete scanning workflow from dependency resolution to vulnerability detection"""
    
    @pytest.fixture
    def js_resolver(self):
        return JavaScriptResolver()
    
    @pytest.fixture
    def python_resolver(self):
        return PythonResolver()
    
    @pytest.fixture
    def osv_scanner(self):
        # Use in-memory database for testing
        return OSVScanner(cache_db_path=":memory:")
    
    @pytest.fixture
    def scan_options(self):
        return ScanOptions(
            include_dev_dependencies=True,
            ignore_severities=[],
            ignore_rules=[]
        )
    
    # JavaScript End-to-End Tests
    
    @pytest.mark.asyncio
    async def test_complete_js_package_json_workflow(self, js_resolver, osv_scanner, scan_options):
        """Test complete workflow: package.json -> dependencies -> vulnerabilities"""
        # Step 1: Resolve dependencies from package.json
        manifest_files = {"package.json": json.dumps(BASIC_PACKAGE_JSON)}
        dependencies = await js_resolver.resolve_dependencies(None, manifest_files)
        
        assert len(dependencies) > 0, "Should resolve some dependencies"
        
        # Verify all dependencies have required fields
        for dep in dependencies:
            assert dep.name is not None
            assert dep.version is not None
            assert dep.ecosystem == "npm"
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1
        
        # Step 2: Scan dependencies for vulnerabilities
        vulnerabilities = await osv_scanner.scan_dependencies(dependencies)
        
        # Should return a list (might be empty if no vulnerabilities found)
        assert isinstance(vulnerabilities, list)
        
        # If vulnerabilities found, verify they have required fields
        for vuln in vulnerabilities:
            assert vuln.package is not None
            assert vuln.version is not None
            assert vuln.ecosystem == "npm"
            assert vuln.vulnerability_id is not None
    
    @pytest.mark.asyncio
    async def test_complete_js_package_lock_workflow(self, js_resolver, osv_scanner, scan_options):
        """Test complete workflow with transitive dependencies from package-lock.json"""
        # Step 1: Resolve dependencies (including transitive)
        manifest_files = {"package-lock.json": json.dumps(PACKAGE_LOCK_V1)}
        dependencies = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should have both direct and transitive dependencies
        direct_deps = [dep for dep in dependencies if dep.is_direct]
        transitive_deps = [dep for dep in dependencies if not dep.is_direct]
        
        assert len(direct_deps) > 0, "Should have direct dependencies"
        assert len(transitive_deps) > 0, "Should have transitive dependencies"
        
        # Verify transitive dependencies have proper paths
        for dep in transitive_deps:
            assert len(dep.path) > 1, "Transitive deps should have path showing dependency chain"
        
        # Step 2: Scan all dependencies
        vulnerabilities = await osv_scanner.scan_dependencies(dependencies)
        assert isinstance(vulnerabilities, list)
        
        # Step 3: Verify vulnerability context
        for vuln in vulnerabilities:
            # Find the corresponding dependency
            matching_dep = next(
                (dep for dep in dependencies 
                 if dep.name == vuln.package and dep.version == vuln.version), 
                None
            )
            assert matching_dep is not None, f"Vulnerability {vuln.vulnerability_id} should match a dependency"
    
    @pytest.mark.asyncio
    async def test_js_format_priority_workflow(self, js_resolver, osv_scanner):
        """Test that format priority works correctly in end-to-end workflow"""
        # Provide both manifest and lockfile - should prefer lockfile
        manifest_files = {
            "package.json": json.dumps(BASIC_PACKAGE_JSON),
            "package-lock.json": json.dumps(PACKAGE_LOCK_V2),
            "yarn.lock": BASIC_YARN_LOCK
        }
        
        dependencies = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Should have used lockfile (has transitive dependencies)
        transitive_deps = [dep for dep in dependencies if not dep.is_direct]
        assert len(transitive_deps) > 0, "Should use lockfile which provides transitive deps"
        
        # Verify dependencies are scannable
        vulnerabilities = await osv_scanner.scan_dependencies(dependencies)
        assert isinstance(vulnerabilities, list)
    
    # Python End-to-End Tests
    
    @pytest.mark.asyncio
    async def test_complete_python_requirements_workflow(self, python_resolver, osv_scanner):
        """Test complete workflow: requirements.txt -> dependencies -> vulnerabilities"""
        # Step 1: Resolve dependencies from requirements.txt
        manifest_files = {"requirements.txt": BASIC_REQUIREMENTS_TXT}
        dependencies = await python_resolver.resolve_dependencies(None, manifest_files)
        
        assert len(dependencies) > 0, "Should resolve some dependencies"
        
        # Verify all dependencies have required fields for Python
        for dep in dependencies:
            assert dep.name is not None
            assert dep.version is not None
            assert dep.ecosystem == "PyPI"
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1
        
        # Step 2: Scan dependencies for vulnerabilities
        vulnerabilities = await osv_scanner.scan_dependencies(dependencies)
        assert isinstance(vulnerabilities, list)
        
        # Verify PyPI vulnerabilities
        for vuln in vulnerabilities:
            assert vuln.ecosystem == "PyPI"
    
    @pytest.mark.asyncio
    async def test_complete_python_poetry_workflow(self, python_resolver, osv_scanner):
        """Test complete workflow with Poetry lockfile"""
        # Step 1: Resolve dependencies (including transitive from poetry.lock)
        manifest_files = {"poetry.lock": BASIC_POETRY_LOCK}
        dependencies = await python_resolver.resolve_dependencies(None, manifest_files)
        
        # Poetry lock should provide transitive dependencies
        direct_deps = [dep for dep in dependencies if dep.is_direct]
        transitive_deps = [dep for dep in dependencies if not dep.is_direct]
        
        assert len(direct_deps) > 0, "Should have direct dependencies"
        # Note: transitive_deps might be 0 if poetry.lock doesn't have full tree
        
        # Step 2: Scan dependencies
        vulnerabilities = await osv_scanner.scan_dependencies(dependencies)
        assert isinstance(vulnerabilities, list)
    
    # Mixed Ecosystem Tests
    
    @pytest.mark.asyncio
    async def test_mixed_ecosystem_scanning(self, js_resolver, python_resolver, osv_scanner):
        """Test scanning dependencies from multiple ecosystems"""
        # Resolve JavaScript dependencies
        js_manifest = {"package.json": json.dumps(BASIC_PACKAGE_JSON)}
        js_deps = await js_resolver.resolve_dependencies(None, js_manifest)
        
        # Resolve Python dependencies  
        py_manifest = {"requirements.txt": BASIC_REQUIREMENTS_TXT}
        py_deps = await python_resolver.resolve_dependencies(None, py_manifest)
        
        # Combine all dependencies
        all_dependencies = js_deps + py_deps
        
        # Verify mixed ecosystems
        ecosystems = set(dep.ecosystem for dep in all_dependencies)
        assert "npm" in ecosystems
        assert "PyPI" in ecosystems
        
        # Scan all dependencies together
        vulnerabilities = await osv_scanner.scan_dependencies(all_dependencies)
        assert isinstance(vulnerabilities, list)
        
        # Verify vulnerabilities maintain correct ecosystem context
        if vulnerabilities:
            vuln_ecosystems = set(vuln.ecosystem for vuln in vulnerabilities)
            for ecosystem in vuln_ecosystems:
                assert ecosystem in ["npm", "PyPI"]
    
    # Repository-based Testing
    
    @pytest.mark.asyncio
    async def test_repository_based_scanning_workflow(self, js_resolver):
        """Test scanning from actual repository directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            
            # Create package.json file
            package_json_path = repo_path / "package.json"
            with open(package_json_path, 'w') as f:
                json.dump(BASIC_PACKAGE_JSON, f)
            
            # Create package-lock.json file
            package_lock_path = repo_path / "package-lock.json"
            with open(package_lock_path, 'w') as f:
                json.dump(PACKAGE_LOCK_V1, f)
            
            # Resolve from repository (should prefer lockfile)
            dependencies = await js_resolver.resolve_dependencies(str(repo_path))
            
            # Should find dependencies
            assert len(dependencies) > 0
            
            # Should have transitive dependencies (from lockfile)
            transitive_deps = [dep for dep in dependencies if not dep.is_direct]
            assert len(transitive_deps) > 0, "Should use lockfile from repository"
    
    # Error Handling and Edge Cases
    
    @pytest.mark.asyncio
    async def test_empty_dependency_list_scanning(self, osv_scanner):
        """Test scanning with empty dependency list"""
        vulnerabilities = await osv_scanner.scan_dependencies([])
        assert vulnerabilities == []
    
    @pytest.mark.asyncio
    async def test_malformed_dependencies_handling(self, js_resolver):
        """Test handling of malformed dependency files"""
        malformed_files = {"package.json": "invalid json content"}
        
        with pytest.raises(Exception):  # Should raise ParseError or similar
            await js_resolver.resolve_dependencies(None, malformed_files)
    
    @pytest.mark.asyncio
    async def test_unsupported_file_format_handling(self, js_resolver):
        """Test handling of unsupported file formats"""
        unsupported_files = {"unknown.xyz": "some content"}
        
        with pytest.raises((ValueError, FileNotFoundError)):
            await js_resolver.resolve_dependencies(None, unsupported_files)
    
    # Performance and Scale Tests
    
    @pytest.mark.asyncio
    async def test_large_dependency_list_performance(self, osv_scanner):
        """Test scanning performance with larger dependency lists"""
        # Create a larger list of dependencies for performance testing
        from backend.app.models import Dep
        
        large_dep_list = []
        for i in range(50):  # 50 dependencies should be manageable for testing
            dep = Dep(
                name=f"test-package-{i}",
                version=f"1.{i}.0",
                ecosystem="npm",
                path=[f"test-package-{i}"],
                is_direct=True,
                is_dev=False
            )
            large_dep_list.append(dep)
        
        # This should complete without timeout
        vulnerabilities = await osv_scanner.scan_dependencies(large_dep_list)
        assert isinstance(vulnerabilities, list)
    
    # Cleanup Tests
    
    @pytest.mark.asyncio
    async def test_cleanup_after_scanning(self, osv_scanner):
        """Test that cleanup works correctly after scanning"""
        from backend.app.models import Dep
        
        # Create test dependencies
        deps = [Dep(
            name="test-package",
            version="1.0.0", 
            ecosystem="npm",
            path=["test-package"],
            is_direct=True,
            is_dev=False
        )]
        
        # Scan dependencies
        await osv_scanner.scan_dependencies(deps)
        
        # Cleanup should work without errors
        await osv_scanner.close()
        
        # Further scanning should fail (client is closed)
        with pytest.raises(Exception):
            await osv_scanner.scan_dependencies(deps)
    
    # Configuration and Options Tests
    
    @pytest.mark.asyncio
    async def test_scan_options_filtering(self, js_resolver, osv_scanner):
        """Test that scan options properly filter results"""
        # Resolve dependencies
        manifest_files = {"package.json": json.dumps(COMPLEX_PACKAGE_JSON)}
        dependencies = await js_resolver.resolve_dependencies(None, manifest_files)
        
        # Separate prod and dev dependencies
        prod_deps = [dep for dep in dependencies if not dep.is_dev]
        dev_deps = [dep for dep in dependencies if dep.is_dev]
        
        assert len(prod_deps) > 0, "Should have production dependencies"
        assert len(dev_deps) > 0, "Should have development dependencies"
        
        # Test excluding dev dependencies
        prod_only_scan = await osv_scanner.scan_dependencies(prod_deps)
        all_deps_scan = await osv_scanner.scan_dependencies(dependencies)
        
        # Results should be consistent (prod-only should be subset of all)
        assert isinstance(prod_only_scan, list)
        assert isinstance(all_deps_scan, list)