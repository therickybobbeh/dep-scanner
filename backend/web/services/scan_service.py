"""Simplified scan service - thin wrapper around CLI"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from ...core.models import ScanRequest, ScanProgress, JobStatus
from .app_state import AppState
from .cli_service import CLIService


class ScanService:
    """Thin wrapper around CLI for web API"""
    
    def __init__(self, state: AppState):
        self.state = state
    
    async def start_scan(self, scan_request: ScanRequest) -> str:
        """Start a new CLI-based scan"""
        job_id = str(uuid.uuid4())
        
        # Initialize simple progress
        progress = ScanProgress(
            job_id=job_id,
            status=JobStatus.PENDING,
            progress_percent=0.0,
            current_step="Starting CLI scan...",
            started_at=datetime.now()
        )
        self.state.scan_jobs[job_id] = progress
        
        # Start CLI scan in background
        asyncio.create_task(self._run_cli_scan(job_id, scan_request))
        
        return job_id
    
    async def _run_cli_scan(self, job_id: str, scan_request: ScanRequest):
        """Run CLI scan and store results"""
        try:
            # Update status to running
            progress = self.state.scan_jobs[job_id]
            progress.status = JobStatus.RUNNING
            progress.current_step = "Initializing scan..."
            progress.progress_percent = 5.0
            
            # Create progress callback to update real-time progress
            async def progress_callback(message: str, percent: float | None):
                """Update progress in real-time from CLI"""
                current_progress = self.state.scan_jobs.get(job_id)
                if current_progress:
                    current_progress.current_step = message
                    if percent is not None:
                        current_progress.progress_percent = min(95.0, percent)  # Cap at 95% until completion
            
            # Run CLI scan with progress callback
            cli_result = await CLIService.run_cli_scan_async(
                path=scan_request.repo_path,
                manifest_files=scan_request.manifest_files,
                include_dev=scan_request.options.include_dev_dependencies,
                ignore_severities=[sev.value for sev in scan_request.options.ignore_severities],
                progress_callback=progress_callback
            )
            
            # Store CLI JSON result directly
            self.state.scan_reports[job_id] = cli_result
            
            # Update final progress
            progress.status = JobStatus.COMPLETED
            progress.current_step = "Scan completed"
            progress.progress_percent = 100.0
            progress.completed_at = datetime.now()
            
            # Set counts from CLI result
            scan_info = cli_result.get('scan_info', {})
            progress.total_dependencies = scan_info.get('total_dependencies', 0)
            progress.vulnerabilities_found = scan_info.get('vulnerable_packages', 0)
            
        except Exception as e:
            # Handle scan failure
            progress = self.state.scan_jobs.get(job_id)
            if progress:
                progress.status = JobStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()
    
    def get_progress(self, job_id: str) -> ScanProgress | None:
        """Get scan progress"""
        return self.state.scan_jobs.get(job_id)
    
    def get_report(self, job_id: str) -> Dict[str, Any] | None:
        """Get CLI JSON report directly"""
        return self.state.scan_reports.get(job_id)