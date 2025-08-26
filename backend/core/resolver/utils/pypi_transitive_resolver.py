"""
PyPI Transitive Dependency Resolver

Resolves complete transitive dependency trees from Python manifest files
(requirements.txt, pyproject.toml) by recursively querying the PyPI registry.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from packaging import version
from packaging.requirements import Requirement, InvalidRequirement
import httpx

from ...models import Dep

logger = logging.getLogger(__name__)


@dataclass
class PyPiPackageInfo:
    """Information about a PyPI package"""
    name: str
    version: str
    dependencies: List[str] = field(default_factory=list)  # requirements format
    dev_dependencies: List[str] = field(default_factory=list)
    is_dev: bool = False
    path: List[str] = field(default_factory=list)


@dataclass 
class PyPiTransitiveResolutionResult:
    """Result of PyPI transitive dependency resolution"""
    dependencies: List[Dep]
    resolution_stats: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    cache_hits: int = 0
    registry_lookups: int = 0


class PyPiRegistryClient:
    """Client for fetching package information from PyPI"""
    
    def __init__(self, base_url: str = "https://pypi.org/pypi", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        self._session = httpx.AsyncClient(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.aclose()
    
    async def get_package_info(self, package_name: str, version: str = None) -> Optional[PyPiPackageInfo]:
        """Get detailed package information including dependencies"""
        if not self._session:
            raise RuntimeError("Client not properly initialized. Use async context manager.")
        
        try:
            # Try specific version first if provided, otherwise get latest
            if version:
                url = f"{self.base_url}/{package_name}/{version}/json"
            else:
                url = f"{self.base_url}/{package_name}/json"
                
            response = await self._session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_package_info(data, package_name)
            elif response.status_code == 404:
                logger.warning(f"Package not found: {package_name}")
                return None
            else:
                logger.error(f"PyPI error for {package_name}: {response.status_code}")
                return None
                    
        except Exception as e:
            logger.error(f"Failed to fetch package info for {package_name}: {e}")
            
        return None
    
    def _parse_package_info(self, data: Dict, name: str) -> PyPiPackageInfo:
        """Parse PyPI API response into PyPiPackageInfo object"""
        info = data.get("info", {})
        
        # Get the latest version info
        version_str = info.get("version", "")
        
        # Extract dependencies from requires_dist
        dependencies = []
        requires_dist = info.get("requires_dist", []) or []
        
        for req_str in requires_dist:
            if req_str:  # Skip None/empty entries
                try:
                    req = Requirement(req_str)
                    # Skip dev/extra dependencies for now (simple heuristic)
                    if not req.marker or not self._is_dev_requirement(req_str):
                        dependencies.append(req_str)
                except InvalidRequirement:
                    continue
        
        return PyPiPackageInfo(
            name=name,
            version=version_str,
            dependencies=dependencies
        )
    
    def _is_dev_requirement(self, requirement_str: str) -> bool:
        """Simple heuristic to detect dev requirements"""
        dev_markers = ['extra == "dev"', 'extra == "test"', 'extra == "testing"', 
                      'extra == "lint"', 'extra == "docs"', 'extra == "build"']
        return any(marker in requirement_str for marker in dev_markers)


class PyPiVersionResolver:
    """Simple version resolver for PyPI packages"""
    
    def __init__(self):
        self.registry_client = PyPiRegistryClient()
        self._version_cache: Dict[str, str] = {}
    
    async def resolve_requirement(self, requirement_str: str) -> Tuple[str, str]:
        """
        Resolve a requirement string to package name and version
        
        Args:
            requirement_str: Requirement in pip format (e.g., "requests>=2.25.0")
            
        Returns:
            Tuple of (package_name, resolved_version)
        """
        try:
            req = Requirement(requirement_str)
            package_name = req.name
            
            # Check cache
            if requirement_str in self._version_cache:
                return package_name, self._version_cache[requirement_str]
            
            # Get package info from PyPI to find latest version that satisfies requirement
            async with self.registry_client as client:
                package_info = await client.get_package_info(package_name)
                
                if package_info and package_info.version:
                    resolved_version = package_info.version
                    
                    # Simple version satisfaction check
                    if req.specifier:
                        try:
                            if version.Version(resolved_version) in req.specifier:
                                self._version_cache[requirement_str] = resolved_version
                                return package_name, resolved_version
                        except version.InvalidVersion:
                            pass
                    
                    # If no specifier or version check failed, use the latest
                    self._version_cache[requirement_str] = resolved_version
                    return package_name, resolved_version
            
            # Fallback: extract version from requirement if possible
            if req.specifier:
                specs = list(req.specifier)
                if specs:
                    fallback_version = str(specs[0]).replace(specs[0].operator, '').strip()
                    return package_name, fallback_version
            
            return package_name, "latest"
            
        except Exception as e:
            logger.error(f"Failed to resolve requirement {requirement_str}: {e}")
            return requirement_str, "unknown"


class PyPiTransitiveDependencyResolver:
    """
    Resolves complete transitive dependency trees from Python manifest files
    
    Similar to the NPM resolver but adapted for PyPI/Python ecosystem
    """
    
    def __init__(
        self,
        max_depth: int = 10,
        max_concurrent: int = 5,
        include_dev_deps: bool = False
    ):
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent
        self.include_dev_deps = include_dev_deps
        
        self.version_resolver = PyPiVersionResolver()
        self.registry_client = PyPiRegistryClient()
        
        # Track resolution state
        self._resolved_packages: Dict[str, str] = {}  # name -> resolved_version
        
        # Statistics
        self.stats = {
            "total_packages": 0,
            "cache_hits": 0,
            "registry_lookups": 0,
            "version_conflicts": 0,
            "circular_dependencies": 0,
            "failed_resolutions": 0
        }
    
    async def resolve_transitive_dependencies(
        self,
        requirements: List[str],
        use_registry: bool = True,
        bypass_cache: bool = False
    ) -> PyPiTransitiveResolutionResult:
        """
        Resolve complete transitive dependency tree from requirements list
        
        Args:
            requirements: List of requirement strings (pip format)
            use_registry: Whether to query PyPI registry
            bypass_cache: Force fresh registry lookups
            
        Returns:
            PyPiTransitiveResolutionResult with complete dependency tree
        """
        try:
            # Initialize resolution state
            self._resolved_packages.clear()
            self.stats = {k: 0 for k in self.stats.keys()}
            
            # Start resolution process
            resolved_deps = await self._resolve_dependency_tree(
                requirements, 
                use_registry=use_registry,
                bypass_cache=bypass_cache,
                is_dev=False,
                path=[]
            )
            
            return PyPiTransitiveResolutionResult(
                dependencies=resolved_deps,
                resolution_stats=dict(self.stats),
                cache_hits=self.stats["cache_hits"],
                registry_lookups=self.stats["registry_lookups"]
            )
            
        except Exception as e:
            logger.error(f"PyPI transitive resolution failed: {e}")
            return PyPiTransitiveResolutionResult(
                dependencies=[],
                errors=[str(e)]
            )
    
    async def resolve_from_requirements_txt(
        self,
        content: str,
        use_registry: bool = True,
        bypass_cache: bool = False
    ) -> PyPiTransitiveResolutionResult:
        """
        Resolve transitive dependencies from requirements.txt content
        
        Args:
            content: Raw requirements.txt content
            use_registry: Whether to query PyPI registry
            bypass_cache: Force fresh registry lookups
            
        Returns:
            PyPiTransitiveResolutionResult with complete dependency tree
        """
        # Parse requirements.txt format
        requirements = []
        
        for line in content.strip().split('\n'):
            line = line.strip()
            
            # Skip empty lines, comments, and pip options
            if not line or line.startswith('#') or line.startswith('-'):
                continue
                
            requirements.append(line)
        
        return await self.resolve_transitive_dependencies(
            requirements, use_registry, bypass_cache
        )
    
    async def _resolve_dependency_tree(
        self,
        requirements: List[str],
        use_registry: bool,
        bypass_cache: bool,
        is_dev: bool,
        path: List[str],
        depth: int = 0
    ) -> List[Dep]:
        """Recursively resolve dependency tree"""
        
        if depth >= self.max_depth:
            logger.warning(f"Maximum depth ({self.max_depth}) reached at path: {' -> '.join(path)}")
            return []
            
        resolved_deps = []
        
        # Process each requirement
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_requirement(requirement_str: str):
            async with semaphore:
                return await self._process_single_requirement(
                    requirement_str, use_registry, bypass_cache,
                    is_dev, path, depth
                )
        
        tasks = [process_requirement(req) for req in requirements]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to process requirement: {result}")
                self.stats["failed_resolutions"] += 1
                continue
                
            if result:
                resolved_deps.extend(result)
        
        return resolved_deps
    
    async def _process_single_requirement(
        self,
        requirement_str: str,
        use_registry: bool,
        bypass_cache: bool,
        is_dev: bool,
        path: List[str],
        depth: int
    ) -> List[Dep]:
        """Process a single requirement and resolve its transitive dependencies"""
        
        try:
            # Resolve requirement to package name and version
            package_name, resolved_version = await self.version_resolver.resolve_requirement(requirement_str)
            
            # Check for circular dependencies
            if package_name in path:
                logger.warning(f"Circular dependency detected: {' -> '.join(path + [package_name])}")
                self.stats["circular_dependencies"] += 1
                return []
            
            # Check for version conflicts
            if package_name in self._resolved_packages:
                existing_version = self._resolved_packages[package_name]
                if existing_version != resolved_version:
                    logger.info(f"Version conflict for {package_name}: {existing_version} vs {resolved_version}")
                    self.stats["version_conflicts"] += 1
                    # Use the higher version (simple conflict resolution)
                    try:
                        if version.Version(resolved_version) > version.Version(existing_version):
                            self._resolved_packages[package_name] = resolved_version
                    except version.InvalidVersion:
                        pass
            else:
                self._resolved_packages[package_name] = resolved_version
            
            # Create the dependency object
            new_path = path + [package_name]
            dep = Dep(
                name=package_name,
                version=resolved_version,
                ecosystem="PyPI",
                path=new_path,
                is_direct=(depth == 0),
                is_dev=is_dev
            )
            
            self.stats["total_packages"] += 1
            self.stats["registry_lookups"] += 1
            
            result_deps = [dep]
            
            # Get package info for transitive dependencies (if using registry)
            if use_registry and depth < self.max_depth - 1:
                package_info = await self._get_package_dependencies(
                    package_name, resolved_version
                )
                
                if package_info and package_info.dependencies:
                    # Recursively resolve transitive dependencies
                    transitive_deps = await self._resolve_dependency_tree(
                        package_info.dependencies,
                        use_registry=use_registry,
                        bypass_cache=bypass_cache,
                        is_dev=is_dev,
                        path=new_path,
                        depth=depth + 1
                    )
                    result_deps.extend(transitive_deps)
            
            return result_deps
            
        except Exception as e:
            logger.error(f"Failed to process requirement {requirement_str}: {e}")
            self.stats["failed_resolutions"] += 1
            return []
    
    async def _get_package_dependencies(self, name: str, version: str) -> Optional[PyPiPackageInfo]:
        """Get package dependency information from PyPI"""
        try:
            async with self.registry_client as client:
                return await client.get_package_info(name, version)
        except Exception as e:
            logger.error(f"Failed to get package info for {name}@{version}: {e}")
            return None
    
    def get_resolution_capabilities(self) -> Dict:
        """Get information about resolver capabilities"""
        return {
            "transitive_resolution": True,
            "version_range_resolution": True,
            "registry_integration": True,
            "circular_dependency_handling": True,
            "version_conflict_resolution": True,
            "max_depth": self.max_depth,
            "max_concurrent": self.max_concurrent,
            "include_dev_deps": self.include_dev_deps,
            "ecosystem": "PyPI"
        }


# Factory function for creating PyPI resolver instances
def create_pypi_transitive_resolver(
    max_depth: int = 10,
    include_dev_deps: bool = False,
    max_concurrent: int = 5
) -> PyPiTransitiveDependencyResolver:
    """Create a new PyPI transitive dependency resolver with specified options"""
    return PyPiTransitiveDependencyResolver(
        max_depth=max_depth,
        max_concurrent=max_concurrent,
        include_dev_deps=include_dev_deps
    )