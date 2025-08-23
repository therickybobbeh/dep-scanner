#!/usr/bin/env python3
"""
DepScan CLI - Dependency Vulnerability Scanner
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import subprocess
import webbrowser

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from app.models import ScanOptions, Report, JobStatus, SeverityLevel
from app.resolver import PythonResolver, JavaScriptResolver
from app.scanner import OSVScanner

app = typer.Typer(help="DepScan - Dependency Vulnerability Scanner")
console = Console()

class DepScanner:
    """Main scanner orchestrator"""
    
    def __init__(self):
        self.python_resolver = PythonResolver()
        self.js_resolver = JavaScriptResolver()
        self.osv_scanner = OSVScanner()
    
    async def scan_repository(self, repo_path: str, options: ScanOptions) -> Report:
        """Scan a repository for vulnerabilities"""
        repo_path_obj = Path(repo_path)
        
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        
        all_dependencies = []
        ecosystems_found = []
        
        # Try to resolve Python dependencies
        try:
            py_deps = await self.python_resolver.resolve_dependencies(repo_path)
            all_dependencies.extend(py_deps)
            ecosystems_found.append("Python")
        except FileNotFoundError:
            pass  # No Python dependencies found
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to resolve Python dependencies: {e}[/yellow]")
        
        # Try to resolve JavaScript dependencies
        try:
            js_deps = await self.js_resolver.resolve_dependencies(repo_path)
            all_dependencies.extend(js_deps)
            ecosystems_found.append("JavaScript")
        except FileNotFoundError:
            pass  # No JavaScript dependencies found
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to resolve JavaScript dependencies: {e}[/yellow]")
        
        if not all_dependencies:
            raise ValueError("No dependencies found in repository")
        
        console.print(f"[green]Found dependencies in: {', '.join(ecosystems_found)}[/green]")
        
        # Filter dependencies based on options
        if not options.include_dev_dependencies:
            all_dependencies = [dep for dep in all_dependencies if not dep.is_dev]
        
        console.print(f"[blue]Scanning {len(all_dependencies)} dependencies...[/blue]")
        
        # Scan for vulnerabilities
        vulnerabilities = await self.osv_scanner.scan_dependencies(all_dependencies)
        
        # Filter by severity
        if options.ignore_severities:
            vulnerabilities = [
                vuln for vuln in vulnerabilities 
                if vuln.severity not in options.ignore_severities
            ]
        
        # Apply ignore rules
        suppressed_count = 0
        if options.ignore_rules:
            filtered_vulns = []
            for vuln in vulnerabilities:
                should_ignore = False
                for rule in options.ignore_rules:
                    if rule.rule_type == "vulnerability" and rule.identifier in [vuln.vulnerability_id] + vuln.cve_ids:
                        should_ignore = True
                        break
                    elif rule.rule_type == "package" and f"{vuln.package}@{vuln.version}" == rule.identifier:
                        should_ignore = True
                        break
                
                if should_ignore:
                    suppressed_count += 1
                else:
                    filtered_vulns.append(vuln)
            
            vulnerabilities = filtered_vulns
        
        # Create report
        report = Report(
            job_id=f"cli_{int(datetime.now().timestamp())}",
            status=JobStatus.COMPLETED,
            total_dependencies=len(all_dependencies),
            vulnerable_count=len(set((v.package, v.version) for v in vulnerabilities)),
            vulnerable_packages=vulnerabilities,
            dependencies=all_dependencies,
            suppressed_count=suppressed_count,
            meta={
                "generated_at": datetime.now().isoformat(),
                "ecosystems": ecosystems_found,
                "scan_options": options.dict()
            }
        )
        
        return report
    
    async def close(self):
        """Clean up resources"""
        await self.osv_scanner.close()

@app.command()
def scan(
    repo_path: str = typer.Argument(..., help="Path to repository or directory to scan"),
    json_output: Optional[str] = typer.Option(None, "--json", "-j", help="Output JSON report to file"),
    include_dev: bool = typer.Option(True, "--dev/--no-dev", help="Include development dependencies"),
    severity_filter: List[str] = typer.Option([], "--ignore-severity", help="Ignore vulnerabilities of specific severity levels"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Start web server and open browser"),
    port: int = typer.Option(8000, "--port", "-p", help="Port for web server"),
):
    """Scan a repository for dependency vulnerabilities"""
    
    async def run_scan():
        scanner = DepScanner()
        
        try:
            # Parse severity filters
            ignore_severities = []
            for sev in severity_filter:
                try:
                    ignore_severities.append(SeverityLevel(sev.upper()))
                except ValueError:
                    console.print(f"[red]Invalid severity level: {sev}[/red]")
                    return
            
            # Create scan options
            options = ScanOptions(
                include_dev_dependencies=include_dev,
                ignore_severities=ignore_severities
            )
            
            # Run scan
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Scanning dependencies...", total=None)
                
                report = await scanner.scan_repository(repo_path, options)
                
                progress.update(task, description="Scan completed!", total=1, completed=1)
            
            # Output results
            print_report_summary(report)
            
            if json_output:
                with open(json_output, 'w') as f:
                    json.dump(report.dict(), f, indent=2, default=str)
                console.print(f"[green]JSON report saved to: {json_output}[/green]")
            
            if open_browser:
                console.print("[blue]Starting web server...[/blue]")
                start_web_server(port)
        
        finally:
            await scanner.close()
    
    asyncio.run(run_scan())

def print_report_summary(report: Report):
    """Print a formatted summary of the scan results"""
    
    console.print(f"\n[bold]Dependency Scan Results[/bold]")
    console.print(f"Found {report.total_dependencies} dependencies")
    
    if report.vulnerable_count == 0:
        console.print("[green]✅ No vulnerabilities found![/green]")
        return
    
    console.print(f"[red]{report.vulnerable_count} vulnerable packages found[/red]")
    if report.suppressed_count > 0:
        console.print(f"[yellow]{report.suppressed_count} vulnerabilities suppressed[/yellow]")
    
    # Group vulnerabilities by severity
    by_severity = {}
    for vuln in report.vulnerable_packages:
        severity = vuln.severity or SeverityLevel.UNKNOWN
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(vuln)
    
    # Create summary table
    table = Table(title="Vulnerability Summary")
    table.add_column("Severity", style="bold")
    table.add_column("Count", justify="right")
    
    severity_order = [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW, SeverityLevel.UNKNOWN]
    for severity in severity_order:
        if severity in by_severity:
            count = len(by_severity[severity])
            color = {
                SeverityLevel.CRITICAL: "red",
                SeverityLevel.HIGH: "orange3",
                SeverityLevel.MEDIUM: "yellow",
                SeverityLevel.LOW: "blue",
                SeverityLevel.UNKNOWN: "dim"
            }.get(severity, "white")
            
            table.add_row(f"[{color}]{severity.value}[/{color}]", f"[{color}]{count}[/{color}]")
    
    console.print(table)
    
    # Show detailed vulnerabilities
    console.print(f"\n[bold]Detailed Vulnerabilities:[/bold]")
    
    for i, vuln in enumerate(report.vulnerable_packages[:10], 1):  # Show first 10
        severity_color = {
            SeverityLevel.CRITICAL: "red",
            SeverityLevel.HIGH: "orange3", 
            SeverityLevel.MEDIUM: "yellow",
            SeverityLevel.LOW: "blue",
            SeverityLevel.UNKNOWN: "dim"
        }.get(vuln.severity, "white")
        
        console.print(f"\n{i}. [bold]{vuln.package}@{vuln.version}[/bold]   severity: [{severity_color}]{vuln.severity.value if vuln.severity else 'UNKNOWN'}[/{severity_color}]")
        
        if vuln.cve_ids:
            console.print(f"   CVE: {', '.join(vuln.cve_ids)}")
        else:
            console.print(f"   ID: {vuln.vulnerability_id}")
        
        if vuln.fixed_range:
            console.print(f"   Fix: {vuln.fixed_range}")
        
        if vuln.advisory_url:
            console.print(f"   Advisory: {vuln.advisory_url}")
        
        # Find dependency path from report
        for dep in report.dependencies:
            if dep.name == vuln.package and dep.version == vuln.version:
                path_str = " -> ".join(dep.path)
                console.print(f"   Path: {path_str}")
                break
        
        console.print(f"   {vuln.summary}")
    
    if len(report.vulnerable_packages) > 10:
        console.print(f"\n[dim]... and {len(report.vulnerable_packages) - 10} more vulnerabilities[/dim]")

def start_web_server(port: int):
    """Start the FastAPI web server"""
    try:
        # Try to import and start the server
        import uvicorn
        url = f"http://127.0.0.1:{port}"
        
        console.print(f"[blue]Opening browser to {url}[/blue]")
        webbrowser.open(url)
        
        # This would start the FastAPI server - for now just show the URL
        console.print(f"[yellow]Web server would start at {url}[/yellow]")
        console.print("[yellow]Web UI not yet implemented - use CLI mode for now[/yellow]")
        
    except ImportError:
        console.print("[red]FastAPI web server not available[/red]")

@app.command()
def version():
    """Show version information"""
    console.print("[bold]DepScan v1.0.0[/bold]")
    console.print("Dependency Vulnerability Scanner")

if __name__ == "__main__":
    app()