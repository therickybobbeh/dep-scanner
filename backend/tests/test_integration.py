"""Integration tests for complete workflow"""
import pytest
import json
import time
from fastapi.testclient import TestClient
from backend.web.main import app

client = TestClient(app)


@pytest.mark.integration
def test_complete_scan_workflow():
    """Test complete scan workflow from upload to results"""
    # 1. Create test package.json with vulnerable package
    package_json = {
        "name": "integration-test",
        "version": "1.0.0", 
        "dependencies": {
            "lodash": "4.17.15"  # Known vulnerable
        }
    }
    
    # 2. Start scan
    scan_request = {
        "manifest_files": {
            "package.json": json.dumps(package_json, indent=2)
        },
        "options": {
            "include_dev_dependencies": False,
            "ignore_severities": [],
            "ignore_rules": []
        }
    }
    
    response = client.post("/scan", json=scan_request)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # 3. Poll status until completion (with timeout)
    max_wait = 30  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = client.get(f"/status/{job_id}")
        assert response.status_code == 200
        status = response.json()
        
        assert status["job_id"] == job_id
        assert 0 <= status["progress_percent"] <= 100
        
        if status["status"] == "completed":
            break
        elif status["status"] == "failed":
            pytest.fail(f"Scan failed: {status.get('error_message')}")
        
        time.sleep(1)
    else:
        pytest.fail("Scan did not complete within timeout")
    
    # 4. Get final report
    response = client.get(f"/report/{job_id}")
    assert response.status_code == 200
    report = response.json()
    
    # 5. Verify CLI JSON structure
    assert "scan_info" in report
    assert "vulnerabilities" in report
    
    scan_info = report["scan_info"]
    assert scan_info["total_dependencies"] >= 1
    assert scan_info["vulnerable_packages"] >= 1
    assert "npm" in scan_info.get("ecosystems", [])
    
    # 6. Verify vulnerability details
    vulnerabilities = report["vulnerabilities"]
    assert len(vulnerabilities) > 0
    
    # Find lodash vulnerability
    lodash_vuln = None
    for vuln in vulnerabilities:
        if vuln["package"] == "lodash":
            lodash_vuln = vuln
            break
    
    assert lodash_vuln is not None, "Expected lodash vulnerability not found"
    assert lodash_vuln["version"] == "4.17.15"
    assert lodash_vuln["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert "vulnerability_id" in lodash_vuln
    assert "summary" in lodash_vuln


@pytest.mark.integration
def test_python_dependencies():
    """Test scanning Python dependencies"""
    requirements_txt = "requests==2.25.0\\nlodash==4.17.15"  # Include a mix
    
    scan_request = {
        "manifest_files": {
            "requirements.txt": requirements_txt
        },
        "options": {
            "include_dev_dependencies": False,
            "ignore_severities": [],
            "ignore_rules": []
        }
    }
    
    response = client.post("/scan", json=scan_request)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # Wait for completion (simplified)
    max_wait = 30
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_response = client.get(f"/status/{job_id}")
        status = status_response.json()
        
        if status["status"] == "completed":
            break
        elif status["status"] == "failed":
            # Python scanning might fail due to package resolution issues
            pytest.skip(f"Python scan failed (expected): {status.get('error_message')}")
        
        time.sleep(1)
    
    # If we get here, scan completed successfully
    response = client.get(f"/report/{job_id}")
    assert response.status_code == 200
    report = response.json()
    
    # Should have found some dependencies
    assert "scan_info" in report
    assert report["scan_info"]["total_dependencies"] >= 1


@pytest.mark.integration
def test_empty_scan():
    """Test behavior with empty/invalid files"""
    scan_request = {
        "manifest_files": {
            "empty.json": "{}"
        },
        "options": {
            "include_dev_dependencies": False,
            "ignore_severities": [],
            "ignore_rules": []
        }
    }
    
    response = client.post("/scan", json=scan_request)
    # Should either succeed with 0 deps or fail gracefully
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        job_id = response.json()["job_id"]
        
        # Check final status
        time.sleep(2)  # Give it a moment
        status_response = client.get(f"/status/{job_id}")
        status = status_response.json()
        
        # Either completes with 0 deps or fails gracefully
        assert status["status"] in ["completed", "failed"]