"""Tests for CLI formatter functionality"""
import pytest
from unittest.mock import Mock, patch
from io import StringIO

from backend.cli.formatter import CLIFormatter
from backend.core.models import Report, Vuln, Dep, SeverityLevel, JobStatus


class TestCLIFormatter:
    """Test cases for CLIFormatter"""
    
    @pytest.fixture
    def formatter(self):
        """Create CLIFormatter instance"""
        return CLIFormatter()
    
    @pytest.fixture
    def sample_report_with_vulns(self, sample_vulnerability):
        """Sample report with vulnerabilities"""
        return Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=10,
            vulnerable_count=1,
            vulnerable_packages=[sample_vulnerability],
            dependencies=[],
            suppressed_count=0,
            meta={"ecosystems": ["Python"], "scan_options": {}}
        )
    
    @pytest.fixture
    def sample_report_clean(self):
        """Sample report with no vulnerabilities"""
        return Report(
            job_id="test-clean",
            status=JobStatus.COMPLETED,
            total_dependencies=5,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={"ecosystems": ["JavaScript"], "scan_options": {}}
        )
    
    def test_formatter_initialization(self, formatter):
        """Test formatter initializes correctly"""
        assert hasattr(formatter, 'console')
        assert formatter.console is not None
    
    def test_print_scan_summary_with_vulnerabilities(self, formatter, sample_report_with_vulns):
        """Test printing scan summary with vulnerabilities"""
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_scan_summary(sample_report_with_vulns)
            
            # Should have made multiple print calls
            assert mock_print.call_count >= 3
            
            # Check that key information was printed
            printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
            assert "10" in printed_text  # total dependencies
            assert "1" in printed_text   # vulnerable count
            assert "Python" in printed_text  # ecosystem
    
    def test_print_scan_summary_clean(self, formatter, sample_report_clean):
        """Test printing scan summary with no vulnerabilities"""
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_scan_summary(sample_report_clean)
            
            # Should have made print calls
            assert mock_print.call_count >= 2
            
            # Check for clean scan indicators
            printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
            assert "5" in printed_text  # total dependencies
            assert "0" in printed_text  # vulnerable count or clean indicator
    
    def test_create_vulnerability_table_with_data(self, formatter, sample_report_with_vulns):
        """Test creating vulnerability table with data"""
        table = formatter.create_vulnerability_table(sample_report_with_vulns)
        
        # Should return a Rich table object
        assert hasattr(table, 'columns')  # Rich table has columns
        assert table.row_count > 0  # Should have at least one row
    
    def test_create_vulnerability_table_empty(self, formatter, sample_report_clean):
        """Test creating vulnerability table with no vulnerabilities"""
        table = formatter.create_vulnerability_table(sample_report_clean)
        
        # Should still return a table, possibly empty or with header only
        assert hasattr(table, 'columns')
    
    def test_print_remediation_suggestions_with_vulns(self, formatter, sample_report_with_vulns):
        """Test printing remediation suggestions with vulnerabilities"""
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_remediation_suggestions(sample_report_with_vulns)
            
            # Should have made print calls for suggestions
            assert mock_print.call_count >= 1
            
            # Check for remediation-related content
            printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
            # Should contain some remediation guidance
            assert len(printed_text) > 0
    
    def test_print_remediation_suggestions_clean(self, formatter, sample_report_clean):
        """Test printing remediation suggestions with clean report"""
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_remediation_suggestions(sample_report_clean)
            
            # Might print something or nothing for clean reports
            # This documents the current behavior
            pass
    
    def test_vulnerability_table_columns(self, formatter):
        """Test that vulnerability table has expected columns"""
        # Create a report with multiple severity levels
        vulns = [
            Vuln(
                package="critical-package",
                version="1.0.0",
                ecosystem="PyPI",
                vulnerability_id="CRIT-001",
                severity=SeverityLevel.CRITICAL,
                summary="Critical vulnerability",
                fixed_range=None
            ),
            Vuln(
                package="high-package",
                version="2.0.0",
                ecosystem="npm",
                vulnerability_id="HIGH-001",
                severity=SeverityLevel.HIGH,
                summary="High vulnerability",
                fixed_range=None
            ),
            Vuln(
                package="medium-package",
                version="3.0.0",
                ecosystem="PyPI",
                vulnerability_id="MED-001",
                severity=SeverityLevel.MEDIUM,
                summary="Medium vulnerability",
                fixed_range=None
            )
        ]
        
        report = Report(
            job_id="multi-vuln",
            status=JobStatus.COMPLETED,
            total_dependencies=15,
            vulnerable_count=3,
            vulnerable_packages=vulns,
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
        
        table = formatter.create_vulnerability_table(report)
        
        # Should have expected columns (exact names depend on implementation)
        assert len(table.columns) >= 3  # At minimum: package, severity, summary
        assert table.row_count == 3  # One row per vulnerability
    
    def test_severity_formatting(self, formatter):
        """Test that different severity levels are formatted correctly"""
        severities = [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]
        
        for severity in severities:
            vuln = Vuln(
                package="test-package",
                version="1.0.0",
                ecosystem="PyPI",
                vulnerability_id=f"{severity.value}-001",
                severity=severity,
                summary=f"{severity.value} vulnerability",
                fixed_range=None
            )
            
            report = Report(
                job_id=f"test-{severity.value.lower()}",
                status=JobStatus.COMPLETED,
                total_dependencies=1,
                vulnerable_count=1,
                vulnerable_packages=[vuln],
                dependencies=[],
                suppressed_count=0,
                meta={}
            )
            
            table = formatter.create_vulnerability_table(report)
            
            # Should handle all severity levels without error
            assert table.row_count == 1
    
    def test_long_package_names(self, formatter):
        """Test formatting with very long package names"""
        long_name = "very-long-package-name-that-might-cause-formatting-issues"
        
        vuln = Vuln(
            package=long_name,
            version="1.0.0",
            ecosystem="npm",
            vulnerability_id="LONG-001",
            severity=SeverityLevel.HIGH,
            summary="Vulnerability in package with very long name that might cause issues",
            fixed_range=None
        )
        
        report = Report(
            job_id="long-name-test",
            status=JobStatus.COMPLETED,
            total_dependencies=1,
            vulnerable_count=1,
            vulnerable_packages=[vuln],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
        
        # Should handle long names without crashing
        table = formatter.create_vulnerability_table(report)
        assert table.row_count == 1
        
        with patch.object(formatter.console, 'print'):
            formatter.print_scan_summary(report)
            # Should not raise exception
    
    def test_unicode_in_vulnerability_data(self, formatter):
        """Test formatting with unicode characters in vulnerability data"""
        vuln = Vuln(
            package="测试包",  # Unicode package name
            version="1.0.0",
            ecosystem="PyPI",
            vulnerability_id="UNICODE-001",
            severity=SeverityLevel.HIGH,
            summary="Vulnerability with unicode: 安全问题 🚨",
            fixed_range=None
        )
        
        report = Report(
            job_id="unicode-test",
            status=JobStatus.COMPLETED,
            total_dependencies=1,
            vulnerable_count=1,
            vulnerable_packages=[vuln],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
        
        # Should handle unicode without crashing
        table = formatter.create_vulnerability_table(report)
        assert table.row_count == 1
        
        with patch.object(formatter.console, 'print'):
            formatter.print_scan_summary(report)
            # Should not raise exception
    
    def test_missing_vulnerability_fields(self, formatter):
        """Test formatting with missing optional vulnerability fields"""
        vuln = Vuln(
            package="minimal-package",
            version="1.0.0",
            ecosystem="PyPI",
            vulnerability_id="MINIMAL-001",
            summary="Minimal vulnerability data",
            fixed_range=None
            # Missing optional fields: severity, cvss_score, etc.
        )
        
        report = Report(
            job_id="minimal-test", 
            status=JobStatus.COMPLETED,
            total_dependencies=1,
            vulnerable_count=1,
            vulnerable_packages=[vuln],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
        
        # Should handle missing optional fields gracefully
        table = formatter.create_vulnerability_table(report)
        assert table.row_count == 1
        
        with patch.object(formatter.console, 'print'):
            formatter.print_scan_summary(report)
            formatter.print_remediation_suggestions(report)
            # Should not raise exception
    
    def test_report_with_suppressed_vulnerabilities(self, formatter):
        """Test formatting report with suppressed vulnerabilities"""
        report = Report(
            job_id="suppressed-test",
            status=JobStatus.COMPLETED,
            total_dependencies=10,
            vulnerable_count=2,
            vulnerable_packages=[],  # Vulnerabilities were suppressed
            dependencies=[],
            suppressed_count=3,  # 3 vulnerabilities were suppressed
            meta={"scan_options": {"ignore_severities": ["LOW", "MEDIUM"]}}
        )
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_scan_summary(report)
            
            # Should mention suppressed vulnerabilities
            printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
            # Implementation-dependent: might mention suppressed count
    
    def test_multi_ecosystem_report(self, formatter):
        """Test formatting report with multiple ecosystems"""
        report = Report(
            job_id="multi-ecosystem-test",
            status=JobStatus.COMPLETED,
            total_dependencies=20,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={"ecosystems": ["Python", "JavaScript"], "scan_options": {}}
        )
        
        with patch.object(formatter.console, 'print') as mock_print:
            formatter.print_scan_summary(report)
            
            # Should handle multiple ecosystems
            printed_text = " ".join([str(call.args[0]) for call in mock_print.call_args_list])
            # Implementation-dependent: might mention both ecosystems
    
    def test_formatter_with_no_console_colors(self, formatter):
        """Test formatter behavior when console doesn't support colors"""
        # This would test graceful degradation for non-color terminals
        # Implementation depends on how Rich handles this
        
        # Mock console to simulate no color support
        with patch.object(formatter.console, 'options') as mock_options:
            mock_options.color_system = None
            
            vuln = Vuln(
                package="test-package",
                version="1.0.0",
                ecosystem="PyPI",
                vulnerability_id="TEST-001",
                severity=SeverityLevel.HIGH,
                summary="Test vulnerability",
                fixed_range=None
            )
            
            report = Report(
                job_id="no-color-test",
                status=JobStatus.COMPLETED,
                total_dependencies=1,
                vulnerable_count=1,
                vulnerable_packages=[vuln],
                dependencies=[],
                suppressed_count=0,
                meta={}
            )
            
            # Should work without colors
            table = formatter.create_vulnerability_table(report)
            assert table.row_count == 1
            
            with patch.object(formatter.console, 'print'):
                formatter.print_scan_summary(report)
                # Should not raise exception