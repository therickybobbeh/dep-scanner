"""
Simplified JavaScript dependency resolver

This module provides a clean, easy-to-follow interface for resolving JavaScript
dependencies from various manifest and lockfile formats.
"""
import subprocess
from pathlib import Path
from typing import Union

from .base import ParseError
from .factories.js_factory import JavaScriptParserFactory
from .parsers.javascript import NpmLsParser
from .utils.scan_consistency import ScanConsistencyAnalyzer
from ..models import Dep, Ecosystem


class JavaScriptResolver:
    """
    JavaScript dependency resolver
    
    Resolves dependencies using a prioritized approach:
    1. Lockfiles (package-lock.json, yarn.lock) - Most accurate
    2. npm ls command - If node_modules exists
    3. Manifest files (package.json) - Fallback for direct deps only
    
    Example usage:
        resolver = JavaScriptResolver()
        
        # From repository directory
        deps = await resolver.resolve_dependencies("/path/to/repo")
        
        # From uploaded files
        files = {"package.json": content, "package-lock.json": content}
        deps = await resolver.resolve_dependencies(None, files)
    """
    
    def __init__(self):
        self.ecosystem: Ecosystem = "npm"
        self.parser_factory = JavaScriptParserFactory()
    
    async def resolve_dependencies(
        self, 
        repo_path: str | None, 
        manifest_files: dict[str, str] | None = None
    ) -> list[Dep]:
        """
        Resolve JavaScript dependencies from repository or manifest files
        
        Args:
            repo_path: Path to repository directory (None if using manifest_files)
            manifest_files: Dict of {filename: content} for uploaded files
            
        Returns:
            List of dependency objects with full transitive resolution when possible
            
        Raises:
            FileNotFoundError: If no supported dependency files found
            ParseError: If parsing fails
        """
        if manifest_files:
            return await self._resolve_from_uploaded_files(manifest_files)
        elif repo_path:
            return await self._resolve_from_repository(repo_path)
        else:
            raise ValueError("Either repo_path or manifest_files must be provided")
    
    async def _resolve_from_repository(self, repo_path: str) -> list[Dep]:
        """
        Resolve dependencies from a repository directory
        
        Priority order:
        1. package-lock.json (full transitive resolution)
        2. yarn.lock (full transitive resolution)  
        3. npm ls command (full transitive resolution)
        4. package.json only (direct dependencies only)
        """
        repo_path_obj = Path(repo_path)
        
        # Step 1: Try lockfiles first (most accurate)
        lockfiles = [
            ("package-lock.json", "package-lock.json"),
            ("yarn.lock", "yarn.lock")
        ]
        
        for filename, format_name in lockfiles:
            file_path = repo_path_obj / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    parser = self.parser_factory.get_parser(filename, content)
                    deps = await parser.parse(content)
                    
                    if deps:  # Successfully parsed with dependencies
                        return deps
                        
                except Exception as e:
                    # Log warning but continue to next method
                    print(f"Warning: Failed to parse {filename}: {e}")
                    continue
        
        # Step 2: Try npm ls if node_modules exists
        if self._can_use_npm_ls(repo_path):
            try:
                npm_parser = self.parser_factory.get_parser_by_format("npm-ls")
                deps = await npm_parser.parse("", repo_path=repo_path)
                
                if deps:
                    return deps
                    
            except Exception as e:
                print(f"Warning: npm ls failed: {e}")
        
        # Step 3: Fallback to package.json (direct dependencies only)
        package_json_path = repo_path_obj / "package.json"
        if package_json_path.exists():
            try:
                content = package_json_path.read_text(encoding='utf-8')
                parser = self.parser_factory.get_parser("package.json", content)
                deps = await parser.parse(content)
                
                if deps:
                    return deps
                    
            except Exception as e:
                print(f"Warning: Failed to parse package.json: {e}")
        
        raise FileNotFoundError("No JavaScript dependency files found in repository")
    
    async def _resolve_from_uploaded_files(self, manifest_files: dict[str, str]) -> list[Dep]:
        """
        Resolve dependencies from uploaded manifest files
        
        Uses the best available file format based on priority:
        1. package-lock.json (most accurate, full transitive dependencies)
        2. yarn.lock (accurate, full transitive dependencies) 
        3. package.json (direct dependencies only)
        """
        if not manifest_files:
            raise ValueError("No manifest files provided")
        
        try:
            # Detect the best format to use with clear priority
            filename, format_name = self.parser_factory.detect_best_format(manifest_files)
            content = manifest_files[filename]
            
            # Get appropriate parser and parse
            parser = self.parser_factory.get_parser(filename, content)
            deps = await parser.parse(content)
            
            return deps
            
        except Exception as e:
            raise ParseError("JavaScript manifest files", e)
    
    def _can_use_npm_ls(self, repo_path: str) -> bool:
        """
        Check if npm ls command can be used for dependency resolution
        
        Requirements:
        - package.json exists
        - node_modules directory exists  
        - npm command is available
        """
        repo_path_obj = Path(repo_path)
        
        # Check required files/directories
        if not (repo_path_obj / "package.json").exists():
            return False
        
        if not (repo_path_obj / "node_modules").exists():
            return False
        
        # Check if npm command is available
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported JavaScript dependency file formats"""
        return self.parser_factory.get_supported_formats()
    
    def can_resolve_transitive_dependencies(self, filename: str) -> bool:
        """
        Check if a file format supports full transitive dependency resolution
        
        Args:
            filename: Name of dependency file
            
        Returns:
            True if format supports transitive dependencies
        """
        transitive_formats = {
            "package-lock.json": True,
            "yarn.lock": True,
            "package.json": False  # Only direct dependencies
        }
        
        return transitive_formats.get(filename, False)
    
    def get_resolution_info(self, filename: str) -> dict[str, Union[str, bool]]:
        """
        Get information about resolution capabilities for a file format
        
        Args:
            filename: Name of dependency file
            
        Returns:
            Dict with resolution information
        """
        if filename == "package-lock.json":
            return {
                "format": "package-lock.json",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "NPM lockfile with full dependency tree and exact versions"
            }
        elif filename == "yarn.lock":
            return {
                "format": "yarn.lock", 
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "Yarn lockfile with flattened dependency tree and exact versions"
            }
        elif filename == "package.json":
            return {
                "format": "package.json",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "NPM manifest with direct dependencies and version ranges only"
            }
        else:
            return {
                "format": "unknown",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "Unsupported format"
            }
    
