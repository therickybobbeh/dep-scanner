"""
Core vulnerability scanning logic shared between CLI and web service
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .models import ScanOptions, Report, Dep, JobStatus
from .resolver import PythonResolver
from .resolver.js_resolver import JavaScriptResolver
from .scanner import OSVScanner
from .lock_generators import NpmLockGenerator, PythonLockGenerator


class CoreScanner:
    """
    Core vulnerability scanner shared between CLI and web interfaces
    
    Handles the main scanning logic:
    1. Dependency resolution (Python + JavaScript)  
    2. Vulnerability scanning with OSV.dev
    3. Result filtering and processing
    4. Report generation
    """
    
    def __init__(self):
        self.python_resolver = PythonResolver()
        self.js_resolver = JavaScriptResolver() 
        self.osv_scanner = OSVScanner()
        self.npm_lock_generator = NpmLockGenerator()
        self.python_lock_generator = PythonLockGenerator()
    
    async def scan_repository(
        self, 
        repo_path: str, 
        options: ScanOptions,
        progress_callback: Optional[callable] = None
    ) -> Report:
        """
        Scan a repository for vulnerabilities
        
        Args:
            repo_path: Path to repository to scan
            options: Scan configuration options
            progress_callback: Optional callback for progress updates
            
        Returns:
            Report with scan results
            
        Raises:
            FileNotFoundError: If repository path doesn't exist
            ValueError: If no supported dependencies found
        """
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        
        return await self._scan_dependencies(
            repo_path=repo_path,
            manifest_files=None,
            options=options,
            progress_callback=progress_callback
        )
    
    async def scan_manifest_files(
        self,
        manifest_files: dict[str, str],
        options: ScanOptions,
        progress_callback: Optional[callable] = None
    ) -> Report:
        """
        Scan from manifest file contents
        
        Args:
            manifest_files: Dict of {filename: content}
            options: Scan configuration options  
            progress_callback: Optional callback for progress updates
            
        Returns:
            Report with scan results
            
        Raises:
            ValueError: If no supported dependencies found
        """
        # Generate lock files for consistency if needed
        enhanced_manifest_files = await self._ensure_lock_files(
            manifest_files, progress_callback
        )
        
        return await self._scan_dependencies(
            repo_path=None,
            manifest_files=enhanced_manifest_files,
            options=options,
            progress_callback=progress_callback
        )
    
    async def _ensure_lock_files(
        self, 
        manifest_files: dict[str, str], 
        progress_callback: Optional[callable] = None
    ) -> dict[str, str]:
        """
        Ensure lock files exist for manifest files to improve consistency
        
        Args:
            manifest_files: Dict of {filename: content}
            progress_callback: Optional callback for progress updates
            
        Returns:
            Enhanced dict with generated lock files when possible
        """
        if progress_callback:
            progress_callback("Checking for lock file generation opportunities...")
        
        result = manifest_files.copy()
        
        # Generate NPM lock files
        try:
            if progress_callback:
                progress_callback("Generating NPM lock files if needed...")
            result = await self.npm_lock_generator.ensure_lock_file(result, progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: NPM lock generation failed: {e}")
        
        # Generate Python lock files
        try:
            if progress_callback:
                progress_callback("Generating Python lock files if needed...")
            result = await self.python_lock_generator.ensure_lock_files(result, progress_callback)
        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: Python lock generation failed: {e}")
        
        return result
    
    async def _scan_dependencies(
        self,
        repo_path: Optional[str],
        manifest_files: Optional[dict[str, str]],
        options: ScanOptions,
        progress_callback: Optional[callable] = None
    ) -> Report:
        """Core scanning logic"""
        
        if progress_callback:
            progress_callback("Resolving dependencies...")
        
        # Resolve dependencies from both ecosystems
        all_dependencies = []
        ecosystems_found = []
        
        # Try Python dependencies
        try:
            if repo_path:
                if progress_callback:
                    progress_callback("Scanning for Python dependency files...")
                py_deps = await self.python_resolver.resolve_dependencies(repo_path)
            elif manifest_files:
                py_files = {k: v for k, v in manifest_files.items() 
                          if k in ["requirements.txt", "requirements.lock", "poetry.lock", "Pipfile.lock", "pyproject.toml", "Pipfile"]}
                if py_files:
                    if progress_callback:
                        for filename in py_files.keys():
                            progress_callback(f"Processing file: {filename}")
                    py_deps = await self.python_resolver.resolve_dependencies(None, py_files)
                else:
                    py_deps = []
            else:
                py_deps = []
                
            if py_deps:
                all_dependencies.extend(py_deps)
                ecosystems_found.append("Python")
                if progress_callback:
                    progress_callback(f"Found {len(py_deps)} Python dependencies")
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: Could not resolve Python dependencies: {e}")
        
        # Try JavaScript dependencies
        try:
            if repo_path:
                if progress_callback:
                    progress_callback("Scanning for JavaScript dependency files...")
                js_deps = await self.js_resolver.resolve_dependencies(repo_path)
            elif manifest_files:
                js_files = {k: v for k, v in manifest_files.items()
                          if k in ["package.json", "package-lock.json", "yarn.lock"]}
                
                if js_files:
                    if progress_callback:
                        for filename in js_files.keys():
                            progress_callback(f"Processing file: {filename}")
                    js_deps = await self.js_resolver.resolve_dependencies(None, js_files)
                else:
                    js_deps = []
            else:
                js_deps = []
                
            if js_deps:
                all_dependencies.extend(js_deps)
                ecosystems_found.append("JavaScript")
                
                
                if progress_callback:
                    progress_callback(f"Found {len(js_deps)} JavaScript dependencies")
                
        except Exception as e:
            if progress_callback:
                progress_callback(f"Warning: Could not resolve JavaScript dependencies: {e}")
        
        if not all_dependencies:
            raise ValueError("No supported dependency files found")
        
        if progress_callback:
            progress_callback(f"Found dependencies in: {', '.join(ecosystems_found)}")
        
        # Filter dev dependencies if requested
        if not options.include_dev_dependencies:
            all_dependencies = [dep for dep in all_dependencies if not dep.is_dev]
        
        if progress_callback:
            progress_callback(f"Scanning {len(all_dependencies)} dependencies...")
        
        # Scan for vulnerabilities
        vulnerable_packages = await self.osv_scanner.scan_dependencies(all_dependencies)
        
        # Apply filtering
        if options.ignore_severities:
            vulnerable_packages = [
                vp for vp in vulnerable_packages 
                if not vp.severity or vp.severity not in options.ignore_severities
            ]
        
        suppressed_count = len([vp for vp in vulnerable_packages]) - len(vulnerable_packages)
        
        if progress_callback:
            progress_callback("Scan completed!")
        
        # Generate report
        report_meta = {
            "ecosystems": ecosystems_found,
            "scan_options": options.model_dump()
        }
        
        return Report(
            job_id=str(uuid4()),
            status=JobStatus.COMPLETED,
            total_dependencies=len(all_dependencies),
            vulnerable_count=len(vulnerable_packages),
            vulnerable_packages=vulnerable_packages,
            dependencies=all_dependencies,
            suppressed_count=suppressed_count,
            meta=report_meta
        )