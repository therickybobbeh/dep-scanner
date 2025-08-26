"""
NPM Transitive Dependency Resolver

Resolves complete transitive dependency trees from package.json manifest files
by recursively querying the NPM registry for dependency information.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from packaging import version
import httpx

from .npm_version_resolver import PackageVersionResolver, ResolvedVersion, NpmRegistryClient
from ...models import Dep

logger = logging.getLogger(__name__)


@dataclass
class PackageInfo:
    """Information about an NPM package"""
    name: str
    version: str
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)
    peer_dependencies: Dict[str, str] = field(default_factory=dict)
    is_dev: bool = False
    is_peer: bool = False
    path: List[str] = field(default_factory=list)


@dataclass 
class TransitiveResolutionResult:
    """Result of transitive dependency resolution"""
    dependencies: List[Dep]
    resolution_stats: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    cache_hits: int = 0
    registry_lookups: int = 0


class NpmPackageInfoClient:
    """Extended client for fetching package dependency information"""
    
    def __init__(self, base_url: str = "https://registry.npmjs.org", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout, read=self.timeout),
            limits=httpx.Limits(max_keepalive_connections=2, max_connections=4)  # Reduced limits
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.aclose()
    
    async def get_package_info(self, package_name: str, version: str, max_retries: int = 3) -> Optional[PackageInfo]:
        """Get detailed package information including dependencies with retry logic"""
        if not self._session:
            raise RuntimeError("Client not properly initialized. Use async context manager.")
        
        for attempt in range(max_retries + 1):
            try:
                # First try to get specific version info
                url = f"{self.base_url}/{package_name}/{version}"
                response = await self._session.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_package_info(data, package_name, version)
                elif response.status_code == 404:
                    # Package/version doesn't exist, no point retrying
                    break
                
                # Fall back to getting all versions and extracting specific one
                url = f"{self.base_url}/{package_name}"
                response = await self._session.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    versions_data = data.get("versions", {})
                    
                    if version in versions_data:
                        version_data = versions_data[version]
                        return self._parse_package_info(version_data, package_name, version)
                elif response.status_code == 404:
                    # Package doesn't exist, no point retrying
                    break
                    
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadTimeout) as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Network error for {package_name}@{version}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Max retries exceeded for {package_name}@{version}: {e}")
            except Exception as e:
                logger.error(f"Failed to fetch package info for {package_name}@{version}: {e}")
                break
                
        return None
    
    def _parse_package_info(self, data: Dict, name: str, version: str) -> PackageInfo:
        """Parse package data into PackageInfo object"""
        return PackageInfo(
            name=name,
            version=version,
            dependencies=data.get("dependencies", {}),
            dev_dependencies=data.get("devDependencies", {}),
            peer_dependencies=data.get("peerDependencies", {})
        )


class NpmTransitiveDependencyResolver:
    """
    Resolves complete transitive dependency trees from package.json manifest files
    
    This resolver can:
    - Start from a package.json manifest with version ranges
    - Resolve version ranges to specific versions using the NPM registry
    - Recursively build a complete dependency tree
    - Handle circular dependencies and version conflicts
    - Provide detailed resolution statistics and error reporting
    """
    
    def __init__(
        self,
        max_depth: int = 8,  # Reduced from 10 to 8
        max_concurrent: int = 2,  # Further reduced from 3 to 2
        cache_ttl: int = 3600,
        include_dev_deps: bool = False,
        include_peer_deps: bool = False,
        rate_limit_delay: float = 0.2  # Increased to 200ms delay between requests
    ):
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent
        self.include_dev_deps = include_dev_deps
        self.include_peer_deps = include_peer_deps
        self.rate_limit_delay = rate_limit_delay
        
        self.version_resolver = PackageVersionResolver(cache_ttl=cache_ttl)
        self.package_client = NpmPackageInfoClient()
        
        # Track resolution state
        self._resolved_packages: Dict[str, str] = {}  # name -> resolved_version
        self._resolution_queue: asyncio.Queue = None
        self._processing_semaphore: asyncio.Semaphore = None
        self._last_request_time: float = 0  # Track last request time for rate limiting
        
        # Statistics
        self.stats = {
            "total_packages": 0,
            "cache_hits": 0,
            "registry_lookups": 0,
            "version_conflicts": 0,
            "circular_dependencies": 0,
            "failed_resolutions": 0,
            "rate_limited_requests": 0,
            "batched_requests": 0
        }
        
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open = False
        self._circuit_open_until = 0
        
        # Track all visited packages to prevent infinite loops
        self._all_visited_packages: Set[str] = set()
        
        # Problematic packages that cause infinite loops - skip their transitive deps
        self._problematic_packages = {
            'mocha', 'istanbul', 'grunt', 'gulp', 'webpack', 'babel-core', 'babel-preset-env',
            'eslint', 'jest', 'karma', 'rollup', 'browserify', 'uglify-js', 'terser',
            'chai', 'sinon', 'nyc', 'tap', 'ava', 'jasmine', 'protractor', 'cypress',
            'puppeteer', 'playwright', 'webdriver', 'selenium-webdriver', 'codecov',
            'coveralls', 'jshint', 'tslint', 'stylelint', 'prettier', 'standard',
            'xo', 'commitlint', 'husky', 'lint-staged', 'semantic-release'
        }
        
    async def resolve_transitive_dependencies(
        self,
        manifest_content: str,
        use_registry: bool = True,
        bypass_cache: bool = False,
        timeout_seconds: int = 60  # 1 minute timeout for entire operation
    ) -> TransitiveResolutionResult:
        """
        Resolve complete transitive dependency tree from package.json
        
        Args:
            manifest_content: Raw package.json content
            use_registry: Whether to query NPM registry
            bypass_cache: Force fresh registry lookups
            timeout_seconds: Maximum time to spend on resolution
            
        Returns:
            TransitiveResolutionResult with complete dependency tree
        """
        try:
            # Wrap entire operation in timeout
            return await asyncio.wait_for(
                self._resolve_with_timeout(manifest_content, use_registry, bypass_cache),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(f"Transitive dependency resolution timed out after {timeout_seconds} seconds")
            return TransitiveResolutionResult(
                dependencies=[],
                resolution_stats=dict(self.stats),
                cache_hits=0,
                registry_lookups=0,
                errors=[f"Resolution timed out after {timeout_seconds} seconds"]
            )
        except Exception as e:
            logger.error(f"Transitive dependency resolution failed: {e}")
            return TransitiveResolutionResult(
                dependencies=[],
                resolution_stats=dict(self.stats),
                cache_hits=0,
                registry_lookups=0,
                errors=[str(e)]
            )
    
    async def _resolve_with_timeout(
        self,
        manifest_content: str,
        use_registry: bool,
        bypass_cache: bool
    ) -> TransitiveResolutionResult:
        """Internal resolution method without timeout wrapper"""
        try:
            # Parse manifest
            manifest = json.loads(manifest_content)
            
            # Initialize resolution state
            self._resolved_packages.clear()
            self.stats = {k: 0 for k in self.stats.keys()}
            
            # Extract root dependencies
            root_deps = manifest.get("dependencies", {})
            root_dev_deps = manifest.get("devDependencies", {}) if self.include_dev_deps else {}
            root_peer_deps = manifest.get("peerDependencies", {}) if self.include_peer_deps else {}
            
            # Start resolution process
            all_deps = []
            
            # Process each category of dependencies
            for deps_dict, is_dev, is_peer in [
                (root_deps, False, False),
                (root_dev_deps, True, False), 
                (root_peer_deps, False, True)
            ]:
                if deps_dict:
                    resolved_deps = await self._resolve_dependency_tree(
                        deps_dict, 
                        use_registry=use_registry,
                        bypass_cache=bypass_cache,
                        is_dev=is_dev,
                        is_peer=is_peer,
                        path=[]
                    )
                    all_deps.extend(resolved_deps)
            
            return TransitiveResolutionResult(
                dependencies=all_deps,
                resolution_stats=dict(self.stats),
                cache_hits=self.stats["cache_hits"],
                registry_lookups=self.stats["registry_lookups"]
            )
            
        except Exception as e:
            logger.error(f"Transitive resolution failed: {e}")
            return TransitiveResolutionResult(
                dependencies=[],
                errors=[str(e)]
            )
    
    async def _resolve_dependency_tree(
        self,
        dependencies: Dict[str, str],
        use_registry: bool,
        bypass_cache: bool,
        is_dev: bool,
        is_peer: bool,
        path: List[str],
        depth: int = 0
    ) -> List[Dep]:
        """Recursively resolve dependency tree"""
        
        if depth >= self.max_depth:
            logger.warning(f"Maximum depth ({self.max_depth}) reached at path: {' -> '.join(path)}")
            return []
            
        resolved_deps = []
        
        # Resolve version ranges to specific versions
        if use_registry and not bypass_cache:
            resolved_versions = await self.version_resolver.resolve_multiple(
                dependencies,
                use_registry=use_registry,
                max_concurrent=self.max_concurrent
            )
        else:
            # Handle bypass cache case or non-registry resolution
            resolved_versions = {}
            for name, range_spec in dependencies.items():
                resolved_version = await self.version_resolver.resolve_version_range(
                    name, range_spec, use_registry=use_registry
                )
                resolved_versions[name] = resolved_version
        
        # Skip processing if we're getting too deep or have too many failures
        if depth > 5 or self._consecutive_failures > 10:
            logger.info(f"Skipping deep dependency resolution at depth {depth} or due to {self._consecutive_failures} failures")
            return []
        
        # Process dependencies in batches to avoid overwhelming the registry
        batch_size = self.max_concurrent
        dependency_items = list(resolved_versions.items())
        
        async def process_dependency_batch(batch_items):
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_dependency(name: str, resolved_version: ResolvedVersion):
                async with semaphore:
                    return await self._process_single_dependency(
                        name, resolved_version, use_registry, bypass_cache,
                        is_dev, is_peer, path, depth
                    )
            
            tasks = [
                process_dependency(name, resolved_version)
                for name, resolved_version in batch_items
            ]
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process dependencies in batches with delays between batches
        results = []
        for i in range(0, len(dependency_items), batch_size):
            batch = dependency_items[i:i + batch_size]
            if i > 0:
                # Add delay between batches to reduce load
                await asyncio.sleep(self.rate_limit_delay * 2)
                self.stats["batched_requests"] += len(batch)
            
            batch_results = await process_dependency_batch(batch)
            results.extend(batch_results)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to process dependency: {result}")
                self.stats["failed_resolutions"] += 1
                continue
                
            if result:
                resolved_deps.extend(result)
        
        return resolved_deps
    
    async def _process_single_dependency(
        self,
        name: str,
        resolved_version: ResolvedVersion,
        use_registry: bool,
        bypass_cache: bool,
        is_dev: bool,
        is_peer: bool,
        path: List[str],
        depth: int
    ) -> List[Dep]:
        """Process a single dependency and resolve its transitive dependencies"""
        
        # Check for circular dependencies
        if name in path:
            logger.warning(f"Circular dependency detected: {' -> '.join(path + [name])}")
            self.stats["circular_dependencies"] += 1
            return []
        
        # Check for version conflicts
        if name in self._resolved_packages:
            existing_version = self._resolved_packages[name]
            if existing_version != resolved_version.resolved_version:
                logger.info(f"Version conflict for {name}: {existing_version} vs {resolved_version.resolved_version}")
                self.stats["version_conflicts"] += 1
                # Use the higher version (simple conflict resolution)
                try:
                    if version.Version(resolved_version.resolved_version) > version.Version(existing_version):
                        self._resolved_packages[name] = resolved_version.resolved_version
                except version.InvalidVersion:
                    pass
        else:
            self._resolved_packages[name] = resolved_version.resolved_version
        
        # Create the dependency object
        new_path = path + [name]
        dep = Dep(
            name=name,
            version=resolved_version.resolved_version,
            ecosystem="npm",
            path=new_path,
            is_direct=(depth == 0),
            is_dev=is_dev
        )
        
        self.stats["total_packages"] += 1
        if resolved_version.source == "cache":
            self.stats["cache_hits"] += 1
        elif resolved_version.source == "registry":
            self.stats["registry_lookups"] += 1
        
        result_deps = [dep]
        
        # Get package info for transitive dependencies (if using registry)
        if use_registry and depth < self.max_depth - 1:
            package_info = await self._get_package_dependencies(
                name, resolved_version.resolved_version
            )
            
            if package_info:
                # Recursively resolve transitive dependencies
                for deps_dict, sub_is_dev, sub_is_peer in [
                    (package_info.dependencies, is_dev, False),
                    (package_info.dev_dependencies, True, False) if self.include_dev_deps else ({}, False, False),
                    (package_info.peer_dependencies, is_dev, True) if self.include_peer_deps else ({}, False, False)
                ]:
                    if deps_dict:
                        transitive_deps = await self._resolve_dependency_tree(
                            deps_dict,
                            use_registry=use_registry,
                            bypass_cache=bypass_cache,
                            is_dev=sub_is_dev,
                            is_peer=sub_is_peer,
                            path=new_path,
                            depth=depth + 1
                        )
                        result_deps.extend(transitive_deps)
        
        return result_deps
    
    async def _get_package_dependencies(self, name: str, version: str) -> Optional[PackageInfo]:
        """Get package dependency information with rate limiting and circuit breaker"""
        try:
            # Check circuit breaker
            current_time = asyncio.get_event_loop().time()
            if self._circuit_open:
                if current_time < self._circuit_open_until:
                    logger.debug(f"Circuit breaker open, skipping {name}@{version}")
                    return None
                else:
                    # Reset circuit breaker
                    self._circuit_open = False
                    self._consecutive_failures = 0
                    logger.info("Circuit breaker reset")
            
            # Rate limiting: ensure minimum delay between requests
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                await asyncio.sleep(wait_time)
                self.stats["rate_limited_requests"] += 1
            
            self._last_request_time = asyncio.get_event_loop().time()
            
            async with self.package_client as client:
                result = await client.get_package_info(name, version)
                # Success - reset failure counter
                self._consecutive_failures = 0
                return result
                
        except Exception as e:
            logger.error(f"Failed to get package info for {name}@{version}: {e}")
            self._consecutive_failures += 1
            
            # Open circuit breaker after 3 consecutive failures (reduced from 5)
            if self._consecutive_failures >= 3:
                self._circuit_open = True
                self._circuit_open_until = asyncio.get_event_loop().time() + 10  # 10 second cooldown (reduced from 30)
                logger.warning(f"Circuit breaker opened after {self._consecutive_failures} failures")
            
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
            "include_peer_deps": self.include_peer_deps
        }


# Factory function for creating resolver instances
def create_transitive_resolver(
    max_depth: int = 8,  # Reduced from 10 to 8
    include_dev_deps: bool = False,
    include_peer_deps: bool = False,
    max_concurrent: int = 2  # Updated default to match new conservative settings
) -> NpmTransitiveDependencyResolver:
    """Create a new transitive dependency resolver with specified options"""
    return NpmTransitiveDependencyResolver(
        max_depth=max_depth,
        max_concurrent=max_concurrent,
        include_dev_deps=include_dev_deps,
        include_peer_deps=include_peer_deps
    )