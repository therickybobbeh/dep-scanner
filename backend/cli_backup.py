#!/usr/bin/env python3
"""
DepScan CLI - Dependency Vulnerability Scanner
"""
import asyncio
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

try:  # Allow running as module or script
    from .app.models import ScanOptions, SeverityLevel, Report, JobStatus
    from .app.resolver import PythonResolver, JavaScriptResolver
    from .app.scanner import OSVScanner
except ImportError:  # pragma: no cover - fallback for script execution
    from app.models import ScanOptions, SeverityLevel, Report, JobStatus
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
                "scan_options": options.model_dump()
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
    severity_filter: list[str] = typer.Option([], "--ignore-severity", help="Ignore vulnerabilities of specific severity levels"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Generate HTML report and open in browser"),
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
            
            # Set up scan options
            options = ScanOptions(
                include_dev_dependencies=include_dev,
                ignore_severities=ignore_severities,
                ignore_rules=[]
            )
            
            # Display scan progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Scanning repository...", total=None)
                report = await scanner.scan_repository(repo_path, options)
                progress.update(task, completed=True)

            # Display results in terminal
            console.print("\n[bold green]Scan completed![/bold green]")

            if report.vulnerable_packages:
                console.print(f"\n[bold red]Found {len(report.vulnerable_packages)} vulnerabilities in {report.vulnerable_count} packages[/bold red]")

                # Create a table with vulnerability information
                table = Table(title="Vulnerability Summary")
                table.add_column("Package", style="cyan")
                table.add_column("Version", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Source", style="magenta")
                table.add_column("Vulnerability ID", style="yellow")
                table.add_column("Severity", style="red")
                table.add_column("Link", style="white", overflow="fold")

                for vuln in report.vulnerable_packages:
                    severity = vuln.severity.value if vuln.severity else "UNKNOWN"
                    severity_color = {
                        "CRITICAL": "[bold red]CRITICAL[/bold red]",
                        "HIGH": "[red]HIGH[/red]",
                        "MEDIUM": "[yellow]MEDIUM[/yellow]",
                        "LOW": "[green]LOW[/green]",
                        "UNKNOWN": "[blue]UNKNOWN[/blue]"
                    }.get(severity, severity)

                    dep_match = next((d for d in report.dependencies if d.name == vuln.package and d.version == vuln.version), None)
                    dep_type = "direct" if dep_match and dep_match.is_direct else "transitive"
                    source = "-"
                    if dep_match and len(dep_match.path) >= 2:
                        source = dep_match.path[-2]

                    table.add_row(
                        vuln.package,
                        vuln.version,
                        dep_type,
                        source,
                        vuln.vulnerability_id,
                        severity_color,
                        vuln.advisory_url or ""
                    )

                console.print(table)

                if report.suppressed_count > 0:
                    console.print(f"\n[yellow]Note: {report.suppressed_count} vulnerabilities were suppressed based on ignore rules[/yellow]")
            else:
                console.print("\n[bold green]No vulnerabilities found! Your dependencies look clean.[/bold green]")

            # Output JSON if requested
            if json_output:
                with open(json_output, "w") as f:
                    f.write(report.model_dump_json(indent=2))
                console.print(f"\n[blue]Report saved to: {json_output}[/blue]")

            # Generate and open HTML report if requested
            if open_browser:
                html_path = generate_modern_html_report(report)
                console.print(f"\n[blue]Opening HTML report: {html_path}[/blue]")
                webbrowser.open(f"file://{html_path}")

        except FileNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error during scan: {e}[/red]")
        finally:
            await scanner.close()

    asyncio.run(run_scan())

def generate_html_report(report: Report) -> str:
    """Generate a simple static HTML report and return its path."""
    from html import escape

    output_path = Path("dep-scan-report.html").resolve()
    if output_path.exists():
        output_path.unlink()

    rows = []
    for vuln in report.vulnerable_packages:
        severity = vuln.severity.value if vuln.severity else "UNKNOWN"
        dep_match = next((d for d in report.dependencies if d.name == vuln.package and d.version == vuln.version), None)
        dep_type = "direct" if dep_match and dep_match.is_direct else "transitive"
        source = "-"
        if dep_match and len(dep_match.path) >= 2:
            source = dep_match.path[-2]
        link_html = (
            f"<a href='{escape(vuln.advisory_url)}'>{escape(vuln.advisory_url)}</a>" if vuln.advisory_url else ""
        )
        rows.append(
            f"<tr><td>{escape(vuln.package)}</td><td>{escape(vuln.version)}</td>"
            f"<td>{dep_type}</td><td>{escape(source)}</td><td>{escape(severity)}</td>"
            f"<td>{escape(vuln.vulnerability_id)}</td><td>{link_html}</td><td>{escape(vuln.summary)}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head><meta charset=\"UTF-8\"><title>DepScan Report</title>
<style>table{{border-collapse:collapse;}}td,th{{border:1px solid #ccc;padding:4px;}}</style>
</head><body>
<h1>DepScan Report</h1>
<p>Scanned {report.total_dependencies} dependencies and found {len(report.vulnerable_packages)} vulnerabilities.</p>
<table>
<tr><th>Package</th><th>Version</th><th>Type</th><th>Source</th><th>Severity</th><th>ID</th><th>Link</th><th>Summary</th></tr>
{''.join(rows)}
</table>
</body></html>"""

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)

def generate_modern_html_report(report: Report) -> str:
    """Generate a modern, responsive HTML report and return its path."""
    from html import escape
    from datetime import datetime

    output_path = Path("dep-scan-report.html").resolve()
    if output_path.exists():
        output_path.unlink()

    # Group vulnerabilities by severity for summary
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for vuln in report.vulnerable_packages:
        severity = vuln.severity.value if vuln.severity else "UNKNOWN"
        severity_counts[severity] += 1

    # Generate vulnerability rows
    rows = []
    for vuln in report.vulnerable_packages:
        severity = vuln.severity.value if vuln.severity else "UNKNOWN"
        dep_match = next((d for d in report.dependencies if d.name == vuln.package and d.version == vuln.version), None)
        dep_type = "direct" if dep_match and dep_match.is_direct else "transitive"
        source = "-"
        if dep_match and len(dep_match.path) >= 2:
            source = dep_match.path[-2]
        
        link_html = ""
        if vuln.advisory_url:
            link_html = f"<a href='{escape(vuln.advisory_url)}' target='_blank' rel='noopener'>🔗</a>"
        
        cve_display = ", ".join(vuln.cve_ids) if vuln.cve_ids else vuln.vulnerability_id
        
        rows.append(f"""
        <tr>
            <td><strong>{escape(vuln.package)}</strong></td>
            <td>{escape(vuln.version)}</td>
            <td><span class="dep-type dep-{dep_type}">{dep_type}</span></td>
            <td>{escape(source)}</td>
            <td><span class="severity severity-{severity.lower()}">{severity}</span></td>
            <td><code>{escape(cve_display)}</code></td>
            <td class="text-center">{link_html}</td>
            <td class="summary">{escape(vuln.summary or "No description available")}</td>
        </tr>
        """)

    # Generate summary cards HTML
    summary_cards = ""
    for severity, count in severity_counts.items():
        if count > 0:
            summary_cards += f"""
            <div class="summary-card severity-{severity.lower()}">
                <div class="count">{count}</div>
                <div class="label">{severity}</div>
            </div>
            """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DepScan Security Report</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }}
        
        .header .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .summary {{
            padding: 30px;
            background: #f8fafc;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .stat-card .number {{
            font-size: 2rem;
            font-weight: bold;
            color: #4a5568;
        }}
        
        .stat-card .label {{
            color: #718096;
            font-size: 0.9rem;
            margin-top: 5px;
        }}
        
        .severity-summary {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        
        .summary-card {{
            padding: 15px 20px;
            border-radius: 8px;
            text-align: center;
            min-width: 100px;
            color: white;
            font-weight: 600;
        }}
        
        .summary-card .count {{
            font-size: 1.8rem;
            font-weight: bold;
        }}
        
        .summary-card .label {{
            font-size: 0.8rem;
            margin-top: 5px;
            text-transform: uppercase;
        }}
        
        .severity-critical {{ background: #e53e3e; }}
        .severity-high {{ background: #dd6b20; }}
        .severity-medium {{ background: #d69e2e; }}
        .severity-low {{ background: #38a169; }}
        .severity-unknown {{ background: #718096; }}
        
        .content {{
            padding: 30px;
        }}
        
        .table-container {{
            overflow-x: auto;
            margin-top: 20px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        
        th {{
            background: #f7fafc;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        td {{
            padding: 15px 12px;
            border-bottom: 1px solid #edf2f7;
            vertical-align: top;
        }}
        
        tr:hover {{
            background: #f7fafc;
        }}
        
        .dep-type {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .dep-direct {{
            background: #e6fffa;
            color: #047857;
        }}
        
        .dep-transitive {{
            background: #fef7e6;
            color: #b45309;
        }}
        
        .severity {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: white;
        }}
        
        .severity-critical {{ background: #e53e3e; }}
        .severity-high {{ background: #dd6b20; }}
        .severity-medium {{ background: #d69e2e; }}
        .severity-low {{ background: #38a169; }}
        .severity-unknown {{ background: #718096; }}
        
        .text-center {{ text-align: center; }}
        
        .summary {{
            max-width: 300px;
            word-break: break-word;
        }}
        
        code {{
            background: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.85rem;
        }}
        
        a {{
            color: #3182ce;
            text-decoration: none;
            font-size: 1.2rem;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .footer {{
            padding: 20px 30px;
            background: #f7fafc;
            border-top: 1px solid #e2e8f0;
            text-align: center;
            color: #718096;
            font-size: 0.9rem;
        }}
        
        .no-vulnerabilities {{
            text-align: center;
            padding: 60px 30px;
            color: #38a169;
        }}
        
        .no-vulnerabilities .icon {{
            font-size: 4rem;
            margin-bottom: 20px;
        }}
        
        .no-vulnerabilities h2 {{
            font-size: 1.5rem;
            margin-bottom: 10px;
        }}
        
        @media (max-width: 768px) {{
            body {{ padding: 10px; }}
            .header {{ padding: 20px; }}
            .header h1 {{ font-size: 2rem; }}
            .content {{ padding: 20px; }}
            .summary {{ padding: 20px; }}
            th, td {{ padding: 10px 8px; }}
            .severity-summary {{ justify-content: space-around; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ DepScan Security Report</h1>
            <div class="subtitle">Dependency Vulnerability Analysis</div>
        </div>
        
        <div class="summary">
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="number">{report.total_dependencies}</div>
                    <div class="label">Total Dependencies</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(report.vulnerable_packages)}</div>
                    <div class="label">Vulnerabilities Found</div>
                </div>
                <div class="stat-card">
                    <div class="number">{report.vulnerable_count}</div>
                    <div class="label">Vulnerable Packages</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(report.meta.get('ecosystems', []))}</div>
                    <div class="label">Ecosystems Scanned</div>
                </div>
            </div>
            
            {f'<div class="severity-summary">{summary_cards}</div>' if summary_cards else ''}
        </div>
        
        <div class="content">
            {'''
            <div class="no-vulnerabilities">
                <div class="icon">✅</div>
                <h2>No Vulnerabilities Found!</h2>
                <p>Your project dependencies appear to be secure.</p>
            </div>
            ''' if not rows else f'''
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Package</th>
                            <th>Version</th>
                            <th>Type</th>
                            <th>Source</th>
                            <th>Severity</th>
                            <th>CVE/ID</th>
                            <th>Link</th>
                            <th>Description</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            '''}
        </div>
        
        <div class="footer">
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by DepScan v1.0.0</p>
            <p>Ecosystems: {', '.join(report.meta.get('ecosystems', []))}</p>
        </div>
    </div>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)

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

@app.command()
def version():
    """Show version information"""
    console.print("[bold]DepScan - Dependency Vulnerability Scanner[/bold]")
    console.print("Version: 1.0.0")
    console.print("Made with ♥ by DepScan Team")

if __name__ == "__main__":
    app()