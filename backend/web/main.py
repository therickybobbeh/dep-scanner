from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from pathlib import Path
import logging
import time

from ..core.models import ScanRequest, ScanProgress, Report
from .services.app_state import AppState, get_app_state
from .services.scan_service import ScanService
from .services.export_service import ExportService
from .services.rate_limiter import check_rate_limit
from .services.validation import validate_scan_request, validate_path_parameters
from ..core.config import settings
from ..core.resolver.utils.npm_version_resolver import PackageVersionResolver

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events"""
    # Startup logic
    print("DepScan API starting up...")
    
    yield
    
    # Shutdown logic  
    print("DepScan API shutting down...")
    state = get_app_state()
    await state.cleanup()
    print("DepScan API shutdown complete")

app = FastAPI(
    title="DepScan API",
    description="""
    ## Dependency Vulnerability Scanner REST API
    
    A comprehensive vulnerability scanning service for software dependencies across multiple ecosystems.
    
    ### Key Features
    - 🔍 **Multi-Ecosystem Support**: Scan NPM (JavaScript) and PyPI (Python) dependencies
    - 📊 **Real-time Progress**: WebSocket-based scan progress tracking  
    - 📁 **Multiple Input Formats**: Support for lockfiles and manifest files
    - 🚀 **Enhanced Consistency**: Advanced version resolution and consistency checking
    - 📤 **Export Options**: JSON and CSV report exports
    - 🗄️ **Cache Management**: Intelligent caching with management endpoints
    
    ### Supported File Formats
    **JavaScript/NPM:**
    - `package.json` - Direct dependencies with version ranges
    - `package-lock.json` (v1, v2, v3) - Lockfile with exact versions and full dependency tree
    - `yarn.lock` - Yarn lockfile format
    
    **Python/PyPI:**
    - `requirements.txt` - Pip requirements format
    - `Pipfile.lock` - Pipenv lockfile format  
    - `poetry.lock` - Poetry lockfile format
    - `pyproject.toml` - Modern Python project configuration
    
    ### Getting Started
    1. Upload dependency files using the `/scan` endpoint
    2. Monitor progress via WebSocket at `/ws/{job_id}` or polling `/status/{job_id}`
    3. Retrieve results from `/report/{job_id}` when completed
    4. Export results in various formats using `/export/{job_id}.{format}`
    
    ### Rate Limiting
    API endpoints are rate-limited to ensure fair usage. Check response headers for rate limit status.
    """,
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Scanning",
            "description": "Core vulnerability scanning operations"
        },
        {
            "name": "Progress Tracking", 
            "description": "Monitor scan progress and status"
        },
        {
            "name": "Results & Reports",
            "description": "Retrieve and export scan results"
        },
        {
            "name": "Cache Management",
            "description": "Manage npm version resolution cache"
        },
        {
            "name": "System",
            "description": "Health checks and system information"
        }
    ]
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Input validation middleware
app.middleware("http")(validate_scan_request)
app.middleware("http")(validate_path_parameters)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "img-src 'self' data: fastapi.tiangolo.com; "
        "font-src 'self' cdn.jsdelivr.net"
    )
    
    # Add rate limit headers if available
    if hasattr(request.state, 'rate_limit_remaining'):
        response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)
    
    return response

# Trusted host configuration for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts_list
)

# CORS configuration using settings
# TODO: Refine CORS settings for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Service factory functions for dependency injection
def get_scan_service(state: AppState = Depends(get_app_state)) -> ScanService:
    """Get scan service instance"""
    return ScanService(state)

@app.post(
    "/scan", 
    response_model=dict[str, str],
    summary="Start Vulnerability Scan",
    description="""
    **Start a comprehensive vulnerability scan of software dependencies**
    
    This endpoint initiates an asynchronous vulnerability scan that analyzes uploaded dependency files
    for known security vulnerabilities using the OSV.dev database.
    
    ### Supported Workflows
    1. **Upload manifest files** (package.json, requirements.txt) for direct dependency analysis
    2. **Upload lockfiles** (package-lock.json, poetry.lock) for complete dependency tree analysis
    3. **Mixed uploads** for consistency checking and enhanced analysis
    
    ### Enhanced Features
    - **Version Resolution**: Resolve version ranges to exact versions for better accuracy
    - **Consistency Checking**: Compare manifest vs lockfile results with detailed analysis
    - **Transitive Dependencies**: Build complete dependency trees from manifest files
    - **Cache Control**: Option to bypass cache for fresh results
    
    ### Response
    Returns a job ID for tracking scan progress. Use the WebSocket endpoint `/ws/{job_id}` 
    for real-time progress updates or poll `/status/{job_id}` for status checks.
    
    ### Rate Limiting
    This endpoint is rate-limited to 10 requests per minute per IP address.
    """,
    responses={
        200: {
            "description": "Scan started successfully",
            "content": {
                "application/json": {
                    "example": {"job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
                }
            }
        },
        400: {
            "description": "Invalid request - missing files or invalid format",
            "content": {
                "application/json": {
                    "example": {"detail": "No supported dependency files found"}
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {"detail": "Rate limit exceeded. Please try again later."}
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "An unexpected error occurred during scan initialization"}
                }
            }
        }
    },
    tags=["Scanning"]
)
async def start_scan(
    scan_request: ScanRequest, 
    scan_service: ScanService = Depends(get_scan_service),
    _: None = Depends(check_rate_limit)
):
    """Start a new vulnerability scan"""
    try:
        job_id = await scan_service.start_scan(scan_request)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get(
    "/status/{job_id}", 
    response_model=ScanProgress,
    summary="Get Scan Status",
    description="""
    **Monitor the progress and status of a vulnerability scan**
    
    This endpoint provides real-time information about a scan's progress, including:
    - Current processing step and percentage complete
    - Number of dependencies processed and vulnerabilities found
    - Estimated completion time and error details if applicable
    
    ### Status Values
    - `pending` - Scan queued but not yet started
    - `running` - Actively scanning dependencies
    - `completed` - Scan finished successfully
    - `failed` - Scan encountered an error
    
    ### Rate Limiting
    This endpoint is rate-limited to prevent excessive polling.
    """,
    responses={
        200: {
            "description": "Scan status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "status": "running",
                        "progress_percent": 75,
                        "current_step": "Analyzing vulnerabilities",
                        "total_dependencies": 127,
                        "scanned_dependencies": 95,
                        "vulnerabilities_found": 3,
                        "started_at": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        404: {
            "description": "Job not found or expired",
            "content": {
                "application/json": {
                    "example": {"detail": "Job not found"}
                }
            }
        }
    },
    tags=["Progress Tracking"]
)
async def get_scan_status(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service),
    _: None = Depends(check_rate_limit)
):
    """Get current status and progress of a scan"""
    progress = scan_service.get_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress

@app.get(
    "/report/{job_id}", 
    response_model=Report,
    summary="Get Scan Report",
    description="""
    **Retrieve the complete vulnerability scan report**
    
    This endpoint returns the full scan results including:
    - Complete list of all dependencies analyzed
    - Detailed vulnerability information with severity levels
    - Scan metadata and statistics
    - Suppressed vulnerabilities and stale package warnings
    
    ### Report Availability
    Reports are only available after the scan status is `completed`. 
    Use the `/status/{job_id}` endpoint to monitor scan progress.
    
    ### Report Contents
    - **Dependencies**: Complete dependency tree with version information
    - **Vulnerabilities**: CVE details, severity levels, and fix recommendations  
    - **Statistics**: Total counts, vulnerability distribution, and scan options used
    - **Metadata**: Scan timestamp, ecosystems analyzed, and processing details
    """,
    responses={
        200: {
            "description": "Scan report retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "status": "completed",
                        "total_dependencies": 127,
                        "vulnerable_count": 5,
                        "vulnerable_packages": [
                            {
                                "package": "lodash",
                                "version": "4.17.15",
                                "ecosystem": "npm",
                                "vulnerability_id": "GHSA-jf85-cpcp-j695",
                                "severity": "HIGH",
                                "cve_ids": ["CVE-2020-8203"],
                                "summary": "Prototype Pollution in lodash",
                                "fixed_range": ">=4.17.19"
                            }
                        ],
                        "dependencies": [],
                        "suppressed_count": 0,
                        "meta": {
                            "generated_at": "2024-01-15T10:35:22Z",
                            "ecosystems": ["npm"],
                            "scan_options": {
                                "include_dev_dependencies": True,
                                "ignore_severities": []
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Report not found or scan not completed",
            "content": {
                "application/json": {
                    "example": {"detail": "Report not found or scan not completed"}
                }
            }
        }
    },
    tags=["Results & Reports"]
)
async def get_scan_report(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Get the final scan report"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or scan not completed")
    return report

@app.get(
    "/export/{job_id}.json",
    summary="Export JSON Report",
    description="""
    **Download scan report as a JSON file**
    
    This endpoint streams the complete scan report as a downloadable JSON file.
    The response includes proper Content-Disposition headers for browser downloads.
    
    ### Use Cases
    - Programmatic integration with other security tools
    - Long-term storage and archival
    - Data analysis and custom reporting
    - CI/CD pipeline integration
    
    ### File Format
    Standard JSON format with the same structure as the `/report/{job_id}` endpoint,
    but optimized for file download with appropriate MIME types.
    """,
    responses={
        200: {
            "description": "JSON report file download",
            "content": {
                "application/json": {
                    "example": "Binary file download with filename: scan-report-{job_id}.json"
                }
            }
        },
        404: {
            "description": "Report not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Report not found"}
                }
            }
        }
    },
    tags=["Results & Reports"]
)
async def export_json_report(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Export scan report as JSON file"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ExportService.export_json_streaming(report, job_id)

@app.get(
    "/export/{job_id}.csv",
    summary="Export CSV Report",
    description="""
    **Download scan report as a CSV file**
    
    This endpoint exports vulnerability findings in CSV format for easy analysis
    in spreadsheet applications and data analysis tools.
    
    ### CSV Structure
    The CSV includes the following columns:
    - Package name and version
    - Vulnerability ID (GHSA/CVE)
    - Severity level
    - Summary and details
    - Fixed version range
    - Advisory URL
    - Publication and modification dates
    
    ### Use Cases
    - Spreadsheet analysis and reporting
    - Integration with business intelligence tools
    - Compliance reporting
    - Risk assessment workflows
    """,
    responses={
        200: {
            "description": "CSV report file download",
            "content": {
                "text/csv": {
                    "example": "Binary file download with filename: scan-report-{job_id}.csv"
                }
            }
        },
        404: {
            "description": "Report not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Report not found"}
                }
            }
        }
    },
    tags=["Results & Reports"]
)
async def export_csv_report(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Export scan report as CSV file"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ExportService.export_csv_streaming(report, job_id)

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    job_id: str, 
    state: AppState = Depends(get_app_state)
):
    """
    **WebSocket endpoint for real-time scan progress updates**
    
    This WebSocket connection provides live updates during vulnerability scanning:
    - Real-time progress percentage and current step information
    - Immediate notification of scan completion or errors  
    - Bidirectional keepalive to maintain connection stability
    
    ### Connection Protocol
    1. Connect to `/ws/{job_id}` where job_id is from the `/scan` endpoint
    2. Server immediately sends current progress if scan is active
    3. Send any message as keepalive to maintain connection
    4. Server sends progress updates as JSON messages
    
    ### Message Format
    ```json
    {
        "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "status": "running", 
        "progress_percent": 45,
        "current_step": "Resolving dependencies",
        "scanned_dependencies": 23,
        "vulnerabilities_found": 1
    }
    ```
    
    ### Error Handling
    Connection automatically closes on scan completion or client disconnect.
    Use exponential backoff for reconnection attempts.
    """
    await websocket.accept()
    scan_service = ScanService(state)
    
    # Add to active connections
    if job_id not in state.active_connections:
        state.active_connections[job_id] = []
    state.active_connections[job_id].append(websocket)
    
    try:
        # Send current progress if available
        progress = scan_service.get_progress(job_id)
        if progress:
            await websocket.send_json(progress.model_dump())
        
        # Keep connection alive
        while True:
            # Wait for any message (keepalive)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        # Remove from active connections
        if job_id in state.active_connections:
            state.active_connections[job_id].remove(websocket)
            if not state.active_connections[job_id]:
                del state.active_connections[job_id]

@app.get(
    "/health",
    summary="Health Check",
    description="""
    **System health and availability check**
    
    This endpoint provides a quick health status check for the DepScan API service.
    Use this endpoint for:
    
    ### Monitoring Use Cases
    - Load balancer health checks
    - Service discovery and registration
    - Monitoring system integration
    - Basic API availability verification
    
    ### Response
    Returns current system status and timestamp for uptime tracking.
    """,
    responses={
        200: {
            "description": "Service is healthy and operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T10:30:00.123456"
                    }
                }
            }
        }
    },
    tags=["System"]
)
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post(
    "/admin/cache/clear",
    summary="Clear Version Cache",
    description="""
    **Clear the NPM version resolution cache**
    
    This administrative endpoint clears all cached NPM version resolution data,
    forcing fresh lookups from the NPM registry for subsequent scans.
    
    ### Use Cases
    - Clear stale version data after NPM registry updates
    - Development and testing scenarios
    - Troubleshooting version resolution issues
    - Periodic cache maintenance
    
    ### Impact
    - Next scans will fetch fresh version data from NPM registry
    - May temporarily increase scan times until cache rebuilds
    - No impact on completed scan reports
    """,
    responses={
        200: {
            "description": "Cache cleared successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "NPM version resolution cache cleared successfully",
                        "timestamp": 1705310400.0,
                        "cache_type": "global"
                    }
                }
            }
        },
        500: {
            "description": "Cache clear operation failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to clear cache: Permission denied"}
                }
            }
        }
    },
    tags=["Cache Management"]
)
async def clear_version_cache():
    """
    Clear the npm version resolution cache
    
    This endpoint clears all cached npm version resolution data.
    Useful for development, testing, or forcing fresh version lookups.
    """
    try:
        # Clear the global cache
        PackageVersionResolver.clear_global_cache()
        
        return {
            "success": True,
            "message": "NPM version resolution cache cleared successfully",
            "timestamp": time.time(),
            "cache_type": "global"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@app.get(
    "/admin/cache/stats",
    summary="Get Cache Statistics",
    description="""
    **Retrieve NPM version resolution cache statistics**
    
    This endpoint provides detailed information about the current state
    of the version resolution cache, including:
    
    ### Statistics Provided
    - Total number of cached entries
    - Cache hit/miss ratios
    - Memory usage and performance metrics
    - Entry age distribution and expiration info
    
    ### Monitoring Use Cases
    - Performance optimization and tuning
    - Cache efficiency analysis
    - Capacity planning
    - Troubleshooting version resolution issues
    """,
    responses={
        200: {
            "description": "Cache statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "cache_stats": {
                            "total_entries": 1247,
                            "hit_ratio": 0.87,
                            "average_age_seconds": 1800,
                            "expired_entries": 23
                        },
                        "timestamp": 1705310400.0
                    }
                }
            }
        },
        500: {
            "description": "Failed to retrieve cache statistics",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to get cache stats: Internal error"}
                }
            }
        }
    },
    tags=["Cache Management"]
)
async def get_cache_stats():
    """
    Get npm version resolution cache statistics
    
    Returns information about the current state of the version resolution cache.
    """
    try:
        stats = PackageVersionResolver.get_global_cache_stats()
        
        return {
            "cache_stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@app.post(
    "/admin/cache/cleanup",
    summary="Clean Expired Cache",
    description="""
    **Remove expired entries from the NPM version resolution cache**
    
    This maintenance endpoint performs selective cache cleanup by removing
    only expired entries while preserving valid cached data.
    
    ### Cleanup Process
    - Identifies entries older than the configured TTL (1 hour default)
    - Removes expired entries to free memory
    - Preserves valid cache entries for continued performance
    - Returns detailed cleanup statistics
    
    ### Benefits
    - Maintains cache performance without full reset
    - Reduces memory usage from stale entries
    - Automated maintenance without service disruption
    - Ideal for scheduled maintenance tasks
    """,
    responses={
        200: {
            "description": "Cache cleanup completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Cleaned up 45 expired cache entries",
                        "expired_entries": 45,
                        "remaining_entries": 1202,
                        "timestamp": 1705310400.0
                    }
                }
            }
        },
        500: {
            "description": "Cache cleanup operation failed",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to cleanup cache: Access denied"}
                }
            }
        }
    },
    tags=["Cache Management"]
)
async def cleanup_expired_cache():
    """
    Clean up expired entries from the npm version resolution cache
    
    This endpoint removes only expired cache entries while keeping valid ones.
    """
    try:
        from ..core.resolver.utils.npm_version_resolver import _GLOBAL_VERSION_CACHE
        import time
        
        current_time = time.time()
        default_ttl = 3600  # 1 hour default
        expired_keys = []
        
        for key, cache_data in _GLOBAL_VERSION_CACHE.items():
            age = current_time - cache_data.get("timestamp", 0)
            if age >= default_ttl:
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            del _GLOBAL_VERSION_CACHE[key]
        
        return {
            "success": True,
            "message": f"Cleaned up {len(expired_keys)} expired cache entries",
            "expired_entries": len(expired_keys),
            "remaining_entries": len(_GLOBAL_VERSION_CACHE),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup cache: {str(e)}")

@app.get("/")
async def read_root():
    """Root endpoint - serve React app in production, API info in development"""
    # Check if React build exists
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist" / "index.html"
    
    if frontend_dist.exists():
        return FileResponse(frontend_dist)
    else:
        return {
            "message": "DepScan API Server",
            "version": "1.0.0",
            "docs_url": "/docs",
            "frontend_available": False
        }

# Serve static files if React build exists
frontend_dist_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dist_dir)), name="static")

