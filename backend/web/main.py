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

from ..core.models import ScanRequest, ScanProgress
from .services.app_state import AppState, get_app_state
from .services.scan_service import ScanService
from .services.consistency_service import ConsistencyService
from .services.rate_limiter import check_rate_limit, check_status_rate_limit
from ..core.config import settings

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
    - 🚀 **Lock File Generation**: Automatic generation of lock files for consistency
    - 📤 **Export Options**: JSON and CSV report exports
    
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

# Simplified middleware - removed complex validation since CLI handles it

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
    _: None = Depends(check_status_rate_limit)
):
    """Get current status and progress of a scan"""
    progress = scan_service.get_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress

@app.get(
    "/report/{job_id}",
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
    """Get the CLI JSON report directly"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or scan not completed")
    return report

# Export endpoints removed - CLI JSON is the standard format
# Frontend can download /report/{job_id} directly as JSON

# WebSocket endpoint removed for simplicity
# Frontend can poll /status/{job_id} for progress updates

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
    "/validate-consistency",
    summary="Validate Package.json vs Package-lock.json Consistency",
    description="""
    **Validate consistency between package.json and package-lock.json files**
    
    This endpoint compares vulnerability scan results from package.json and package-lock.json
    to ensure they produce consistent findings. This is important because:
    
    - package.json contains version ranges (^4.17.15, ~1.2.3)  
    - package-lock.json contains exact resolved versions (4.17.15)
    - Different parsing logic might produce different vulnerability results
    
    ### What is Validated
    - Same vulnerability counts for direct dependencies
    - Same vulnerable packages identified
    - Consistent severity distributions
    - Expected differences (transitive deps) are explained
    
    ### When to Use
    - Before deploying to production
    - When version ranges might resolve to different versions  
    - To verify scanner consistency
    - When scan results seem unexpected
    
    ### Response
    Returns detailed analysis including:
    - Overall consistency status
    - Specific differences found
    - Actionable recommendations
    - Both individual scan results for comparison
    """,
    responses={
        200: {
            "description": "Consistency validation completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "is_consistent": True,
                        "analysis": {
                            "overall": {"is_consistent": True},
                            "metrics": {"package_json": {"vulnerabilities": 3}, "package_lock": {"vulnerabilities": 3}}
                        },
                        "recommendations": ["✅ Scan results are consistent"],
                        "warnings": [],
                        "errors": []
                    }
                }
            }
        },
        400: {
            "description": "Invalid request or missing required files",
            "content": {
                "application/json": {
                    "example": {"detail": "Both package.json and package-lock.json are required"}
                }
            }
        }
    },
    tags=["Consistency Validation"]
)
async def validate_consistency(scan_request: ScanRequest):
    """Validate consistency between package.json and package-lock.json scan results"""
    try:
        # Validate that both files are provided
        manifest_files = scan_request.manifest_files or {}
        has_package_json = 'package.json' in manifest_files
        has_package_lock = 'package-lock.json' in manifest_files
        
        if not (has_package_json and has_package_lock):
            raise HTTPException(
                status_code=400, 
                detail="Both package.json and package-lock.json files are required for consistency validation"
            )
        
        # Run consistency validation
        result = await ConsistencyService.validate_consistency(
            manifest_files=manifest_files,
            include_dev=scan_request.options.include_dev_dependencies,
            ignore_severities=[sev.value for sev in scan_request.options.ignore_severities]
        )
        
        # Return validation results
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consistency validation failed: {str(e)}")


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
