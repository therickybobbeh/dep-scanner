"""
CLI output formatting utilities
"""
from rich.console import Console
from rich.table import Table
from rich.text import Text

try:
    from .models import Report, SeverityLevel
    from .resolver.utils.path_utils import PathTracker
except ImportError:
    from app.models import Report, SeverityLevel
    from app.resolver.utils.path_utils import PathTracker


class CLIFormatter:
    """Handles CLI output formatting"""
    
    def __init__(self):
        self.console = Console()
    
    def create_vulnerability_table(self, report: Report) -> Table:
        """Create a formatted table of vulnerabilities"""
        table = Table(title="Vulnerability Summary", show_header=True, header_style="bold magenta")
        
        table.add_column("Package", style="cyan", no_wrap=True)
        table.add_column("Version", style="yellow")
        table.add_column("Type", style="green")
        table.add_column("Source", style="blue")
        table.add_column("Vulnerability ID", style="red")
        table.add_column("Severity", style="bold")
        table.add_column("Link", style="dim")
        
        for vuln in report.vulnerable_packages:
            # Find the dependency to get type and source info
            dep_match = next((d for d in report.dependencies if d.name == vuln.package and d.version == vuln.version), None)
            dep_type = "direct" if dep_match and dep_match.is_direct else "transitive"
            
            # Determine source: direct dependency or root cause for transitive
            source = "unknown"
            if dep_match:
                if dep_match.is_direct:
                    source = "direct"
                elif dep_match.path and len(dep_match.path) > 1:
                    # For transitive dependencies, show the direct dependency that introduced it
                    # The first item in the path is typically the direct dependency
                    source = dep_match.path[0]
                else:
                    # Fallback if we can't determine the path
                    source = "transitive"
            
            # Format severity with color
            severity_text = self._format_severity(vuln.severity)
            
            # Generate link - prioritize advisory_url, fallback to OSV.dev
            link = ""
            if vuln.advisory_url:
                link = "🔗"
            elif vuln.vulnerability_id:
                link = "🔗"
            
            table.add_row(
                vuln.package,
                vuln.version,
                dep_type,
                source,
                vuln.vulnerability_id or "Unknown",
                severity_text,
                link
            )
        
        return table
    
    def _format_severity(self, severity: SeverityLevel | None) -> Text:
        """Format severity with appropriate color"""
        if not severity:
            return Text("UNKNOWN", style="dim")
        
        severity_str = severity.value
        color_map = {
            "CRITICAL": "bold red",
            "HIGH": "red",
            "MEDIUM": "yellow",
            "LOW": "green",
            "UNKNOWN": "dim"
        }
        
        return Text(severity_str, style=color_map.get(severity_str, "dim"))
    
    def print_scan_summary(self, report: Report) -> None:
        """Print scan summary statistics"""
        vulnerable_count = len(report.vulnerable_packages)
        unique_packages = len(set(vp.package for vp in report.vulnerable_packages))
        
        if vulnerable_count == 0:
            self.console.print("[green]🎉 No vulnerabilities found![/green]")
            return
        
        # Count by severity
        severity_counts = {}
        for vuln in report.vulnerable_packages:
            severity = vuln.severity.value if vuln.severity else "UNKNOWN"
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        self.console.print(f"\n[bold]Found {vulnerable_count} vulnerabilities in {unique_packages} packages[/bold]")
        
        # Print severity breakdown
        for severity, count in severity_counts.items():
            color = {
                "CRITICAL": "bold red",
                "HIGH": "red", 
                "MEDIUM": "yellow",
                "LOW": "green",
                "UNKNOWN": "dim"
            }.get(severity, "dim")
            
            self.console.print(f"  {severity}: {count}", style=color)