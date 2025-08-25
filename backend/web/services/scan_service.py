"""Simplified scan service using core scanner"""
import asyncio
import uuid
from datetime import datetime
from fastapi import WebSocket

from ...core.core_scanner import CoreScanner
from ...core.models import ScanRequest, ScanProgress, Report, JobStatus
from .app_state import AppState


class ScanService:
    """Simplified service for managing vulnerability scanning jobs"""
    
    def __init__(self, state: AppState):
        self.state = state
        self.core_scanner = CoreScanner()
    
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
        self.state.scan_jobs[job_id] = progress
        
        # Start background scan
        asyncio.create_task(self._run_scan(job_id, scan_request))
        
        return job_id
    
    async def _run_scan(self, job_id: str, scan_request: ScanRequest):
        """Run the actual vulnerability scan using core scanner"""
        try:
            progress = self.state.scan_jobs[job_id]
            progress.status = JobStatus.RUNNING
            await self._broadcast_progress(job_id, progress)
            
            # Use core scanner to do the heavy lifting
            if scan_request.repo_path:
                report = await self.core_scanner.scan_repository(
                    repo_path=scan_request.repo_path,
                    options=scan_request.options,
                    progress_callback=lambda msg: asyncio.create_task(self._update_web_progress(job_id, msg))
                )
            elif scan_request.manifest_files:
                report = await self.core_scanner.scan_manifest_files(
                    manifest_files=scan_request.manifest_files,
                    options=scan_request.options,
                    progress_callback=lambda msg: asyncio.create_task(self._update_web_progress(job_id, msg))
                )
            else:
                raise ValueError("Either repo_path or manifest_files must be provided")
            
            # Update report with job_id from web service
            report.job_id = job_id
            
            # Update final progress
            progress.status = JobStatus.COMPLETED
            progress.current_step = "Scan completed"
            progress.progress_percent = 100.0
            progress.total_dependencies = report.total_dependencies
            progress.vulnerabilities_found = report.vulnerable_count
            progress.completed_at = datetime.now()
            
            # Store report and broadcast final progress
            self.state.scan_reports[job_id] = report
            await self._broadcast_progress(job_id, progress)
            
        except Exception as e:
            # Handle scan failure
            progress = self.state.scan_jobs.get(job_id)
            if progress:
                progress.status = JobStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()
                await self._broadcast_progress(job_id, progress)
    
    async def _update_web_progress(self, job_id: str, message: str):
        """Update web progress based on core scanner messages"""
        progress = self.state.scan_jobs.get(job_id)
        if not progress:
            return
            
        if "Resolving dependencies" in message:
            progress.progress_percent = 20.0
        elif "Scanning" in message and "dependencies" in message:
            progress.progress_percent = 60.0
        elif "completed" in message.lower():
            progress.progress_percent = 90.0
        
        progress.current_step = message
        await self._broadcast_progress(job_id, progress)
    
    async def _broadcast_progress(self, job_id: str, progress: ScanProgress):
        """Broadcast progress to connected WebSocket clients"""
        if job_id in self.state.active_connections:
            # Create a copy to avoid modification during iteration
            connections = list(self.state.active_connections[job_id])
            for websocket in connections:
                try:
                    await websocket.send_json(progress.model_dump())
                except Exception:
                    # Remove failed connections
                    self.state.active_connections[job_id].remove(websocket)
                    if not self.state.active_connections[job_id]:
                        del self.state.active_connections[job_id]
                        break
    
    def get_progress(self, job_id: str) -> ScanProgress | None:
        """Get current progress for a job"""
        return self.state.scan_jobs.get(job_id)
    
    def get_report(self, job_id: str) -> Report | None:
        """Get completed report for a job"""
        return self.state.scan_reports.get(job_id)