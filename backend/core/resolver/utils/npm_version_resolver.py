"""
NPM Version Resolver

Resolves npm version ranges (^1.2.3, ~1.2.3, >=1.2.3) to actual versions
using npm registry API or cached data.
"""
import json
import re
from typing import Optional, Dict, List
import httpx
from packaging import version
import asyncio
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResolvedVersion:
    """Result of version resolution"""
    original_range: str
    resolved_version: str
    source: str  # 'registry', 'cache', 'fallback'
    metadata: Dict = None


class SemverResolver:
    """Semantic version range resolution utilities"""
    
    @staticmethod
    def satisfies_range(version_str: str, range_spec: str) -> bool:
        """Check if a version satisfies a semver range specification"""
        try:
            v = version.Version(version_str)
            
            # Handle caret ranges (^1.2.3)
            if range_spec.startswith('^'):
                base_version = version.Version(range_spec[1:])
                # Compatible if major version matches and >= base version
                return (v.major == base_version.major and 
                        v >= base_version)
            
            # Handle tilde ranges (~1.2.3)
            elif range_spec.startswith('~'):
                base_version = version.Version(range_spec[1:])
                # Compatible if major.minor matches and >= base version
                return (v.major == base_version.major and 
                        v.minor == base_version.minor and 
                        v >= base_version)
            
            # Handle comparison operators (>=, >, <=, <, =)
            elif re.match(r'^[><=]+', range_spec):
                operator_match = re.match(r'^([><=]+)', range_spec)
                if operator_match:
                    op = operator_match.group(1)
                    target_version = version.Version(range_spec[len(op):])
                    
                    if op == '>=':
                        return v >= target_version
                    elif op == '>':
                        return v > target_version
                    elif op == '<=':
                        return v <= target_version
                    elif op == '<':
                        return v < target_version
                    elif op == '=':
                        return v == target_version
            
            # Exact version match
            else:
                return v == version.Version(range_spec)
                
        except version.InvalidVersion:
            return False
        
        return False
    
    @staticmethod
    def find_best_version(available_versions: List[str], range_spec: str) -> Optional[str]:
        """Find the best version from available versions that satisfies the range"""
        compatible_versions = []
        
        for v in available_versions:
            if SemverResolver.satisfies_range(v, range_spec):
                try:
                    compatible_versions.append(version.Version(v))
                except version.InvalidVersion:
                    continue
        
        if compatible_versions:
            # Return the highest compatible version
            return str(max(compatible_versions))
        
        return None


class NpmRegistryClient:
    """Client for querying npm registry"""
    
    def __init__(self, base_url: str = "https://registry.npmjs.org", timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self._session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._session = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.aclose()
    
    async def get_package_versions(self, package_name: str) -> Optional[List[str]]:
        """Get all available versions for a package"""
        if not self._session:
            raise RuntimeError("Client not properly initialized. Use async context manager.")
        
        try:
            url = f"{self.base_url}/{package_name}"
            response = await self._session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                versions = list(data.get("versions", {}).keys())
                return versions
            elif response.status_code == 404:
                logger.warning(f"Package not found: {package_name}")
                return None
            else:
                logger.error(f"Registry error for {package_name}: {response.status_code}")
                return None
                
        except httpx.RequestError as e:
            logger.error(f"Network error querying {package_name}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for {package_name}: {e}")
            return None


# Global cache shared across all resolver instances
_GLOBAL_VERSION_CACHE: Dict[str, Dict] = {}

class PackageVersionResolver:
    """
    Resolves npm package version ranges to actual versions
    
    Provides caching and fallback strategies for reliable version resolution
    """
    
    def __init__(self, cache_ttl: int = 3600, use_global_cache: bool = True):
        self.cache_ttl = cache_ttl
        self.use_global_cache = use_global_cache
        
        if use_global_cache:
            self._version_cache = _GLOBAL_VERSION_CACHE
        else:
            self._version_cache: Dict[str, Dict] = {}
            
        self.resolver = SemverResolver()
        self.registry_client = NpmRegistryClient()
    
    async def resolve_version_range(
        self, 
        package_name: str, 
        version_range: str,
        use_registry: bool = True
    ) -> ResolvedVersion:
        """
        Resolve a version range to an actual version
        
        Args:
            package_name: Name of the package
            version_range: Version range specification (^1.2.3, ~1.2.3, etc.)
            use_registry: Whether to query npm registry
            
        Returns:
            ResolvedVersion with resolved version and metadata
        """
        # Check cache first
        cache_key = f"{package_name}@{version_range}"
        if cache_key in self._version_cache:
            cached_data = self._version_cache[cache_key]
            if self._is_cache_valid(cached_data):
                return ResolvedVersion(
                    original_range=version_range,
                    resolved_version=cached_data["version"],
                    source="cache",
                    metadata=cached_data.get("metadata", {})
                )
        
        # Try registry resolution
        if use_registry:
            try:
                async with self.registry_client as client:
                    versions = await client.get_package_versions(package_name)
                    
                    if versions:
                        best_version = self.resolver.find_best_version(versions, version_range)
                        
                        if best_version:
                            # Cache the result
                            self._cache_version(cache_key, best_version, {"source": "registry"})
                            
                            return ResolvedVersion(
                                original_range=version_range,
                                resolved_version=best_version,
                                source="registry",
                                metadata={"available_versions": len(versions)}
                            )
            
            except Exception as e:
                logger.warning(f"Registry resolution failed for {package_name}: {e}")
        
        # Fallback to heuristic resolution
        fallback_version = self._fallback_resolve(version_range)
        return ResolvedVersion(
            original_range=version_range,
            resolved_version=fallback_version,
            source="fallback",
            metadata={"method": "heuristic"}
        )
    
    async def resolve_multiple(
        self, 
        packages: Dict[str, str],
        use_registry: bool = True,
        max_concurrent: int = 10
    ) -> Dict[str, ResolvedVersion]:
        """
        Resolve multiple package version ranges concurrently
        
        Args:
            packages: Dict of {package_name: version_range}
            use_registry: Whether to use npm registry
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dict of {package_name: ResolvedVersion}
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def resolve_single(name: str, range_spec: str) -> tuple[str, ResolvedVersion]:
            async with semaphore:
                result = await self.resolve_version_range(name, range_spec, use_registry)
                return name, result
        
        tasks = [
            resolve_single(name, range_spec) 
            for name, range_spec in packages.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        resolved = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Resolution failed: {result}")
                continue
            
            name, resolved_version = result
            resolved[name] = resolved_version
        
        return resolved
    
    def _fallback_resolve(self, version_range: str) -> str:
        """
        Heuristic version resolution when registry is unavailable
        
        This provides reasonable fallback versions based on common patterns
        """
        # Remove version prefixes for heuristic resolution
        clean_version = re.sub(r'^[~^>=<]+', '', version_range)
        
        # Handle version ranges by taking the first part
        if " - " in clean_version:
            clean_version = clean_version.split(" - ")[0]
        elif " || " in clean_version:
            clean_version = clean_version.split(" || ")[0]
        elif "," in clean_version:
            clean_version = clean_version.split(",")[0]
        
        clean_version = clean_version.strip()
        
        # Validate and return
        try:
            version.Version(clean_version)  # Validate format
            return clean_version
        except version.InvalidVersion:
            # If all else fails, return a safe default
            return "1.0.0"
    
    def _cache_version(self, cache_key: str, resolved_version: str, metadata: Dict):
        """Cache a resolved version"""
        import time
        self._version_cache[cache_key] = {
            "version": resolved_version,
            "timestamp": time.time(),
            "metadata": metadata
        }
    
    def _is_cache_valid(self, cached_data: Dict) -> bool:
        """Check if cached data is still valid"""
        import time
        age = time.time() - cached_data.get("timestamp", 0)
        return age < self.cache_ttl
    
    def clear_cache(self):
        """Clear the version resolution cache"""
        self._version_cache.clear()
    
    @classmethod
    def clear_global_cache(cls):
        """Clear the global version resolution cache"""
        _GLOBAL_VERSION_CACHE.clear()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        import time
        valid_entries = 0
        expired_entries = 0
        
        current_time = time.time()
        for cache_data in self._version_cache.values():
            age = current_time - cache_data.get("timestamp", 0)
            if age < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._version_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "size_kb": len(str(self._version_cache)) / 1024,
            "cache_ttl_seconds": self.cache_ttl
        }
    
    @classmethod
    def get_global_cache_stats(cls) -> Dict:
        """Get global cache statistics"""
        import time
        total_entries = len(_GLOBAL_VERSION_CACHE)
        
        return {
            "total_entries": total_entries,
            "size_kb": len(str(_GLOBAL_VERSION_CACHE)) / 1024,
            "cache_type": "global"
        }