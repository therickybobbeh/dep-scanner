import asyncio
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
import httpx
from dataclasses import dataclass
import random

from ..models import Dep, OSVQuery, OSVBatchQuery, OSVVulnerability, OSVBatchResponse, Vuln, SeverityLevel

@dataclass
class OSVCacheEntry:
    """Represents a cached OSV query result"""
    query_hash: str
    ecosystem: str
    name: str
    version: str
    vulnerabilities: str  # JSON serialized list
    cached_at: datetime
    expires_at: datetime

class OSVScanner:
    """OSV.dev API client with batching, caching, and retry logic"""
    
    def __init__(self, cache_db_path: Optional[str] = None, batch_size: int = 100, 
                 rate_limit_delay: float = 1.0, max_retries: int = 3):
        self.base_url = "https://api.osv.dev"
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        
        # Initialize cache
        self.cache_db_path = cache_db_path or "osv_cache.db"
        self._init_cache_db()
        
        # HTTP client with reasonable timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
    
    def _init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = sqlite3.connect(self.cache_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS osv_cache (
                query_hash TEXT PRIMARY KEY,
                ecosystem TEXT NOT NULL,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                vulnerabilities TEXT NOT NULL,
                cached_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_osv_cache_package 
            ON osv_cache(ecosystem, name, version)
        """)
        conn.commit()
        conn.close()
    
    async def scan_dependencies(self, dependencies: List[Dep]) -> List[Vuln]:
        """
        Scan a list of dependencies for vulnerabilities
        Returns a list of vulnerabilities found
        """
        # Deduplicate dependencies by (ecosystem, name, version)
        unique_deps = self._deduplicate_dependencies(dependencies)
        
        # Check cache first
        cached_results, uncached_deps = await self._check_cache(unique_deps)
        
        # Query OSV for uncached dependencies
        if uncached_deps:
            fresh_results = await self._query_osv_batch(uncached_deps)
            # Cache the fresh results
            await self._cache_results(uncached_deps, fresh_results)
        else:
            fresh_results = []
        
        # Combine cached and fresh results
        all_vulnerabilities = cached_results + fresh_results
        
        # Convert to Vuln objects and enrich with dependency metadata
        vulnerabilities = []
        for dep in dependencies:
            dep_vulns = [v for v in all_vulnerabilities 
                        if v.get("package") == dep.name and v.get("ecosystem") == dep.ecosystem]
            
            for vuln_data in dep_vulns:
                vuln = self._convert_osv_to_vuln(vuln_data, dep)
                vulnerabilities.append(vuln)
        
        return vulnerabilities
    
    def _deduplicate_dependencies(self, dependencies: List[Dep]) -> List[Dep]:
        """Remove duplicate dependencies based on (ecosystem, name, version)"""
        seen = set()
        unique_deps = []
        
        for dep in dependencies:
            key = (dep.ecosystem, dep.name, dep.version)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)
        
        return unique_deps
    
    async def _check_cache(self, dependencies: List[Dep]) -> Tuple[List[Dict], List[Dep]]:
        """
        Check cache for vulnerability data
        Returns: (cached_vulnerabilities, uncached_dependencies)
        """
        cached_results = []
        uncached_deps = []
        
        conn = sqlite3.connect(self.cache_db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            for dep in dependencies:
                query_hash = self._generate_query_hash(dep.ecosystem, dep.name, dep.version)
                
                cursor = conn.execute("""
                    SELECT vulnerabilities, expires_at FROM osv_cache 
                    WHERE query_hash = ?
                """, (query_hash,))
                
                row = cursor.fetchone()
                if row and datetime.fromisoformat(row["expires_at"]) > datetime.now():
                    # Cache hit and not expired
                    vulns = json.loads(row["vulnerabilities"])
                    for vuln in vulns:
                        vuln["package"] = dep.name
                        vuln["ecosystem"] = dep.ecosystem
                    cached_results.extend(vulns)
                else:
                    # Cache miss or expired
                    uncached_deps.append(dep)
        finally:
            conn.close()
        
        return cached_results, uncached_deps
    
    async def _query_osv_batch(self, dependencies: List[Dep]) -> List[Dict]:
        """Query OSV.dev API in batches with retry logic"""
        all_results = []
        
        # Split into batches
        for i in range(0, len(dependencies), self.batch_size):
            batch = dependencies[i:i + self.batch_size]
            batch_results = await self._query_single_batch(batch)
            all_results.extend(batch_results)
            
            # Rate limiting between batches
            await self._rate_limit()
        
        return all_results
    
    async def _query_single_batch(self, batch: List[Dep]) -> List[Dict]:
        """Query a single batch of dependencies with retry logic"""
        queries = []
        for dep in batch:
            query = OSVQuery(
                package={"name": dep.name, "ecosystem": dep.ecosystem},
                version=dep.version if dep.version != "unknown" else None
            )
            queries.append(query)
        
        batch_query = OSVBatchQuery(queries=queries)
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/v1/querybatch",
                    json=batch_query.dict()
                )
                
                if response.status_code == 200:
                    batch_response = OSVBatchResponse(**response.json())
                    
                    # Flatten results and add package metadata
                    results = []
                    for i, query_result in enumerate(batch_response.results):
                        dep = batch[i]
                        
                        # Handle different response formats
                        vulns_list = []
                        if isinstance(query_result, dict):
                            if "vulns" in query_result:
                                vulns_list = query_result["vulns"]
                        elif isinstance(query_result, list):
                            vulns_list = query_result
                        
                        for vuln in vulns_list:
                            if isinstance(vuln, dict):
                                vuln_dict = vuln.copy()
                                vuln_dict["package"] = dep.name
                                vuln_dict["ecosystem"] = dep.ecosystem
                                results.append(vuln_dict)
                    
                    return results
                
                elif response.status_code == 429:
                    # Rate limited - exponential backoff
                    delay = self.rate_limit_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    continue
                
                else:
                    response.raise_for_status()
                    
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"Failed to query OSV after {self.max_retries} attempts: {e}")
                
                # Exponential backoff with jitter
                delay = self.rate_limit_delay * (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(delay)
        
        return []  # Should not reach here
    
    async def _cache_results(self, dependencies: List[Dep], results: List[Dict]):
        """Cache OSV query results"""
        conn = sqlite3.connect(self.cache_db_path)
        
        try:
            # Group results by dependency
            results_by_dep = {}
            for result in results:
                key = (result["ecosystem"], result["package"])
                if key not in results_by_dep:
                    results_by_dep[key] = []
                results_by_dep[key].append(result)
            
            now = datetime.now()
            expires_at = now + timedelta(hours=24)  # Cache for 24 hours
            
            for dep in dependencies:
                key = (dep.ecosystem, dep.name)
                dep_vulns = results_by_dep.get(key, [])
                
                query_hash = self._generate_query_hash(dep.ecosystem, dep.name, dep.version)
                
                # Remove package metadata before caching (it's redundant)
                cache_vulns = []
                for vuln in dep_vulns:
                    cache_vuln = {k: v for k, v in vuln.items() 
                                if k not in ["package", "ecosystem"]}
                    cache_vulns.append(cache_vuln)
                
                conn.execute("""
                    INSERT OR REPLACE INTO osv_cache 
                    (query_hash, ecosystem, name, version, vulnerabilities, cached_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    query_hash,
                    dep.ecosystem,
                    dep.name,
                    dep.version,
                    json.dumps(cache_vulns),
                    now.isoformat(),
                    expires_at.isoformat()
                ))
            
            conn.commit()
        finally:
            conn.close()
    
    def _generate_query_hash(self, ecosystem: str, name: str, version: str) -> str:
        """Generate a hash for cache key"""
        content = f"{ecosystem}:{name}:{version}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1
    
    def _convert_osv_to_vuln(self, osv_data: Dict, dep: Dep) -> Vuln:
        """Convert OSV vulnerability data to our Vuln model"""
        
        # Extract severity
        severity = self._extract_severity(osv_data.get("severity", []))
        
        # Extract CVE IDs from aliases
        cve_ids = [alias for alias in osv_data.get("aliases", []) if alias.startswith("CVE-")]
        
        # Find advisory URL
        advisory_url = None
        for ref in osv_data.get("references", []):
            if ref.get("type") == "ADVISORY":
                advisory_url = ref.get("url")
                break
        
        # Extract fixed version range
        fixed_range = self._extract_fixed_range(osv_data.get("affected", []), dep.name)
        
        # Parse dates
        published = None
        modified = None
        if osv_data.get("published"):
            try:
                published = datetime.fromisoformat(osv_data["published"].replace("Z", "+00:00"))
            except ValueError:
                pass
        
        if osv_data.get("modified"):
            try:
                modified = datetime.fromisoformat(osv_data["modified"].replace("Z", "+00:00"))
            except ValueError:
                pass
        
        return Vuln(
            package=dep.name,
            version=dep.version,
            ecosystem=dep.ecosystem,
            vulnerability_id=osv_data.get("id", ""),
            severity=severity,
            cve_ids=cve_ids,
            summary=osv_data.get("summary", ""),
            details=osv_data.get("details"),
            advisory_url=advisory_url,
            fixed_range=fixed_range,
            published=published,
            modified=modified,
            aliases=osv_data.get("aliases", [])
        )
    
    def _extract_severity(self, severity_list: List[Dict]) -> Optional[SeverityLevel]:
        """Extract and normalize severity from OSV data"""
        if not severity_list:
            return SeverityLevel.UNKNOWN
        
        # OSV can have multiple severity ratings, prefer CVSS
        cvss_severity = None
        for sev in severity_list:
            if sev.get("type") == "CVSS_V3":
                score = sev.get("score", 0)
                if score >= 9.0:
                    cvss_severity = SeverityLevel.CRITICAL
                elif score >= 7.0:
                    cvss_severity = SeverityLevel.HIGH
                elif score >= 4.0:
                    cvss_severity = SeverityLevel.MEDIUM
                else:
                    cvss_severity = SeverityLevel.LOW
                break
        
        if cvss_severity:
            return cvss_severity
        
        # Fall back to other severity types
        for sev in severity_list:
            severity_str = sev.get("severity", "").upper()
            if severity_str in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                return SeverityLevel(severity_str)
        
        return SeverityLevel.UNKNOWN
    
    def _extract_fixed_range(self, affected_list: List[Dict], package_name: str) -> Optional[str]:
        """Extract fixed version range from OSV affected data"""
        for affected in affected_list:
            package_info = affected.get("package", {})
            if package_info.get("name") == package_name:
                ranges = affected.get("ranges", [])
                for range_info in ranges:
                    events = range_info.get("events", [])
                    for event in events:
                        if "fixed" in event:
                            return f">={event['fixed']}"
        
        return None
    
    async def cleanup_cache(self, max_age_days: int = 7):
        """Remove old cache entries"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        conn = sqlite3.connect(self.cache_db_path)
        try:
            conn.execute("""
                DELETE FROM osv_cache 
                WHERE expires_at < ?
            """, (cutoff_date.isoformat(),))
            conn.commit()
        finally:
            conn.close()
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()