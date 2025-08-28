"""
Simplified Python lock file generator

This module provides a clean, unified approach to Python dependency resolution.
For lock files: Just parse them (they already have everything)
For manifest files: Use PyPI API directly (no complex fallbacks)
"""
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
    Simplified Python lock file generator
    
    Approach:
    - Lock files already contain all dependencies - just return them
    - Manifest files: Query PyPI API for dependency info (simple and reliable)
    - No complex fallback chains - one approach per file type
    """
    
    def __init__(self):
        pass  # No need to track pip availability anymore
    
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
        
        # For manifest files, generate requirements.lock
        try:
            dependencies = self._extract_dependencies_from_manifests(manifest_files)
            
            if dependencies:
                # Generate requirements.lock using simple PyPI queries
                lock_content = await self._generate_requirements_lock_simple(dependencies)
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
        Extract dependency list from various Python manifest formats
        Simple extraction - no complex parsing needed
        """
        dependencies = []
        
        # Priority: requirements.txt > pyproject.toml > Pipfile
        if "requirements.txt" in manifest_files:
            dependencies.extend(self._parse_requirements_txt(manifest_files["requirements.txt"]))
        elif "pyproject.toml" in manifest_files:
            dependencies.extend(self._parse_pyproject_toml(manifest_files["pyproject.toml"]))
        elif "Pipfile" in manifest_files:
            dependencies.extend(self._parse_pipfile(manifest_files["Pipfile"]))
        
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
    
    def _parse_pyproject_toml(self, content: str) -> list[str]:
        """Simple pyproject.toml parser"""
        try:
            import toml
            data = toml.loads(content)
            
            # Check for dependencies in standard location
            if "project" in data and "dependencies" in data["project"]:
                return data["project"]["dependencies"]
            
            # Fallback to build-system requires
            if "build-system" in data and "requires" in data["build-system"]:
                return data["build-system"]["requires"]
            
        except Exception as e:
            logger.warning(f"Error parsing pyproject.toml: {e}")
        
        return []
    
    def _parse_pipfile(self, content: str) -> list[str]:
        """Simple Pipfile parser"""
        try:
            import toml
            data = toml.loads(content)
            dependencies = []
            
            if "packages" in data:
                for package, version in data["packages"].items():
                    if isinstance(version, str) and version != "*":
                        if version.startswith("=="):
                            dependencies.append(f"{package}{version}")
                        else:
                            dependencies.append(f"{package}=={version}")
                    else:
                        dependencies.append(package)
            
            return dependencies
            
        except Exception as e:
            logger.warning(f"Error parsing Pipfile: {e}")
            return []
    
    async def _generate_requirements_lock_simple(self, dependencies: list[str]) -> Optional[str]:
        """
        Generate requirements.lock using simple PyPI API queries
        No complex fallbacks - just query PyPI directly
        """
        if not dependencies:
            return None
        
        lines = [
            "# Generated by dep-scan using PyPI API",
            "# This file contains resolved dependencies with exact versions",
            "# Direct dependencies are marked with # direct, transitive with # transitive",
            "#"
        ]
        
        resolved = {}
        direct_packages = set()
        
        # First pass: Resolve direct dependencies
        for dep in dependencies:
            package_name, version = self._parse_dependency_spec(dep)
            if package_name:
                direct_packages.add(package_name.lower())
                
                # Get exact version from PyPI
                if not version or not version.startswith("=="):
                    version = await self._get_latest_version_from_pypi(package_name)
                else:
                    version = version[2:]  # Remove ==
                
                if version:
                    resolved[package_name] = version
        
        # Second pass: Get transitive dependencies (simple approach)
        transitive = {}
        for package_name in list(resolved.keys()):
            package_deps = await self._get_package_dependencies_from_pypi(package_name, resolved[package_name])
            for dep_name, dep_version in package_deps.items():
                if dep_name.lower() not in direct_packages and dep_name not in transitive:
                    transitive[dep_name] = dep_version
        
        # Build the output
        # Direct dependencies first
        for name in sorted(resolved.keys()):
            lines.append(f"{name}=={resolved[name]}  # direct")
        
        # Then transitive
        for name in sorted(transitive.keys()):
            lines.append(f"{name}=={transitive[name]}  # transitive")
        
        return '\n'.join(lines)
    
    def _parse_dependency_spec(self, dep: str) -> tuple[str, str]:
        """Parse dependency spec like 'django==3.2.13' -> ('django', '==3.2.13')"""
        dep = dep.strip()
        
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
            url = f"https://pypi.org/pypi/{package_name}/{version}/json"
            request = urllib.request.Request(url)
            request.add_header('User-Agent', 'dep-scan/1.0')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    deps = {}
                    
                    requires_dist = data.get('info', {}).get('requires_dist', [])
                    if requires_dist:
                        for req_str in requires_dist[:10]:  # Limit to first 10 to keep it simple
                            if req_str and ';' not in req_str:  # Skip conditional deps
                                dep_name, dep_version = self._parse_dependency_spec(req_str)
                                if dep_name:
                                    # Just use latest version for simplicity
                                    if not dep_version or not dep_version.startswith("=="):
                                        dep_version = await self._get_latest_version_from_pypi(dep_name)
                                    else:
                                        dep_version = dep_version[2:]
                                    
                                    if dep_version:
                                        deps[dep_name] = dep_version
                    
                    return deps
                    
        except Exception as e:
            logger.debug(f"Could not get dependencies for {package_name}: {e}")
        
        return {}
    
    def _create_simple_requirements_lock(self, dependencies: list[str]) -> str:
        """Create simple requirements.lock as fallback"""
        lines = [
            "# Generated by dep-scan (simple format)",
            "# Only direct dependencies available",
            "#"
        ]
        lines.extend(dependencies)
        return '\n'.join(lines)


# Global instance
python_lock_generator = PythonLockGenerator()