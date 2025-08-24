"""Export service for generating scan reports in various formats"""
import json
import csv
import io
import tempfile
from pathlib import Path
from fastapi.responses import FileResponse, StreamingResponse

from ..models import Report


class ExportService:
    """Service for exporting scan reports"""
    
    @staticmethod
    def export_json_streaming(report: Report, job_id: str) -> StreamingResponse:
        """Export report as JSON streaming response"""
        def generate():
            yield json.dumps(report.model_dump(), indent=2, default=str)
        
        return StreamingResponse(
            generate(), 
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=depscan_report_{job_id}.json"}
        )
    
    @staticmethod
    def export_csv_streaming(report: Report, job_id: str) -> StreamingResponse:
        """Export report as CSV streaming response"""
        def generate():
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Package", "Version", "Ecosystem", "Severity", "CVE IDs", "Vulnerability ID",
                "Summary", "Fixed Range", "Advisory URL", "Published", "Modified"
            ])
            
            # Write vulnerability data
            for vuln in report.vulnerable_packages:
                writer.writerow([
                    vuln.package,
                    vuln.version,
                    vuln.ecosystem,
                    vuln.severity.value if vuln.severity else "",
                    ";".join(vuln.cve_ids),
                    vuln.vulnerability_id,
                    vuln.summary,
                    vuln.fixed_range or "",
                    vuln.advisory_url or "",
                    vuln.published.isoformat() if vuln.published else "",
                    vuln.modified.isoformat() if vuln.modified else ""
                ])
            
            output.seek(0)
            yield output.getvalue()
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=depscan_report_{job_id}.csv"}
        )
    
    @staticmethod
    def export_json_file(report: Report, job_id: str) -> FileResponse:
        """Export report as JSON file (legacy method with temp file)"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(report.model_dump(), f, indent=2, default=str)
            temp_path = f.name
        
        return FileResponse(
            temp_path,
            media_type='application/json',
            filename=f"depscan_report_{job_id}.json"
        )
    
    @staticmethod
    def export_csv_file(report: Report, job_id: str) -> FileResponse:
        """Export report as CSV file (legacy method with temp file)"""
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Package", "Version", "Ecosystem", "Severity", "CVE IDs", "Vulnerability ID",
            "Summary", "Fixed Range", "Advisory URL", "Published", "Modified"
        ])
        
        # Write vulnerability data
        for vuln in report.vulnerable_packages:
            writer.writerow([
                vuln.package,
                vuln.version,
                vuln.ecosystem,
                vuln.severity.value if vuln.severity else "",
                ";".join(vuln.cve_ids),
                vuln.vulnerability_id,
                vuln.summary,
                vuln.fixed_range or "",
                vuln.advisory_url or "",
                vuln.published.isoformat() if vuln.published else "",
                vuln.modified.isoformat() if vuln.modified else ""
            ])
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            f.write(output.getvalue())
            temp_path = f.name
        
        return FileResponse(
            temp_path,
            media_type='text/csv',
            filename=f"depscan_report_{job_id}.csv"
        )