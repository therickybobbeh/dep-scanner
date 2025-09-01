"""Service for running CLI commands and returning results"""
from __future__ import annotations

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, Callable, Awaitable
import logging
from datetime import datetime

from ...cli.scanner import DepScanner
from ...core.models import ScanOptions, SeverityLevel

logger = logging.getLogger(__name__)


class CLIService:
    """Service to execute vulnerability scans using core scanner"""
    
    @staticmethod
    async def run_cli_scan(
        path: Optional[str] = None,
        manifest_files: Optional[Dict[str, str]] = None,
        include_dev: bool = False,
        ignore_severity: Optional[str] = None,
        verbose: bool = False,
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Run vulnerability scan using core scanner directly
        
        Args:
            path: Directory path to scan
            manifest_files: Dict of filename -> content for uploaded files
            include_dev: Include development dependencies
            ignore_severity: Severity level to ignore (CRITICAL, HIGH, MEDIUM, LOW)
            verbose: Show detailed output
            
        Returns:
            JSON output in CLI format
        """
        logger.info(f"Starting CLI scan - path: {path}, manifest_files: {list(manifest_files.keys()) if manifest_files else None}")
        logger.info(f"Scan options - include_dev: {include_dev}, ignore_severity: {ignore_severity}, verbose: {verbose}")
        
        try:
            if progress_callback:
                await progress_callback("🔧 Initializing security scanner...", 5.0)
            
            # Create scan options
            ignore_severities = []
            if ignore_severity:
                # Convert string to SeverityLevel enum
                severity_map = {
                    'critical': SeverityLevel.CRITICAL,
                    'high': SeverityLevel.HIGH,
                    'medium': SeverityLevel.MEDIUM,
                    'low': SeverityLevel.LOW
                }
                if ignore_severity.lower() in severity_map:
                    ignore_severities.append(severity_map[ignore_severity.lower()])
            
            scan_options = ScanOptions(
                include_dev_dependencies=include_dev,
                ignore_severities=ignore_severities
            )
            
            # Use DepScanner (same as CLI) for consistency
            scanner = DepScanner(verbose=verbose)
            
            # Handle path or manifest files
            if manifest_files:
                if progress_callback:
                    await progress_callback("📄 Processing your manifest files...", 10.0)
                
                # Write manifest files to temporary files so DepScanner can process them
                report = await CLIService._scan_manifest_files_with_depscanner(
                    scanner, manifest_files, scan_options, progress_callback
                )
            elif path:
                if progress_callback:
                    await progress_callback(f"Scanning repository: {path}", 10.0)
                
                # Use DepScanner with repository path (same as CLI)
                report = await scanner.scan_path(path, scan_options)
            else:
                # Scan current directory
                if progress_callback:
                    await progress_callback("Scanning current directory...", 10.0)
                
                report = await scanner.scan_path(".", scan_options)
            
            if progress_callback:
                await progress_callback("📊 Generating your security report...", 95.0)
            
            # Convert core scanner report to CLI JSON format
            result = CLIService._convert_report_to_cli_format(report, scan_options)
            
            if progress_callback:
                await progress_callback("✅ Security scan completed successfully!", 100.0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error running scan: {e}")
            logger.error(f"Scan parameters - path: {path}, manifest_files keys: {list(manifest_files.keys()) if manifest_files else None}")
            logger.error(f"Stack trace:", exc_info=True)
            
            if progress_callback:
                try:
                    await progress_callback(f"Scan failed: {str(e)}", None)
                except Exception as cb_err:
                    logger.error(f"Progress callback failed: {cb_err}")
            
            # Return error in frontend format
            return {
                "job_id": "",
                "status": "failed",
                "total_dependencies": 0,
                "vulnerable_count": 0,
                "vulnerable_packages": [],
                "dependencies": [],
                "suppressed_count": 0,
                "meta": {
                    "generated_at": datetime.now().isoformat(),
                    "ecosystems": [],
                    "scan_options": {
                        "include_dev_dependencies": include_dev,
                        "ignore_severities": [sev.value for sev in ignore_severities]
                    }
                },
                "error": str(e)
            }
    
    @staticmethod
    def _convert_report_to_cli_format(report, scan_options=None) -> Dict[str, Any]:
        """Convert core scanner Report to format expected by frontend"""
        
        # Get unique ecosystems
        ecosystems = list(set(dep.ecosystem for dep in report.dependencies))
        
        # Simple lookup for direct vs transitive
        direct_packages = {dep.name.lower() for dep in report.dependencies if dep.is_direct}
        
        # Convert dependencies to frontend format
        frontend_dependencies = []
        for dep in report.dependencies:
            frontend_dep = {
                "name": dep.name,
                "version": dep.version,
                "ecosystem": dep.ecosystem,
                "path": dep.path if dep.path else [dep.name],
                "is_direct": dep.is_direct,
                "is_dev": dep.is_dev
            }
            frontend_dependencies.append(frontend_dep)
        
        # Convert vulnerabilities to frontend format
        frontend_vulnerabilities = []
        for vuln in report.vulnerable_packages:
            # Simple classification: if package is in direct_packages, it's direct, else transitive
            is_direct = vuln.package.lower() in direct_packages
            
            # Find the dependency to get the ecosystem
            dep_match = next((d for d in report.dependencies if d.name.lower() == vuln.package.lower()), None)
            ecosystem = dep_match.ecosystem if dep_match else "unknown"
            
            frontend_vuln = {
                "package": vuln.package,
                "version": vuln.version,
                "ecosystem": ecosystem,
                "vulnerability_id": vuln.vulnerability_id,
                "severity": vuln.severity.value if vuln.severity else "UNKNOWN",
                "cvss_score": vuln.cvss_score,  # Include actual CVSS score from OSV data
                "cve_ids": vuln.cve_ids,
                "summary": vuln.summary,
                "details": vuln.details,
                "advisory_url": vuln.advisory_url,
                "fixed_range": vuln.fixed_range,
                "published": vuln.published.isoformat() if vuln.published else None,
                "modified": vuln.modified.isoformat() if vuln.modified else None,
                "aliases": vuln.aliases if vuln.aliases else [],  # Include actual aliases
                "type": "direct" if is_direct else "transitive"  # Add dependency classification
            }
            frontend_vulnerabilities.append(frontend_vuln)
        
        # Return in format expected by frontend
        return {
            "job_id": "",  # Will be set by scan service
            "status": "completed",
            "total_dependencies": report.total_dependencies,
            "vulnerable_count": report.vulnerable_count,
            "vulnerable_packages": frontend_vulnerabilities,  # Array, not count!
            "dependencies": frontend_dependencies,
            "suppressed_count": 0,  # Not implemented yet
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "ecosystems": ecosystems,
                "scan_options": {
                    "include_dev_dependencies": scan_options.include_dev_dependencies if scan_options else True,
                    "ignore_severities": [sev.value for sev in scan_options.ignore_severities] if scan_options else []
                }
            }
        }
    
    @staticmethod
    async def _scan_manifest_files_with_depscanner(
        scanner: DepScanner,
        manifest_files: Dict[str, str],
        scan_options: ScanOptions,
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ):
        """
        Write manifest files to temporary files and scan with DepScanner
        This ensures we use the exact same code path as the CLI
        """
        import tempfile
        import os
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory(prefix="depscan_web_") as temp_dir:
            temp_path = Path(temp_dir)
            
            if progress_callback:
                await progress_callback("Writing manifest files to temporary directory...", 15.0)
            
            # Write all manifest files to the temporary directory
            written_files = []
            for filename, content in manifest_files.items():
                file_path = temp_path / filename
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    written_files.append(str(file_path))
                    if progress_callback:
                        await progress_callback(f"Wrote {filename} to temporary file", None)
                    logger.info(f"Wrote {filename} to {file_path}")
                except Exception as e:
                    logger.error(f"Failed to write {filename}: {e}")
                    raise
            
            if not written_files:
                raise ValueError("No manifest files could be written")
            
            if progress_callback:
                await progress_callback(f"Processing {len(written_files)} manifest files...", 25.0)
            
            # Use scan_path method which handles both files and directories
            if len(written_files) == 1:
                logger.info(f"Scanning single file: {written_files[0]}")
                return await scanner.scan_path(written_files[0], scan_options)
            else:
                # Multiple files - scan the directory 
                logger.info(f"Scanning directory with {len(written_files)} files: {temp_path}")
                return await scanner.scan_path(str(temp_path), scan_options)
    
    @staticmethod
    def _parse_progress(line: str) -> Optional[tuple[str, float]]:
        """
        Parse progress information from CLI output
        
        Returns:
            Tuple of (message, progress_percent) or None
        """
        # Progress patterns mapped to CLI scanner stages
        patterns = [
            (r"Initializing", 5.0),
            (r"Processing.*manifest", 15.0),
            (r"Resolving dependencies", 30.0),
            (r"Found (\d+).*dependencies", 50.0),
            (r"Scanning.*dependencies", 70.0),
            (r"Generating.*report", 90.0),
            (r"completed", 100.0),
        ]
        
        for pattern, progress in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return (line.strip(), progress)
        
        return None
    
    @staticmethod
    async def run_cli_scan_async(
        path: Optional[str] = None,
        manifest_files: Optional[Dict[str, str]] = None,
        include_dev: bool = False,
        ignore_severities: Optional[list[str]] = None,
        progress_callback: Optional[Callable[[str, float], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Run CLI scan for async job-based scanning
        Converts options to match CLI interface
        """
        # Convert ignore_severities list to single value for CLI
        ignore_severity = None
        if ignore_severities and len(ignore_severities) > 0:
            # CLI accepts only one severity level to ignore
            ignore_severity = ignore_severities[0].lower()
        
        # Always use verbose mode for progress tracking
        result = await CLIService.run_cli_scan(
            path=path,
            manifest_files=manifest_files,
            include_dev=include_dev,
            ignore_severity=ignore_severity,
            verbose=True,  # Always verbose for progress
            progress_callback=progress_callback
        )
        
        return result