"""Test CLI service wrapper"""
import pytest
import json
from backend.web.services.cli_service import CLIService


@pytest.mark.asyncio
async def test_cli_service_basic():
    """Test basic CLI service functionality"""
    # Simple package.json with known vulnerable package
    package_json = {
        "name": "test",
        "version": "1.0.0",
        "dependencies": {
            "lodash": "4.17.15"  # Known vulnerable version
        }
    }
    
    manifest_files = {
        "package.json": json.dumps(package_json, indent=2)
    }
    
    result = await CLIService.run_cli_scan_async(
        manifest_files=manifest_files,
        include_dev=False,
        ignore_severities=[]
    )
    
    # Check CLI JSON structure
    assert "scan_info" in result
    assert "vulnerabilities" in result
    assert result["scan_info"]["total_dependencies"] >= 1
    assert result["scan_info"]["vulnerable_packages"] >= 1
    
    # Check vulnerability structure
    assert len(result["vulnerabilities"]) > 0
    vuln = result["vulnerabilities"][0]
    assert "package" in vuln
    assert "version" in vuln
    assert "vulnerability_id" in vuln
    assert "severity" in vuln
    assert "summary" in vuln


@pytest.mark.asyncio 
async def test_cli_service_clean_project():
    """Test CLI service with clean dependencies"""
    package_json = {
        "name": "clean-test",
        "version": "1.0.0",
        "dependencies": {
            "express": "4.19.0"  # Should be clean
        }
    }
    
    manifest_files = {
        "package.json": json.dumps(package_json, indent=2)
    }
    
    result = await CLIService.run_cli_scan_async(
        manifest_files=manifest_files,
        include_dev=False,
        ignore_severities=[]
    )
    
    # Should have dependencies but possibly no vulnerabilities
    assert "scan_info" in result
    assert result["scan_info"]["total_dependencies"] >= 1
    # May or may not have vulnerabilities depending on when test runs


def test_cli_service_progress_parsing():
    """Test progress parsing functionality"""
    test_lines = [
        "Starting scan",
        "Found 5 Python dependencies", 
        "Processing file: requirements.txt",
        "Resolving dependencies",
        "Scan completed"
    ]
    
    for line in test_lines:
        result = CLIService._parse_progress(line)
        if result:
            message, progress = result
            assert isinstance(message, str)
            assert progress is None or (isinstance(progress, float) and 0 <= progress <= 100)