"""
CLI Scanner orchestrator - handles progress display and user interaction
"""
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn

try:
    from ..core.core_scanner import CoreScanner
    from ..core.models import ScanOptions, Report
except ImportError:
    from backend.core.core_scanner import CoreScanner
    from backend.core.models import ScanOptions, Report


class DepScanner:
    """CLI scanner with enhanced Rich progress display"""
    
    def __init__(self, verbose: bool = False):
        self.core_scanner = CoreScanner()
        self.console = Console()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.current_progress = None
        self.current_task = None
        self.verbose = verbose
        
        # Progress stages with percentage ranges
        self.progress_stages = {
            "init": (0, 10),           # Initial setup and validation
            "discovery": (10, 30),     # File discovery and reading  
            "generation": (30, 50),    # Lock file generation (npm/pip-tools)
            "parsing": (50, 70),       # Dependency parsing and tree building
            "scanning": (70, 90),      # Vulnerability scanning (OSV API)
            "reporting": (90, 100)     # Report generation and finalization
        }
    
    @contextmanager
    def _suppress_logging(self):
        """Temporarily suppress INFO level logging to prevent interference with progress bar"""
        # Get root logger and current level
        root_logger = logging.getLogger()
        original_level = root_logger.level
        
        # Temporarily raise level to WARNING to hide INFO messages
        if original_level <= logging.INFO:
            root_logger.setLevel(logging.WARNING)
        
        try:
            yield
        finally:
            # Restore original level
            root_logger.setLevel(original_level)
    
    async def scan_path(self, path: str, options: ScanOptions) -> Report:
        """Scan either a directory or individual dependency file"""
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        if path_obj.is_file():
            return await self.scan_single_file(str(path_obj), options)
        elif path_obj.is_dir():
            return await self.scan_repository(path, options)
        else:
            raise ValueError(f"Path must be a file or directory: {path}")
    
    async def scan_single_file(self, file_path: str, options: ScanOptions) -> Report:
        """Scan a single dependency file for vulnerabilities"""
        file_path_obj = Path(file_path)
        filename = file_path_obj.name
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task(f"Scanning {filename}...", total=100)
            self.current_progress = progress
            self.current_task = task
            
            try:
                # Stage 1: Initial validation (0-10%)
                self._update_progress_stage("init", 0.0)
                if self.verbose:
                    self.console.print(f"[dim]📁 Processing file: {filename}[/dim]")
                
                # Validate file format
                supported_files = [
                    # JavaScript
                    "package.json", "package-lock.json", "yarn.lock",
                    # Python  
                    "requirements.txt", "requirements.lock", "pyproject.toml", 
                    "poetry.lock", "Pipfile.lock", "Pipfile"
                ]
                
                if filename not in supported_files:
                    raise ValueError(f"Unsupported file format: {filename}")
                
                self._update_progress_stage("init", 1.0)
                
                # Stage 2: File reading (10-30%)
                self._update_progress_stage("discovery", 0.0)
                
                try:
                    content = file_path_obj.read_text(encoding='utf-8')
                    manifest_files = {filename: content}
                    
                    if self.verbose:
                        ecosystem = "JavaScript" if filename in ["package.json", "package-lock.json", "yarn.lock"] else "Python"
                        self.console.print(f"[dim]📦 Detected {ecosystem} dependency file[/dim]")
                    
                except Exception as e:
                    raise ValueError(f"Could not read file {filename}: {e}")
                
                self._update_progress_stage("discovery", 1.0)
                
                # Stage 3-6: Use existing manifest file processing (30-100%)
                with self._suppress_logging():
                    report = await self.core_scanner.scan_manifest_files(
                        manifest_files=manifest_files,
                        options=options,
                        progress_callback=self._update_progress_from_callback
                    )
                
                progress.update(task, completed=100)
                self.console.print("\n[green]✅ Scan completed![/green]")
                return report
                
            except Exception as e:
                progress.update(task, completed=0)
                raise e
    
    async def scan_repository(self, repo_path: str, options: ScanOptions) -> Report:
        """Scan a repository for vulnerabilities with enhanced progress display"""
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        ) as progress:
            task = progress.add_task("Scanning dependencies...", total=100)
            self.current_progress = progress
            self.current_task = task
            
            try:
                # Stage 1: Initial setup (0-10%)
                self._update_progress_stage("init", 0.0)
                if self.verbose:
                    self.console.print(f"[dim]📁 Scanning directory: {repo_path}[/dim]")
                self._update_progress_stage("init", 1.0)
                
                # Stage 2: File discovery (10-30%) 
                self._update_progress_stage("discovery", 0.0)
                manifest_files = await self._read_repository_manifest_files(repo_path)
                
                if not manifest_files:
                    raise ValueError("No supported dependency files found in repository")
                
                if self.verbose:
                    file_list = ", ".join(manifest_files.keys())
                    self.console.print(f"[dim]📦 Found files: {file_list}[/dim]")
                
                self._update_progress_stage("discovery", 1.0)
                
                # Stages 3-6: Use enhanced manifest file processing (30-100%)
                with self._suppress_logging():
                    report = await self.core_scanner.scan_manifest_files(
                        manifest_files=manifest_files,
                        options=options,
                        progress_callback=self._update_progress_from_callback
                    )
                
                progress.update(task, completed=100)
                self.console.print("\n[green]✅ Scan completed![/green]")
                return report
                
            except Exception as e:
                progress.update(task, completed=0)
                raise e
    
    async def _read_repository_manifest_files(self, repo_path: str) -> dict[str, str]:
        """
        Read manifest files from repository directory
        
        Args:
            repo_path: Path to repository directory
            
        Returns:
            Dict of {filename: content} for supported manifest files
        """
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
                        self.console.print(f"[dim]📄 Found manifest file: {filename}[/dim]")
                except Exception as e:
                    if self.verbose:
                        self.console.print(f"[yellow]⚠️  Warning: Could not read {filename}: {e}[/yellow]")
        
        return manifest_files
    
    def _update_progress_stage(self, stage: str, sub_progress: float):
        """Update progress within a specific stage"""
        if self.current_progress and self.current_task is not None:
            start, end = self.progress_stages[stage]
            current = start + (end - start) * max(0, min(1, sub_progress))
            self.current_progress.update(self.current_task, completed=current)
    
    def _update_progress_from_callback(self, message: str):
        """Handle progress updates from core scanner with stage mapping"""
        if self.current_progress and self.current_task is not None:
            
            # Map callback messages to progress stages
            if "generating" in message.lower() or "npm install" in message.lower() or "pip-compile" in message.lower():
                # Lock file generation stage (30-50%)
                if "running" in message.lower():
                    self._update_progress_stage("generation", 0.5)
                    if self.verbose:
                        self.console.print(f"[dim]⚙️  {message}[/dim]")
                elif "successfully" in message.lower():
                    self._update_progress_stage("generation", 1.0)
                    if self.verbose:
                        self.console.print(f"[dim]✅ {message}[/dim]")
                        
            elif "parsing" in message.lower() or "found" in message.lower() and "dependencies" in message.lower():
                # Dependency parsing stage (50-70%) 
                self._update_progress_stage("parsing", 0.7)
                if self.verbose:
                    self.console.print(f"[dim]📦 {message}[/dim]")
                    
            elif "scanning" in message.lower() or "vulnerability" in message.lower() or "osv" in message.lower():
                # Vulnerability scanning stage (70-90%)
                if "batch" in message.lower():
                    # Extract batch progress if available
                    try:
                        if "batch" in message.lower() and "/" in message:
                            parts = message.split("batch")[1].strip()
                            current, total = parts.split("/")[:2]
                            current = int(current.strip())
                            total = int(total.split()[0])
                            batch_progress = current / total
                            self._update_progress_stage("scanning", batch_progress)
                        else:
                            self._update_progress_stage("scanning", 0.5)
                    except:
                        self._update_progress_stage("scanning", 0.5)
                else:
                    self._update_progress_stage("scanning", 0.3)
                    
                if self.verbose:
                    self.console.print(f"[dim]🔒 {message}[/dim]")
                    
            elif "report" in message.lower() or "generating" in message.lower():
                # Report generation stage (90-100%)
                self._update_progress_stage("reporting", 0.5)
                if self.verbose:
                    self.console.print(f"[dim]📊 {message}[/dim]")
                    
            else:
                # General progress messages
                if self.verbose:
                    if message.startswith("Warning"):
                        self.console.print(f"[yellow]⚠️  {message}[/yellow]")
                    elif message.startswith("Found") and ("Python" in message or "JavaScript" in message):
                        self.console.print(f"[cyan]📦 {message}[/cyan]")
                    else:
                        self.console.print(f"[dim]{message}[/dim]")