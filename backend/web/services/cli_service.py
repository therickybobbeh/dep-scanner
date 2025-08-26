"""Service for running CLI commands and returning results"""
import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


class CLIService:
    """Service to execute dep-scan CLI and return results"""
    
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
        Run dep-scan CLI command and return JSON results
        
        Args:
            path: Directory path to scan
            manifest_files: Dict of filename -> content for uploaded files
            include_dev: Include development dependencies
            ignore_severity: Severity level to ignore (CRITICAL, HIGH, MEDIUM, LOW)
            verbose: Show detailed output
            
        Returns:
            JSON output from CLI command
        """
        temp_dir = None
        try:
            # Build command arguments
            cmd = ["dep-scan", "scan"]
            
            # Handle path or manifest files
            if manifest_files:
                # Create temp directory with uploaded files
                temp_dir = tempfile.mkdtemp(prefix="depscan_")
                for filename, content in manifest_files.items():
                    file_path = Path(temp_dir) / filename
                    file_path.write_text(content)
                scan_path = temp_dir
            elif path:
                scan_path = path
            else:
                scan_path = "."
            
            cmd.append(scan_path)
            
            # Add JSON output to temp file
            json_output = tempfile.NamedTemporaryFile(
                mode='w+', 
                suffix='.json', 
                delete=False
            )
            cmd.extend(["--json", json_output.name])
            
            # Add optional flags
            if include_dev:
                cmd.append("--include-dev")
            if ignore_severity:
                cmd.extend(["--ignore-severity", ignore_severity])
            if verbose:
                cmd.append("--verbose")
            
            # Run CLI command with progress monitoring
            logger.info(f"Running CLI command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Parse progress from stderr if callback provided
            if progress_callback and verbose:
                stderr_text = ""
                stdout_text = ""
                
                # Read stderr line by line for progress
                async def read_stream(stream, is_stderr=False):
                    nonlocal stderr_text, stdout_text
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        text = line.decode('utf-8', errors='ignore')
                        if is_stderr:
                            stderr_text += text
                            # Parse progress from stderr
                            progress = CLIService._parse_progress(text)
                            if progress:
                                await progress_callback(progress[0], progress[1] or 0.0)
                        else:
                            stdout_text += text
                
                # Read both streams concurrently
                await asyncio.gather(
                    read_stream(process.stderr, is_stderr=True),
                    read_stream(process.stdout, is_stderr=False)
                )
                
                await process.wait()
                stdout = stdout_text.encode()
                stderr = stderr_text.encode()
            else:
                stdout, stderr = await process.communicate()
            
            # Read JSON output
            json_output.seek(0)
            result = json.load(json_output)
            
            # Add metadata
            result["cli_exit_code"] = process.returncode
            result["cli_stdout"] = stdout.decode() if stdout else ""
            result["cli_stderr"] = stderr.decode() if stderr else ""
            
            # Clean up temp file
            json_output.close()
            Path(json_output.name).unlink(missing_ok=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Error running CLI scan: {e}")
            raise
        finally:
            # Clean up temp directory if created
            if temp_dir:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    
    @staticmethod
    def _parse_progress(line: str) -> Optional[tuple[str, float]]:
        """
        Parse progress information from CLI output
        
        Returns:
            Tuple of (message, progress_percent) or None
        """
        # Common progress patterns in CLI output
        patterns = [
            (r"Starting scan", 5.0),
            (r"Found (\d+) (Python|JavaScript) dependencies", 15.0),
            (r"Processing file: (.+)", 25.0),
            (r"Scanning file: (.+)", 35.0),
            (r"Resolving dependencies", 45.0),
            (r"Scanning (\d+) dependencies", 60.0),
            (r"Checking for vulnerabilities", 75.0),
            (r"Scan completed", 95.0),
        ]
        
        for pattern, progress in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return (line.strip(), progress)
        
        # Generic progress for any meaningful output
        if line.strip() and not line.startswith("DEBUG"):
            return (line.strip(), None)
        
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