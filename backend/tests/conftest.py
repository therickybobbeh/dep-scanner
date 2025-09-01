"""Test configuration and fixtures for pytest"""
import pytest
import asyncio
from pathlib import Path
from typing import Dict
from unittest.mock import Mock

from backend.core.models import ScanOptions, Dep, Vuln, SeverityLevel, Report, JobStatus


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_scan_options() -> ScanOptions:
    """Sample scan options for testing"""
    return ScanOptions(
        include_dev_dependencies=True,
        ignore_severities=[]
    )


@pytest.fixture
def sample_python_dep() -> Dep:
    """Sample Python dependency"""
    return Dep(
        name="requests",
        version="2.25.1",
        ecosystem="PyPI",
        path=["requests"],
        is_direct=True,
        is_dev=False
    )


@pytest.fixture
def sample_js_dep() -> Dep:
    """Sample JavaScript dependency"""
    return Dep(
        name="lodash",
        version="4.17.19",
        ecosystem="npm",
        path=["lodash"],
        is_direct=True,
        is_dev=False
    )


@pytest.fixture
def sample_vulnerability() -> Vuln:
    """Sample vulnerability"""
    return Vuln(
        package="requests",
        version="2.25.1",
        ecosystem="PyPI",
        vulnerability_id="PYSEC-2022-43012",
        severity=SeverityLevel.HIGH,
        cvss_score=7.5,
        cve_ids=["CVE-2022-48147"],
        summary="Requests library vulnerable to SSRF",
        details="The Requests library is vulnerable to SSRF attacks when...",
        advisory_url="https://osv.dev/vulnerability/PYSEC-2022-43012",
        fixed_range=">=2.31.0"
    )


@pytest.fixture
def sample_report(sample_python_dep, sample_vulnerability) -> Report:
    """Sample report with one vulnerability"""
    return Report(
        job_id="test-job-123",
        status=JobStatus.COMPLETED,
        total_dependencies=1,
        vulnerable_count=1,
        vulnerable_packages=[sample_vulnerability],
        dependencies=[sample_python_dep],
        suppressed_count=0,
        meta={"ecosystems": ["Python"], "scan_options": {}}
    )


@pytest.fixture
def mock_progress_callback() -> Mock:
    """Mock progress callback for testing"""
    return Mock()


@pytest.fixture
def sample_package_json() -> str:
    """Sample package.json content"""
    return '''{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "lodash": "^4.17.19",
    "axios": "^0.21.0"
  },
  "devDependencies": {
    "jest": "^26.0.0"
  }
}'''


@pytest.fixture
def sample_requirements_txt() -> str:
    """Sample requirements.txt content"""
    return '''requests==2.25.1
urllib3==1.26.5
certifi==2021.5.30'''


@pytest.fixture
def sample_pyproject_toml() -> str:
    """Sample pyproject.toml content"""
    return '''[tool.poetry]
name = "test-project"
version = "0.1.0"

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.25.1"
pydantic = "^2.0.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
black = "^22.0.0"
'''


@pytest.fixture
def temp_test_dir(tmp_path) -> Path:
    """Create a temporary directory for testing"""
    return tmp_path


@pytest.fixture
def sample_manifest_files(sample_package_json, sample_requirements_txt) -> Dict[str, str]:
    """Sample manifest files dictionary"""
    return {
        "package.json": sample_package_json,
        "requirements.txt": sample_requirements_txt
    }