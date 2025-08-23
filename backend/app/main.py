from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
import tempfile
import os

from .models import ScanRequest, ScanProgress, Report, JobStatus, ScanOptions
from .resolver import PythonResolver, JavaScriptResolver
from .scanner import OSVScanner

app = FastAPI(
    title="DepScan API",
    description="Dependency Vulnerability Scanner REST API",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for managing scan jobs
scan_jobs: Dict[str, ScanProgress] = {}
scan_results: Dict[str, Report] = {}
active_connections: Dict[str, List[WebSocket]] = {}

# Initialize resolvers and scanner
python_resolver = PythonResolver()
js_resolver = JavaScriptResolver()
osv_scanner = OSVScanner()

class ScanManager:
    """Manages vulnerability scanning jobs"""
    
    async def start_scan(self, scan_request: ScanRequest) -> str:
        """Start a new vulnerability scan"""
        job_id = str(uuid.uuid4())
        
        # Initialize job progress
        progress = ScanProgress(
            job_id=job_id,
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_step="Initializing scan...",
            started_at=datetime.now()
        )
        scan_jobs[job_id] = progress
        
        # Start background scan
        asyncio.create_task(self._run_scan(job_id, scan_request))
        
        return job_id
    
    async def _run_scan(self, job_id: str, scan_request: ScanRequest):
        """Run the actual vulnerability scan"""
        try:
            progress = scan_jobs[job_id]
            progress.status = JobStatus.RUNNING
            await self._broadcast_progress(job_id, progress)
            
            # Resolve dependencies
            progress.current_step = "Resolving dependencies..."
            progress.progress_percent = 10.0
            await self._broadcast_progress(job_id, progress)
            
            all_dependencies = []
            ecosystems_found = []
            
            if scan_request.repo_path:
                # Scan from repository
                repo_path = scan_request.repo_path
                
                # Try Python dependencies
                try:
                    py_deps = await python_resolver.resolve_dependencies(repo_path)
                    all_dependencies.extend(py_deps)
                    ecosystems_found.append("Python")
                except Exception:
                    pass
                
                # Try JavaScript dependencies
                try:
                    js_deps = await js_resolver.resolve_dependencies(repo_path)
                    all_dependencies.extend(js_deps)
                    ecosystems_found.append("JavaScript")
                except Exception:
                    pass
            
            elif scan_request.manifest_files:
                # Scan from uploaded files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Try Python files
                    py_files = {k: v for k, v in scan_request.manifest_files.items() 
                              if k in ["requirements.txt", "poetry.lock", "Pipfile.lock", "pyproject.toml"]}
                    if py_files:
                        try:
                            py_deps = await python_resolver.resolve_dependencies(None, py_files)
                            all_dependencies.extend(py_deps)
                            ecosystems_found.append("Python")
                        except Exception:
                            pass
                    
                    # Try JavaScript files
                    js_files = {k: v for k, v in scan_request.manifest_files.items()
                              if k in ["package.json", "package-lock.json", "yarn.lock"]}
                    if js_files:
                        try:
                            js_deps = await js_resolver.resolve_dependencies(None, js_files)
                            all_dependencies.extend(js_deps)
                            ecosystems_found.append("JavaScript")
                        except Exception:
                            pass
            
            if not all_dependencies:
                raise ValueError("No dependencies found to scan")
            
            # Filter dev dependencies if requested
            if not scan_request.options.include_dev_dependencies:
                all_dependencies = [dep for dep in all_dependencies if not dep.is_dev]
            
            progress.total_dependencies = len(all_dependencies)
            progress.current_step = f"Scanning {len(all_dependencies)} dependencies for vulnerabilities..."
            progress.progress_percent = 30.0
            await self._broadcast_progress(job_id, progress)
            
            # Scan for vulnerabilities
            vulnerabilities = await osv_scanner.scan_dependencies(all_dependencies)
            
            progress.vulnerabilities_found = len(vulnerabilities)
            progress.current_step = "Processing results..."
            progress.progress_percent = 80.0
            await self._broadcast_progress(job_id, progress)
            
            # Apply filters and ignore rules
            filtered_vulns = vulnerabilities
            suppressed_count = 0
            
            if scan_request.options.ignore_severities:
                filtered_vulns = [v for v in filtered_vulns 
                                if v.severity not in scan_request.options.ignore_severities]
            
            if scan_request.options.ignore_rules:
                final_vulns = []
                for vuln in filtered_vulns:
                    should_ignore = False
                    for rule in scan_request.options.ignore_rules:
                        if (rule.rule_type == "vulnerability" and 
                            rule.identifier in [vuln.vulnerability_id] + vuln.cve_ids):
                            should_ignore = True
                            break
                        elif (rule.rule_type == "package" and 
                              f"{vuln.package}@{vuln.version}" == rule.identifier):
                            should_ignore = True
                            break
                    
                    if should_ignore:
                        suppressed_count += 1
                    else:
                        final_vulns.append(vuln)
                
                filtered_vulns = final_vulns
            
            # Create final report
            report = Report(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                total_dependencies=len(all_dependencies),
                vulnerable_count=len(set((v.package, v.version) for v in filtered_vulns)),
                vulnerable_packages=filtered_vulns,
                dependencies=all_dependencies,
                suppressed_count=suppressed_count,
                meta={
                    "generated_at": datetime.now().isoformat(),
                    "ecosystems": ecosystems_found,
                    "scan_options": scan_request.options.dict()
                }
            )
            
            # Store results
            scan_results[job_id] = report
            
            # Update final progress
            progress.status = JobStatus.COMPLETED
            progress.current_step = "Scan completed"
            progress.progress_percent = 100.0
            progress.completed_at = datetime.now()
            await self._broadcast_progress(job_id, progress)
            
        except Exception as e:
            # Handle scan failure
            progress = scan_jobs.get(job_id)
            if progress:
                progress.status = JobStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()
                await self._broadcast_progress(job_id, progress)
    
    async def _broadcast_progress(self, job_id: str, progress: ScanProgress):
        """Broadcast progress to all connected WebSocket clients"""
        if job_id in active_connections:
            message = progress.dict()
            disconnected = []
            
            for websocket in active_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Remove disconnected clients
            for ws in disconnected:
                active_connections[job_id].remove(ws)
    
    def get_progress(self, job_id: str) -> Optional[ScanProgress]:
        """Get current progress for a job"""
        return scan_jobs.get(job_id)
    
    def get_report(self, job_id: str) -> Optional[Report]:
        """Get final report for a completed job"""
        return scan_results.get(job_id)

scan_manager = ScanManager()

@app.post("/scan", response_model=Dict[str, str])
async def start_scan(scan_request: ScanRequest):
    """Start a new vulnerability scan"""
    try:
        job_id = await scan_manager.start_scan(scan_request)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status/{job_id}", response_model=ScanProgress)
async def get_scan_status(job_id: str):
    """Get current status and progress of a scan"""
    progress = scan_manager.get_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress

@app.get("/report/{job_id}", response_model=Report)
async def get_scan_report(job_id: str):
    """Get the final scan report"""
    report = scan_manager.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or scan not completed")
    return report

@app.get("/export/{job_id}.json")
async def export_json_report(job_id: str):
    """Export scan report as JSON file"""
    report = scan_manager.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(report.dict(), f, indent=2, default=str)
        temp_path = f.name
    
    return FileResponse(
        temp_path,
        media_type='application/json',
        filename=f"depscan_report_{job_id}.json"
    )

@app.get("/export/{job_id}.csv")
async def export_csv_report(job_id: str):
    """Export scan report as CSV file"""
    report = scan_manager.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Create CSV content
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Package", "Version", "Ecosystem", "Severity", "CVE IDs", "Vulnerability ID",
        "Summary", "Fixed Range", "Advisory URL", "Published", "Modified"
    ])
    
    # Write vulnerability data
    for vuln in report.vulnerable_packages:
        writer.writerow([
            vuln.package,
            vuln.version,
            vuln.ecosystem,
            vuln.severity.value if vuln.severity else "",
            ";".join(vuln.cve_ids),
            vuln.vulnerability_id,
            vuln.summary,
            vuln.fixed_range or "",
            vuln.advisory_url or "",
            vuln.published.isoformat() if vuln.published else "",
            vuln.modified.isoformat() if vuln.modified else ""
        ])
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
        f.write(output.getvalue())
        temp_path = f.name
    
    return FileResponse(
        temp_path,
        media_type='text/csv',
        filename=f"depscan_report_{job_id}.csv"
    )

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time scan progress"""
    await websocket.accept()
    
    # Add to active connections
    if job_id not in active_connections:
        active_connections[job_id] = []
    active_connections[job_id].append(websocket)
    
    try:
        # Send current progress if available
        progress = scan_manager.get_progress(job_id)
        if progress:
            await websocket.send_json(progress.dict())
        
        # Keep connection alive
        while True:
            # Wait for any message (keepalive)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        # Remove from active connections
        if job_id in active_connections:
            active_connections[job_id].remove(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

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

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    await osv_scanner.close()
    
    # Clean up temporary files
    for connections_list in active_connections.values():
        for ws in connections_list:
            try:
                await ws.close()
            except:
                pass