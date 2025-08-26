"""
CLI Scanner orchestrator - handles progress display and user interaction
"""
import logging
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from ..core.core_scanner import CoreScanner
    from ..core.models import ScanOptions, Report
except ImportError:
    from backend.core.core_scanner import CoreScanner
    from backend.core.models import ScanOptions, Report


class DepScanner:
    """CLI scanner with Rich progress display"""
    
    def __init__(self, verbose: bool = False):
        self.core_scanner = CoreScanner()
        self.console = Console()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.current_progress = None
        self.verbose = verbose
    
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
                # Convert repository scan to manifest file scan for consistency
                manifest_files = await self._read_repository_manifest_files(repo_path)
                
                if not manifest_files:
                    raise ValueError("No supported dependency files found in repository")
                
                # Use the enhanced manifest file processing (includes lock file generation)
                report = await self.core_scanner.scan_manifest_files(
                    manifest_files=manifest_files,
                    options=options,
                    progress_callback=self._update_progress
                )
                
                progress.remove_task(task)
                self.console.print("\n[green]Scan completed![/green]")
                return report
                
            except Exception as e:
                progress.remove_task(task)
                raise e
    
    async def _read_repository_manifest_files(self, repo_path: str) -> dict[str, str]:
        """
        Read manifest files from repository directory
        
        Args:
            repo_path: Path to repository directory
            
        Returns:
            Dict of {filename: content} for supported manifest files
        """
        from pathlib import Path
        
        repo_path_obj = Path(repo_path)
        manifest_files = {}
        
        # List of supported dependency files to look for
        supported_files = [
            # JavaScript/NPM
            "package.json",
            # Note: We intentionally skip package-lock.json to force regeneration for consistency
            "yarn.lock",
            
            # Python
            "requirements.txt", 
            "pyproject.toml",
            "poetry.lock",
            "Pipfile.lock"
        ]
        
        for filename in supported_files:
            file_path = repo_path_obj / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    manifest_files[filename] = content
                    if self.verbose:
                        self.console.print(f"[dim]Found manifest file: {filename}[/dim]")
                except Exception as e:
                    if self.verbose:
                        self.console.print(f"[yellow]Warning: Could not read {filename}: {e}[/yellow]")
        
        return manifest_files
    
    def _update_progress(self, message: str):
        """Update progress display"""
        if self.current_progress and hasattr(self, 'current_task'):
            # Always show file processing messages in verbose mode
            if self.verbose and ("processing" in message.lower() or "scanning" in message.lower() or "found" in message.lower()):
                self.console.print(f"[dim]{message}[/dim]")
            
            if message.startswith("Found") and ("Python" in message or "JavaScript" in message):
                self.console.print(message)
            elif message.startswith("Warning"):
                self.console.print(f"[yellow]{message}[/yellow]")
            elif message.startswith("Processing file:") or message.startswith("Scanning file:"):
                # Always show individual file processing in verbose mode
                if self.verbose:
                    self.console.print(f"[cyan]{message}[/cyan]")
            else:
                self.current_progress.update(self.current_task, description=message)