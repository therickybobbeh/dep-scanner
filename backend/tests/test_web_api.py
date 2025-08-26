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
            "lodash": "4.17.15"
        }
    }
    
    scan_request = {
        "manifest_files": {
            "package.json": json.dumps(package_json)
        },
        "options": {
            "include_dev_dependencies": False,
            "ignore_severities": [],
            "ignore_rules": []
        }
    }
    
    response = client.post("/scan", json=scan_request)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)
    
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


def test_status_endpoint_not_found():
    """Test status endpoint with non-existent job"""
    response = client.get("/status/non-existent-job")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_report_endpoint():
    """Test report endpoint after scan completes"""
    # This test would need to wait for scan completion
    # For now, just test the 404 case
    response = client.get("/report/non-existent-job")
    assert response.status_code == 404


def test_cache_clear_endpoint():
    """Test cache management endpoint"""
    response = client.post("/admin/cache/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message" in data


def test_cache_stats_endpoint():
    """Test cache stats endpoint"""
    response = client.get("/admin/cache/stats")
    assert response.status_code == 200
    data = response.json()
    assert "cache_stats" in data
    assert "timestamp" in data


def test_invalid_scan_request():
    """Test scan endpoint with invalid request"""
    # Missing required fields
    scan_request = {
        "options": {}
    }
    
    response = client.post("/scan", json=scan_request)
    # Should handle gracefully, might be 400 or proceed with empty files
    assert response.status_code in [200, 400]