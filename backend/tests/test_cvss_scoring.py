"""Tests for CVSS score parsing and severity classification"""
import pytest
from unittest.mock import Mock, AsyncMock

from backend.core.scanner.osv import OSVScanner
from backend.core.models import Dep, SeverityLevel


class TestCVSSScoring:
    """Test CVSS score parsing and severity classification"""

    @pytest.fixture
    def osv_scanner(self):
        """Create OSVScanner instance for testing"""
        return OSVScanner()

    @pytest.fixture
    def lodash_dep(self):
        """Create lodash dependency for testing"""
        return Dep(
            name="lodash",
            version="4.17.11", 
            ecosystem="npm",
            path=["lodash"],
            is_direct=True
        )

    def test_ghsa_jf85_cpcp_j695_cvss_parsing(self, osv_scanner):
        """Test that GHSA-jf85-cpcp-j695 gets CVSS 9.1 (CRITICAL) not 7.5 (HIGH)"""
        
        # Mock OSV data for GHSA-jf85-cpcp-j695 with CVSS vector
        osv_data = {
            "id": "GHSA-jf85-cpcp-j695",
            "summary": "Prototype Pollution in lodash",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H"
                }
            ],
            "aliases": ["CVE-2020-8203"],
            "affected": [],
            "references": []
        }

        dep = Dep(name="lodash", version="4.17.11", ecosystem="npm", path=["lodash"], is_direct=True)
        
        # Convert OSV data to Vuln object
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Assert that we get the correct CVSS score and severity
        assert vuln.cvss_score == 9.1, f"Expected CVSS 9.1, got {vuln.cvss_score}"
        assert vuln.severity == SeverityLevel.CRITICAL, f"Expected CRITICAL, got {vuln.severity}"
        assert vuln.vulnerability_id == "GHSA-jf85-cpcp-j695"

    def test_cvss_vector_calculation(self, osv_scanner):
        """Test CVSS 3.1 vector calculation for specific case"""
        
        # Test the specific vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H
        # This should calculate to 9.1 (CRITICAL)
        metrics = {
            'AV': 'N',  # Attack Vector: Network
            'AC': 'L',  # Attack Complexity: Low  
            'PR': 'N',  # Privileges Required: None
            'UI': 'N',  # User Interaction: None
            'S': 'U',   # Scope: Unchanged
            'C': 'N',   # Confidentiality Impact: None
            'I': 'H',   # Integrity Impact: High
            'A': 'H'    # Availability Impact: High
        }
        
        score = osv_scanner._calculate_cvss31_score(metrics)
        
        # Should be 9.1, allowing for small floating point differences
        assert abs(score - 9.1) < 0.1, f"Expected ~9.1, got {score}"
        
        # Verify severity classification
        if score >= 9.0:
            severity = SeverityLevel.CRITICAL
        elif score >= 7.0:
            severity = SeverityLevel.HIGH
        else:
            severity = SeverityLevel.MEDIUM
            
        assert severity == SeverityLevel.CRITICAL

    def test_cvss_with_embedded_score(self, osv_scanner):
        """Test CVSS parsing when score is embedded in string"""
        
        osv_data = {
            "id": "TEST-VULN-001",
            "summary": "Test vulnerability",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:H/A:H score:9.1"
                }
            ],
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="npm", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should extract the embedded score
        assert vuln.cvss_score == 9.1
        assert vuln.severity == SeverityLevel.CRITICAL

    def test_cvss_with_numeric_score(self, osv_scanner):
        """Test CVSS parsing when score is already numeric"""
        
        osv_data = {
            "id": "TEST-VULN-002", 
            "summary": "Test vulnerability",
            "severity": [
                {
                    "type": "CVSS_V3",
                    "score": 9.1
                }
            ],
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="npm", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should use the numeric score directly
        assert vuln.cvss_score == 9.1
        assert vuln.severity == SeverityLevel.CRITICAL

    def test_database_specific_score_extraction(self, osv_scanner):
        """Test score extraction from database_specific fields"""
        
        osv_data = {
            "id": "TEST-VULN-003",
            "summary": "Test vulnerability", 
            "severity": [],
            "database_specific": {
                "cvss_score": 9.1,
                "severity": "high"
            },
            "aliases": [],
            "affected": [],
            "references": []
        }

        dep = Dep(name="test-pkg", version="1.0.0", ecosystem="npm", path=["test-pkg"], is_direct=True)
        
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
        
        # Should extract score from database_specific
        assert vuln.cvss_score == 9.1
        assert vuln.severity == SeverityLevel.CRITICAL

    def test_severity_classification_boundaries(self, osv_scanner):
        """Test that severity boundaries are correctly applied"""
        
        test_cases = [
            (10.0, SeverityLevel.CRITICAL),
            (9.5, SeverityLevel.CRITICAL),
            (9.0, SeverityLevel.CRITICAL),
            (8.9, SeverityLevel.HIGH),
            (7.5, SeverityLevel.HIGH),
            (7.0, SeverityLevel.HIGH),
            (6.9, SeverityLevel.MEDIUM),
            (5.0, SeverityLevel.MEDIUM),
            (4.0, SeverityLevel.MEDIUM),
            (3.9, SeverityLevel.LOW),
            (2.0, SeverityLevel.LOW),
            (0.1, SeverityLevel.LOW),
        ]
        
        for score, expected_severity in test_cases:
            osv_data = {
                "id": f"TEST-VULN-{score}",
                "summary": "Test vulnerability",
                "severity": [{"type": "CVSS_V3", "score": score}],
                "aliases": [],
                "affected": [],
                "references": []
            }

            dep = Dep(name="test-pkg", version="1.0.0", ecosystem="npm", path=["test-pkg"], is_direct=True)
            vuln = osv_scanner._convert_osv_to_vuln(osv_data, dep)
            
            assert vuln.cvss_score == score
            assert vuln.severity == expected_severity, f"Score {score} should be {expected_severity}, got {vuln.severity}"

    def test_fallback_cvss_calculation(self, osv_scanner):
        """Test fallback calculation when CVSS vector parsing fails"""
        
        # Test high impact, network accessible case
        fallback_score = osv_scanner._calculate_cvss_fallback("UNKNOWN:VECTOR/AV:N/AC:L/PR:N/UI:N/C:H/I:H/A:H")
        assert fallback_score == 8.5
        
        # Test high impact, network accessible but not low complexity
        fallback_score = osv_scanner._calculate_cvss_fallback("UNKNOWN:VECTOR/AV:N/AC:H/PR:N/UI:N/C:H/I:H/A:H")
        assert fallback_score == 7.5
        
        # Test high impact but not network accessible
        fallback_score = osv_scanner._calculate_cvss_fallback("UNKNOWN:VECTOR/AV:L/AC:L/PR:N/UI:N/C:H/I:H/A:H")
        assert fallback_score == 6.5
        
        # Test no high impact
        fallback_score = osv_scanner._calculate_cvss_fallback("UNKNOWN:VECTOR/AV:N/AC:L/PR:N/UI:N/C:L/I:L/A:L")
        assert fallback_score == 5.0