"""Tests for core scanner functionality"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from backend.core.core_scanner import CoreScanner
from backend.core.models import ScanOptions, Report, JobStatus, Dep, Vuln, SeverityLevel


class TestCoreScanner:
    """Test cases for CoreScanner core functionality"""
    
    @pytest.fixture
    def scanner(self):
        """Create CoreScanner instance for testing"""
        return CoreScanner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock dependencies for testing"""
        return [
            Dep(name="requests", version="2.25.1", ecosystem="PyPI", path=["requests"], is_direct=True),
            Dep(name="lodash", version="4.17.19", ecosystem="npm", path=["lodash"], is_direct=True),
            Dep(name="urllib3", version="1.26.5", ecosystem="PyPI", path=["requests", "urllib3"], is_direct=False)
        ]
    
    @pytest.fixture
    def mock_vulnerabilities(self):
        """Mock vulnerabilities for testing"""
        return [
            Vuln(
                package="requests",
                version="2.25.1", 
                ecosystem="PyPI",
                vulnerability_id="PYSEC-2022-43012",
                severity=SeverityLevel.HIGH,
                summary="SSRF vulnerability in requests",
                fixed_range=None
            ),
            Vuln(
                package="lodash",
                version="4.17.19",
                ecosystem="npm", 
                vulnerability_id="GHSA-35jh-r3h4-6jhm",
                severity=SeverityLevel.MEDIUM,
                summary="Prototype pollution in lodash",
                fixed_range=None
            )
        ]
    
    def test_scanner_initialization(self, scanner):
        """Test scanner initializes with required components"""
        assert hasattr(scanner, 'python_resolver')
        assert hasattr(scanner, 'js_resolver')
        assert hasattr(scanner, 'osv_scanner')
        assert hasattr(scanner, 'npm_lock_generator')
        assert hasattr(scanner, 'python_lock_generator')
    
    @pytest.mark.asyncio
    async def test_scan_repository_nonexistent_path(self, scanner):
        """Test scan_repository with nonexistent path"""
        with pytest.raises(FileNotFoundError, match="Repository path does not exist"):
            await scanner.scan_repository("/nonexistent/path", ScanOptions())
    
    @pytest.mark.asyncio
    async def test_scan_repository_success(self, scanner, tmp_path, mock_dependencies, mock_vulnerabilities):
        """Test successful repository scan"""
        # Create test directory
        test_dir = tmp_path / "test_repo"
        test_dir.mkdir()
        
        # Mock the internal _scan_dependencies method
        with patch.object(scanner, '_scan_dependencies', new_callable=AsyncMock) as mock_scan:
            mock_report = Report(
                job_id="test-123",
                status=JobStatus.COMPLETED,
                total_dependencies=3,
                vulnerable_count=2,
                vulnerable_packages=mock_vulnerabilities,
                dependencies=mock_dependencies,
                suppressed_count=0,
                meta={}
            )
            mock_scan.return_value = mock_report
            
            result = await scanner.scan_repository(str(test_dir), ScanOptions())
            
            assert result == mock_report
            mock_scan.assert_called_once_with(
                repo_path=str(test_dir),
                manifest_files=None,
                options=ScanOptions(),
                progress_callback=None
            )
    
    @pytest.mark.asyncio
    async def test_scan_manifest_files_success(self, scanner, sample_manifest_files, mock_dependencies, mock_vulnerabilities):
        """Test successful manifest files scan"""
        with patch.object(scanner, '_ensure_lock_files', new_callable=AsyncMock) as mock_ensure:
            with patch.object(scanner, '_scan_dependencies', new_callable=AsyncMock) as mock_scan:
                mock_ensure.return_value = sample_manifest_files
                mock_report = Report(
                    job_id="test-123", 
                    status=JobStatus.COMPLETED,
                    total_dependencies=3,
                    vulnerable_count=2,
                    vulnerable_packages=mock_vulnerabilities,
                    dependencies=mock_dependencies,
                    suppressed_count=0,
                    meta={}
                )
                mock_scan.return_value = mock_report
                
                result = await scanner.scan_manifest_files(sample_manifest_files, ScanOptions())
                
                assert result == mock_report
                mock_ensure.assert_called_once_with(sample_manifest_files, None)
                mock_scan.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_lock_files_npm_success(self, scanner, sample_manifest_files):
        """Test _ensure_lock_files with successful NPM lock generation"""
        mock_progress = Mock()
        
        with patch.object(scanner.npm_lock_generator, 'ensure_lock_file', new_callable=AsyncMock) as mock_npm:
            with patch.object(scanner.python_lock_generator, 'ensure_lock_files', new_callable=AsyncMock) as mock_python:
                enhanced_files = sample_manifest_files.copy()
                enhanced_files["package-lock.json"] = '{"lockfileVersion": 2}'
                
                mock_npm.return_value = enhanced_files
                mock_python.return_value = enhanced_files
                
                result = await scanner._ensure_lock_files(sample_manifest_files, mock_progress)
                
                assert result == enhanced_files
                mock_npm.assert_called_once_with(sample_manifest_files, mock_progress)
                mock_python.assert_called_once_with(enhanced_files, mock_progress)
                
                # Verify progress callbacks were made
                assert mock_progress.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_ensure_lock_files_with_errors(self, scanner, sample_manifest_files):
        """Test _ensure_lock_files handles errors gracefully"""
        mock_progress = Mock()
        
        with patch.object(scanner.npm_lock_generator, 'ensure_lock_file', new_callable=AsyncMock) as mock_npm:
            with patch.object(scanner.python_lock_generator, 'ensure_lock_files', new_callable=AsyncMock) as mock_python:
                # Make NPM generation fail
                mock_npm.side_effect = Exception("NPM lock generation failed")
                mock_python.return_value = sample_manifest_files
                
                result = await scanner._ensure_lock_files(sample_manifest_files, mock_progress)
                
                # Should return original files despite error
                assert result == sample_manifest_files
                
                # Should have logged warning
                warning_calls = [call for call in mock_progress.call_args_list 
                               if len(call[0]) > 0 and "Warning:" in call[0][0]]
                assert len(warning_calls) > 0
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_python_only(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test _scan_dependencies with Python dependencies only"""
        python_deps = [dep for dep in mock_dependencies if dep.ecosystem == "PyPI"]
        python_vulns = [vuln for vuln in mock_vulnerabilities if vuln.ecosystem == "PyPI"]
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = python_deps
                    mock_js_resolver.return_value = []
                    mock_osv.return_value = python_vulns
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    assert result.total_dependencies == len(python_deps)
                    assert result.vulnerable_count == len(python_vulns)
                    assert "Python" in result.meta["ecosystems"]
                    assert "JavaScript" not in result.meta["ecosystems"]
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_javascript_only(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test _scan_dependencies with JavaScript dependencies only"""
        js_deps = [dep for dep in mock_dependencies if dep.ecosystem == "npm"]
        js_vulns = [vuln for vuln in mock_vulnerabilities if vuln.ecosystem == "npm"]
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = []
                    mock_js_resolver.return_value = js_deps
                    mock_osv.return_value = js_vulns
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    assert result.total_dependencies == len(js_deps)
                    assert result.vulnerable_count == len(js_vulns)
                    assert "JavaScript" in result.meta["ecosystems"]
                    assert "Python" not in result.meta["ecosystems"]
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_mixed_ecosystems(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test _scan_dependencies with mixed Python and JavaScript dependencies"""
        python_deps = [dep for dep in mock_dependencies if dep.ecosystem == "PyPI"]
        js_deps = [dep for dep in mock_dependencies if dep.ecosystem == "npm"]
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = python_deps
                    mock_js_resolver.return_value = js_deps
                    mock_osv.return_value = mock_vulnerabilities
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    assert result.total_dependencies == len(mock_dependencies)
                    assert result.vulnerable_count == len(mock_vulnerabilities)
                    assert "Python" in result.meta["ecosystems"]
                    assert "JavaScript" in result.meta["ecosystems"]
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_no_dependencies_found(self, scanner):
        """Test _scan_dependencies when no dependencies are found"""
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js_resolver:
                mock_py_resolver.return_value = []
                mock_js_resolver.return_value = []
                
                with pytest.raises(ValueError, match="No supported dependency files found"):
                    await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_exclude_dev_dependencies(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test _scan_dependencies excluding dev dependencies"""
        # Add dev dependency
        dev_deps = mock_dependencies + [
            Dep(name="jest", version="26.0.0", ecosystem="npm", path=["jest"], is_direct=True, is_dev=True)
        ]
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = []
                    mock_js_resolver.return_value = dev_deps
                    mock_osv.return_value = []
                    
                    options = ScanOptions(include_dev_dependencies=False)
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=options,
                        progress_callback=None
                    )
                    
                    # Should exclude dev dependencies
                    assert result.total_dependencies == len(mock_dependencies)  # Excludes jest
                    
                    # Verify only non-dev dependencies were passed to OSV scanner
                    osv_call_args = mock_osv.call_args[0][0]
                    assert all(not dep.is_dev for dep in osv_call_args)
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_ignore_severities(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test _scan_dependencies ignoring certain severities"""
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = mock_dependencies[:2]  # Python deps
                    mock_js_resolver.return_value = mock_dependencies[2:]  # JS deps
                    mock_osv.return_value = mock_vulnerabilities
                    
                    options = ScanOptions(ignore_severities=[SeverityLevel.MEDIUM])
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=options,
                        progress_callback=None
                    )
                    
                    # Should exclude MEDIUM severity vulnerabilities
                    high_vulns = [v for v in mock_vulnerabilities if v.severity != SeverityLevel.MEDIUM]
                    assert result.vulnerable_count == len(high_vulns)
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_with_progress_callback(self, scanner, mock_dependencies):
        """Test _scan_dependencies with progress callback"""
        mock_progress = Mock()
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = mock_dependencies
                    mock_js_resolver.return_value = []
                    mock_osv.return_value = []
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=mock_progress
                    )
                    
                    # Verify progress callbacks were made
                    assert mock_progress.call_count >= 3
                    
                    # Check specific progress messages
                    progress_calls = [call[0][0] for call in mock_progress.call_args_list]
                    assert any("Resolving dependency tree" in msg for msg in progress_calls)
                    assert any("Querying OSV database" in msg for msg in progress_calls)
                    assert any("Scan completed" in msg for msg in progress_calls)
    
    @pytest.mark.asyncio 
    async def test_scan_dependencies_resolver_errors(self, scanner):
        """Test _scan_dependencies handles resolver errors gracefully"""
        mock_progress = Mock()
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    # Make Python resolver fail
                    mock_py_resolver.side_effect = Exception("Python resolver failed")
                    mock_js_resolver.return_value = [
                        Dep(name="lodash", version="4.17.19", ecosystem="npm", path=["lodash"], is_direct=True)
                    ]
                    mock_osv.return_value = []
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=mock_progress
                    )
                    
                    # Should still succeed with JavaScript dependencies
                    assert result.total_dependencies == 1
                    
                    # Should have logged warning
                    warning_calls = [call for call in mock_progress.call_args_list 
                                   if len(call[0]) > 0 and "Warning:" in call[0][0]]
                    assert len(warning_calls) > 0
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_with_manifest_files(self, scanner, sample_manifest_files, mock_dependencies):
        """Test _scan_dependencies using manifest files instead of repo path"""
        python_deps = [dep for dep in mock_dependencies if dep.ecosystem == "PyPI"]
        js_deps = [dep for dep in mock_dependencies if dep.ecosystem == "npm"]
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = python_deps
                    mock_js_resolver.return_value = js_deps
                    mock_osv.return_value = []
                    
                    result = await scanner._scan_dependencies(
                        repo_path=None,
                        manifest_files=sample_manifest_files,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    # Verify resolvers were called with manifest files, not repo path
                    mock_py_resolver.assert_called_with(None, {"requirements.txt": sample_manifest_files["requirements.txt"]})
                    mock_js_resolver.assert_called_with(None, {"package.json": sample_manifest_files["package.json"]})
    
    @pytest.mark.asyncio
    async def test_scan_dependencies_report_generation(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test report generation in _scan_dependencies"""
        with patch.object(scanner.python_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_py_resolver:
            with patch.object(scanner.js_resolver, 'resolve_dependencies', new_callable=AsyncMock) as mock_js_resolver:
                with patch.object(scanner.osv_scanner, 'scan_dependencies', new_callable=AsyncMock) as mock_osv:
                    mock_py_resolver.return_value = mock_dependencies
                    mock_js_resolver.return_value = []
                    mock_osv.return_value = mock_vulnerabilities
                    
                    options = ScanOptions(include_dev_dependencies=True)
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=options,
                        progress_callback=None
                    )
                    
                    # Verify report structure
                    assert isinstance(result, Report)
                    assert result.status == JobStatus.COMPLETED
                    assert result.total_dependencies == len(mock_dependencies)
                    assert result.vulnerable_count == len(mock_vulnerabilities)
                    assert result.vulnerable_packages == mock_vulnerabilities
                    assert result.dependencies == mock_dependencies
                    assert result.suppressed_count == 0
                    
                    # Verify metadata
                    assert "ecosystems" in result.meta
                    assert "scan_options" in result.meta
                    assert result.meta["scan_options"] == options.model_dump()


class TestCoreScannerEdgeCases:
    """Test edge cases and error conditions for CoreScanner"""
    
    @pytest.fixture
    def scanner(self):
        return CoreScanner()
    
    @pytest.mark.asyncio
    async def test_empty_manifest_files(self, scanner):
        """Test scanning with empty manifest files dict"""
        with pytest.raises(ValueError):
            await scanner.scan_manifest_files({}, ScanOptions())
    
    @pytest.mark.asyncio
    async def test_malformed_manifest_files(self, scanner):
        """Test scanning with malformed manifest content"""
        malformed_files = {
            "package.json": "invalid json content",
            "requirements.txt": ""
        }
        
        # This should be handled by the resolvers, not cause scanner to crash
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js:
                mock_py.side_effect = Exception("Invalid requirements format")
                mock_js.side_effect = Exception("Invalid JSON")
                
                with pytest.raises(ValueError, match="No supported dependency files found"):
                    await scanner.scan_manifest_files(malformed_files, ScanOptions())
    
    @pytest.mark.asyncio
    async def test_very_large_dependency_list(self, scanner):
        """Test scanning with very large number of dependencies"""
        # Create large list of mock dependencies
        large_deps = []
        for i in range(1000):
            large_deps.append(Dep(
                name=f"package-{i}",
                version="1.0.0", 
                ecosystem="npm",
                path=[f"package-{i}"],
                is_direct=True
            ))
        
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js:
                with patch.object(scanner.osv_scanner, 'scan_dependencies') as mock_osv:
                    mock_py.return_value = []
                    mock_js.return_value = large_deps
                    mock_osv.return_value = []  # No vulnerabilities for simplicity
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    assert result.total_dependencies == 1000
                    assert result.vulnerable_count == 0
    
    @pytest.mark.asyncio
    async def test_all_severities_ignored(self, scanner, mock_dependencies, mock_vulnerabilities):
        """Test when all severities are ignored"""
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js:
                with patch.object(scanner.osv_scanner, 'scan_dependencies') as mock_osv:
                    mock_py.return_value = []
                    mock_js.return_value = mock_dependencies
                    mock_osv.return_value = mock_vulnerabilities
                    
                    # Ignore all severities
                    options = ScanOptions(ignore_severities=[
                        SeverityLevel.CRITICAL,
                        SeverityLevel.HIGH, 
                        SeverityLevel.MEDIUM,
                        SeverityLevel.LOW,
                        SeverityLevel.UNKNOWN
                    ])
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test/path",
                        manifest_files=None,
                        options=options,
                        progress_callback=None
                    )
                    
                    # All vulnerabilities should be filtered out
                    assert result.vulnerable_count == 0