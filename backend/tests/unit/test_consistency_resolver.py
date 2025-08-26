"""
Tests for consistency improvements between package.json and package-lock.json scanning
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.resolver.js_resolver import JavaScriptResolver
from backend.core.resolver.utils.scan_consistency import ScanConsistencyAnalyzer
from backend.core.resolver.utils.npm_version_resolver import PackageVersionResolver, ResolvedVersion
from backend.core.models import Dep


class TestPackageJsonConsistency:
    """Test consistency improvements for package.json scanning"""
    
    @pytest.fixture
    def sample_package_json(self):
        return {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "~4.17.21",
                "axios": ">=0.27.0"
            },
            "devDependencies": {
                "jest": "^28.0.0",
                "eslint": "^8.0.0"
            }
        }
    
    @pytest.fixture
    def sample_package_lock_json(self):
        return {
            "name": "test-project",
            "version": "1.0.0",
            "lockfileVersion": 2,
            "requires": True,
            "packages": {
                "": {
                    "name": "test-project",
                    "version": "1.0.0",
                    "dependencies": {
                        "express": "^4.18.0",
                        "lodash": "~4.17.21",
                        "axios": ">=0.27.0"
                    },
                    "devDependencies": {
                        "jest": "^28.0.0",
                        "eslint": "^8.0.0"
                    }
                },
                "node_modules/express": {
                    "version": "4.18.2",
                    "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz"
                },
                "node_modules/lodash": {
                    "version": "4.17.21",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz"
                },
                "node_modules/axios": {
                    "version": "0.27.2",
                    "resolved": "https://registry.npmjs.org/axios/-/axios-0.27.2.tgz"
                },
                "node_modules/jest": {
                    "version": "28.1.3",
                    "resolved": "https://registry.npmjs.org/jest/-/jest-28.1.3.tgz",
                    "dev": True
                },
                "node_modules/eslint": {
                    "version": "8.23.1",
                    "resolved": "https://registry.npmjs.org/eslint/-/eslint-8.23.1.tgz",
                    "dev": True
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_standard_vs_enhanced_package_json_parsing(self, sample_package_json):
        """Test that enhanced parsing provides more consistent results"""
        # Test standard resolver
        standard_resolver = JavaScriptResolver(enhanced_package_json=False)
        
        manifest_files = {"package.json": json.dumps(sample_package_json)}
        standard_deps = await standard_resolver.resolve_dependencies(None, manifest_files)
        
        # Test enhanced resolver with version resolution
        enhanced_resolver = JavaScriptResolver(
            enhanced_package_json=True, 
            resolve_versions=True
        )
        
        # Mock version resolution for testing
        with patch('backend.core.resolver.utils.npm_version_resolver.PackageVersionResolver.resolve_multiple') as mock_resolve:
            mock_resolve.return_value = {
                "express": ResolvedVersion("^4.18.0", "4.18.2", "registry"),
                "lodash": ResolvedVersion("~4.17.21", "4.17.21", "registry"),
                "axios": ResolvedVersion(">=0.27.0", "0.27.2", "registry"),
                "jest": ResolvedVersion("^28.0.0", "28.1.3", "registry"),
                "eslint": ResolvedVersion("^8.0.0", "8.23.1", "registry")
            }
            
            enhanced_deps = await enhanced_resolver.resolve_dependencies(None, manifest_files)
        
        # Compare results
        assert len(standard_deps) == len(enhanced_deps)
        
        # Standard deps should have version ranges, enhanced should have resolved versions
        standard_express = next(d for d in standard_deps if d.name == "express")
        enhanced_express = next(d for d in enhanced_deps if d.name == "express")
        
        # Standard parser would clean "^4.18.0" to "4.18.0"
        assert standard_express.version == "4.18.0"
        # Enhanced parser should resolve to actual version
        assert enhanced_express.version == "4.18.2"
    
    @pytest.mark.asyncio
    async def test_consistency_check_between_manifest_and_lockfile(
        self, 
        sample_package_json, 
        sample_package_lock_json
    ):
        """Test consistency checking between package.json and package-lock.json"""
        resolver = JavaScriptResolver(enhanced_package_json=True, resolve_versions=True)
        
        manifest_files = {
            "package.json": json.dumps(sample_package_json),
            "package-lock.json": json.dumps(sample_package_lock_json)
        }
        
        # Mock version resolution to return lockfile versions
        with patch('backend.core.resolver.utils.npm_version_resolver.PackageVersionResolver.resolve_multiple') as mock_resolve:
            mock_resolve.return_value = {
                "express": ResolvedVersion("^4.18.0", "4.18.2", "registry"),
                "lodash": ResolvedVersion("~4.17.21", "4.17.21", "registry"),
                "axios": ResolvedVersion(">=0.27.0", "0.27.2", "registry"),
                "jest": ResolvedVersion("^28.0.0", "28.1.3", "registry"),
                "eslint": ResolvedVersion("^8.0.0", "8.23.1", "registry")
            }
            
            deps, consistency_report = await resolver.resolve_with_consistency_check(
                manifest_files, 
                check_consistency=True
            )
        
        # Verify consistency report structure
        assert "enabled" in consistency_report
        assert consistency_report["enabled"] is True
        assert "best_source" in consistency_report
        assert "manifest_vs_lockfile" in consistency_report
        
        # Should prefer lockfile as best source
        assert consistency_report["best_source"] == "package-lock.json"
        
        # Consistency should be high when enhanced parser resolves to lockfile versions
        manifest_lockfile_comparison = consistency_report["manifest_vs_lockfile"]
        assert manifest_lockfile_comparison["consistency_score"] > 0.8
        assert manifest_lockfile_comparison["version_mismatches"] == 0
    
    @pytest.mark.asyncio
    async def test_version_mismatch_detection(self, sample_package_json):
        """Test detection of version mismatches between approaches"""
        resolver = JavaScriptResolver(enhanced_package_json=True, resolve_versions=True)
        
        # Create a lockfile with different versions
        mismatched_lockfile = {
            "lockfileVersion": 2,
            "packages": {
                "": {"dependencies": {"express": "^4.18.0", "lodash": "~4.17.21"}},
                "node_modules/express": {"version": "4.17.0"},  # Different from resolved version
                "node_modules/lodash": {"version": "4.17.21"}   # Matches
            }
        }
        
        manifest_files = {
            "package.json": json.dumps(sample_package_json),
            "package-lock.json": json.dumps(mismatched_lockfile)
        }
        
        # Mock version resolution to return different versions than lockfile
        with patch('backend.core.resolver.utils.npm_version_resolver.PackageVersionResolver.resolve_multiple') as mock_resolve:
            mock_resolve.return_value = {
                "express": ResolvedVersion("^4.18.0", "4.18.2", "registry"),  # Different from lockfile
                "lodash": ResolvedVersion("~4.17.21", "4.17.21", "registry"),  # Same as lockfile
                "axios": ResolvedVersion(">=0.27.0", "0.27.2", "fallback")
            }
            
            deps, consistency_report = await resolver.resolve_with_consistency_check(
                manifest_files,
                check_consistency=True
            )
        
        # Should detect version mismatches
        manifest_lockfile_comparison = consistency_report["manifest_vs_lockfile"]
        assert manifest_lockfile_comparison["version_mismatches"] > 0
        assert manifest_lockfile_comparison["consistency_score"] < 1.0
        assert len(manifest_lockfile_comparison["recommendations"]) > 0


class TestScanConsistencyAnalyzer:
    """Test the scan consistency analyzer"""
    
    @pytest.fixture
    def sample_deps_manifest(self):
        """Dependencies as they would appear from package.json parsing"""
        return [
            Dep(name="express", version="4.18.0", ecosystem="npm", path=["express"], is_direct=True, is_dev=False),
            Dep(name="lodash", version="4.17.21", ecosystem="npm", path=["lodash"], is_direct=True, is_dev=False),
            Dep(name="jest", version="28.0.0", ecosystem="npm", path=["jest"], is_direct=True, is_dev=True)
        ]
    
    @pytest.fixture  
    def sample_deps_lockfile(self):
        """Dependencies as they would appear from lockfile parsing"""
        return [
            Dep(name="express", version="4.18.2", ecosystem="npm", path=["express"], is_direct=True, is_dev=False),
            Dep(name="lodash", version="4.17.21", ecosystem="npm", path=["lodash"], is_direct=True, is_dev=False),
            Dep(name="jest", version="28.1.3", ecosystem="npm", path=["jest"], is_direct=True, is_dev=True),
            # Transitive dependency only in lockfile
            Dep(name="accepts", version="1.3.8", ecosystem="npm", path=["express", "accepts"], is_direct=False, is_dev=False)
        ]
    
    def test_dependency_comparison(self, sample_deps_manifest, sample_deps_lockfile):
        """Test basic dependency comparison functionality"""
        analyzer = ScanConsistencyAnalyzer()
        
        report = analyzer.compare_dependency_lists(
            sample_deps_manifest, 
            sample_deps_lockfile
        )
        
        # Verify basic metrics
        assert report.total_manifest_deps == 3
        assert report.total_lockfile_deps == 4
        assert report.matching_dependencies == 1  # Only lodash matches exactly
        assert report.version_mismatches == 2     # express and jest have different versions
        assert report.missing_in_manifest == 1   # accepts is only in lockfile
        assert report.missing_in_lockfile == 0   # All manifest deps are in lockfile
        
        # Verify consistency score
        expected_score = 1 / 4  # 1 matching out of 4 total dependencies
        assert abs(report.consistency_score - expected_score) < 0.01
        
        # Verify recommendations are generated
        assert len(report.recommendations) > 0
    
    def test_version_mismatch_details(self, sample_deps_manifest, sample_deps_lockfile):
        """Test detailed version mismatch reporting"""
        analyzer = ScanConsistencyAnalyzer()
        
        report = analyzer.compare_dependency_lists(
            sample_deps_manifest,
            sample_deps_lockfile
        )
        
        mismatch_details = analyzer.get_version_mismatch_details(report)
        
        # Should have 2 mismatches: express and jest
        assert len(mismatch_details) == 2
        
        # Check express mismatch
        express_mismatch = next(d for d in mismatch_details if d["package"] == "express")
        assert express_mismatch["manifest_version"] == "4.18.0"
        assert express_mismatch["lockfile_version"] == "4.18.2"
        
        # Check jest mismatch
        jest_mismatch = next(d for d in mismatch_details if d["package"] == "jest")
        assert jest_mismatch["manifest_version"] == "28.0.0"
        assert jest_mismatch["lockfile_version"] == "28.1.3"
    
    def test_consistency_summary_generation(self, sample_deps_manifest, sample_deps_lockfile):
        """Test human-readable summary generation"""
        analyzer = ScanConsistencyAnalyzer()
        
        report = analyzer.compare_dependency_lists(
            sample_deps_manifest,
            sample_deps_lockfile
        )
        
        summary = analyzer.generate_consistency_summary(report)
        
        # Verify summary contains key information
        assert "Scan Consistency Analysis" in summary
        assert "Manifest dependencies: 3" in summary
        assert "Lockfile dependencies: 4" in summary
        assert "Version mismatches: 2" in summary
        assert "Recommendations:" in summary


class TestVersionResolution:
    """Test npm version resolution functionality"""
    
    @pytest.mark.asyncio
    async def test_version_range_resolution_fallback(self):
        """Test version resolution with fallback when registry is unavailable"""
        from backend.core.resolver.utils.npm_version_resolver import PackageVersionResolver
        
        resolver = PackageVersionResolver()
        
        # Test fallback resolution (without registry)
        result = await resolver.resolve_version_range(
            "express", 
            "^4.18.0", 
            use_registry=False
        )
        
        assert result.original_range == "^4.18.0"
        assert result.source == "fallback"
        assert result.resolved_version == "4.18.0"  # Should strip the caret
    
    def test_semver_range_satisfaction(self):
        """Test semantic version range satisfaction logic"""
        from backend.core.resolver.utils.npm_version_resolver import SemverResolver
        
        resolver = SemverResolver()
        
        # Test caret ranges
        assert resolver.satisfies_range("4.18.2", "^4.18.0") is True
        assert resolver.satisfies_range("4.19.0", "^4.18.0") is True
        assert resolver.satisfies_range("5.0.0", "^4.18.0") is False
        assert resolver.satisfies_range("4.17.0", "^4.18.0") is False
        
        # Test tilde ranges
        assert resolver.satisfies_range("4.18.5", "~4.18.0") is True
        assert resolver.satisfies_range("4.19.0", "~4.18.0") is False
        
        # Test comparison operators
        assert resolver.satisfies_range("1.0.0", ">=0.27.0") is True
        assert resolver.satisfies_range("0.26.0", ">=0.27.0") is False
    
    def test_best_version_selection(self):
        """Test selection of best version from available versions"""
        from backend.core.resolver.utils.npm_version_resolver import SemverResolver
        
        resolver = SemverResolver()
        
        available_versions = ["4.17.0", "4.18.0", "4.18.1", "4.18.2", "4.19.0", "5.0.0"]
        
        # Should select highest compatible version
        best = resolver.find_best_version(available_versions, "^4.18.0")
        assert best == "4.19.0"
        
        # Tilde range should be more restrictive
        best_tilde = resolver.find_best_version(available_versions, "~4.18.0")
        assert best_tilde == "4.18.2"
        
        # Exact version
        best_exact = resolver.find_best_version(available_versions, "4.18.1")
        assert best_exact == "4.18.1"


@pytest.mark.integration
class TestEndToEndConsistency:
    """Integration tests for full consistency checking workflow"""
    
    @pytest.mark.asyncio
    async def test_full_consistency_workflow(self):
        """Test the complete workflow from file upload to consistency report"""
        # This would test the integration with the web service
        # Mock the core scanner to use enhanced JavaScript resolver
        
        package_json_content = json.dumps({
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "~4.17.21"
            }
        })
        
        package_lock_content = json.dumps({
            "lockfileVersion": 2,
            "packages": {
                "": {"dependencies": {"express": "^4.18.0", "lodash": "~4.17.21"}},
                "node_modules/express": {"version": "4.18.2"},
                "node_modules/lodash": {"version": "4.17.21"}
            }
        })
        
        # Test that enhanced resolver provides consistency information
        enhanced_resolver = JavaScriptResolver(
            enhanced_package_json=True,
            resolve_versions=True
        )
        
        manifest_files = {
            "package.json": package_json_content,
            "package-lock.json": package_lock_content
        }
        
        with patch('backend.core.resolver.utils.npm_version_resolver.PackageVersionResolver.resolve_multiple') as mock_resolve:
            mock_resolve.return_value = {
                "express": ResolvedVersion("^4.18.0", "4.18.2", "registry"),
                "lodash": ResolvedVersion("~4.17.21", "4.17.21", "registry")
            }
            
            deps, consistency_report = await enhanced_resolver.resolve_with_consistency_check(
                manifest_files,
                check_consistency=True
            )
        
        # Verify that consistency checking provides actionable information
        assert consistency_report["enabled"] is True
        assert "manifest_vs_lockfile" in consistency_report
        assert consistency_report["manifest_vs_lockfile"]["consistency_score"] >= 0.8
        
        # The resolved dependencies should match lockfile versions when version resolution works
        assert len(deps) >= 2
        express_dep = next(d for d in deps if d.name == "express")
        assert express_dep.version == "4.18.2"  # Should match lockfile version