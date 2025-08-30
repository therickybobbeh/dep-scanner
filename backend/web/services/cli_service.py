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

from ...core.core_scanner import CoreScanner
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
        scanner = CoreScanner()
        
        try:
            if progress_callback:
                await progress_callback("Initializing vulnerability scanner...", 5.0)
            
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
            
            # Setup progress callback for core scanner
            def sync_progress_callback(message: str, percent: Optional[float] = None):
                # Convert to sync callback since core scanner may not handle async properly
                if progress_callback:
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Create a task if we're already in an async context
                            asyncio.create_task(progress_callback(message, percent))
                        else:
                            # Run directly if no event loop is running
                            loop.run_until_complete(progress_callback(message, percent))
                    except RuntimeError:
                        # Fallback: just log the message
                        logger.info(f"Progress: {message} ({percent}%)")
            
            async def async_progress_callback(message: str, percent: Optional[float] = None):
                if progress_callback:
                    await progress_callback(message, percent)
            
            # Handle path or manifest files
            if manifest_files:
                if progress_callback:
                    await progress_callback("Processing uploaded manifest files...", 10.0)
                
                # Use core scanner with manifest files
                report = await scanner.scan_manifest_files(
                    manifest_files=manifest_files,
                    options=scan_options,
                    progress_callback=sync_progress_callback
                )
            elif path:
                if progress_callback:
                    await progress_callback(f"Scanning repository: {path}", 10.0)
                
                # Use core scanner with repository path
                report = await scanner.scan_repository(
                    repo_path=path,
                    options=scan_options,
                    progress_callback=sync_progress_callback
                )
            else:
                # Scan current directory
                if progress_callback:
                    await progress_callback("Scanning current directory...", 10.0)
                
                report = await scanner.scan_repository(
                    repo_path=".",
                    options=scan_options,
                    progress_callback=sync_progress_callback
                )
            
            if progress_callback:
                await progress_callback("Generating scan report...", 95.0)
            
            # Convert core scanner report to CLI JSON format
            result = CLIService._convert_report_to_cli_format(report)
            
            if progress_callback:
                await progress_callback("Scan completed", 100.0)
            
            return result
            
        except Exception as e:
            logger.error(f"Error running scan: {e}")
            
            # Return error in CLI format
            return {
                "scan_info": {
                    "total_dependencies": 0,
                    "vulnerable_packages": 0,
                    "ecosystems": []
                },
                "vulnerabilities": [],
                "meta": {
                    "generated_at": datetime.now().isoformat(),
                    "scan_options": {
                        "include_dev_dependencies": include_dev,
                        "ignore_severities": [sev.value for sev in ignore_severities]
                    },
                    "error": str(e)
                },
                "cli_exit_code": 1,
                "cli_stdout": "",
                "cli_stderr": str(e)
            }
    
    @staticmethod
    def _convert_report_to_cli_format(report) -> Dict[str, Any]:
        """Convert core scanner Report to CLI JSON format"""
        
        # Get unique ecosystems
        ecosystems = list(set(dep.ecosystem for dep in report.dependencies))
        
        # Simple lookup for direct vs transitive
        direct_packages = {dep.name.lower() for dep in report.dependencies if dep.is_direct}
        
        # Convert vulnerabilities to CLI format
        cli_vulnerabilities = []
        for vuln in report.vulnerable_packages:
            # Simple classification: if package is in direct_packages, it's direct, else transitive
            is_direct = vuln.package.lower() in direct_packages
            
            # Find the dependency to get the actual path
            dep_match = next((d for d in report.dependencies if d.name.lower() == vuln.package.lower()), None)
            dependency_path = dep_match.path if dep_match and dep_match.path else [vuln.package]
            
            cli_vuln = {
                "package": vuln.package,
                "version": vuln.version,
                "vulnerability_id": vuln.vulnerability_id,
                "severity": vuln.severity.value if vuln.severity else "UNKNOWN",
                "summary": vuln.summary,
                "cve_ids": vuln.cve_ids,
                "advisory_url": vuln.advisory_url,
                "type": "direct" if is_direct else "transitive",
                "dependency_path": dependency_path,
                "fixed_range": vuln.fixed_range,
                "details": vuln.details,
                "published": vuln.published.isoformat() if vuln.published else None,
                "modified": vuln.modified.isoformat() if vuln.modified else None
            }
            cli_vulnerabilities.append(cli_vuln)
        
        return {
            "scan_info": {
                "total_dependencies": report.total_dependencies,
                "vulnerable_packages": report.vulnerable_count,
                "ecosystems": ecosystems
            },
            "vulnerabilities": cli_vulnerabilities,
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "scan_options": {
                    "include_dev_dependencies": True,  # TODO: Get from actual options
                    "ignore_severities": []
                }
            },
            "cli_exit_code": 0,
            "cli_stdout": "",
            "cli_stderr": ""
        }
    
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