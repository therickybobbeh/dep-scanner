import asyncio
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
# Modern type annotations - no imports needed for basic types
import httpx
import random

from ..models import Dep, OSVQuery, OSVBatchQuery, OSVBatchResponse, Vuln, SeverityLevel

class OSVScanner:
    """OSV.dev API client with batching, caching, and retry logic"""
    
    def __init__(self, cache_db_path: str | None = None, batch_size: int = 100, 
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
    
    async def scan_dependencies(self, dependencies: list[Dep]) -> list[Vuln]:
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
    
    def _deduplicate_dependencies(self, dependencies: list[Dep]) -> list[Dep]:
        """Remove duplicate dependencies based on (ecosystem, name, version)"""
        seen = set()
        unique_deps = []
        
        for dep in dependencies:
            key = (dep.ecosystem, dep.name, dep.version)
            if key not in seen:
                seen.add(key)
                unique_deps.append(dep)
        
        return unique_deps
    
    async def _check_cache(self, dependencies: list[Dep]) -> tuple[list[dict], list[Dep]]:
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

                    # If cached vulnerabilities lack severity info, re-fetch them
                    missing_severity = False
                    for vuln in vulns:
                        if not vuln.get("severity") and not (
                            isinstance(vuln.get("database_specific"), dict)
                            and vuln["database_specific"].get("severity")
                        ):
                            missing_severity = True
                            break

                    if missing_severity:
                        # Treat as cache miss to refresh with severity data
                        uncached_deps.append(dep)
                    else:
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
    
    async def _query_osv_batch(self, dependencies: list[Dep]) -> list[dict]:
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
    
    async def _query_single_batch(self, batch: list[Dep]) -> list[dict]:
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
                    json=batch_query.model_dump()
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Debug the response structure (limit output)
                    # print(f"DEBUG: Raw OSV response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'list'}")
                    
                    batch_response = OSVBatchResponse(**response_data)
                    
                    # Flatten results and add package metadata
                    results = []
                    for i, query_result in enumerate(batch_response.results):
                        dep = batch[i]
                        
                        # Handle different response formats from OSV API
                        vulns_list = []
                        if isinstance(query_result, dict):
                            if "vulns" in query_result:
                                vulns_list = query_result["vulns"]
                            else:
                                # Sometimes the response is the vulnerability object itself
                                vulns_list = [query_result]
                        elif isinstance(query_result, list):
                            vulns_list = query_result
                        
                        for vuln in vulns_list:
                            if isinstance(vuln, dict) and vuln:  # Skip empty dicts
                                vuln_dict = vuln.copy()
                                vuln_dict["package"] = dep.name
                                vuln_dict["ecosystem"] = dep.ecosystem
                                results.append(vuln_dict)
                    
                    # If results are minimal (only id, modified, package, ecosystem), 
                    # we need to fetch individual vulnerability details
                    if results and all(len(r.keys()) <= 4 for r in results):
                        # print("DEBUG: Results are minimal, fetching detailed vulnerability data...")
                        enriched_results = await self._enrich_vulnerability_data(results)
                        return enriched_results
                    
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
    
    async def _cache_results(self, dependencies: list[Dep], results: list[dict]):
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
    
    async def _enrich_vulnerability_data(self, minimal_results: list[dict]) -> list[dict]:
        """Fetch detailed vulnerability data for minimal results"""
        enriched_results = []
        
        # Process in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(minimal_results), batch_size):
            batch = minimal_results[i:i + batch_size]
            
            # Fetch details for each vulnerability in batch
            batch_tasks = []
            for vuln in batch:
                if vuln.get('id'):
                    batch_tasks.append(self._fetch_individual_vulnerability(vuln))
                else:
                    batch_tasks.append(asyncio.create_task(self._return_original(vuln)))
            
            # Wait for all tasks in batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict):
                    enriched_results.append(result)
                elif not isinstance(result, Exception):
                    # Fallback to original if enrichment failed
                    pass
        
        return enriched_results
    
    async def _return_original(self, vuln: dict) -> dict:
        """Return original vulnerability data as fallback"""
        return vuln
    
    async def _fetch_individual_vulnerability(self, minimal_vuln: dict) -> dict:
        """Fetch complete vulnerability details using the individual vulnerability endpoint"""
        vuln_id = minimal_vuln.get('id')
        if not vuln_id:
            return minimal_vuln
        
        await self._rate_limit()
        
        try:
            response = await self.client.get(f"{self.base_url}/v1/vulns/{vuln_id}")
            
            if response.status_code == 200:
                detailed_vuln = response.json()
                # Preserve the package and ecosystem from minimal data
                detailed_vuln["package"] = minimal_vuln.get("package")
                detailed_vuln["ecosystem"] = minimal_vuln.get("ecosystem")
                return detailed_vuln
            else:
                # Failed to fetch details, use minimal data
                return minimal_vuln
                
        except Exception as e:
            # Error fetching details, use minimal data
            return minimal_vuln
    
    def _convert_osv_to_vuln(self, osv_data: dict, dep: Dep) -> Vuln:
        """Convert OSV vulnerability data to our Vuln model"""
        
        # Debug: Print OSV data structure for first few vulnerabilities
        if hasattr(self, '_debug_count'):
            self._debug_count += 1
        else:
            self._debug_count = 1
            
        # Debugging disabled for cleaner output
        # if self._debug_count <= 1:  # Debug first vulnerability only
        #     print(f"DEBUG: OSV data keys: {list(osv_data.keys())}")
        #     if "severity" in osv_data:
        #         print(f"DEBUG: Severity field: {osv_data['severity']}")
        #     if "database_specific" in osv_data:
        #         print(f"DEBUG: Database specific: {osv_data['database_specific']}")
        
        # Extract severity (including database_specific fallback)
        severity = self._extract_severity(
            osv_data.get("severity", []),
            osv_data.get("database_specific"),
            osv_data.get("ecosystem_specific")
        )
        
        # Extract CVE IDs from aliases
        cve_ids = [alias for alias in osv_data.get("aliases", []) if alias.startswith("CVE-")]
        
        # Find advisory URL - prioritize ADVISORY, fallback to any URL, then generate OSV.dev link
        advisory_url = None
        
        # First, look for ADVISORY type references
        for ref in osv_data.get("references", []):
            if ref.get("type") == "ADVISORY":
                advisory_url = ref.get("url")
                break
        
        # If no ADVISORY found, use first available URL
        if not advisory_url:
            for ref in osv_data.get("references", []):
                if ref.get("url"):
                    advisory_url = ref.get("url")
                    break
        
        # If still no URL and we have an OSV ID, generate OSV.dev link
        if not advisory_url and osv_data.get("id"):
            advisory_url = f"https://osv.dev/vulnerability/{osv_data['id']}"
        
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
    
    def _extract_severity(self, severity_list: list[dict], db_specific: dict | None = None, ecosystem_specific: dict | None = None) -> SeverityLevel:
        """Extract and normalize severity from OSV data"""

        def _to_float(val) -> float:
            """Safely convert severity scores to float"""
            try:
                return float(val)
            except Exception:
                return 0.0
        
        def _parse_cvss_score(cvss_string: str) -> float:
            """Parse CVSS score from string like 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H'"""
            try:
                # CVSS v3/v4 scoring - we need to calculate from vector or use a lookup
                # For simplicity, let's use a basic heuristic based on impact values
                if 'A:H' in cvss_string or 'VA:H' in cvss_string:  # High availability impact
                    if 'AC:L' in cvss_string and 'PR:N' in cvss_string:  # Low complexity, no privileges
                        return 7.5  # HIGH
                    else:
                        return 5.3  # MEDIUM
                elif 'A:L' in cvss_string or 'VA:L' in cvss_string:  # Low availability impact
                    return 3.1  # LOW
                elif 'C:H' in cvss_string or 'VC:H' in cvss_string:  # High confidentiality impact
                    return 7.5  # HIGH
                elif 'I:H' in cvss_string or 'VI:H' in cvss_string:  # High integrity impact
                    return 7.5  # HIGH
                else:
                    return 0.0
            except Exception:
                return 0.0

        if severity_list:
            # OSV can have multiple severity ratings, prefer CVSS
            cvss_severity = None
            for sev in severity_list:
                if sev.get("type") in ["CVSS_V3", "CVSS_V4"]:
                    score_str = sev.get("score", "")
                    if isinstance(score_str, str) and score_str.startswith("CVSS:"):
                        score = _parse_cvss_score(score_str)
                    else:
                        score = _to_float(score_str)
                    
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

            # Fall back to other severity descriptors
            for sev in severity_list:
                severity_str = sev.get("severity", "").upper()
                if severity_str in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    return SeverityLevel(severity_str)
                if severity_str == "MODERATE":
                    return SeverityLevel.MEDIUM

        # Check database_specific severity (e.g., GitHub advisories)
        if db_specific and isinstance(db_specific, dict):
            sev_str = db_specific.get("severity") or db_specific.get("github_severity")
            if isinstance(sev_str, str):
                sev_str = sev_str.upper()
                if sev_str in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    return SeverityLevel(sev_str)
                if sev_str == "MODERATE":
                    return SeverityLevel.MEDIUM

            # Some databases expose numeric score
            score_val = _to_float(db_specific.get("score"))
            if score_val:
                if score_val >= 9.0:
                    return SeverityLevel.CRITICAL
                if score_val >= 7.0:
                    return SeverityLevel.HIGH
                if score_val >= 4.0:
                    return SeverityLevel.MEDIUM
                return SeverityLevel.LOW

        # Check ecosystem_specific data (npm, PyPI specific fields)
        if ecosystem_specific and isinstance(ecosystem_specific, dict):
            # Check for npm specific severity
            npm_sev = ecosystem_specific.get("severity")
            if isinstance(npm_sev, str):
                npm_sev = npm_sev.upper()
                if npm_sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    return SeverityLevel(npm_sev)
                if npm_sev == "MODERATE":
                    return SeverityLevel.MEDIUM
            
            # Check for advisory severity (common in GitHub advisories)
            advisory_sev = ecosystem_specific.get("advisory_severity")
            if isinstance(advisory_sev, str):
                advisory_sev = advisory_sev.upper()
                if advisory_sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    return SeverityLevel(advisory_sev)
                if advisory_sev == "MODERATE":
                    return SeverityLevel.MEDIUM

        # Try to infer severity from vulnerability ID patterns as last resort
        return self._infer_severity_from_patterns(severity_list, db_specific, ecosystem_specific)
    
    def _infer_severity_from_patterns(self, severity_list: list[dict], db_specific: dict | None, ecosystem_specific: dict | None) -> SeverityLevel:
        """Attempt to infer severity from common patterns in OSV data"""
        
        # Look for any string fields that might contain severity information
        all_data = {}
        if db_specific:
            all_data.update(db_specific)
        if ecosystem_specific:
            all_data.update(ecosystem_specific)
            
        # Check all string values for severity keywords
        for key, value in all_data.items():
            if isinstance(value, str):
                value_upper = value.upper()
                if any(word in value_upper for word in ["CRITICAL", "HIGH", "MEDIUM", "MODERATE", "LOW"]):
                    if "CRITICAL" in value_upper:
                        return SeverityLevel.CRITICAL
                    elif "HIGH" in value_upper:
                        return SeverityLevel.HIGH
                    elif any(word in value_upper for word in ["MEDIUM", "MODERATE"]):
                        return SeverityLevel.MEDIUM
                    elif "LOW" in value_upper:
                        return SeverityLevel.LOW
        
        # If we have any severity data at all, even if we can't parse it, 
        # default to MEDIUM rather than UNKNOWN for better UX
        if severity_list or db_specific or ecosystem_specific:
            return SeverityLevel.MEDIUM
            
        return SeverityLevel.UNKNOWN
    
    def _extract_fixed_range(self, affected_list: list[dict], package_name: str) -> str | None:
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
    
    async def cleanup_cache(self, max_age_days: int = 1):
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