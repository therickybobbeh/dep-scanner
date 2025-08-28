"""Test simplified web API endpoints"""
import pytest
import json
from fastapi.testclient import TestClient
from backend.web.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_scan_endpoint():
    """Test scan endpoint with file upload"""
    package_json = {
        "name": "test",
        "version": "1.0.0",
        "dependencies": {
            "axios": "0.21.0"  # Known vulnerability for testing
        }
    }
    
    scan_request = {
        "manifest_files": {
            "package.json": json.dumps(package_json)
        },
        "options": {
            "include_dev_dependencies": True,
            "ignore_severities": []
        }
    }
    
    response = client.post("/scan", json=scan_request)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    assert len(data["job_id"]) > 0
    
    # Return job_id for other tests
    return data["job_id"]


def test_status_endpoint():
    """Test status endpoint"""
    # Start a scan first
    job_id = test_scan_endpoint()
    
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["status"] in ["pending", "running", "completed", "failed"]
    assert "progress_percent" in data
    assert "current_step" in data
    assert isinstance(data["progress_percent"], (int, float))
    assert 0 <= data["progress_percent"] <= 100


def test_status_endpoint_not_found():
    """Test status endpoint with non-existent job"""
    response = client.get("/status/non-existent-job-id-12345")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "message" in data


def test_report_endpoint_not_found():
    """Test report endpoint with non-existent job"""
    response = client.get("/report/non-existent-job-id-12345")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "message" in data


def test_validate_consistency_endpoint():
    """Test consistency validation endpoint"""
    package_json = {
        "name": "test",
        "version": "1.0.0",
        "dependencies": {
            "lodash": "4.17.20"
        }
    }
    
    scan_request = {
        "manifest_files": {
            "package.json": json.dumps(package_json)
        },
        "options": {
            "include_dev_dependencies": False,
            "ignore_severities": []
        }
    }
    
    response = client.post("/validate-consistency", json=scan_request)
    assert response.status_code == 200
    data = response.json()
    assert "is_consistent" in data
    assert "analysis" in data
    assert "recommendations" in data


def test_invalid_scan_request():
    """Test scan endpoint with invalid request"""
    # Missing required fields
    scan_request = {
        "options": {}
    }
    
    response = client.post("/scan", json=scan_request)
    # Should handle gracefully, might be 400 or proceed with empty files
    assert response.status_code in [200, 400, 422]
    
    if response.status_code != 200:
        data = response.json()
        assert "detail" in data or "message" in data or "error" in data


def test_scan_with_multiple_files():
    """Test scan with multiple manifest files"""
    package_json = {
        "name": "multi-test",
        "version": "1.0.0",
        "dependencies": {
            "lodash": "4.17.20"
        }
    }
    
    requirements_txt = "requests==2.25.1\nflask==1.1.4"
    
    scan_request = {
        "manifest_files": {
            "package.json": json.dumps(package_json),
            "requirements.txt": requirements_txt
        },
        "options": {
            "include_dev_dependencies": True,
            "ignore_severities": ["low"]
        }
    }
    
    response = client.post("/scan", json=scan_request)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    
    return data["job_id"]


def test_scan_status_integration():
    """Test full scan to completion workflow"""
    import time
    
    # Start scan
    job_id = test_scan_endpoint()
    
    # Poll status until completion (with timeout)
    max_attempts = 60  # 60 seconds timeout
    attempt = 0
    
    while attempt < max_attempts:
        response = client.get(f"/status/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        status = data["status"]
        
        if status == "completed":
            # Test report endpoint
            report_response = client.get(f"/report/{job_id}")
            assert report_response.status_code == 200
            
            report_data = report_response.json()
            assert "scan_info" in report_data
            assert "vulnerabilities" in report_data
            assert isinstance(report_data["vulnerabilities"], list)
            break
        elif status == "failed":
            pytest.fail(f"Scan failed: {data.get('error_message', 'Unknown error')}")
        
        time.sleep(1)
        attempt += 1
    
    if attempt >= max_attempts:
        pytest.fail("Scan did not complete within timeout period")