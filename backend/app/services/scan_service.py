"""Scan service for managing vulnerability scans"""
import asyncio
import uuid
import tempfile
from datetime import datetime
from fastapi import WebSocket

from ..models import ScanRequest, ScanProgress, Report, JobStatus
from .app_state import AppState


class ScanService:
    """Service for managing vulnerability scanning jobs"""
    
    def __init__(self, state: AppState):
        self.state = state
    
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
        """Run the actual vulnerability scan"""
        try:
            progress = self.state.scan_jobs[job_id]
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
                    py_deps = await self.state.python_resolver.resolve_dependencies(repo_path)
                    all_dependencies.extend(py_deps)
                    ecosystems_found.append("Python")
                except Exception:
                    pass
                
                # Try JavaScript dependencies
                try:
                    js_deps = await self.state.js_resolver.resolve_dependencies(repo_path)
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
                            py_deps = await self.state.python_resolver.resolve_dependencies(None, py_files)
                            all_dependencies.extend(py_deps)
                            ecosystems_found.append("Python")
                        except Exception:
                            pass
                    
                    # Try JavaScript files
                    js_files = {k: v for k, v in scan_request.manifest_files.items()
                              if k in ["package.json", "package-lock.json", "yarn.lock"]}
                    if js_files:
                        try:
                            js_deps = await self.state.js_resolver.resolve_dependencies(None, js_files)
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
            vulnerabilities = await self.state.osv_scanner.scan_dependencies(all_dependencies)
            
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
                    "scan_options": scan_request.options.model_dump()
                }
            )
            
            # Store results
            self.state.scan_results[job_id] = report
            
            # Update final progress
            progress.status = JobStatus.COMPLETED
            progress.current_step = "Scan completed"
            progress.progress_percent = 100.0
            progress.completed_at = datetime.now()
            await self._broadcast_progress(job_id, progress)
            
        except Exception as e:
            # Handle scan failure
            progress = self.state.scan_jobs.get(job_id)
            if progress:
                progress.status = JobStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()
                await self._broadcast_progress(job_id, progress)
    
    async def _broadcast_progress(self, job_id: str, progress: ScanProgress):
        """Broadcast progress to all connected WebSocket clients"""
        if job_id in self.state.active_connections:
            message = progress.model_dump()
            disconnected = []
            
            for websocket in self.state.active_connections[job_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Remove disconnected clients
            for ws in disconnected:
                self.state.active_connections[job_id].remove(ws)
    
    def get_progress(self, job_id: str) -> ScanProgress | None:
        """Get current progress for a job"""
        return self.state.scan_jobs.get(job_id)
    
    def get_report(self, job_id: str) -> Report | None:
        """Get final report for a completed job"""
        return self.state.scan_results.get(job_id)