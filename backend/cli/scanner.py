"""
CLI Scanner orchestrator - handles the main scanning logic
"""
import asyncio
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

try:
    from ..app.models import ScanOptions, Report, Dep, JobStatus
    from ..app.resolver import PythonResolver, JavaScriptResolver
    from ..app.scanner import OSVScanner
except ImportError:
    from app.models import ScanOptions, Report, Dep, JobStatus
    from app.resolver import PythonResolver, JavaScriptResolver
    from app.scanner import OSVScanner


class DepScanner:
    """Main scanner orchestrator"""
    
    def __init__(self):
        self.python_resolver = PythonResolver()
        self.js_resolver = JavaScriptResolver()
        self.osv_scanner = OSVScanner()
        self.console = Console()
    
    async def scan_repository(self, repo_path: str, options: ScanOptions) -> Report:
        """Scan a repository for vulnerabilities"""
        repo_path_obj = Path(repo_path)
        
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        
        all_dependencies = []
        ecosystems_found = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            
            # Try to resolve Python dependencies
            task = progress.add_task("Detecting Python dependencies...", total=None)
            try:
                py_deps = await self.python_resolver.resolve_dependencies(repo_path)
                if py_deps:
                    all_dependencies.extend(py_deps)
                    ecosystems_found.append("Python")
                    self.console.print(f"Found {len(py_deps)} Python dependencies")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not resolve Python dependencies: {e}[/yellow]")
            
            progress.update(task, description="Detecting JavaScript dependencies...")
            # Try to resolve JavaScript dependencies  
            try:
                js_deps = await self.js_resolver.resolve_dependencies(repo_path)
                if js_deps:
                    all_dependencies.extend(js_deps)
                    ecosystems_found.append("JavaScript")
                    self.console.print(f"Found {len(js_deps)} JavaScript dependencies")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not resolve JavaScript dependencies: {e}[/yellow]")
            
            progress.remove_task(task)
        
        if not all_dependencies:
            raise ValueError("No supported dependency files found. Supported: package.json, requirements.txt, pyproject.toml")
        
        self.console.print(f"Found dependencies in: {', '.join(ecosystems_found)}")
        self.console.print(f"Scanning {len(all_dependencies)} dependencies...")
        
        # Scan for vulnerabilities with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            scan_task = progress.add_task("Scanning repository...", total=None)
            vulnerable_packages = await self.osv_scanner.scan_dependencies(all_dependencies)
            progress.remove_task(scan_task)
        
        self.console.print("\n[green]Scan completed![/green]")
        
        # Filter by severity if specified
        if options.ignore_severities:
            vulnerable_packages = [
                vp for vp in vulnerable_packages 
                if not vp.severity or vp.severity not in options.ignore_severities
            ]
        
        from uuid import uuid4
        
        return Report(
            job_id=str(uuid4()),
            status=JobStatus.COMPLETED,
            total_dependencies=len(all_dependencies),
            vulnerable_count=len(vulnerable_packages),
            vulnerable_packages=vulnerable_packages,
            dependencies=all_dependencies,
            meta={"ecosystems": ecosystems_found}
        )
    
    def print_summary(self, report: Report) -> None:
        """Print a summary of the scan results"""
        vulnerable_count = len(report.vulnerable_packages)
        unique_packages = len(set(vp.package for vp in report.vulnerable_packages))
        
        if vulnerable_count == 0:
            self.console.print("[green]🎉 No vulnerabilities found![/green]")
            return
        
        self.console.print(f"\nFound {vulnerable_count} vulnerabilities in {unique_packages} packages")