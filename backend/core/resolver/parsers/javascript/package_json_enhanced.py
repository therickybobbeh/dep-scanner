"""
Enhanced Parser for package.json manifest files

This parser can optionally resolve version ranges to actual versions
and provide better consistency with lockfile-based scanning.
"""
import json
from typing import Optional, Dict, List
import logging

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ...utils.npm_version_resolver import PackageVersionResolver, ResolvedVersion
from ...utils.npm_transitive_resolver import NpmTransitiveDependencyResolver
from ....models import Dep

logger = logging.getLogger(__name__)


class EnhancedPackageJsonParser(BaseDependencyParser):
    """
    Enhanced parser for package.json manifest files
    
    Features:
    - Version range resolution using npm registry
    - Optional transitive dependency simulation
    - Consistent version handling with lockfiles
    - Fallback modes for offline usage
    """
    
    def __init__(
        self, 
        resolve_versions: bool = False, 
        use_registry: bool = True,
        enable_transitive: bool = False,
        max_depth: int = 10
    ):
        super().__init__(ecosystem="npm")
        self.version_cleaner = VersionCleaner()
        self.resolve_versions = resolve_versions
        self.use_registry = use_registry
        self.enable_transitive = enable_transitive
        self.max_depth = max_depth
        self._version_resolver: Optional[PackageVersionResolver] = None
        self._transitive_resolver: Optional[NpmTransitiveDependencyResolver] = None
        
        if self.resolve_versions:
            self._version_resolver = PackageVersionResolver()
            
        if self.enable_transitive:
            self._transitive_resolver = NpmTransitiveDependencyResolver(
                max_depth=max_depth,
                include_dev_deps=True,  # Will be controlled by parse kwargs
                include_peer_deps=False
            )
    
    @property
    def supported_formats(self) -> list[str]:
        return ["package.json"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse package.json content with optional version resolution
        
        Args:
            content: Raw package.json content
            **kwargs: Additional parsing options
                - include_dev: Whether to include dev dependencies (default: True)
                - resolve_versions: Override instance setting for version resolution
                - use_registry: Override instance setting for registry usage
                - max_concurrent: Max concurrent registry requests (default: 10)
            
        Returns:
            List of dependency objects with resolved versions when possible
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            package_data = json.loads(content)
            deps = []
            
            # Extract options
            include_dev = kwargs.get("include_dev", True)
            resolve_versions = kwargs.get("resolve_versions", self.resolve_versions)
            use_registry = kwargs.get("use_registry", self.use_registry)
            max_concurrent = kwargs.get("max_concurrent", 10)
            enable_transitive = kwargs.get("enable_transitive", self.enable_transitive)
            bypass_cache = kwargs.get("bypass_cache", False)
            
            # Check if transitive resolution is requested and available
            if enable_transitive and self._transitive_resolver and use_registry:
                logger.info("Attempting transitive dependency resolution")
                
                try:
                    # Configure transitive resolver based on options
                    self._transitive_resolver.include_dev_deps = include_dev
                    self._transitive_resolver.include_peer_deps = False  # For now
                    
                    # Use transitive resolver with timeout
                    result = await self._transitive_resolver.resolve_transitive_dependencies(
                        content,
                        use_registry=use_registry,
                        bypass_cache=bypass_cache,
                        timeout_seconds=120  # 2 minute timeout for web requests
                    )
                    
                    if result.errors:
                        logger.warning(f"Transitive resolution had errors: {result.errors}")
                        
                        # If we have some dependencies despite errors, use them
                        if result.dependencies:
                            logger.info(f"Returning {len(result.dependencies)} dependencies despite errors")
                            logger.info(f"Transitive resolution stats: {result.resolution_stats}")
                            return result.dependencies
                        else:
                            logger.warning("Transitive resolution failed completely, falling back to direct dependencies")
                    else:
                        logger.info(f"Transitive resolution successful: {len(result.dependencies)} dependencies")
                        logger.info(f"Resolution stats: {result.resolution_stats}")
                        return result.dependencies
                        
                except Exception as e:
                    logger.error(f"Transitive resolution failed with exception: {e}")
                    logger.info("Falling back to direct dependencies only")
                    
                # Fall through to standard resolution if transitive failed
            
            # Fall back to standard resolution
            logger.info("Using standard dependency resolution")
            
            # Collect all dependencies for batch resolution
            all_deps_for_resolution = {}
            dependencies_info = []
            
            # Parse production dependencies
            prod_deps = package_data.get("dependencies", {})
            for name, version_spec in prod_deps.items():
                if resolve_versions:
                    all_deps_for_resolution[name] = version_spec
                
                dependencies_info.append({
                    "name": name,
                    "version_spec": version_spec,
                    "is_dev": False,
                    "is_peer": False
                })
            
            # Parse development dependencies if requested
            if include_dev:
                dev_deps = package_data.get("devDependencies", {})
                for name, version_spec in dev_deps.items():
                    if resolve_versions:
                        all_deps_for_resolution[name] = version_spec
                    
                    dependencies_info.append({
                        "name": name,
                        "version_spec": version_spec,
                        "is_dev": True,
                        "is_peer": False
                    })
            
            # Parse peer dependencies
            peer_deps = package_data.get("peerDependencies", {})
            for name, version_spec in peer_deps.items():
                if resolve_versions:
                    all_deps_for_resolution[name] = version_spec
                
                dependencies_info.append({
                    "name": name,
                    "version_spec": version_spec,
                    "is_dev": False,
                    "is_peer": True
                })
            
            # Resolve versions if requested
            resolved_versions = {}
            if resolve_versions and all_deps_for_resolution and self._version_resolver:
                try:
                    resolved_versions = await self._version_resolver.resolve_multiple(
                        all_deps_for_resolution,
                        use_registry=use_registry,
                        max_concurrent=max_concurrent
                    )
                    logger.info(f"Resolved {len(resolved_versions)} package versions")
                except Exception as e:
                    logger.warning(f"Version resolution failed, falling back to range cleaning: {e}")
            
            # Create dependency objects
            for dep_info in dependencies_info:
                name = dep_info["name"]
                version_spec = dep_info["version_spec"]
                
                # Use resolved version if available
                if name in resolved_versions:
                    resolved = resolved_versions[name]
                    final_version = resolved.resolved_version
                    
                    # Add resolution metadata
                    metadata = {
                        "original_range": resolved.original_range,
                        "resolution_source": resolved.source
                    }
                    if resolved.metadata:
                        metadata.update(resolved.metadata)
                else:
                    # Fall back to version cleaning
                    final_version = self.version_cleaner.clean_npm_version(version_spec)
                    metadata = {
                        "original_range": version_spec,
                        "resolution_source": "cleaned"
                    }
                
                dep = self._create_dependency(
                    name=name,
                    version=final_version,
                    path=[name],
                    is_direct=True,
                    is_dev=dep_info["is_dev"]
                )
                
                # Store resolution metadata for debugging
                if hasattr(dep, '_metadata'):
                    dep._metadata.update(metadata)
                else:
                    dep._metadata = metadata
                
                deps.append(dep)
            
            return deps
            
        except json.JSONDecodeError as e:
            raise ParseError("package.json", e)
        except Exception as e:
            raise ParseError("package.json enhanced", e)
    
    async def parse_with_consistency_check(
        self, 
        content: str, 
        lockfile_content: Optional[str] = None,
        **kwargs
    ) -> tuple[list[Dep], Dict]:
        """
        Parse package.json with consistency checking against a lockfile
        
        Args:
            content: Raw package.json content
            lockfile_content: Optional lockfile content for comparison
            **kwargs: Additional parsing options
            
        Returns:
            Tuple of (dependencies, consistency_report)
        """
        deps = await self.parse(content, resolve_versions=True, **kwargs)
        
        consistency_report = {
            "total_dependencies": len(deps),
            "resolved_versions": 0,
            "fallback_versions": 0,
            "version_differences": [],
            "resolution_sources": {}
        }
        
        # Analyze resolution results
        for dep in deps:
            metadata = getattr(dep, '_metadata', {})
            source = metadata.get('resolution_source', 'unknown')
            
            if source in consistency_report["resolution_sources"]:
                consistency_report["resolution_sources"][source] += 1
            else:
                consistency_report["resolution_sources"][source] = 1
            
            if source == "registry":
                consistency_report["resolved_versions"] += 1
            elif source in ["cleaned", "fallback"]:
                consistency_report["fallback_versions"] += 1
        
        # Compare with lockfile if provided
        if lockfile_content:
            consistency_report["lockfile_comparison"] = await self._compare_with_lockfile(
                deps, lockfile_content
            )
        
        return deps, consistency_report
    
    async def _compare_with_lockfile(self, deps: List[Dep], lockfile_content: str) -> Dict:
        """Compare resolved versions with those in a lockfile"""
        try:
            lockfile_data = json.loads(lockfile_content)
            comparison = {
                "matching_versions": 0,
                "different_versions": 0,
                "missing_in_lockfile": 0,
                "differences": []
            }
            
            # Get lockfile versions (handle both v1 and v2 formats)
            lockfile_versions = {}
            
            if "dependencies" in lockfile_data:
                # v1 format
                for name, dep_info in lockfile_data.get("dependencies", {}).items():
                    if isinstance(dep_info, dict) and "version" in dep_info:
                        lockfile_versions[name] = dep_info["version"]
            
            if "packages" in lockfile_data:
                # v2+ format
                for path, pkg_info in lockfile_data.get("packages", {}).items():
                    if path.startswith("node_modules/"):
                        name = path[len("node_modules/"):]
                        if "version" in pkg_info:
                            lockfile_versions[name] = pkg_info["version"]
            
            # Compare versions
            for dep in deps:
                if dep.name in lockfile_versions:
                    lockfile_version = lockfile_versions[dep.name]
                    if dep.version == lockfile_version:
                        comparison["matching_versions"] += 1
                    else:
                        comparison["different_versions"] += 1
                        comparison["differences"].append({
                            "package": dep.name,
                            "manifest_version": dep.version,
                            "lockfile_version": lockfile_version,
                            "metadata": getattr(dep, '_metadata', {})
                        })
                else:
                    comparison["missing_in_lockfile"] += 1
            
            return comparison
            
        except Exception as e:
            logger.error(f"Lockfile comparison failed: {e}")
            return {"error": str(e)}
    
    def get_package_info(self, content: str) -> dict:
        """
        Extract basic package information from package.json
        
        Returns:
            Dict with name, version, description, etc.
        """
        try:
            data = json.loads(content)
            return {
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "main": data.get("main", ""),
                "scripts": data.get("scripts", {}),
                "engines": data.get("engines", {}),
                "keywords": data.get("keywords", []),
            }
        except json.JSONDecodeError:
            return {}
    
    def has_lockfile_reference(self, content: str) -> bool:
        """
        Check if package.json suggests a lockfile should be present
        
        Returns:
            True if lockfile is expected (has dependencies)
        """
        try:
            data = json.loads(content)
            has_deps = bool(
                data.get("dependencies") or 
                data.get("devDependencies") or
                data.get("peerDependencies")
            )
            return has_deps
        except json.JSONDecodeError:
            return False
    
    def supports_transitive_resolution(self) -> bool:
        """
        Check if this parser instance supports transitive dependency resolution
        
        Returns:
            True if version resolution is enabled
        """
        return self.resolve_versions
    
    def get_resolution_capabilities(self) -> Dict:
        """Get information about this parser's resolution capabilities"""
        return {
            "resolve_versions": self.resolve_versions,
            "use_registry": self.use_registry,
            "transitive_resolution": self.enable_transitive,
            "max_transitive_depth": self.max_depth if self.enable_transitive else 0,
            "consistency_checking": True,
            "version_source_tracking": True,
            "circular_dependency_handling": self.enable_transitive,
            "version_conflict_resolution": self.enable_transitive
        }