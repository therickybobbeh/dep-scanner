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
    
    def __init__(
        self, 
        enhanced_package_json: bool = False, 
        resolve_versions: bool = False,
        enable_transitive: bool = False,
        cache_control: dict = None
    ):
        self.ecosystem: Ecosystem = "npm"
        self.enhanced_package_json = enhanced_package_json
        self.resolve_versions = resolve_versions
        self.enable_transitive = enable_transitive
        self.cache_control = cache_control or {}
        
        self.parser_factory = JavaScriptParserFactory(
            use_enhanced_package_json=enhanced_package_json,
            resolve_versions=resolve_versions,
            enable_transitive=enable_transitive
        )
    
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
        
        Uses the best available file format based on priority
        """
        if not manifest_files:
            raise ValueError("No manifest files provided")
        
        try:
            # Detect the best format to use
            filename, format_name = self.parser_factory.detect_best_format(manifest_files)
            content = manifest_files[filename]
            
            # Get appropriate parser and parse
            parser = self.parser_factory.get_parser(filename, content)
            
            # Prepare parse options based on cache control
            parse_kwargs = {}
            if self.cache_control:
                parse_kwargs.update({
                    "bypass_cache": self.cache_control.get("bypass_cache", False),
                    "enable_transitive": self.cache_control.get("use_enhanced_resolution", False) or self.enable_transitive,
                    "resolve_versions": self.resolve_versions or self.cache_control.get("use_enhanced_resolution", False)
                })
            
            deps = await parser.parse(content, **parse_kwargs)
            
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
    
    async def resolve_with_consistency_check(
        self, 
        manifest_files: dict[str, str],
        check_consistency: bool = True
    ) -> tuple[list[Dep], dict]:
        """
        Resolve dependencies with optional consistency checking between formats
        
        Args:
            manifest_files: Dict of {filename: content} for uploaded files
            check_consistency: Whether to perform consistency analysis
            
        Returns:
            Tuple of (best_dependencies, consistency_report)
        """
        if not manifest_files:
            raise ValueError("No manifest files provided")
        
        results = {}
        consistency_report = {"enabled": check_consistency}
        
        # Try to parse with both approaches if both files are available
        if "package.json" in manifest_files and check_consistency:
            # Parse with standard package.json parser
            try:
                standard_parser = self.parser_factory.get_parser_by_format("package-json")
                standard_deps = await standard_parser.parse(manifest_files["package.json"])
                results["standard_package_json"] = standard_deps
            except Exception as e:
                results["standard_package_json_error"] = str(e)
            
            # Parse with enhanced package.json parser if available
            if self.enhanced_package_json:
                try:
                    enhanced_parser = self.parser_factory.get_parser_by_format("package-json-enhanced")
                    enhanced_deps = await enhanced_parser.parse(
                        manifest_files["package.json"], 
                        resolve_versions=True
                    )
                    results["enhanced_package_json"] = enhanced_deps
                except Exception as e:
                    results["enhanced_package_json_error"] = str(e)
        
        # Parse lockfile if available
        for lockfile in ["package-lock.json", "yarn.lock"]:
            if lockfile in manifest_files:
                try:
                    parser = self.parser_factory.get_parser(lockfile, manifest_files[lockfile])
                    lockfile_deps = await parser.parse(manifest_files[lockfile])
                    results[lockfile.replace(".", "_").replace("-", "_")] = lockfile_deps
                except Exception as e:
                    results[f"{lockfile}_error"] = str(e)
        
        # Determine best result using priority order
        best_deps = None
        best_source = None
        
        priority_order = [
            ("package_lock_json", "package-lock.json"),
            ("yarn_lock", "yarn.lock"),
            ("enhanced_package_json", "enhanced package.json"),
            ("standard_package_json", "package.json")
        ]
        
        for key, source_name in priority_order:
            if key in results and isinstance(results[key], list):
                best_deps = results[key]
                best_source = source_name
                break
        
        if best_deps is None:
            raise ParseError("JavaScript resolver", "No valid dependency files could be parsed")
        
        # Perform consistency analysis if requested and multiple results available
        if check_consistency and len([k for k in results.keys() if not k.endswith("_error")]) > 1:
            analyzer = ScanConsistencyAnalyzer()
            
            # Compare manifest vs lockfile if both available
            manifest_deps = results.get("enhanced_package_json") or results.get("standard_package_json")
            lockfile_deps = results.get("package_lock_json") or results.get("yarn_lock")
            
            if manifest_deps and lockfile_deps:
                comparison = analyzer.compare_dependency_lists(manifest_deps, lockfile_deps)
                consistency_report["manifest_vs_lockfile"] = {
                    "consistency_score": comparison.consistency_score,
                    "matching_dependencies": comparison.matching_dependencies,
                    "version_mismatches": comparison.version_mismatches,
                    "missing_in_manifest": comparison.missing_in_manifest,
                    "missing_in_lockfile": comparison.missing_in_lockfile,
                    "recommendations": comparison.recommendations
                }
            
            # Compare standard vs enhanced package.json parsing if both available
            if "standard_package_json" in results and "enhanced_package_json" in results:
                standard_deps = results["standard_package_json"]
                enhanced_deps = results["enhanced_package_json"]
                
                enhanced_comparison = analyzer.compare_dependency_lists(standard_deps, enhanced_deps)
                consistency_report["standard_vs_enhanced"] = {
                    "consistency_score": enhanced_comparison.consistency_score,
                    "version_resolution_differences": enhanced_comparison.version_mismatches,
                    "recommendations": enhanced_comparison.recommendations
                }
        
        consistency_report.update({
            "best_source": best_source,
            "available_sources": list(results.keys()),
            "parsing_errors": {k: v for k, v in results.items() if k.endswith("_error")}
        })
        
        return best_deps, consistency_report