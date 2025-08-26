"""Unified export functions for CLI and Web interfaces"""
import json
from pathlib import Path
from typing import Any, Dict
from .models import Report


def export_json_report(report: Report, output_path: str = None) -> Dict[str, Any]:
    """
    Export scan report to JSON format (CLI-compatible structure)
    
    This function creates a JSON report matching the CLI output format,
    ensuring consistency between CLI and Web interfaces.
    
    Args:
        report: The scan report to export
        output_path: Optional path to save JSON file
        
    Returns:
        Dictionary with CLI-compatible JSON structure
    """
    # Derive ecosystems from dependencies
    ecosystems = list(set(dep.ecosystem for dep in report.dependencies))
    
    # Convert report to CLI JSON format
    json_data = {
        "scan_info": {
            "total_dependencies": len(report.dependencies),
            "vulnerable_packages": len(report.vulnerable_packages),
            "ecosystems": ecosystems
        },
        "vulnerabilities": []
    }
    
    for vuln in report.vulnerable_packages:
        # Find matching dependency for additional context
        dep_match = next(
            (d for d in report.dependencies 
             if d.name == vuln.package and d.version == vuln.version), 
            None
        )
        
        vuln_data = {
            "package": vuln.package,
            "version": vuln.version,
            "vulnerability_id": vuln.vulnerability_id,
            "severity": vuln.severity.value if vuln.severity else "UNKNOWN",
            "summary": vuln.summary,
            "cve_ids": vuln.cve_ids,
            "advisory_url": vuln.advisory_url,
            "type": "direct" if dep_match and dep_match.is_direct else "transitive",
            "dependency_path": dep_match.path if dep_match else []
        }
        
        # Add optional fields if present
        if vuln.fixed_range:
            vuln_data["fixed_range"] = vuln.fixed_range
        if vuln.details:
            vuln_data["details"] = vuln.details
        if vuln.published:
            vuln_data["published"] = vuln.published.isoformat()
        if vuln.modified:
            vuln_data["modified"] = vuln.modified.isoformat()
            
        json_data["vulnerabilities"].append(vuln_data)
    
    # Add scan metadata
    if hasattr(report, 'meta') and report.meta:
        json_data["meta"] = {
            "generated_at": report.meta.get("generated_at", ""),
            "scan_options": report.meta.get("scan_options", {})
        }
    
    # Write to file if path provided
    if output_path:
        output_path_obj = Path(output_path)
        output_path_obj.write_text(
            json.dumps(json_data, indent=2), 
            encoding="utf-8"
        )
    
    return json_data


def export_web_json_report(report: Report) -> Dict[str, Any]:
    """
    Export scan report in Web API format (for backward compatibility)
    
    Args:
        report: The scan report to export
        
    Returns:
        Dictionary with Web API JSON structure
    """
    return report.model_dump()