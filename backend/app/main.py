from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from .models import ScanRequest, ScanProgress, Report
from .services.app_state import AppState, get_app_state
from .services.scan_service import ScanService
from .services.export_service import ExportService

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
    description="Dependency Vulnerability Scanner REST API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service factory functions for dependency injection
def get_scan_service(state: AppState = Depends(get_app_state)) -> ScanService:
    """Get scan service instance"""
    return ScanService(state)

@app.post("/scan", response_model=dict[str, str])
async def start_scan(
    scan_request: ScanRequest, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Start a new vulnerability scan"""
    try:
        job_id = await scan_service.start_scan(scan_request)
        return {"job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status/{job_id}", response_model=ScanProgress)
async def get_scan_status(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Get current status and progress of a scan"""
    progress = scan_service.get_progress(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Job not found")
    return progress

@app.get("/report/{job_id}", response_model=Report)
async def get_scan_report(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Get the final scan report"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or scan not completed")
    return report

@app.get("/export/{job_id}.json")
async def export_json_report(
    job_id: str, 
    scan_service: ScanService = Depends(get_scan_service)
):
    """Export scan report as JSON file"""
    report = scan_service.get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ExportService.export_json_streaming(report, job_id)

@app.get("/export/{job_id}.csv")
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
    """WebSocket endpoint for real-time scan progress"""
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
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

