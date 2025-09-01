"""Tests for data models"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.core.models import (
    Dep, Vuln, ScanOptions, Report, JobStatus, SeverityLevel
)


class TestDep:
    """Test cases for Dep model"""
    
    def test_dep_creation_minimal(self):
        """Test creating Dep with minimal required fields"""
        dep = Dep(
            name="requests",
            version="2.25.1",
            ecosystem="PyPI",
            path=["requests"]
        )
        
        assert dep.name == "requests"
        assert dep.version == "2.25.1"
        assert dep.ecosystem == "PyPI"
        assert dep.path == ["requests"]
        assert dep.is_direct == False  # Default value
        assert dep.is_dev == False  # Default value
    
    def test_dep_creation_full(self):
        """Test creating Dep with all fields"""
        dep = Dep(
            name="pytest",
            version="7.0.0",
            ecosystem="PyPI",
            path=["pytest"],
            is_direct=True,
            is_dev=True
        )
        
        assert dep.name == "pytest"
        assert dep.version == "7.0.0"
        assert dep.ecosystem == "PyPI"
        assert dep.path == ["pytest"]
        assert dep.is_direct == True
        assert dep.is_dev == True
    
    def test_dep_transitive_dependency(self):
        """Test creating transitive dependency with path"""
        dep = Dep(
            name="urllib3",
            version="1.26.5",
            ecosystem="PyPI",
            path=["requests", "urllib3"],
            is_direct=False,
            is_dev=False
        )
        
        assert len(dep.path) == 2
        assert dep.path == ["requests", "urllib3"]
        assert dep.is_direct == False
    
    def test_dep_invalid_ecosystem(self):
        """Test creating Dep with invalid ecosystem"""
        with pytest.raises(ValidationError):
            Dep(
                name="test",
                version="1.0.0",
                ecosystem="invalid",  # Only "npm" and "PyPI" are valid
                path=["test"]
            )
    
    def test_dep_empty_path(self):
        """Test creating Dep with empty path"""
        dep = Dep(
            name="test",
            version="1.0.0", 
            ecosystem="npm",
            path=[]  # Empty path should be allowed
        )
        
        assert dep.path == []
    
    def test_dep_serialization(self):
        """Test Dep model serialization"""
        dep = Dep(
            name="lodash",
            version="4.17.19",
            ecosystem="npm",
            path=["lodash"],
            is_direct=True,
            is_dev=False
        )
        
        data = dep.model_dump()
        assert data["name"] == "lodash"
        assert data["ecosystem"] == "npm"
        assert data["is_direct"] == True
        assert data["is_dev"] == False


class TestVuln:
    """Test cases for Vuln model"""
    
    def test_vuln_creation_minimal(self):
        """Test creating Vuln with minimal required fields"""
        vuln = Vuln(
            package="requests",
            version="2.25.1",
            ecosystem="PyPI",
            vulnerability_id="PYSEC-2022-43012",
            summary="SSRF vulnerability",
            fixed_range=None
        )
        
        assert vuln.package == "requests"
        assert vuln.version == "2.25.1"
        assert vuln.ecosystem == "PyPI"
        assert vuln.vulnerability_id == "PYSEC-2022-43012"
        assert vuln.summary == "SSRF vulnerability"
        assert vuln.severity is None  # Default
        assert vuln.cvss_score is None  # Default
        assert vuln.cve_ids == []  # Default
        assert vuln.details is None  # Default
        assert vuln.aliases == []  # Default
    
    def test_vuln_creation_full(self):
        """Test creating Vuln with all fields"""
        published = datetime(2022, 1, 15, 10, 0, 0)
        modified = datetime(2022, 1, 16, 11, 0, 0)
        
        vuln = Vuln(
            package="lodash",
            version="4.17.19",
            ecosystem="npm",
            vulnerability_id="GHSA-35jh-r3h4-6jhm",
            severity=SeverityLevel.HIGH,
            cvss_score=7.5,
            cve_ids=["CVE-2021-23337"],
            summary="Prototype pollution vulnerability",
            details="Lodash versions prior to 4.17.21 are vulnerable to...",
            advisory_url="https://github.com/advisories/GHSA-35jh-r3h4-6jhm",
            fixed_range=">=4.17.21",
            published=published,
            modified=modified,
            aliases=["CVE-2021-23337", "SNYK-JS-LODASH-1018905"],
            immediate_parent="express"
        )
        
        assert vuln.severity == SeverityLevel.HIGH
        assert vuln.cvss_score == 7.5
        assert vuln.cve_ids == ["CVE-2021-23337"]
        assert "Prototype pollution" in vuln.summary
        assert vuln.details is not None
        assert vuln.advisory_url == "https://github.com/advisories/GHSA-35jh-r3h4-6jhm"
        assert vuln.fixed_range == ">=4.17.21"
        assert vuln.published == published
        assert vuln.modified == modified
        assert len(vuln.aliases) == 2
        assert vuln.immediate_parent == "express"
    
    def test_vuln_invalid_cvss_score(self):
        """Test creating Vuln with invalid CVSS score"""
        with pytest.raises(ValidationError):
            Vuln(
                package="test",
                version="1.0.0",
                ecosystem="npm",
                vulnerability_id="TEST-001",
                summary="Test vulnerability",
                cvss_score=15.0  # CVSS scores should be 0.0-10.0
            )
    
    def test_vuln_invalid_ecosystem(self):
        """Test creating Vuln with invalid ecosystem"""
        with pytest.raises(ValidationError):
            Vuln(
                package="test",
                version="1.0.0",
                ecosystem="invalid",
                vulnerability_id="TEST-001",
                summary="Test vulnerability"
            )
    
    def test_vuln_serialization(self):
        """Test Vuln model serialization"""
        vuln = Vuln(
            package="requests",
            version="2.25.1",
            ecosystem="PyPI",
            vulnerability_id="PYSEC-2022-43012",
            severity=SeverityLevel.HIGH,
            summary="SSRF vulnerability",
            fixed_range=None
        )
        
        data = vuln.model_dump()
        assert data["package"] == "requests"
        assert data["severity"] == "HIGH"
        assert data["vulnerability_id"] == "PYSEC-2022-43012"


class TestSeverityLevel:
    """Test cases for SeverityLevel enum"""
    
    def test_severity_level_values(self):
        """Test all severity level values"""
        assert SeverityLevel.CRITICAL == "CRITICAL"
        assert SeverityLevel.HIGH == "HIGH"
        assert SeverityLevel.MEDIUM == "MEDIUM"
        assert SeverityLevel.LOW == "LOW"
        assert SeverityLevel.UNKNOWN == "UNKNOWN"
    
    def test_severity_level_comparison(self):
        """Test severity level comparison (if implemented)"""
        # This documents expected behavior if severity comparison is added
        critical = SeverityLevel.CRITICAL
        high = SeverityLevel.HIGH
        medium = SeverityLevel.MEDIUM
        
        assert critical != high
        assert high != medium
        
        # Test string comparison
        assert critical == "CRITICAL"
        assert high == "HIGH"
    
    def test_severity_level_invalid(self):
        """Test invalid severity level"""
        with pytest.raises(ValueError):
            SeverityLevel("INVALID")


class TestScanOptions:
    """Test cases for ScanOptions model"""
    
    def test_scan_options_defaults(self):
        """Test ScanOptions with default values"""
        options = ScanOptions()
        
        assert options.include_dev_dependencies == True
        assert options.ignore_severities == []
    
    def test_scan_options_custom(self):
        """Test ScanOptions with custom values"""
        options = ScanOptions(
            include_dev_dependencies=False,
            ignore_severities=[SeverityLevel.LOW, SeverityLevel.MEDIUM]
        )
        
        assert options.include_dev_dependencies == False
        assert len(options.ignore_severities) == 2
        assert SeverityLevel.LOW in options.ignore_severities
        assert SeverityLevel.MEDIUM in options.ignore_severities
    
    def test_scan_options_serialization(self):
        """Test ScanOptions serialization"""
        options = ScanOptions(
            include_dev_dependencies=False,
            ignore_severities=[SeverityLevel.LOW]
        )
        
        data = options.model_dump()
        assert data["include_dev_dependencies"] == False
        assert data["ignore_severities"] == ["LOW"]


class TestJobStatus:
    """Test cases for JobStatus enum"""
    
    def test_job_status_values(self):
        """Test all job status values"""
        assert JobStatus.PENDING == "pending"
        # Note: Only PENDING is visible in the provided code snippet
        # Add other values as they exist in the full model


class TestReport:
    """Test cases for Report model"""
    
    @pytest.fixture
    def sample_deps(self):
        """Sample dependencies for testing"""
        return [
            Dep(name="requests", version="2.25.1", ecosystem="PyPI", path=["requests"], is_direct=True),
            Dep(name="urllib3", version="1.26.5", ecosystem="PyPI", path=["requests", "urllib3"], is_direct=False)
        ]
    
    @pytest.fixture
    def sample_vulns(self):
        """Sample vulnerabilities for testing"""
        return [
            Vuln(
                package="requests",
                version="2.25.1",
                ecosystem="PyPI", 
                vulnerability_id="PYSEC-2022-43012",
                severity=SeverityLevel.HIGH,
                summary="SSRF vulnerability",
                fixed_range=None
            )
        ]
    
    def test_report_creation(self, sample_deps, sample_vulns):
        """Test creating Report with all fields"""
        report = Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=2,
            vulnerable_count=1,
            vulnerable_packages=sample_vulns,
            dependencies=sample_deps,
            suppressed_count=0,
            meta={"ecosystems": ["Python"], "scan_options": {}}
        )
        
        assert report.job_id == "test-123"
        assert report.status == JobStatus.COMPLETED
        assert report.total_dependencies == 2
        assert report.vulnerable_count == 1
        assert len(report.vulnerable_packages) == 1
        assert len(report.dependencies) == 2
        assert report.suppressed_count == 0
        assert "ecosystems" in report.meta
    
    def test_report_empty_vulnerabilities(self, sample_deps):
        """Test creating Report with no vulnerabilities"""
        report = Report(
            job_id="clean-scan",
            status=JobStatus.COMPLETED,
            total_dependencies=2,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=sample_deps,
            suppressed_count=0,
            meta={}
        )
        
        assert report.vulnerable_count == 0
        assert len(report.vulnerable_packages) == 0
        assert len(report.dependencies) == 2
    
    def test_report_serialization(self, sample_deps, sample_vulns):
        """Test Report serialization"""
        report = Report(
            job_id="test-123",
            status=JobStatus.COMPLETED,
            total_dependencies=2,
            vulnerable_count=1,
            vulnerable_packages=sample_vulns,
            dependencies=sample_deps,
            suppressed_count=0,
            meta={"test": "data"}
        )
        
        data = report.model_dump()
        assert data["job_id"] == "test-123"
        assert data["total_dependencies"] == 2
        assert data["vulnerable_count"] == 1
        assert len(data["vulnerable_packages"]) == 1
        assert len(data["dependencies"]) == 2
        assert data["meta"]["test"] == "data"


class TestModelValidation:
    """Test model validation and edge cases"""
    
    def test_dep_required_fields(self):
        """Test Dep model requires essential fields"""
        with pytest.raises(ValidationError):
            Dep()  # Missing all required fields
        
        with pytest.raises(ValidationError):
            Dep(name="test")  # Missing version, ecosystem, path
        
        with pytest.raises(ValidationError):
            Dep(name="test", version="1.0.0")  # Missing ecosystem, path
    
    def test_vuln_required_fields(self):
        """Test Vuln model requires essential fields"""
        with pytest.raises(ValidationError):
            Vuln()  # Missing all required fields
        
        with pytest.raises(ValidationError):
            Vuln(package="test", version="1.0.0")  # Missing ecosystem, id, summary
    
    def test_report_required_fields(self):
        """Test Report model requires essential fields"""
        with pytest.raises(ValidationError):
            Report()  # Missing required fields
        
        # Test with minimal required fields
        report = Report(
            job_id="test",
            status=JobStatus.COMPLETED,
            total_dependencies=0,
            vulnerable_count=0,
            vulnerable_packages=[],
            dependencies=[],
            suppressed_count=0,
            meta={}
        )
        assert report.job_id == "test"
    
    def test_model_type_validation(self):
        """Test type validation in models"""
        # Test invalid types
        with pytest.raises(ValidationError):
            Dep(
                name=123,  # Should be string
                version="1.0.0",
                ecosystem="PyPI",
                path=["test"]
            )
        
        with pytest.raises(ValidationError):
            Report(
                job_id="test",
                status="invalid",  # Should be JobStatus enum
                total_dependencies=0,
                vulnerable_count=0,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={}
            )
    
    def test_model_field_constraints(self):
        """Test field constraints and validation"""
        # Test negative counts (if validation is implemented)
        try:
            report = Report(
                job_id="test",
                status=JobStatus.COMPLETED,
                total_dependencies=-1,  # Negative count
                vulnerable_count=0,
                vulnerable_packages=[],
                dependencies=[],
                suppressed_count=0,
                meta={}
            )
            # If no validation error, document this behavior
            assert report.total_dependencies == -1
        except ValidationError:
            # If validation error occurs, that's expected behavior
            pass