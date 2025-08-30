"""
Python lock file generator using PyPI API

This module provides a simple, reliable approach to Python dependency resolution:
- For lock files (poetry.lock, Pipfile.lock): Return as-is (already resolved)
- For requirements.txt: Query PyPI API directly for dependency resolution
- No external tool dependencies (pip-compile, pip-tools, etc.)
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional
import urllib.request
import urllib.error

from ..temp_file_manager import temp_manager

logger = logging.getLogger(__name__)


class PythonLockGenerator:
    """
    Python lock file generator using PyPI API
    
    Approach:
    - Lock files already contain all dependencies - return as-is
    - requirements.txt: Query PyPI API directly for complete dependency tree
    - No external dependencies or subprocess calls
    - Consistent behavior across all environments
    """
    
    def __init__(self):
        pass  # No external dependencies needed
    
    async def ensure_lock_files(self, manifest_files: Dict[str, str], progress_callback: Optional[callable] = None) -> Dict[str, str]:
        """
        Ensure requirements.lock exists for consistent dependency resolution
        
        For lock files: Return as-is (they're already complete)
        For manifest files: Generate requirements.lock using PyPI API
        """
        result = manifest_files.copy()
        
        # If we already have a lock file, we're done
        lock_files = ["requirements.lock", "poetry.lock", "Pipfile.lock"]
        if any(f in manifest_files for f in lock_files):
            if progress_callback:
                progress_callback("Lock file found, using existing resolution")
            else:
                logger.info("Lock file found, using existing resolution")
            return result
        
        # Check if any file looks like a pip-compile generated lockfile (has "# via" comments)
        for filename, content in manifest_files.items():
            if "requirements" in filename.lower() and filename.endswith(".txt") and "# via " in content:
                # This appears to be a pip-compile generated lockfile, treat as requirements.lock
                result["requirements.lock"] = content
                if progress_callback:
                    progress_callback("pip-compile lockfile detected, using as requirements.lock")
                else:
                    logger.info("pip-compile lockfile detected, using as requirements.lock")
                return result
        
        # For manifest files, generate requirements.lock
        try:
            dependencies = self._extract_dependencies_from_manifests(manifest_files)
            
            if dependencies:
                # Generate requirements.lock using PyPI API
                lock_content = await self._generate_requirements_lock(dependencies)
                if lock_content:
                    result["requirements.lock"] = lock_content
                    if progress_callback:
                        progress_callback("Successfully generated requirements.lock")
                    else:
                        logger.info("Successfully generated requirements.lock")
                else:
                    logger.warning("Could not generate requirements.lock")
            else:
                logger.warning("No dependencies found in manifest files")
                
        except Exception as e:
            logger.warning(f"Error generating requirements.lock: {e}")
        
        return result
    
    # Alias for compatibility
    async def ensure_requirements_lock(self, manifest_files: Dict[str, str]) -> Dict[str, str]:
        return await self.ensure_lock_files(manifest_files)
    
    def _extract_dependencies_from_manifests(self, manifest_files: Dict[str, str]) -> list[str]:
        """
        Extract dependency list from requirements.txt or similar files
        
        Simplified to only support requirements-style files.
        Lock files (poetry.lock, Pipfile.lock) are handled separately as they
        already contain resolved dependencies.
        """
        dependencies = []
        
        # Support requirements.txt and similar files
        for filename, content in manifest_files.items():
            if (filename == "requirements.txt" or 
                ("requirements" in filename.lower() and filename.endswith(".txt"))):
                dependencies.extend(self._parse_requirements_txt(content))
        
        return list(dict.fromkeys(dependencies))  # Remove duplicates
    
    def _parse_requirements_txt(self, content: str) -> list[str]:
        """Simple requirements.txt parser"""
        dependencies = []
        
        for line in content.strip().split('\n'):
            line = line.strip()
            
            # Skip empty lines, comments, and options
            if not line or line.startswith('#') or line.startswith('-'):
                continue
            
            # Remove inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
            
            if line:
                dependencies.append(line)
        
        return dependencies
    
    
    async def _generate_requirements_lock(self, dependencies: list[str]) -> Optional[str]:
        """
        Generate requirements.lock using PyPI API for dependency resolution
        
        This method queries PyPI directly to resolve all dependencies including
        transitive ones, creating a complete lock file with exact versions.
        """
        if not dependencies:
            return None
        
        # Generate lock file using PyPI API
        lines = [
            "# Generated by dep-scan using PyPI API",
            "# This file contains all resolved dependencies with exact versions",
            "#"
        ]
        
        resolved = {}
        direct_packages = set()
        
        # Resolve direct dependencies
        for dep in dependencies:
            package_name, version = self._parse_dependency_spec(dep)
            if package_name:
                direct_packages.add(package_name.lower())
                
                if not version or not version.startswith("=="):
                    version = await self._get_latest_version_from_pypi(package_name)
                else:
                    version = version[2:]
                
                if version:
                    resolved[package_name] = version
        
        # Get transitive dependencies - no limit!
        transitive = {}
        to_process = list(resolved.keys())
        processed = set()
        
        while to_process:
            package_name = to_process.pop(0)
            if package_name in processed:
                continue
            processed.add(package_name)
            
            package_deps = await self._get_package_dependencies_from_pypi(package_name, resolved.get(package_name, ""))
            for dep_name, dep_version in package_deps.items():
                if dep_name.lower() not in direct_packages and dep_name not in transitive:
                    transitive[dep_name] = dep_version
                    to_process.append(dep_name)
        
        # Build output
        for name in sorted(resolved.keys()):
            lines.append(f"{name}=={resolved[name]}  # direct")
        
        for name in sorted(transitive.keys()):
            lines.append(f"{name}=={transitive[name]}  # transitive")
        
        return '\n'.join(lines)
    
    def _parse_dependency_spec(self, dep: str) -> tuple[str, str]:
        """Parse dependency spec like 'django==3.2.13' -> ('django', '==3.2.13')"""
        dep = dep.strip()
        
        # Handle parentheses - extract package name before any operator
        if '(' in dep:
            package_name = dep.split('(')[0].strip()
            return package_name, ""  # Just return package name for complex specs
        
        # Handle simple operators
        for op in ["==", ">=", "<=", ">", "<", "~=", "!="]:
            if op in dep:
                parts = dep.split(op, 1)
                if len(parts) == 2:
                    return parts[0].strip(), f"{op}{parts[1].strip()}"
        
        return dep, ""
    
    async def _get_latest_version_from_pypi(self, package_name: str) -> Optional[str]:
        """Get latest version from PyPI JSON API - simple and direct"""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'dep-scan/1.0')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return data.get('info', {}).get('version')
        except Exception as e:
            logger.debug(f"Could not get version for {package_name}: {e}")
        
        return None
    
    async def _get_package_dependencies_from_pypi(self, package_name: str, version: str) -> dict[str, str]:
        """Get package dependencies from PyPI - simple approach"""
        try:
            # Try specific version first, then fall back to latest
            urls = []
            if version:
                urls.append(f"https://pypi.org/pypi/{package_name}/{version}/json")
            urls.append(f"https://pypi.org/pypi/{package_name}/json")
            
            for url in urls:
                try:
                    request = urllib.request.Request(url)
                    request.add_header('User-Agent', 'dep-scan/1.0')
                    
                    with urllib.request.urlopen(request, timeout=10) as response:
                        if response.status == 200:
                            data = json.loads(response.read().decode())
                            deps = {}
                            
                            requires_dist = data.get('info', {}).get('requires_dist', [])
                            if requires_dist:
                                for req_str in requires_dist:  # No limit - get all dependencies
                                    if req_str:
                                        # Check if this is a conditional dependency (extra feature)
                                        if 'extra ==' in req_str:
                                            continue  # Skip extra dependencies
                                        
                                        # Clean the requirement string - remove environment markers
                                        clean_req = req_str.split(';')[0].strip()
                                        dep_name, dep_version = self._parse_dependency_spec(clean_req)
                                        
                                        if dep_name and dep_name.lower() not in ['setuptools', 'wheel', 'pip']:
                                            # Just use latest version for simplicity
                                            if not dep_version or not dep_version.startswith("=="):
                                                dep_version = await self._get_latest_version_from_pypi(dep_name)
                                            else:
                                                dep_version = dep_version[2:]
                                            
                                            if dep_version:
                                                deps[dep_name] = dep_version
                            
                            return deps
                except Exception:
                    continue  # Try next URL
                    
        except Exception as e:
            logger.debug(f"Could not get dependencies for {package_name}: {e}")
        
        return {}
    


# Global instance
python_lock_generator = PythonLockGenerator()