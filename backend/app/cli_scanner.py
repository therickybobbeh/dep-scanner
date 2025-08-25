"""
CLI Scanner orchestrator - handles progress display and user interaction
"""
import logging
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from ..core_scanner import CoreScanner
    from .models import ScanOptions, Report
except ImportError:
    from core_scanner import CoreScanner
    from app.models import ScanOptions, Report


class DepScanner:
    """CLI scanner with Rich progress display"""
    
    def __init__(self):
        self.core_scanner = CoreScanner()
        self.console = Console()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.current_progress = None
    
    async def scan_repository(self, repo_path: str, options: ScanOptions) -> Report:
        """Scan a repository for vulnerabilities with CLI progress display"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Starting scan...", total=None)
            self.current_progress = progress
            self.current_task = task
            
            try:
                report = await self.core_scanner.scan_repository(
                    repo_path=repo_path,
                    options=options,
                    progress_callback=self._update_progress
                )
                
                progress.remove_task(task)
                self.console.print("\n[green]Scan completed![/green]")
                return report
                
            except Exception as e:
                progress.remove_task(task)
                raise e
    
    def _update_progress(self, message: str):
        """Update progress display"""
        if self.current_progress and hasattr(self, 'current_task'):
            if message.startswith("Found") and ("Python" in message or "JavaScript" in message):
                self.console.print(message)
            elif message.startswith("Warning"):
                self.console.print(f"[yellow]{message}[/yellow]")
            else:
                self.current_progress.update(self.current_task, description=message)