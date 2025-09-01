"""Tests for Python CVSS scoring consistency between CLI and frontend"""
import pytest

from backend.core.scanner.osv import OSVScanner
from backend.core.models import Dep, SeverityLevel, Report, JobStatus
from backend.web.services.cli_service import CLIService


class TestPythonCVSSConsistency:
    """Test CVSS score consistency for Python vulnerabilities"""

    @pytest.fixture
    def osv_scanner(self):
        """Create OSVScanner instance for testing"""
        return OSVScanner()

    def test_pysec_2022_230_consistent_scoring(self, osv_scanner):
        """Test PYSEC-2022-230 shows consistent CVSS 5.3 in both CLI and frontend"""
        
        # OSV data for PYSEC-2022-230 (lxml vulnerability)
        osv_data = {
            "id": "PYSEC-2022-230",
            "summary": "lxml NULL Pointer Dereference allows attackers to cause a denial of service",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": "5.3"
                }
            ],
            "aliases": ["CVE-2022-2309"],
            "affected": [],
            "references": []
        }

        dep = Dep(name="lxml", version="4.6.3", ecosystem="PyPI", path=["lxml"], is_direct=True)
        
        # Test OSV scanner (used by CLI)
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        assert vuln.cvss_score == 5.3, f"Expected CVSS 5.3, got {vuln.cvss_score}"
        assert vuln.severity == SeverityLevel.MEDIUM, f"Expected MEDIUM, got {vuln.severity}"
        
        # Test frontend API conversion
        report = Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=1,
            vulnerable_count=1,
            vulnerable_packages=[vuln],
            dependencies=[dep]
        )
        
        frontend_data = CLIService._convert_report_to_cli_format(report)
        frontend_vuln = frontend_data["vulnerable_packages"][0]
        
        # Frontend should get the same data
        assert frontend_vuln["cvss_score"] == 5.3, f"Frontend CVSS should be 5.3, got {frontend_vuln['cvss_score']}"
        assert frontend_vuln["severity"] == "MEDIUM", f"Frontend severity should be MEDIUM, got {frontend_vuln['severity']}"

    def test_python_vulnerability_with_embedded_score(self, osv_scanner):
        """Test Python vulnerability with embedded CVSS score"""
        
        osv_data = {
            "id": "PYSEC-TEST-001",
            "summary": "Test Python vulnerability with embedded score",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N score:6.5"
                }
            ],
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="PyPI", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should extract embedded score
        assert vuln.cvss_score == 6.5, f"Expected CVSS 6.5, got {vuln.cvss_score}"
        assert vuln.severity == SeverityLevel.MEDIUM

    def test_python_vulnerability_unknown_severity_no_hardcode(self, osv_scanner):
        """Test that UNKNOWN severity Python vulns don't get hardcoded 5.0"""
        
        osv_data = {
            "id": "PYSEC-UNKNOWN-TEST",
            "summary": "Test vulnerability with no severity data",
            "severity": [],  # No severity info
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="PyPI", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should NOT get hardcoded 5.0 score
        assert vuln.cvss_score is None or vuln.cvss_score == 0.0, f"UNKNOWN vuln should not get hardcoded score, got {vuln.cvss_score}"
        assert vuln.severity == SeverityLevel.UNKNOWN

    def test_python_vulnerability_with_database_specific_score(self, osv_scanner):
        """Test Python vulnerability with score in database_specific field"""
        
        osv_data = {
            "id": "PYSEC-DB-TEST",
            "summary": "Test vulnerability with database_specific score",
            "severity": [],
            "database_specific": {
                "cvss_score": 8.2,
                "severity": "high"
            },
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="PyPI", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should extract from database_specific
        assert vuln.cvss_score == 8.2, f"Expected CVSS 8.2, got {vuln.cvss_score}"
        assert vuln.severity == SeverityLevel.HIGH

    def test_multiple_python_vulnerabilities_different_scores(self, osv_scanner):
        """Test multiple Python vulnerabilities with different CVSS scores"""
        
        test_cases = [
            ("PYSEC-LOW", "3.1", SeverityLevel.LOW),
            ("PYSEC-MED", "5.7", SeverityLevel.MEDIUM), 
            ("PYSEC-HIGH", "7.8", SeverityLevel.HIGH),
            ("PYSEC-CRIT", "9.2", SeverityLevel.CRITICAL)
        ]
        
        results = []
        for vuln_id, score_str, expected_severity in test_cases:
            osv_data = {
                "id": vuln_id,
                "summary": f"Test vulnerability {vuln_id}",
                "severity": [{"type": "CVSS_V3", "score": score_str}],
                "aliases": [],
                "affected": [],
                "references": []
            }
            
            dep = Dep(name="test-pkg", version="1.0.0", ecosystem="PyPI", path=["test-pkg"], is_direct=True)
            vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
            
            expected_score = float(score_str)
            assert vuln.cvss_score == expected_score, f"Expected {expected_score}, got {vuln.cvss_score} for {vuln_id}"
            assert vuln.severity == expected_severity, f"Expected {expected_severity}, got {vuln.severity} for {vuln_id}"
            
            results.append((vuln_id, vuln.cvss_score, vuln.severity.value))
        
        # Verify we got different scores, not all hardcoded to 5.0
        scores = [r[1] for r in results]
        assert len(set(scores)) == 4, f"Should have 4 different scores, got {set(scores)}"
        assert 5.0 not in scores or scores.count(5.0) <= 1, f"Too many 5.0 hardcoded scores: {scores}"

    def test_frontend_api_includes_cvss_scores(self, osv_scanner):
        """Test that frontend API response includes actual CVSS scores"""
        
        # Create vulnerabilities with different scores
        vulns = []
        deps = []
        
        test_data = [
            ("pkg1", "1.0", "VULN-001", 4.2, SeverityLevel.MEDIUM),
            ("pkg2", "2.0", "VULN-002", 7.8, SeverityLevel.HIGH),
            ("pkg3", "3.0", "VULN-003", 9.1, SeverityLevel.CRITICAL)
        ]
        
        for pkg_name, version, vuln_id, cvss_score, severity in test_data:
            dep = Dep(name=pkg_name, version=version, ecosystem="PyPI", path=[pkg_name], is_direct=True)
            vuln = vuln = osv_scanner._convert_osv_to_vuln({
                "id": vuln_id,
                "summary": f"Test vuln for {pkg_name}",
                "severity": [{"type": "CVSS_V3", "score": str(cvss_score)}],
                "aliases": [], "affected": [], "references": []
            }, dep)
            
            deps.append(dep)
            vulns.append(vuln)
        
        # Create report and convert to frontend format
        report = Report(
            job_id="test-multi",
            status=JobStatus.COMPLETED,
            total_dependencies=len(deps),
            vulnerable_count=len(vulns),
            vulnerable_packages=vulns,
            dependencies=deps
        )
        
        frontend_data = CLIService._convert_report_to_cli_format(report)
        frontend_vulns = frontend_data["vulnerable_packages"]
        
        # Check each vulnerability has correct CVSS score
        for i, (_, _, _, expected_score, expected_severity) in enumerate(test_data):
            frontend_vuln = frontend_vulns[i]
            assert frontend_vuln["cvss_score"] == expected_score, f"Frontend CVSS mismatch: expected {expected_score}, got {frontend_vuln['cvss_score']}"
            assert frontend_vuln["severity"] == expected_severity.value, f"Frontend severity mismatch for {frontend_vuln['vulnerability_id']}"