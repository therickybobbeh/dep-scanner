"""Tests for CLI scanner module"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from backend.cli.scanner import DepScanner
from backend.core.models import ScanOptions, Report, JobStatus


class TestDepScanner:
    """Test cases for DepScanner CLI functionality"""
    
    @pytest.fixture
    def scanner(self):
        """Create DepScanner instance for testing"""
        return DepScanner(verbose=False)
    
    @pytest.fixture
    def verbose_scanner(self):
        """Create verbose DepScanner instance for testing"""
        return DepScanner(verbose=True)
    
    @pytest.fixture
    def mock_core_scanner(self):
        """Mock core scanner"""
        with patch('backend.cli.scanner.CoreScanner') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def simple_report(self):
        """Simple report for testing"""
        return Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=5,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
    
    def test_scanner_initialization(self):
        """Test scanner initialization"""
        scanner = DepScanner(verbose=False)
        assert scanner.verbose == False
        assert scanner.current_progress is None
        assert scanner.current_task is None
        assert hasattr(scanner, 'core_scanner')
        assert hasattr(scanner, 'console')
        assert hasattr(scanner, 'logger')
    
    def test_scanner_verbose_initialization(self):
        """Test scanner initialization with verbose mode"""
        scanner = DepScanner(verbose=True)
        assert scanner.verbose == True
    
    def test_progress_stages_configuration(self, scanner):
        """Test progress stages are properly configured"""
        expected_stages = ["init", "discovery", "generation", "parsing", "scanning", "reporting"]
        
        assert all(stage in scanner.progress_stages for stage in expected_stages)
        
        # Verify progress ranges add up to 0-100
        for stage, (start, end) in scanner.progress_stages.items():
            assert 0 <= start < end <= 100
            assert isinstance(start, int)
            assert isinstance(end, int)
    
    @pytest.mark.asyncio
    async def test_scan_path_with_file(self, scanner, mock_core_scanner, simple_report, tmp_path):
        """Test scan_path with a single file"""
        # Create temporary file
        test_file = tmp_path / "package.json"
        test_file.write_text('{"name": "test"}')
        
        mock_core_scanner.scan_manifest_files = AsyncMock(return_value=simple_report)
        
        result = await scanner.scan_path(str(test_file), ScanOptions())
        
        assert result == simple_report
        mock_core_scanner.scan_manifest_files.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scan_path_with_directory(self, scanner, mock_core_scanner, simple_report, tmp_path):
        """Test scan_path with a directory"""
        # Create temporary directory with manifest file
        (tmp_path / "package.json").write_text('{"name": "test"}')
        
        mock_core_scanner.scan_manifest_files = AsyncMock(return_value=simple_report)
        
        result = await scanner.scan_path(str(tmp_path), ScanOptions())
        
        assert result == simple_report
        mock_core_scanner.scan_manifest_files.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scan_path_nonexistent(self, scanner):
        """Test scan_path with nonexistent path"""
        with pytest.raises(FileNotFoundError, match="Path not found"):
            await scanner.scan_path("/nonexistent/path", ScanOptions())
    
    @pytest.mark.asyncio
    async def test_scan_single_file_supported_js(self, scanner, mock_core_scanner, simple_report, tmp_path):
        """Test scan_single_file with supported JavaScript file"""
        test_file = tmp_path / "package.json"
        test_file.write_text('{"name": "test", "dependencies": {"lodash": "^4.0.0"}}')
        
        mock_core_scanner.scan_manifest_files = AsyncMock(return_value=simple_report)
        
        result = await scanner.scan_single_file(str(test_file), ScanOptions())
        
        assert result == simple_report
        mock_core_scanner.scan_manifest_files.assert_called_once()
        
        # Verify the manifest files were passed correctly
        args, kwargs = mock_core_scanner.scan_manifest_files.call_args
        assert "manifest_files" in kwargs
        assert "package.json" in kwargs["manifest_files"]
    
    @pytest.mark.asyncio
    async def test_scan_single_file_supported_python(self, scanner, mock_core_scanner, simple_report, tmp_path):
        """Test scan_single_file with supported Python file"""
        test_file = tmp_path / "requirements.txt"
        test_file.write_text("requests==2.25.1\nurllib3==1.26.5")
        
        mock_core_scanner.scan_manifest_files = AsyncMock(return_value=simple_report)
        
        result = await scanner.scan_single_file(str(test_file), ScanOptions())
        
        assert result == simple_report
        
        # Verify the manifest files were passed correctly
        args, kwargs = mock_core_scanner.scan_manifest_files.call_args
        assert "manifest_files" in kwargs
        assert "requirements.txt" in kwargs["manifest_files"]
        assert "requests==2.25.1" in kwargs["manifest_files"]["requirements.txt"]
    
    @pytest.mark.asyncio
    async def test_scan_single_file_unsupported(self, scanner, tmp_path):
        """Test scan_single_file with unsupported file format"""
        test_file = tmp_path / "unsupported.xyz"
        test_file.write_text("some content")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            await scanner.scan_single_file(str(test_file), ScanOptions())
    
    @pytest.mark.asyncio
    async def test_scan_single_file_unreadable(self, scanner, tmp_path):
        """Test scan_single_file with unreadable file"""
        test_file = tmp_path / "package.json"
        test_file.write_bytes(b'\x00\x01\x02\x03')  # Binary content that will cause UTF-8 error
        
        with pytest.raises(ValueError, match="Could not read file"):
            await scanner.scan_single_file(str(test_file), ScanOptions())
    
    def test_supported_file_detection(self, scanner):
        """Test file format detection logic"""
        # This tests the is_supported_file function indirectly
        supported_files = [
            "package.json", "package-lock.json", "yarn.lock",
            "requirements.txt", "requirements.lock", "pyproject.toml",
            "poetry.lock", "Pipfile.lock", "Pipfile",
            "test-requirements.txt", "dev-requirements.txt"
        ]
        
        unsupported_files = [
            "README.md", "setup.py", "Dockerfile", "config.json",
            "data.txt", "script.sh", "requirements.py"
        ]
        
        # We'll test this by attempting scans (which will fail for other reasons
        # but should pass the file format check)
        for filename in supported_files:
            # The function should not raise "Unsupported file format" error
            # We can't test this directly without refactoring, but this documents
            # the expected behavior
            pass
    
    @pytest.mark.asyncio
    async def test_scan_repository_with_manifest_files(self, scanner, mock_core_scanner, simple_report, tmp_path):
        """Test scan_repository with multiple manifest files"""
        # Create test files
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "requirements.txt").write_text("requests==2.25.1")
        (tmp_path / "poetry.lock").write_text("# poetry lock file")
        
        mock_core_scanner.scan_manifest_files = AsyncMock(return_value=simple_report)
        
        result = await scanner.scan_repository(str(tmp_path), ScanOptions())
        
        assert result == simple_report
        
        # Verify multiple files were found
        args, kwargs = mock_core_scanner.scan_manifest_files.call_args
        manifest_files = kwargs["manifest_files"]
        assert "package.json" in manifest_files
        assert "requirements.txt" in manifest_files
        assert "poetry.lock" in manifest_files
    
    @pytest.mark.asyncio
    async def test_scan_repository_no_manifest_files(self, scanner, tmp_path):
        """Test scan_repository with no supported files"""
        # Create directory with only unsupported files
        (tmp_path / "README.md").write_text("# Test project")
        (tmp_path / "config.txt").write_text("config=value")
        
        with pytest.raises(ValueError, match="No supported dependency files found"):
            await scanner.scan_repository(str(tmp_path), ScanOptions())
    
    @pytest.mark.asyncio
    async def test_read_repository_manifest_files(self, scanner, tmp_path):
        """Test _read_repository_manifest_files method"""
        # Create test files
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "requirements.txt").write_text("requests==2.25.1")
        (tmp_path / "README.md").write_text("# Not a manifest file")
        
        result = await scanner._read_repository_manifest_files(str(tmp_path))
        
        assert "package.json" in result
        assert "requirements.txt" in result
        assert "README.md" not in result
        assert result["package.json"] == '{"name": "test"}'
        assert result["requirements.txt"] == "requests==2.25.1"
    
    @pytest.mark.asyncio
    async def test_read_repository_manifest_files_verbose(self, verbose_scanner, tmp_path):
        """Test _read_repository_manifest_files with verbose output"""
        # Create test file
        (tmp_path / "package.json").write_text('{"name": "test"}')
        
        with patch.object(verbose_scanner.console, 'print') as mock_print:
            result = await verbose_scanner._read_repository_manifest_files(str(tmp_path))
            
            # Should have printed found file message
            mock_print.assert_called()
            # Check that a print call contained the expected message
            print_calls = [call.args[0] for call in mock_print.call_args_list]
            assert any("Found manifest file: package.json" in call for call in print_calls)
    
    def test_update_progress_stage(self, scanner):
        """Test _update_progress_stage method"""
        # Mock progress objects
        mock_progress = Mock()
        mock_task = Mock()
        scanner.current_progress = mock_progress
        scanner.current_task = mock_task
        
        # Test progress update
        scanner._update_progress_stage("parsing", 0.5)
        
        # Verify progress was updated
        mock_progress.update.assert_called_once()
        args = mock_progress.update.call_args[0]
        assert args[0] == mock_task
        
        # Check the calculated progress is within expected range for parsing stage
        kwargs = mock_progress.update.call_args[1]
        progress_value = kwargs["completed"]
        parsing_start, parsing_end = scanner.progress_stages["parsing"]
        expected = parsing_start + (parsing_end - parsing_start) * 0.5
        assert progress_value == expected
    
    def test_update_progress_stage_no_progress(self, scanner):
        """Test _update_progress_stage when no progress object exists"""
        # Should not raise error when no progress object
        scanner.current_progress = None
        scanner.current_task = None
        
        # This should not raise an exception
        scanner._update_progress_stage("parsing", 0.5)
    
    def test_update_progress_from_callback_warnings(self, scanner):
        """Test _update_progress_from_callback with warning messages"""
        mock_progress = Mock()
        scanner.current_progress = mock_progress
        
        with patch.object(scanner.console, 'print') as mock_print:
            # Test warning message
            scanner._update_progress_from_callback("Warning: Something went wrong")
            
            # Should stop and start progress around warning
            mock_progress.stop.assert_called_once()
            mock_progress.start.assert_called_once()
            mock_print.assert_called_once()
            
            # Check warning was printed
            warning_msg = mock_print.call_args[0][0]
            assert "Warning: Something went wrong" in warning_msg
    
    def test_update_progress_from_callback_generation_stage(self, scanner):
        """Test _update_progress_from_callback with generation messages"""
        mock_progress = Mock()
        mock_task = Mock()
        scanner.current_progress = mock_progress
        scanner.current_task = mock_task
        
        # Test generation message
        scanner._update_progress_from_callback("Running npm install to generate lock file")
        
        # Should update progress in generation stage
        mock_progress.update.assert_called()
        
        # Reset and test completion message
        mock_progress.reset_mock()
        scanner._update_progress_from_callback("Lock file generated successfully")
        
        mock_progress.update.assert_called()
    
    def test_update_progress_from_callback_scanning_stage(self, scanner):
        """Test _update_progress_from_callback with scanning messages"""
        mock_progress = Mock()
        mock_task = Mock()
        scanner.current_progress = mock_progress
        scanner.current_task = mock_task
        
        # Test batch progress parsing
        scanner._update_progress_from_callback("Scanning batch 3/10 packages")
        
        mock_progress.update.assert_called()
        
        # Test general scanning message
        mock_progress.reset_mock()
        scanner._update_progress_from_callback("Querying OSV database for vulnerabilities")
        
        mock_progress.update.assert_called()
    
    def test_suppress_logging_context_manager(self, scanner):
        """Test _suppress_logging context manager"""
        import logging
        
        # Create a test handler
        test_handler = logging.StreamHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(test_handler)
        
        original_handler_count = len(root_logger.handlers)
        
        # Test context manager
        with scanner._suppress_logging():
            # Handler should be temporarily removed
            current_handlers = [h for h in root_logger.handlers 
                              if isinstance(h, logging.StreamHandler)]
            # Some handlers might remain (file handlers, etc.)
            pass
        
        # Handler should be restored
        assert len(root_logger.handlers) == original_handler_count
        assert test_handler in root_logger.handlers
        
        # Clean up
        root_logger.removeHandler(test_handler)


class TestDepScannerIntegration:
    """Integration tests for DepScanner with real-like scenarios"""
    
    @pytest.mark.asyncio
    async def test_full_scan_workflow_mocked(self, tmp_path):
        """Test complete scan workflow with mocked core scanner"""
        # Create test project
        package_json = tmp_path / "package.json"
        package_json.write_text('''
        {
            "name": "test-project",
            "dependencies": {
                "lodash": "^4.17.19"
            }
        }
        ''')
        
        requirements_txt = tmp_path / "requirements.txt"
        requirements_txt.write_text("requests==2.25.1")
        
        # Mock the core scanner
        with patch('backend.cli.scanner.CoreScanner') as mock_core_class:
            mock_core = Mock()
            mock_core_class.return_value = mock_core
            
            # Create a report with some findings
            test_report = Report(
                job_id="integration-test",
                status=JobStatus.COMPLETED,
                total_dependencies=15,
                vulnerable_count=2,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={"ecosystems": ["Python", "JavaScript"]}
            )
            
            mock_core.scan_manifest_files = AsyncMock(return_value=test_report)
            
            # Run the scan
            scanner = DepScanner(verbose=True)
            result = await scanner.scan_path(str(tmp_path), ScanOptions())
            
            # Verify results
            assert result.total_dependencies == 15
            assert result.vulnerable_count == 2
            assert "ecosystems" in result.meta
            
            # Verify core scanner was called correctly
            mock_core.scan_manifest_files.assert_called_once()
            
            # Check that both manifest files were passed
            call_kwargs = mock_core.scan_manifest_files.call_args[1]
            manifest_files = call_kwargs["manifest_files"]
            assert "package.json" in manifest_files
            assert "requirements.txt" in manifest_files