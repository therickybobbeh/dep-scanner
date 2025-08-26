#!/usr/bin/env python3
"""
DepScan CLI - Dependency Vulnerability Scanner
Refactored for better modularity and maintainability
"""
import asyncio
import json
import logging
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

# Import CLI components
try:  # Allow running as module or script
    from ..core.models import ScanOptions, SeverityLevel
    from ..core.config import settings
    from ..core.export import export_json_report
    from .scanner import DepScanner
    from .formatter import CLIFormatter
    from ..core.reports import generate_modern_html_report
except ImportError:  # pragma: no cover - fallback for script execution
    from backend.core.models import ScanOptions, SeverityLevel
    from backend.core.config import settings
    from backend.core.export import export_json_report
    from backend.cli.scanner import DepScanner
    from backend.cli.formatter import CLIFormatter
    from backend.core.reports import generate_modern_html_report

app = typer.Typer(help="DepScan - Dependency Vulnerability Scanner")
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to scan for dependencies"),
    json_output: Optional[str] = typer.Option(None, "--json", help="Export results as JSON"),
    include_dev: bool = typer.Option(True, "--include-dev/--no-include-dev", help="Include development dependencies (default: True)"),
    ignore_severity: Optional[str] = typer.Option(None, "--ignore-severity", help="Ignore vulnerabilities of specified severity"),
    open_report: bool = typer.Option(False, "--open", help="Generate and open HTML report in browser"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="HTML report output file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed scanning progress including files being processed")
):
    """Scan a repository for dependency vulnerabilities."""
    
    # Parse ignore severity
    ignore_sev = None
    if ignore_severity:
        try:
            ignore_sev = SeverityLevel(ignore_severity.upper())
        except ValueError:
            console.print(f"[red]Error:[/red] Invalid severity level: {ignore_severity}")
            console.print("Valid levels: CRITICAL, HIGH, MEDIUM, LOW")
            raise typer.Exit(1)
    
    # Create scan options
    options = ScanOptions(
        include_dev_dependencies=include_dev,
        ignore_severities=[ignore_sev] if ignore_sev else []
    )
    
    try:
        # Initialize scanner and formatter
        scanner = DepScanner(verbose=verbose)
        formatter = CLIFormatter()
        
        # Run the scan
        report = asyncio.run(scanner.scan_repository(path, options))
        
        # Print results to console
        formatter.print_scan_summary(report)
        
        if report.vulnerable_packages:
            console.print()  # Add spacing
            table = formatter.create_vulnerability_table(report)
            console.print(table)
        
        # Export JSON if requested
        if json_output:
            export_json_report(report, json_output)
            console.print(f"\n[green]✓ JSON report saved to: {json_output}[/green]")
        
        # Generate and optionally open HTML report
        if open_report or output_file:
            html_path = generate_modern_html_report(report, output_file)
            console.print(f"\n[green]✓ HTML report generated: {html_path}[/green]")
            
            if open_report:
                try:
                    webbrowser.open(f"file://{html_path}")
                    console.print(f"Opening HTML report: {html_path}")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not open browser: {e}[/yellow]")
        
        # Exit with appropriate code
        if report.vulnerable_packages:
            raise typer.Exit(1)  # Exit with error code if vulnerabilities found
        else:
            raise typer.Exit(0)
            
    except typer.Exit:
        # Allow typer.Exit to propagate normally (for clean exit codes)
        raise
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information."""
    console.print(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    console.print("Dependency Vulnerability Scanner")
    console.print("Data source: OSV.dev")
    if settings.DEBUG:
        console.print(f"Debug mode: {settings.DEBUG}")
        console.print(f"Log level: {settings.LOG_LEVEL}")


if __name__ == "__main__":
    app()