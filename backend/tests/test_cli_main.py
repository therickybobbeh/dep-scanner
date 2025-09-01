"""Tests for CLI main module"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from typer.testing import CliRunner
from io import StringIO
import sys

from backend.cli.main import app, scan, version
from backend.core.models import ScanOptions, SeverityLevel, Report, JobStatus


class TestCLIMain:
    """Test cases for CLI main functionality"""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner"""
        return CliRunner()
    
    @pytest.fixture
    def mock_report(self, sample_vulnerability):
        """Mock report for testing"""
        return Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=10,
            vulnerable_count=1,
            vulnerable_packages=[sample_vulnerability],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
    
    def test_version_command(self, runner):
        """Test version command output"""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "DepScan" in result.stdout
        assert "Dependency Vulnerability Scanner" in result.stdout
        assert "OSV.dev" in result.stdout
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_success_no_vulnerabilities(self, mock_scanner_class, runner):
        """Test successful scan with no vulnerabilities"""
        # Setup mock
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=5,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={}
        ))
        
        result = runner.invoke(app, ["scan", "."])
        
        assert result.exit_code == 0
        mock_scanner.scan_path.assert_called_once()
        args, kwargs = mock_scanner.scan_path.call_args
        assert args[0] == "."
        assert isinstance(args[1], ScanOptions)
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_with_vulnerabilities(self, mock_scanner_class, runner, mock_report):
        """Test scan command with vulnerabilities found"""
        # Setup mock
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=mock_report)
        
        result = runner.invoke(app, ["scan", ".", "--verbose"])
        
        # Should exit with code 1 when vulnerabilities found
        assert result.exit_code == 1
        mock_scanner.scan_path.assert_called_once()
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_with_options(self, mock_scanner_class, runner):
        """Test scan command with various options"""
        # Setup mock
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=3,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={}
        ))
        
        result = runner.invoke(app, [
            "scan", 
            "test_file.txt",
            "--no-include-dev",
            "--ignore-severity", "LOW",
            "--verbose"
        ])
        
        assert result.exit_code == 0
        mock_scanner.scan_path.assert_called_once()
        
        # Verify scan options
        args, kwargs = mock_scanner.scan_path.call_args
        scan_options = args[1]
        assert scan_options.include_dev_dependencies == False
        assert SeverityLevel.LOW in scan_options.ignore_severities
    
    def test_scan_command_invalid_severity(self, runner):
        """Test scan command with invalid severity level"""
        result = runner.invoke(app, [
            "scan", 
            ".",
            "--ignore-severity", "INVALID"
        ])
        
        assert result.exit_code == 1
        assert "Invalid severity level" in result.stdout
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_file_not_found(self, mock_scanner_class, runner):
        """Test scan command with file not found"""
        # Setup mock to raise FileNotFoundError
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(side_effect=FileNotFoundError("File not found"))
        
        result = runner.invoke(app, ["scan", "nonexistent.txt"])
        
        assert result.exit_code == 1
        assert "Error:" in result.stdout
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_value_error(self, mock_scanner_class, runner):
        """Test scan command with value error"""
        # Setup mock to raise ValueError
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(side_effect=ValueError("Invalid file format"))
        
        result = runner.invoke(app, ["scan", "invalid.txt"])
        
        assert result.exit_code == 1
        assert "Error:" in result.stdout
    
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_unexpected_error(self, mock_scanner_class, runner):
        """Test scan command with unexpected error"""
        # Setup mock to raise unexpected error
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(side_effect=RuntimeError("Unexpected error"))
        
        result = runner.invoke(app, ["scan", "."])
        
        assert result.exit_code == 1
        assert "Unexpected error:" in result.stdout
    
    @patch('backend.cli.main.export_json_report')
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_json_export(self, mock_scanner_class, mock_export, runner, mock_report):
        """Test scan command with JSON export"""
        # Setup mocks
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=mock_report)
        
        result = runner.invoke(app, [
            "scan", 
            ".",
            "--json", "output.json"
        ])
        
        assert result.exit_code == 1  # Exit code 1 because vulnerabilities found
        mock_export.assert_called_once_with(mock_report, "output.json")
        assert "JSON report saved" in result.stdout
    
    @patch('backend.cli.main.generate_modern_html_report')
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_html_output(self, mock_scanner_class, mock_html, runner, mock_report):
        """Test scan command with HTML output"""
        # Setup mocks
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=mock_report)
        mock_html.return_value = Path("/tmp/report.html")
        
        result = runner.invoke(app, [
            "scan", 
            ".",
            "--output", "report.html"
        ])
        
        assert result.exit_code == 1  # Exit code 1 because vulnerabilities found
        mock_html.assert_called_once_with(mock_report, "report.html")
        assert "HTML report generated" in result.stdout
    
    @patch('backend.cli.main.webbrowser.open')
    @patch('backend.cli.main.generate_modern_html_report')
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_open_report(self, mock_scanner_class, mock_html, mock_browser, runner, mock_report):
        """Test scan command with --open flag"""
        # Setup mocks
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=mock_report)
        mock_html.return_value = Path("/tmp/report.html")
        
        result = runner.invoke(app, [
            "scan", 
            ".",
            "--open"
        ])
        
        assert result.exit_code == 1  # Exit code 1 because vulnerabilities found
        mock_html.assert_called_once()
        mock_browser.assert_called_once()
        assert "HTML report generated" in result.stdout
    
    @patch('backend.cli.main.webbrowser.open')
    @patch('backend.cli.main.generate_modern_html_report')
    @patch('backend.cli.main.DepScanner')
    def test_scan_command_open_browser_error(self, mock_scanner_class, mock_html, mock_browser, runner, mock_report):
        """Test scan command when browser fails to open"""
        # Setup mocks
        mock_scanner = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_scanner.scan_path = AsyncMock(return_value=mock_report)
        mock_html.return_value = Path("/tmp/report.html")
        mock_browser.side_effect = Exception("Browser error")
        
        result = runner.invoke(app, [
            "scan", 
            ".",
            "--open"
        ])
        
        assert result.exit_code == 1  # Exit code 1 because vulnerabilities found
        assert "Warning: Could not open browser" in result.stdout


class TestScanOptionsValidation:
    """Test scan options validation and parsing"""
    
    def test_severity_level_parsing_valid(self):
        """Test valid severity level parsing"""
        valid_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "critical", "high"]
        
        for level in valid_levels:
            try:
                severity = SeverityLevel(level.upper())
                assert severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, 
                                  SeverityLevel.MEDIUM, SeverityLevel.LOW]
            except ValueError:
                pytest.fail(f"Should accept {level} as valid severity")
    
    def test_severity_level_parsing_invalid(self):
        """Test invalid severity level parsing"""
        invalid_levels = ["INVALID", "NONE", "EXTREME", ""]
        
        for level in invalid_levels:
            with pytest.raises(ValueError):
                SeverityLevel(level)
    
    def test_scan_options_creation(self):
        """Test ScanOptions model creation"""
        options = ScanOptions(
            include_dev_dependencies=False,
            ignore_severities=[SeverityLevel.LOW, SeverityLevel.MEDIUM]
        )
        
        assert options.include_dev_dependencies == False
        assert len(options.ignore_severities) == 2
        assert SeverityLevel.LOW in options.ignore_severities
        assert SeverityLevel.MEDIUM in options.ignore_severities


class TestCLIFormatter:
    """Test CLI output formatting (integration with formatter)"""
    
    @patch('backend.cli.main.CLIFormatter')
    @patch('backend.cli.main.DepScanner')
    def test_formatter_integration(self, mock_scanner_class, mock_formatter_class, sample_report):
        """Test that CLI properly uses formatter"""
        from typer.testing import CliRunner
        
        # Setup mocks
        runner = CliRunner()
        mock_scanner = Mock()
        mock_formatter = Mock()
        mock_scanner_class.return_value = mock_scanner
        mock_formatter_class.return_value = mock_formatter
        mock_scanner.scan_path = AsyncMock(return_value=sample_report)
        
        result = runner.invoke(app, ["scan", "."])
        
        # Verify formatter methods were called
        mock_formatter.print_scan_summary.assert_called_once_with(sample_report)
        mock_formatter.create_vulnerability_table.assert_called_once_with(sample_report)
        mock_formatter.print_remediation_suggestions.assert_called_once_with(sample_report)