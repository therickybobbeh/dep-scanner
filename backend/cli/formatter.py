"""
CLI output formatting utilities - Simple and readable
"""
from rich.console import Console
from rich.table import Table
from rich.text import Text

try:
    from ..core.models import Report, SeverityLevel
except ImportError:
    from backend.core.models import Report, SeverityLevel


class CLIFormatter:
    """Handles CLI output formatting with better readability"""
    
    def __init__(self):
        self.console = Console()
    
    def create_vulnerability_table(self, report: Report) -> Table:
        """Create a clean, readable table of vulnerabilities"""
        table = Table(title="Vulnerability Summary", show_header=True, header_style="bold magenta")
        
        # Cleaner column layout with proper widths
        table.add_column("Package", style="cyan", no_wrap=True, min_width=12)
        table.add_column("Version", style="yellow", min_width=8)
        table.add_column("Severity", style="bold", min_width=8)
        table.add_column("CVSS", style="magenta", min_width=6)  # CVSS score (0.0-10.0)
        table.add_column("CVE ID", style="red", min_width=15)
        table.add_column("Type", style="green", min_width=8)
        table.add_column("Link", style="dim blue", min_width=12)  # Clickable link
        
        for vuln in report.vulnerable_packages:
            # Find dependency info
            dep_match = next((d for d in report.dependencies if d.name == vuln.package and d.version == vuln.version), None)
            dep_type = "direct" if dep_match and dep_match.is_direct else "transitive"
            
            # Format severity with color and CVSS score
            severity_text, cvss_score_str = self._format_severity_with_score(vuln.severity, vuln.cvss_score)
            
            # Format CVE ID (truncate if too long)
            cve_id = vuln.vulnerability_id or "Unknown"
            if len(cve_id) > 18:
                cve_id = cve_id[:15] + "..."
            
            # Create clickable terminal links without emojis
            if vuln.advisory_url:
                if "nvd.nist.gov" in vuln.advisory_url:
                    link_text = f"[link={vuln.advisory_url}]nvd.nist.gov[/link]"
                elif "github.com" in vuln.advisory_url:
                    link_text = f"[link={vuln.advisory_url}]github.com[/link]"
                else:
                    domain = self._format_url(vuln.advisory_url)
                    link_text = f"[link={vuln.advisory_url}]{domain}[/link]"
            elif vuln.vulnerability_id:
                # Create OSV URL from vulnerability ID
                osv_url = f"https://osv.dev/vulnerability/{vuln.vulnerability_id}"
                link_text = f"[link={osv_url}]osv.dev[/link]"
            else:
                link_text = "-"
            
            table.add_row(
                vuln.package[:12],  # Truncate package name if needed
                vuln.version[:10],  # Truncate version if needed
                severity_text,
                cvss_score_str,
                cve_id,
                dep_type,
                link_text
            )
        
        return table
    
    def _format_severity_with_score(self, severity: SeverityLevel | None, cvss_score: float | None) -> tuple[Text, str]:
        """
        Format severity with color and return CVSS score
        Shows actual CVSS scores (0.0-10.0) when available
        """
        if not severity:
            return Text("UNKNOWN", style="dim"), "-"
        
        severity_str = severity.value
        
        # Map to colors
        severity_colors = {
            "CRITICAL": "bold red",
            "HIGH": "red",
            "MEDIUM": "yellow",
            "LOW": "green",
            "UNKNOWN": "dim"
        }
        
        style = severity_colors.get(severity_str, "dim")
        
        # Format CVSS score with 1 decimal place, or use dash if not available
        score_str = f"{cvss_score:.1f}" if cvss_score is not None else "-"
        
        return Text(severity_str, style=style), score_str
    
    def _format_url(self, url: str) -> str:
        """
        Format URL to fit in table - show domain and key parts
        Max 20 chars to keep table readable and clean
        """
        if not url:
            return "-"
        
        # Remove protocol
        url_short = url.replace("https://", "").replace("http://", "")
        
        # Special handling for common domains - shorter format
        if "github.com" in url_short:
            return "github.com"
        elif "nvd.nist.gov" in url_short:
            return "nvd.nist.gov"
        elif "osv.dev" in url_short:
            return "osv.dev"
        elif "snyk.io" in url_short:
            return "snyk.io"
        elif "vulncheck.com" in url_short:
            return "vulncheck.com"
        else:
            # Extract just the domain
            parts = url_short.split("/")
            domain = parts[0]
            if len(domain) > 15:
                return domain[:12] + "..."
            return domain
    
    def print_scan_summary(self, report: Report) -> None:
        """Print clean scan summary statistics"""
        vulnerable_count = len(report.vulnerable_packages)
        unique_packages = len(set(vp.package for vp in report.vulnerable_packages))
        total_dependencies = len(report.dependencies)
        
        if vulnerable_count == 0:
            self.console.print("\n[green]✓ No vulnerabilities found![/green]")
            self.console.print(f"Scanned {total_dependencies} dependencies")
            return
        
        # Count by severity
        severity_counts = {}
        for vuln in report.vulnerable_packages:
            sev = vuln.severity.value if vuln.severity else "UNKNOWN"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Print summary
        self.console.print(f"\n[red]Found {vulnerable_count} vulnerabilities[/red] in {unique_packages} packages")
        
        # Show severity breakdown with CVSS score ranges
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
        cvss_ranges = {"CRITICAL": "9.0+", "HIGH": "7.0-8.9", "MEDIUM": "4.0-6.9", "LOW": "0.1-3.9", "UNKNOWN": "N/A"}
        
        for sev in severity_order:
            if sev in severity_counts:
                count = severity_counts[sev]
                cvss_range = cvss_ranges[sev]
                style = self._get_severity_style(sev)
                self.console.print(f"  {sev} (CVSS {cvss_range}): {count}", style=style)
        
        # Dependency breakdown
        direct_count = sum(1 for d in report.dependencies if d.is_direct)
        transitive_count = total_dependencies - direct_count
        self.console.print(f"\nTotal dependencies: {total_dependencies}")
        self.console.print(f"  Direct: {direct_count}")
        self.console.print(f"  Transitive: {transitive_count}")
        
        # Percentage vulnerable
        vuln_percentage = (unique_packages / total_dependencies * 100) if total_dependencies > 0 else 0
        self.console.print(f"  Vulnerable: {unique_packages} ({vuln_percentage:.1f}%)")
    
    def _get_severity_style(self, severity: str) -> str:
        """Get console style for severity level"""
        styles = {
            "CRITICAL": "bold red",
            "HIGH": "red", 
            "MEDIUM": "yellow",
            "LOW": "green",
            "UNKNOWN": "dim"
        }
        return styles.get(severity, "dim")
    
    def print_remediation_suggestions(self, report: Report) -> None:
        """Print simple remediation suggestions"""
        if not report.vulnerable_packages:
            return
        
        self.console.print("\n[bold]Suggested Remediations:[/bold]")
        
        # Group vulnerabilities by package
        package_vulns = {}
        for vuln in report.vulnerable_packages:
            key = f"{vuln.package}@{vuln.version}"
            if key not in package_vulns:
                package_vulns[key] = []
            package_vulns[key].append(vuln)
        
        # Show top 5 most critical packages to update
        critical_packages = []
        for package_key, vulns in package_vulns.items():
            # Calculate priority score using CVSS scores when available
            max_cvss_score = 0.0
            max_severity = "UNKNOWN"
            
            for v in vulns:
                if v.cvss_score and v.cvss_score > max_cvss_score:
                    max_cvss_score = v.cvss_score
                    max_severity = v.severity.value if v.severity else "UNKNOWN"
                elif not v.cvss_score and v.severity:
                    # Fallback to severity level mapping
                    sev_scores = {"CRITICAL": 9.5, "HIGH": 7.5, "MEDIUM": 5.0, "LOW": 2.5, "UNKNOWN": 0.0}
                    score = sev_scores.get(v.severity.value, 0.0)
                    if score > max_cvss_score:
                        max_cvss_score = score
                        max_severity = v.severity.value
            
            package_name = package_key.split('@')[0]
            current_version = package_key.split('@')[1]
            critical_packages.append((package_name, current_version, max_cvss_score, max_severity, len(vulns)))
        
        # Sort by CVSS score and vulnerability count
        critical_packages.sort(key=lambda x: (x[2], x[4]), reverse=True)
        
        # Show top 5
        for i, (pkg, version, cvss_score, severity_name, vuln_count) in enumerate(critical_packages[:5], 1):
            style = self._get_severity_style(severity_name)
            cvss_display = f"CVSS {cvss_score:.1f}" if cvss_score > 0 else severity_name
            self.console.print(
                f"  {i}. Update [cyan]{pkg}[/cyan] from {version} "
                f"({vuln_count} vulnerabilities, highest: [{style}]{cvss_display}[/{style}])"
            )
        
        if len(critical_packages) > 5:
            remaining = len(critical_packages) - 5
            self.console.print(f"  ... and {remaining} more packages with vulnerabilities")
        
        self.console.print("\nRun with --json flag for full details and advisory URLs")