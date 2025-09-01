"""Edge cases and error handling tests"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json
import tempfile
import os

from backend.cli.scanner import DepScanner
from backend.core.core_scanner import CoreScanner
from backend.core.models import ScanOptions, SeverityLevel, Report, JobStatus


class TestFileHandlingEdgeCases:
    """Test edge cases in file handling"""
    
    @pytest.mark.asyncio
    async def test_scanner_with_permission_denied_file(self, tmp_path):
        """Test scanning file with no read permissions"""
        scanner = DepScanner()
        
        # Create file and remove read permissions
        test_file = tmp_path / "package.json"
        test_file.write_text('{"name": "test"}')
        
        # On systems where we can actually remove permissions
        try:
            test_file.chmod(0o000)  # No permissions
            
            with pytest.raises(ValueError, match="Could not read file"):
                await scanner.scan_single_file(str(test_file), ScanOptions())
        finally:
            # Restore permissions for cleanup
            try:
                test_file.chmod(0o644)
            except:
                pass
    
    @pytest.mark.asyncio
    async def test_scanner_with_very_large_file(self, tmp_path):
        """Test scanning very large dependency file"""
        scanner = DepScanner()
        
        # Create a large package.json
        large_deps = {}
        for i in range(1000):
            large_deps[f"package-{i}"] = "^1.0.0"
        
        large_package_json = {
            "name": "large-project",
            "dependencies": large_deps
        }
        
        test_file = tmp_path / "package.json"
        test_file.write_text(json.dumps(large_package_json, indent=2))
        
        # Mock the core scanner to avoid actual network calls
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            mock_instance.scan_manifest_files = AsyncMock(return_value=Report(
                job_id="large-test",
                status=JobStatus.COMPLETED,
                total_dependencies=1000,
                vulnerable_count=0,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={}
            ))
            
            result = await scanner.scan_single_file(str(test_file), ScanOptions())
            
            # Should handle large files without issues
            assert result.total_dependencies == 1000
    
    @pytest.mark.asyncio
    async def test_scanner_with_binary_file(self, tmp_path):
        """Test scanning binary file with dependency extension"""
        scanner = DepScanner()
        
        # Create binary file with .txt extension
        test_file = tmp_path / "requirements.txt"
        test_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe\xfd')
        
        with pytest.raises(ValueError, match="Could not read file"):
            await scanner.scan_single_file(str(test_file), ScanOptions())
    
    @pytest.mark.asyncio
    async def test_scanner_with_empty_file(self, tmp_path):
        """Test scanning empty dependency file"""
        scanner = DepScanner()
        
        test_file = tmp_path / "requirements.txt"
        test_file.write_text("")  # Empty file
        
        # Mock core scanner
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            mock_instance.scan_manifest_files = AsyncMock(side_effect=ValueError("No dependencies found"))
            
            with pytest.raises(ValueError):
                await scanner.scan_single_file(str(test_file), ScanOptions())
    
    @pytest.mark.asyncio
    async def test_scanner_with_symlink(self, tmp_path):
        """Test scanning symlinked files"""
        scanner = DepScanner()
        
        # Create original file
        original_file = tmp_path / "original_package.json"
        original_file.write_text('{"name": "test", "dependencies": {"lodash": "^4.0.0"}}')
        
        # Create symlink
        symlink_file = tmp_path / "package.json"
        try:
            symlink_file.symlink_to(original_file)
            
            # Mock core scanner
            with patch('backend.cli.scanner.CoreScanner') as mock_core:
                mock_instance = Mock()
                mock_core.return_value = mock_instance
                mock_instance.scan_manifest_files = AsyncMock(return_value=Report(
                    job_id="symlink-test",
                    status=JobStatus.COMPLETED,
                    total_dependencies=1,
                    vulnerable_count=0,
                    vulnerable_packages=[],
                    dependencies=[],
                    suppressed_count=0,
                    meta={}
                ))
                
                result = await scanner.scan_single_file(str(symlink_file), ScanOptions())
                
                # Should follow symlinks successfully
                assert result.total_dependencies == 1
                
        except OSError:
            # Skip if symlinks not supported on this system
            pytest.skip("Symlinks not supported on this system")
    
    @pytest.mark.asyncio
    async def test_scanner_with_unicode_content(self, tmp_path):
        """Test scanning files with unicode content"""
        scanner = DepScanner()
        
        # Create file with unicode characters
        test_file = tmp_path / "requirements.txt"
        test_file.write_text("# 测试依赖项\nrequests==2.25.1\n# café dependencies", encoding='utf-8')
        
        # Mock core scanner
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            mock_instance.scan_manifest_files = AsyncMock(return_value=Report(
                job_id="unicode-test",
                status=JobStatus.COMPLETED,
                total_dependencies=1,
                vulnerable_count=0,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={}
            ))
            
            result = await scanner.scan_single_file(str(test_file), ScanOptions())
            
            # Should handle unicode content
            assert result.total_dependencies == 1


class TestNetworkAndAPIEdgeCases:
    """Test edge cases related to network and API interactions"""
    
    @pytest.mark.asyncio
    async def test_osv_scanner_timeout(self):
        """Test OSV scanner with network timeout"""
        from backend.core.scanner.osv import OSVScanner
        from backend.core.models import Dep
        
        scanner = OSVScanner()
        deps = [Dep(name="requests", version="2.25.1", ecosystem="PyPI", path=["requests"], is_direct=True)]
        
        # Mock httpx client to simulate timeout
        with patch('backend.core.scanner.osv.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=Exception("Timeout"))
            
            # Should handle timeout gracefully
            result = await scanner.scan_dependencies(deps)
            
            # Should return empty list or handle error gracefully
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_osv_scanner_invalid_response(self):
        """Test OSV scanner with invalid API response"""
        from backend.core.scanner.osv import OSVScanner
        from backend.core.models import Dep
        
        scanner = OSVScanner()
        deps = [Dep(name="requests", version="2.25.1", ecosystem="PyPI", path=["requests"], is_direct=True)]
        
        # Mock httpx client to return invalid response
        with patch('backend.core.scanner.osv.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"invalid": "response"}  # Not expected format
            mock_client.post = AsyncMock(return_value=mock_response)
            
            # Should handle invalid response gracefully
            result = await scanner.scan_dependencies(deps)
            assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_osv_scanner_rate_limiting(self):
        """Test OSV scanner with rate limiting response"""
        from backend.core.scanner.osv import OSVScanner
        from backend.core.models import Dep
        
        scanner = OSVScanner()
        deps = [Dep(name="requests", version="2.25.1", ecosystem="PyPI", path=["requests"], is_direct=True)]
        
        # Mock httpx client to return rate limit response
        with patch('backend.core.scanner.osv.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = Mock()
            mock_response.status_code = 429  # Rate limited
            mock_response.text = "Rate limited"
            mock_client.post = AsyncMock(return_value=mock_response)
            
            # Should handle rate limiting gracefully
            result = await scanner.scan_dependencies(deps)
            assert isinstance(result, list)


class TestMemoryAndPerformanceEdgeCases:
    """Test memory and performance edge cases"""
    
    @pytest.mark.asyncio
    async def test_scanner_with_deeply_nested_dependencies(self):
        """Test scanner with very deeply nested dependency paths"""
        from backend.core.models import Dep
        
        # Create dependency with very deep nesting path
        deep_path = [f"level-{i}" for i in range(100)]  # 100 levels deep
        
        deep_dep = Dep(
            name="deeply-nested-package",
            version="1.0.0",
            ecosystem="npm",
            path=deep_path,
            is_direct=False
        )
        
        scanner = CoreScanner()
        
        # Mock resolvers to return deep dependency
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js:
                with patch.object(scanner.osv_scanner, 'scan_dependencies') as mock_osv:
                    mock_py.return_value = []
                    mock_js.return_value = [deep_dep]
                    mock_osv.return_value = []
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    # Should handle deep nesting without issues
                    assert result.total_dependencies == 1
                    assert len(result.dependencies[0].path) == 100
    
    @pytest.mark.asyncio
    async def test_scanner_with_circular_dependencies(self):
        """Test scanner with circular dependency references"""
        from backend.core.models import Dep
        
        # Create circular dependency scenario
        deps = [
            Dep(name="package-a", version="1.0.0", ecosystem="npm", path=["package-a"], is_direct=True),
            Dep(name="package-b", version="1.0.0", ecosystem="npm", path=["package-a", "package-b"], is_direct=False),
            Dep(name="package-c", version="1.0.0", ecosystem="npm", path=["package-a", "package-b", "package-c"], is_direct=False),
            # This would be circular: package-c -> package-a
            Dep(name="package-a", version="1.0.0", ecosystem="npm", path=["package-a", "package-b", "package-c", "package-a"], is_direct=False),
        ]
        
        scanner = CoreScanner()
        
        # Mock resolvers to return circular dependencies
        with patch.object(scanner.python_resolver, 'resolve_dependencies') as mock_py:
            with patch.object(scanner.js_resolver, 'resolve_dependencies') as mock_js:
                with patch.object(scanner.osv_scanner, 'scan_dependencies') as mock_osv:
                    mock_py.return_value = []
                    mock_js.return_value = deps
                    mock_osv.return_value = []
                    
                    result = await scanner._scan_dependencies(
                        repo_path="/test",
                        manifest_files=None,
                        options=ScanOptions(),
                        progress_callback=None
                    )
                    
                    # Should handle circular dependencies
                    assert result.total_dependencies == len(deps)
    
    def test_progress_callback_with_none_handler(self):
        """Test progress callback handling with None values"""
        scanner = DepScanner()
        
        # Should not crash when progress objects are None
        scanner.current_progress = None
        scanner.current_task = None
        
        # These should not raise exceptions
        scanner._update_progress_stage("parsing", 0.5)
        scanner._update_progress_from_callback("Test message")
        scanner._update_progress_from_callback("Warning: Test warning")
    
    def test_progress_callback_with_invalid_stage(self):
        """Test progress callback with invalid stage name"""
        scanner = DepScanner()
        
        # Mock progress objects
        scanner.current_progress = Mock()
        scanner.current_task = Mock()
        
        # Should handle invalid stage gracefully
        with pytest.raises(KeyError):
            scanner._update_progress_stage("invalid_stage", 0.5)


class TestErrorRecoveryAndRobustness:
    """Test error recovery and system robustness"""
    
    @pytest.mark.asyncio
    async def test_scanner_partial_failure_recovery(self, tmp_path):
        """Test scanner recovery from partial failures"""
        scanner = DepScanner()
        
        # Create directory with mixed valid and invalid files
        (tmp_path / "package.json").write_text('{"name": "valid"}')
        (tmp_path / "requirements.txt").write_text("valid-package==1.0.0")
        (tmp_path / "invalid.json").write_text("invalid json{")
        
        # Mock core scanner to succeed despite some invalid files
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            mock_instance.scan_manifest_files = AsyncMock(return_value=Report(
                job_id="partial-test",
                status=JobStatus.COMPLETED,
                total_dependencies=2,
                vulnerable_count=0,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={}
            ))
            
            result = await scanner.scan_repository(str(tmp_path), ScanOptions())
            
            # Should succeed with valid files
            assert result.total_dependencies == 2
    
    @pytest.mark.asyncio
    async def test_scanner_with_concurrent_file_modification(self, tmp_path):
        """Test scanner behavior when files are modified during scan"""
        scanner = DepScanner()
        
        test_file = tmp_path / "package.json"
        test_file.write_text('{"name": "test", "dependencies": {"lodash": "^4.0.0"}}')
        
        # Mock core scanner to simulate concurrent modification
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            
            async def modify_file_during_scan(*args, **kwargs):
                # Simulate file modification during scan
                test_file.write_text('{"name": "modified", "dependencies": {}}')
                return Report(
                    job_id="concurrent-test",
                    status=JobStatus.COMPLETED,
                    total_dependencies=1,
                    vulnerable_count=0,
                    vulnerable_packages=[],
                    dependencies=[],
                    suppressed_count=0,
                    meta={}
                )
            
            mock_instance.scan_manifest_files = AsyncMock(side_effect=modify_file_during_scan)
            mock_core.return_value = mock_instance
            
            # Should complete scan with original content
            result = await scanner.scan_single_file(str(test_file), ScanOptions())
            assert result.total_dependencies == 1
    
    @pytest.mark.asyncio
    async def test_scanner_cleanup_on_exception(self, tmp_path):
        """Test scanner cleanup when exceptions occur"""
        scanner = DepScanner()
        
        test_file = tmp_path / "package.json" 
        test_file.write_text('{"name": "test"}')
        
        # Mock core scanner to raise exception
        with patch('backend.cli.scanner.CoreScanner') as mock_core:
            mock_instance = Mock()
            mock_core.return_value = mock_instance
            mock_instance.scan_manifest_files = AsyncMock(side_effect=RuntimeError("Simulated error"))
            
            with pytest.raises(RuntimeError):
                await scanner.scan_single_file(str(test_file), ScanOptions())
            
            # Verify scanner state is clean after exception
            assert scanner.current_progress is None
            assert scanner.current_task is None
    
    def test_model_validation_edge_cases(self):
        """Test model validation with edge case inputs"""
        from backend.core.models import Dep, Vuln, ScanOptions
        
        # Test with edge case string inputs
        dep = Dep(
            name="",  # Empty name
            version="",  # Empty version
            ecosystem="PyPI",
            path=[]
        )
        assert dep.name == ""
        assert dep.version == ""
        
        # Test with very long strings
        long_name = "a" * 10000  # Very long package name
        dep_long = Dep(
            name=long_name,
            version="1.0.0",
            ecosystem="npm",
            path=[long_name]
        )
        assert len(dep_long.name) == 10000
    
    @pytest.mark.asyncio
    async def test_scanner_with_system_resource_constraints(self):
        """Test scanner behavior under system resource constraints"""
        scanner = DepScanner()
        
        # Create many temporary files to simulate resource usage
        temp_files = []
        try:
            # Create many temporary files
            for i in range(100):
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
                temp_file.write(b'{"name": "test"}')
                temp_file.close()
                temp_files.append(temp_file.name)
            
            # Mock core scanner
            with patch('backend.cli.scanner.CoreScanner') as mock_core:
                mock_instance = Mock()
                mock_core.return_value = mock_instance
                mock_instance.scan_manifest_files = AsyncMock(return_value=Report(
                    job_id="resource-test",
                    status=JobStatus.COMPLETED,
                    total_dependencies=1,
                    vulnerable_count=0,
                    vulnerable_packages=[],
                    dependencies=[],
                    suppressed_count=0,
                    meta={}
                ))
                
                # Should handle resource constraints gracefully
                result = await scanner.scan_single_file(temp_files[0], ScanOptions())
                assert result.total_dependencies == 1
                
        finally:
            # Cleanup temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass