"""
NPM lock file generator using npm Registry API

Generates package-lock.json files from package.json using npm Registry API.
No external dependencies or tools required - works with HTTP calls only.
"""
import asyncio
import json
import logging
import httpx
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class NpmLockGenerator:
    """
    Generator for NPM lock files using npm Registry API
    
    Uses npm Registry API to resolve all dependencies (direct and transitive)
    from package.json files. No external tools or dependencies required.
    
    This ensures that the vulnerability scan uses a complete dependency
    tree resolved from the npm registry.
    """
    
    def __init__(self):
        self._registry_url = "https://registry.npmjs.org"
        self._client = None
    
    
    
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_connections=30, max_keepalive_connections=10),
                headers={"User-Agent": "dep-scan/1.0"}
            )
        return self._client
    
    async def _close_client(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _fetch_package_from_registry(self, name: str, version: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch package information from npm registry using httpx
        
        Args:
            name: Package name
            version: Optional specific version (if None, fetches latest)
            
        Returns:
            Package metadata dict or None if fetch fails
        """
        try:
            # Build URL - if version specified, get that version, else get full package info
            if version and not version.startswith('^') and not version.startswith('~') and version != '*':
                # Clean version (remove = or v prefix)
                clean_version = version.lstrip('=v')
                url = f"{self._registry_url}/{name}/{clean_version}"
            else:
                url = f"{self._registry_url}/{name}"
            
            client = await self._get_http_client()
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.debug(f"Package {name}@{version or 'latest'} not found in registry")
            else:
                logger.debug(f"HTTP {response.status_code} error fetching {name}")
        except httpx.TimeoutException:
            logger.debug(f"Timeout fetching package {name} from registry")
        except Exception as e:
            logger.debug(f"Error fetching package {name} from registry: {e}")
        
        return None
    
    async def _fetch_packages_batch(self, package_requests: List[Tuple[str, str, bool]]) -> List[Tuple[str, str, bool, Optional[Dict]]]:
        """
        Fetch multiple packages concurrently
        
        Args:
            package_requests: List of (name, version_range, is_dev) tuples
            
        Returns:
            List of (name, version_range, is_dev, package_info) tuples
        """
        async def fetch_single(name: str, version_range: str, is_dev: bool):
            package_info = await self._fetch_package_from_registry(name)
            return (name, version_range, is_dev, package_info)
        
        # Batch process with concurrency limit
        batch_size = 25  # Process 25 packages concurrently
        results = []
        
        for i in range(0, len(package_requests), batch_size):
            batch = package_requests[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[fetch_single(name, version_range, is_dev) for name, version_range, is_dev in batch],
                return_exceptions=True
            )
            
            # Filter out exceptions and add successful results
            for result in batch_results:
                if not isinstance(result, Exception):
                    results.append(result)
        
        return results
    
    def _resolve_semver_version(self, version_range: str, available_versions: list) -> Optional[str]:
        """
        Resolve a semver range to a specific version
        
        Simple implementation - can be enhanced with proper semver library
        
        Args:
            version_range: Version range like ^1.0.0, ~2.1.0, >=3.0.0
            available_versions: List of available versions
            
        Returns:
            Resolved version or None
        """
        if not version_range or version_range == '*' or version_range == 'latest':
            # Return latest stable version (skip pre-releases)
            stable_versions = [v for v in available_versions if '-' not in v]
            if stable_versions:
                return stable_versions[-1]  # Assuming sorted
        
        # Handle exact version
        if not any(c in version_range for c in ['^', '~', '>', '<', '=']):
            return version_range
        
        # Handle caret (^) - compatible with version
        if version_range.startswith('^'):
            target = version_range[1:]
            # For now, just return the target version if available
            if target in available_versions:
                return target
            # Otherwise return latest available
            return available_versions[-1] if available_versions else None
        
        # Handle tilde (~) - approximately equivalent to version
        if version_range.startswith('~'):
            target = version_range[1:]
            if target in available_versions:
                return target
            return available_versions[-1] if available_versions else None
        
        # For other cases, try to find exact match or use latest
        clean_range = version_range.lstrip('>=<~^')
        if clean_range in available_versions:
            return clean_range
        
        return available_versions[-1] if available_versions else None
    
    async def _build_dependency_tree_from_api(self, package_json: Dict, progress_callback: Optional[callable] = None) -> Dict:
        """
        Build complete dependency tree using npm Registry API with batch processing
        
        Args:
            package_json: Parsed package.json content
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with resolved dependencies
        """
        try:
            resolved = {}
            to_process = []
            processed = set()
            
            # Start with direct dependencies
            deps = package_json.get('dependencies', {})
            dev_deps = package_json.get('devDependencies', {})
            
            # Combine all direct dependencies
            all_direct_deps = {**deps, **dev_deps}
            
            if progress_callback:
                progress_callback(f"Resolving {len(all_direct_deps)} direct dependencies via npm registry...")
            
            # Add direct deps to processing queue
            for name, version_range in all_direct_deps.items():
                to_process.append((name, version_range, name in dev_deps))
            
            # Process dependencies in batches
            total_processed = 0
            while to_process:
                # Take a batch of unprocessed dependencies
                batch = []
                remaining = []
                
                for name, version_range, is_dev in to_process:
                    if name not in processed:
                        batch.append((name, version_range, is_dev))
                        processed.add(name)
                    else:
                        remaining.append((name, version_range, is_dev))
                
                to_process = remaining
                
                if not batch:
                    break  # No more work to do
                
                if progress_callback:
                    progress_callback(f"Processing batch of {len(batch)} packages ({total_processed} completed so far)...")
                
                # Fetch batch concurrently
                batch_results = await self._fetch_packages_batch(batch)
                
                # Process results and add transitive dependencies
                for name, version_range, is_dev, package_info in batch_results:
                    if not package_info:
                        logger.warning(f"Could not fetch {name} from registry")
                        continue
                    
                    # Resolve version
                    if 'dist-tags' in package_info and 'latest' in package_info['dist-tags']:
                        # Full package info returned
                        available_versions = list(package_info.get('versions', {}).keys())
                        resolved_version = self._resolve_semver_version(version_range, available_versions)
                        
                        if resolved_version and resolved_version in package_info['versions']:
                            version_info = package_info['versions'][resolved_version]
                        else:
                            version_info = package_info['versions'].get(
                                package_info['dist-tags']['latest']
                            )
                    else:
                        # Specific version info returned
                        version_info = package_info
                        resolved_version = package_info.get('version')
                    
                    if not version_info:
                        continue
                    
                    # Store resolved dependency
                    resolved[name] = {
                        'version': resolved_version or version_info.get('version'),
                        'resolved': version_info.get('dist', {}).get('tarball', ''),
                        'integrity': version_info.get('dist', {}).get('integrity', ''),
                        'dev': is_dev,
                        'dependencies': version_info.get('dependencies', {})
                    }
                    
                    # Add transitive dependencies to queue
                    transitive_deps = version_info.get('dependencies', {})
                    for dep_name, dep_version in transitive_deps.items():
                        if dep_name not in processed:
                            to_process.append((dep_name, dep_version, False))
                
                total_processed += len(batch_results)
            
            return resolved
        
        finally:
            # Clean up HTTP client
            await self._close_client()
    
    async def _generate_lock_from_api(self, package_json_content: str, progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        Generate package-lock.json using npm Registry API
        
        Args:
            package_json_content: Raw package.json content
            progress_callback: Optional progress callback
            
        Returns:
            Generated package-lock.json content or None if generation fails
        """
        try:
            package_json = json.loads(package_json_content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid package.json: {e}")
            return None
        
        if progress_callback:
            progress_callback("Generating package-lock.json using npm Registry API...")
        
        # Build dependency tree
        resolved_deps = await self._build_dependency_tree_from_api(package_json, progress_callback)
        
        if not resolved_deps:
            logger.warning("No dependencies resolved from npm registry")
            return None
        
        # Generate package-lock.json v2 format
        lock_file = {
            "name": package_json.get("name", "unknown"),
            "version": package_json.get("version", "1.0.0"),
            "lockfileVersion": 2,
            "requires": True,
            "packages": {
                "": {
                    "name": package_json.get("name", "unknown"),
                    "version": package_json.get("version", "1.0.0"),
                    "dependencies": package_json.get("dependencies", {}),
                    "devDependencies": package_json.get("devDependencies", {})
                }
            },
            "dependencies": {}
        }
        
        # Add resolved dependencies to lock file
        for name, info in resolved_deps.items():
            lock_file["dependencies"][name] = {
                "version": info["version"],
                "resolved": info["resolved"],
                "integrity": info["integrity"],
                "dev": info.get("dev", False),
                "requires": info.get("dependencies", {})
            }
            
            # Also add to packages section (v2 format)
            lock_file["packages"][f"node_modules/{name}"] = {
                "version": info["version"],
                "resolved": info["resolved"],
                "integrity": info["integrity"],
                "dependencies": info.get("dependencies", {})
            }
        
        if progress_callback:
            progress_callback(f"Successfully resolved {len(resolved_deps)} dependencies via npm registry")
        
        return json.dumps(lock_file, indent=2)
    
    async def ensure_lock_file(self, manifest_files: Dict[str, str], progress_callback: Optional[callable] = None) -> Dict[str, str]:
        """
        Ensure package-lock.json exists for package.json files using npm Registry API
        
        Args:
            manifest_files: Dict of {filename: content} 
            progress_callback: Optional callback for progress updates
            
        Returns:
            Updated dict with generated lock file if needed
            
        Example:
            files = {"package.json": content}
            result = await generator.ensure_lock_file(files)
            # result = {"package.json": content, "package-lock.json": generated_content}
        """
        result = manifest_files.copy()
        
        # Check if we have package.json but no package-lock.json
        if "package.json" in manifest_files and "package-lock.json" not in manifest_files:
            if progress_callback:
                progress_callback("package.json found without package-lock.json, generating lock file...")
            else:
                logger.info("package.json found without package-lock.json, generating lock file...")
            
            # Generate lock file using npm Registry API
            try:
                lock_content = await self._generate_lock_from_api(manifest_files["package.json"], progress_callback)
                if lock_content:
                    result["package-lock.json"] = lock_content
                    if progress_callback:
                        progress_callback("Successfully generated package-lock.json using npm registry API")
                    else:
                        logger.info("Successfully generated package-lock.json using npm registry API")
                else:
                    logger.warning("Failed to generate package-lock.json, proceeding with package.json only")
            except Exception as e:
                logger.warning(f"Error generating package-lock.json: {e}, proceeding with package.json only")
        
        return result


# Global NPM lock generator instance
npm_lock_generator = NpmLockGenerator()