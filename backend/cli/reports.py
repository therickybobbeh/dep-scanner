"""
HTML report generation for DepScan CLI
"""
from pathlib import Path
from html import escape
from datetime import datetime
from typing import Optional

try:
    from ..app.models import Report
except ImportError:
    from app.models import Report


def generate_modern_html_report(report: Report, output_path: Optional[str] = None) -> str:
    """Generate a modern, responsive HTML report and return its path."""
    
    if output_path:
        output_path = Path(output_path).resolve()
    else:
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
        
        # Improve source tracking for transitive dependencies
        source = "-"
        if dep_match:
            if dep_match.is_direct:
                source = "direct"
            elif dep_match.path and len(dep_match.path) >= 2:
                # Path format: [root, parent1, parent2, ..., current]
                # We want the direct parent (second-to-last in path)
                source = dep_match.path[-2]
            elif dep_match.path and len(dep_match.path) == 1:
                # Single item path means it's the package name itself
                source = "transitive"
            else:
                source = "transitive"
        
        # Generate links from OSV data
        link_html = ""
        if vuln.advisory_url:
            link_html = f"<a href='{escape(vuln.advisory_url)}' target='_blank' rel='noopener' class='vuln-link'>🔗 Details</a>"
        elif vuln.vulnerability_id:
            # Generate OSV.dev link
            osv_url = f"https://osv.dev/vulnerability/{vuln.vulnerability_id}"
            link_html = f"<a href='{osv_url}' target='_blank' rel='noopener' class='vuln-link'>🔗 OSV.dev</a>"
        
        cve_display = ", ".join(vuln.cve_ids) if vuln.cve_ids else vuln.vulnerability_id
        
        rows.append(f"""
        <tr>
            <td><strong>{escape(vuln.package)}</strong></td>
            <td><code>{escape(vuln.version)}</code></td>
            <td><span class="dep-type dep-{dep_type}">{dep_type}</span></td>
            <td>{escape(source)}</td>
            <td><span class="severity severity-{severity.lower()}">{severity}</span></td>
            <td><code class="vuln-id">{escape(cve_display)}</code></td>
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

    # Enhanced CSS with better styling and responsive design
    css_styles = """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header .subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .summary {
            padding: 30px;
            background: #fafbfc;
            border-bottom: 1px solid #e1e5e9;
        }
        
        .summary h2 {
            margin-bottom: 20px;
            color: #2d3748;
            font-size: 1.8rem;
        }
        
        .summary-cards {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            min-width: 120px;
            border-left: 4px solid;
        }
        
        .summary-card .count {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .summary-card .label {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .severity-critical { border-left-color: #e53e3e; color: #e53e3e; }
        .severity-high { border-left-color: #dd6b20; color: #dd6b20; }
        .severity-medium { border-left-color: #d69e2e; color: #d69e2e; }
        .severity-low { border-left-color: #38a169; color: #38a169; }
        .severity-unknown { border-left-color: #718096; color: #718096; }
        
        .content {
            padding: 30px;
        }
        
        .section-title {
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #2d3748;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        th {
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            position: sticky;
            top: 0;
        }
        
        tr:hover {
            background: #f7fafc;
        }
        
        .severity {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .severity-critical { background: #fed7d7; color: #9b2c2c; }
        .severity-high { background: #feebc8; color: #9c4221; }
        .severity-medium { background: #fefcbf; color: #975a16; }
        .severity-low { background: #c6f6d5; color: #276749; }
        .severity-unknown { background: #e2e8f0; color: #4a5568; }
        
        .dep-type {
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        .dep-direct { background: #bee3f8; color: #2b6cb0; }
        .dep-transitive { background: #d6f5d6; color: #38a169; }
        
        .vuln-link {
            color: #3182ce;
            text-decoration: none;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #3182ce;
            font-size: 0.8rem;
            transition: all 0.2s;
        }
        
        .vuln-link:hover {
            background: #3182ce;
            color: white;
        }
        
        .vuln-id {
            background: #edf2f7;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        .text-center { text-align: center; }
        
        .summary { max-width: 300px; line-height: 1.4; }
        
        .footer {
            background: #f7fafc;
            padding: 20px 30px;
            text-align: center;
            color: #718096;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container { margin: 10px; }
            .header { padding: 20px; }
            .header h1 { font-size: 2rem; }
            .content { padding: 20px; }
            table { font-size: 0.9rem; }
            th, td { padding: 8px; }
            .summary-cards { justify-content: center; }
        }
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DepScan Security Report</title>
    <style>{css_styles}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ DepScan Security Report</h1>
            <p class="subtitle">Dependency Vulnerability Analysis</p>
        </div>
        
        <div class="summary">
            <h2>📊 Vulnerability Summary</h2>
            <div class="summary-cards">
                {summary_cards}
            </div>
        </div>
        
        <div class="content">
            <h3 class="section-title">🔍 Detailed Vulnerability Report</h3>
            
            <p><strong>Total Dependencies:</strong> {len(report.dependencies)} | 
               <strong>Vulnerable Packages:</strong> {len(report.vulnerable_packages)} | 
               <strong>Scan Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <table>
                <thead>
                    <tr>
                        <th>Package</th>
                        <th>Version</th>
                        <th>Type</th>
                        <th>Source</th>
                        <th>Severity</th>
                        <th>Vulnerability ID</th>
                        <th>Link</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by DepScan - Dependency Vulnerability Scanner</p>
            <p>Vulnerability data from <a href="https://osv.dev" target="_blank">OSV.dev</a></p>
        </div>
    </div>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    return str(output_path)