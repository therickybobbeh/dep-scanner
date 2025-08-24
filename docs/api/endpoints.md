# 🌐 API Documentation

DepScan provides a comprehensive REST API with WebSocket support for real-time updates. This document covers all available endpoints and their usage.

## 🔗 Base URL

- **Development**: `http://127.0.0.1:8000`
- **Production**: `https://your-domain.com`

## 📋 API Overview

### Available APIs
- **REST API**: HTTP endpoints for scan management and results
- **WebSocket API**: Real-time progress updates and notifications  
- **OpenAPI**: Auto-generated interactive documentation at `/docs`

### Authentication
Currently, no authentication is required. This is suitable for internal tools but should be enhanced for production deployments.

---

## 📊 REST Endpoints

### Health Check

#### `GET /health`

Check API health and version information.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "cache_stats": {
    "total_entries": 1250,
    "cache_hits": 875,
    "cache_misses": 375
  }
}
```

---

### Scan Management

#### `POST /scan/upload-files`

Start a new scan by uploading dependency files.

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/scan/upload-files" \
  -F "files=@package.json" \
  -F "files=@package-lock.json" \
  -F "include_dev=true" \
  -F "ignore_severities=LOW"
```

**Form Data:**
- `files`: Dependency files (multiple allowed)
- `include_dev`: Include development dependencies (optional, default: true)
- `ignore_severities`: Comma-separated severity levels to ignore (optional)

**Response:**
```json
{
  "job_id": "scan_1640995200_abc123",
  "status": "PENDING",
  "message": "Scan started successfully",
  "websocket_url": "/ws/scan/scan_1640995200_abc123"
}
```

#### `POST /scan/repository`

Start a new scan by specifying a repository path (server-side).

**Request:**
```json
{
  "repo_path": "/path/to/repository",
  "options": {
    "include_dev_dependencies": true,
    "ignore_severities": ["LOW"],
    "ignore_rules": []
  }
}
```

**Response:**
```json
{
  "job_id": "scan_1640995200_def456", 
  "status": "PENDING",
  "message": "Repository scan started",
  "websocket_url": "/ws/scan/scan_1640995200_def456"
}
```

#### `GET /scan/{job_id}/status`

Get current status of a scan job.

**Response:**
```json
{
  "job_id": "scan_1640995200_abc123",
  "status": "IN_PROGRESS",
  "current_step": "resolving_dependencies",
  "progress_percent": 45,
  "dependencies_found": 47,
  "vulnerabilities_found": 3,
  "start_time": "2024-01-01T12:00:00Z",
  "estimated_completion": "2024-01-01T12:02:30Z"
}
```

**Status Values:**
- `PENDING`: Scan queued but not started
- `IN_PROGRESS`: Currently scanning
- `COMPLETED`: Scan finished successfully  
- `FAILED`: Scan failed with errors

#### `GET /scan/{job_id}/results`

Get detailed scan results.

**Response:**
```json
{
  "job_id": "scan_1640995200_abc123",
  "status": "COMPLETED",
  "total_dependencies": 47,
  "vulnerable_count": 3,
  "vulnerable_packages": [
    {
      "package": "lodash",
      "version": "4.17.20",
      "ecosystem": "npm", 
      "vulnerability_id": "GHSA-35jh-r3h4-6jhm",
      "severity": "HIGH",
      "cve_ids": ["CVE-2020-8203"],
      "summary": "Prototype Pollution in lodash",
      "description": "lodash versions prior to 4.17.21 are vulnerable to Prototype Pollution.",
      "advisory_url": "https://github.com/advisories/GHSA-35jh-r3h4-6jhm",
      "fixed_range": ">=4.17.21",
      "published": "2020-05-08T18:25:00Z",
      "modified": "2021-01-08T19:02:00Z"
    }
  ],
  "dependencies": [
    {
      "name": "lodash",
      "version": "4.17.20",
      "ecosystem": "npm",
      "path": ["my-app", "express", "lodash"],
      "is_direct": false,
      "is_dev": false
    }
  ],
  "suppressed_count": 0,
  "meta": {
    "generated_at": "2024-01-01T12:02:00Z",
    "ecosystems": ["npm"],
    "scan_duration_seconds": 120.5,
    "scan_options": {
      "include_dev_dependencies": true,
      "ignore_severities": [],
      "ignore_rules": []
    }
  }
}
```

#### `DELETE /scan/{job_id}`

Cancel a running scan or delete completed scan results.

**Response:**
```json
{
  "job_id": "scan_1640995200_abc123",
  "message": "Scan cancelled successfully"
}
```

---

### Export Endpoints  

#### `GET /scan/{job_id}/export/json`

Download scan results as JSON file.

**Response:** File download with `Content-Type: application/json`

#### `GET /scan/{job_id}/export/csv`

Download vulnerability summary as CSV file.

**Response:** File download with `Content-Type: text/csv`

**CSV Format:**
```csv
Package,Version,Ecosystem,Severity,CVE,Description,Fix Available
lodash,4.17.20,npm,HIGH,CVE-2020-8203,Prototype Pollution,>=4.17.21
minimist,0.0.8,npm,CRITICAL,CVE-2020-7598,Prototype Pollution,>=1.2.5
```

#### `GET /scan/{job_id}/export/sbom`

Download Software Bill of Materials (SBOM) in SPDX format.

**Response:** File download with `Content-Type: application/json`

---

### Statistics & Analytics

#### `GET /stats/overview`

Get system-wide scanning statistics.

**Response:**
```json
{
  "total_scans": 1250,
  "total_dependencies_scanned": 125000,
  "total_vulnerabilities_found": 3750,
  "unique_packages": 15000,
  "ecosystems": {
    "npm": 85000,
    "PyPI": 40000
  },
  "severities": {
    "CRITICAL": 125,
    "HIGH": 875,
    "MEDIUM": 1500,
    "LOW": 1250
  },
  "cache_effectiveness": 0.85,
  "avg_scan_duration_seconds": 45.2
}
```

#### `GET /stats/trends`

Get vulnerability trends over time.

**Query Parameters:**
- `days`: Number of days to include (default: 30)
- `ecosystem`: Filter by ecosystem (optional)

**Response:**
```json
{
  "period_days": 30,
  "daily_stats": [
    {
      "date": "2024-01-01",
      "scans_completed": 25,
      "vulnerabilities_found": 75,
      "packages_scanned": 2500
    }
  ],
  "trends": {
    "vulnerability_rate_change": 0.15,
    "most_vulnerable_packages": [
      {"package": "lodash", "vulnerability_count": 15},
      {"package": "minimist", "vulnerability_count": 12}
    ]
  }
}
```

---

### System Management

#### `POST /admin/cache/clear`

Clear vulnerability cache (admin endpoint).

**Response:**
```json
{
  "message": "Cache cleared successfully", 
  "entries_removed": 1250
}
```

#### `GET /admin/cache/stats`

Get detailed cache statistics.

**Response:**
```json
{
  "total_entries": 1250,
  "cache_size_mb": 15.2,
  "hit_rate": 0.85,
  "oldest_entry": "2024-01-01T10:00:00Z",
  "newest_entry": "2024-01-01T15:30:00Z",
  "entries_by_ecosystem": {
    "npm": 750,
    "PyPI": 500
  }
}
```

---

## 🔌 WebSocket API

### Connection

Connect to WebSocket for real-time updates:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws/scan/{job_id}');

ws.onopen = function() {
    console.log('Connected to scan updates');
};

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    console.log('Progress update:', update);
};
```

### Message Types

#### Progress Updates
```json
{
  "type": "progress",
  "job_id": "scan_1640995200_abc123",
  "status": "IN_PROGRESS",
  "current_step": "scanning_vulnerabilities",
  "progress_percent": 75,
  "message": "Checking 47 dependencies for vulnerabilities...",
  "dependencies_found": 47,
  "vulnerabilities_found": 2
}
```

#### Completion Notification
```json
{
  "type": "completed",
  "job_id": "scan_1640995200_abc123", 
  "status": "COMPLETED",
  "total_dependencies": 47,
  "vulnerable_count": 3,
  "scan_duration_seconds": 120.5,
  "results_url": "/scan/scan_1640995200_abc123/results"
}
```

#### Error Notification
```json
{
  "type": "error",
  "job_id": "scan_1640995200_abc123",
  "status": "FAILED", 
  "error_code": "PARSE_ERROR",
  "error_message": "Failed to parse package.json: Invalid JSON format",
  "details": {
    "file": "package.json",
    "line": 15,
    "column": 3
  }
}
```

---

## 📝 Request/Response Examples

### Complete Workflow Example

```javascript
// 1. Upload files and start scan
const formData = new FormData();
formData.append('files', packageJsonFile);
formData.append('files', packageLockFile);
formData.append('include_dev', 'true');

const scanResponse = await fetch('/scan/upload-files', {
    method: 'POST',
    body: formData
});
const { job_id, websocket_url } = await scanResponse.json();

// 2. Connect to WebSocket for updates
const ws = new WebSocket(`ws://127.0.0.1:8000${websocket_url}`);

ws.onmessage = function(event) {
    const update = JSON.parse(event.data);
    
    if (update.type === 'progress') {
        updateProgressBar(update.progress_percent);
        showStatusMessage(update.message);
    } else if (update.type === 'completed') {
        // Scan finished, get results
        fetchScanResults(job_id);
        ws.close();
    } else if (update.type === 'error') {
        showError(update.error_message);
        ws.close();
    }
};

// 3. Get detailed results
async function fetchScanResults(jobId) {
    const response = await fetch(`/scan/${jobId}/results`);
    const results = await response.json();
    
    displayVulnerabilities(results.vulnerable_packages);
    showSummary(results.total_dependencies, results.vulnerable_count);
}

// 4. Export results if needed
async function exportResults(jobId, format) {
    const response = await fetch(`/scan/${jobId}/export/${format}`);
    const blob = await response.blob();
    
    // Download file
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-report.${format}`;
    a.click();
}
```

### Batch Processing Example

```python
import asyncio
import aiohttp

async def scan_multiple_projects(projects):
    """Scan multiple projects concurrently"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        for project in projects:
            task = scan_project(session, project)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

async def scan_project(session, project_path):
    """Scan a single project"""
    # Start scan
    data = {
        "repo_path": project_path,
        "options": {"include_dev_dependencies": True}
    }
    
    async with session.post('/scan/repository', json=data) as resp:
        scan_info = await resp.json()
        job_id = scan_info['job_id']
    
    # Poll for completion
    while True:
        async with session.get(f'/scan/{job_id}/status') as resp:
            status = await resp.json()
            
            if status['status'] == 'COMPLETED':
                # Get results
                async with session.get(f'/scan/{job_id}/results') as resp:
                    return await resp.json()
            elif status['status'] == 'FAILED':
                raise Exception(f"Scan failed: {status.get('error_message')}")
            
            await asyncio.sleep(5)  # Poll every 5 seconds
```

---

## 🚨 Error Handling

### HTTP Status Codes

- **200**: Success
- **201**: Created (new scan started)
- **400**: Bad Request (invalid parameters)  
- **404**: Not Found (scan job not found)
- **422**: Unprocessable Entity (validation errors)
- **429**: Too Many Requests (rate limited)
- **500**: Internal Server Error

### Error Response Format

```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid file format provided",
  "details": {
    "field": "files",
    "provided": "image.png",
    "expected": ["package.json", "requirements.txt", "..."]
  },
  "request_id": "req_1640995200_xyz789"
}
```

### Common Errors

#### File Upload Errors
```json
{
  "error": "INVALID_FILE_FORMAT",
  "message": "Unsupported file type: image.png",
  "details": {
    "supported_formats": [
      "package.json", "package-lock.json", "yarn.lock",
      "requirements.txt", "poetry.lock", "pyproject.toml"
    ]
  }
}
```

#### Scan Job Errors
```json
{
  "error": "JOB_NOT_FOUND",
  "message": "Scan job not found: scan_invalid_123",
  "details": {
    "job_id": "scan_invalid_123",
    "suggestion": "Check job ID or create a new scan"
  }
}
```

---

## 🔒 Rate Limiting

### Limits
- **Scan Creation**: 10 scans per minute per IP
- **Result Queries**: 100 requests per minute per IP
- **WebSocket Connections**: 5 concurrent per IP

### Headers
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1640995260
```

### Rate Limit Response
```json
{
  "error": "RATE_LIMITED",
  "message": "Too many requests. Please wait before retrying.",
  "retry_after_seconds": 45
}
```

---

## 🔧 SDK & Client Libraries

### Python Client Example

```python
import aiohttp
import asyncio

class DepScanClient:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def scan_files(self, files: dict, include_dev=True):
        """Upload files and start scan"""
        data = aiohttp.FormData()
        
        for filename, content in files.items():
            data.add_field('files', content, filename=filename)
        data.add_field('include_dev', str(include_dev).lower())
        
        async with self.session.post(f'{self.base_url}/scan/upload-files', 
                                   data=data) as resp:
            return await resp.json()
    
    async def wait_for_completion(self, job_id: str):
        """Wait for scan completion and return results"""
        while True:
            async with self.session.get(
                f'{self.base_url}/scan/{job_id}/status'
            ) as resp:
                status = await resp.json()
                
                if status['status'] == 'COMPLETED':
                    async with self.session.get(
                        f'{self.base_url}/scan/{job_id}/results'
                    ) as resp:
                        return await resp.json()
                elif status['status'] == 'FAILED':
                    raise Exception(f"Scan failed: {status}")
                
                await asyncio.sleep(2)

# Usage
async def main():
    files = {
        'package.json': open('package.json').read(),
        'package-lock.json': open('package-lock.json').read()
    }
    
    async with DepScanClient() as client:
        scan_info = await client.scan_files(files)
        results = await client.wait_for_completion(scan_info['job_id'])
        
        print(f"Found {results['vulnerable_count']} vulnerabilities")
        for vuln in results['vulnerable_packages']:
            print(f"- {vuln['package']}@{vuln['version']}: {vuln['severity']}")

asyncio.run(main())
```

---

## 📖 Interactive Documentation

### OpenAPI/Swagger UI

Visit `/docs` for interactive API documentation:
- Try endpoints directly from the browser
- View request/response schemas
- Download OpenAPI specification

### Redoc Documentation

Visit `/redoc` for alternative documentation format:
- Clean, organized presentation
- Detailed schema information  
- Easy navigation

---

## 🔄 Changelog & Versioning

The API follows semantic versioning. Check [CHANGELOG.md](../CHANGELOG.md) for version history and breaking changes.

### Current Version: 1.0.0
- Initial stable release
- Complete REST API
- WebSocket support
- Export capabilities

---

For additional help or questions about the API, please refer to the [Contributing Guide](../development/contributing.md) or open an issue on GitHub.