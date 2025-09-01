from __future__ import annotations

import asyncio
import logging
import random
import time
from datetime import datetime
import httpx

from ..models import Dep, OSVQuery, OSVBatchQuery, OSVBatchResponse, Vuln, SeverityLevel


class OSVScanner:
    """OSV.dev API client with batching and retry logic"""
    
    def __init__(self, batch_size: int = 100, rate_limit_delay: float = 1.0, max_retries: int = 3):
        self.base_url = "https://api.osv.dev"
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # HTTP client with reasonable timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Rate limiting
        self._last_request_time = 0.0
        self._request_count = 0
    
    async def scan_dependencies(self, dependencies: list[Dep]) -> list[Vuln]:
        """
        Scan a list of dependencies for vulnerabilities
        Returns a list of vulnerabilities found
        """
        # Removed accuracy tracking
        
        try:
            # Deduplicate dependencies by (ecosystem, name, version)
            unique_deps = self._deduplicate_dependencies(dependencies)
            
            # Query OSV for all dependencies
            fresh_results = await self._query_osv_batch(unique_deps)
            
            # Convert to Vuln objects and enrich with dependency metadata
            vulnerabilities = []
            seen_vulnerabilities = set()  # Track unique vulnerabilities by (id, package, ecosystem)
            
            for dep in unique_deps:
                dep_vulns = [v for v in fresh_results 
                            if v.get("package") == dep.name and v.get("ecosystem") == dep.ecosystem]
                
                for vuln_data in dep_vulns:
                    # Create unique key for this vulnerability
                    vuln_id = vuln_data.get("id", "")
                    vuln_key = (vuln_id, dep.name, dep.ecosystem)
                    
                    # Only add if we haven't seen this vulnerability for this package before
                    if vuln_key not in seen_vulnerabilities:
                        vuln = self._convert_osv_to_vuln(vuln_data, dep)
                        vulnerabilities.append(vuln)
                        seen_vulnerabilities.add(vuln_key)
            
            # Removed accuracy tracking
            
            return vulnerabilities
            
        except Exception as e:
            # Log scan failure but don't track inaccurate results
            self.logger.error(f"Scan failed: {e}")
            raise
    
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
            version_to_send = dep.version if dep.version != "unknown" else None
            query = OSVQuery(
                package={"name": dep.name, "ecosystem": dep.ecosystem},
                version=version_to_send
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
                    
                    self.logger.debug(f"OSV response received with {len(response_data.get('results', []))} result(s)")
                    
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
                        self.logger.info(f"Fetching detailed vulnerability data for {len(results)} vulnerabilities")
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
    
    async def _rate_limit(self):
        """Implement rate limiting between requests"""
        # Use time.time() instead of event loop time for better performance
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = time.time()
        self._request_count += 1
    
    async def _enrich_vulnerability_data(self, minimal_results: list[dict]) -> list[dict]:
        """Fetch detailed vulnerability data for minimal results"""
        enriched_results = []
        
        # Process in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(minimal_results), batch_size):
            batch = minimal_results[i:i + batch_size]
            
            # Separate sync and async tasks for better performance
            async_tasks = []
            sync_results = []
            
            for vuln in batch:
                if vuln.get('id'):
                    async_tasks.append(self._fetch_individual_vulnerability(vuln))
                else:
                    # Handle sync results immediately
                    sync_results.append(self._return_original_sync(vuln))
            
            # Wait for async tasks only if we have any
            async_results = []
            if async_tasks:
                async_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            
            # Combine results
            for result in sync_results + async_results:
                if isinstance(result, dict):
                    enriched_results.append(result)
                elif not isinstance(result, Exception):
                    # Fallback to original if enrichment failed
                    pass
        
        return enriched_results
    
    async def _return_original(self, vuln: dict) -> dict:
        """Return original vulnerability data as fallback"""
        return vuln
    
    def _return_original_sync(self, vuln: dict) -> dict:
        """Return original vulnerability data synchronously"""
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
        
        # Log vulnerability processing for debugging
        vuln_id = osv_data.get('id', 'unknown')
        self.logger.debug(f"Processing vulnerability {vuln_id} for {dep.name}@{dep.version}")
        
        if self.logger.isEnabledFor(logging.DEBUG):
            # Only log detailed info if debug logging is enabled
            self.logger.debug(f"OSV data keys: {list(osv_data.keys())}")
            if "severity" in osv_data:
                self.logger.debug(f"Severity field for {vuln_id}: {osv_data['severity']}")
            if "database_specific" in osv_data:
                self.logger.debug(f"Database specific for {vuln_id}: {osv_data['database_specific']}")
        
        # Extract immediate parent for transitive dependencies
        immediate_parent = self._extract_immediate_parent(dep)
        
        # Extract severity and CVSS score (including database_specific fallback)
        severity, cvss_score = self._extract_severity_and_score(
            osv_data.get("severity", []),
            osv_data.get("database_specific"),
            osv_data.get("ecosystem_specific")
        )
        
        # Log final score assignment for debugging
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Final score for {vuln_id}: CVSS={cvss_score}, Severity={severity.value if severity else 'None'}")
        
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
            cvss_score=cvss_score,
            cve_ids=cve_ids,
            summary=osv_data.get("summary", ""),
            details=osv_data.get("details"),
            advisory_url=advisory_url,
            fixed_range=fixed_range,
            published=published,
            modified=modified,
            aliases=osv_data.get("aliases", []),
            immediate_parent=immediate_parent
        )
    
    def _extract_immediate_parent(self, dep: Dep) -> str | None:
        """
        Extract the immediate parent package for transitive dependencies
        
        For direct dependencies (path length 1), returns None
        For transitive dependencies, returns the immediate parent (second-to-last in path)
        
        Examples:
        - ["axios"] -> None (direct dependency)
        - ["axios", "form-data"] -> "axios" (transitive via axios)
        - ["next-auth", "oauth", "jose"] -> "oauth" (transitive via oauth)
        """
        # Debug logging
        self.logger.debug(f"Extracting immediate parent for {dep.name}: path={dep.path}, is_direct={dep.is_direct}")
        
        if not dep.path or len(dep.path) <= 1:
            # Direct dependency or invalid path
            self.logger.debug(f"  -> No parent (direct dependency or invalid path)")
            return None
        
        # For transitive dependencies, the immediate parent is the second-to-last element
        # Path structure: [root, intermediate1, intermediate2, ..., vulnerable_package]
        immediate_parent = dep.path[-2]
        self.logger.debug(f"  -> Immediate parent: {immediate_parent}")
        return immediate_parent
    
    def _extract_severity_and_score(self, severity_list: list[dict], db_specific: dict | None = None, ecosystem_specific: dict | None = None) -> tuple[SeverityLevel, float | None]:
        """Extract and normalize severity and CVSS score from OSV data"""
        
        def _to_float(val) -> float:
            """Safely convert severity scores to float"""
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        
        def _parse_cvss_score(cvss_string: str) -> float:
            """Parse CVSS score from CVSS vector string using proper CVSS 3.1 calculation"""
            try:
                # If it's already a number, use it
                if isinstance(cvss_string, (int, float)):
                    return float(cvss_string)
                
                # Try to extract embedded score first
                # Sometimes the score is embedded like "CVSS:3.1/.../ score:7.5"
                import re
                score_match = re.search(r'score[:\s]+(\d+\.?\d*)', cvss_string, re.IGNORECASE)
                if score_match:
                    return float(score_match.group(1))
                
                # Parse CVSS 3.1 vector string
                if not cvss_string.startswith("CVSS:3."):
                    # If not CVSS 3.x, use fallback calculation
                    return self._calculate_cvss_fallback(cvss_string)
                
                # Extract metrics from CVSS vector
                metrics = {}
                parts = cvss_string.split('/')
                for part in parts[1:]:  # Skip "CVSS:3.1"
                    if ':' in part:
                        key, value = part.split(':', 1)
                        metrics[key] = value
                
                # Calculate CVSS 3.1 score
                return self._calculate_cvss31_score(metrics)
                
            except (ValueError, TypeError) as e:
                self.logger.debug(f"CVSS parsing failed for '{cvss_string}': {e}")
                return self._calculate_cvss_fallback(cvss_string)

        cvss_score = None
        severity_level = SeverityLevel.UNKNOWN
        
        if severity_list:
            # OSV can have multiple severity ratings, prefer CVSS
            for sev in severity_list:
                if sev.get("type") in ["CVSS_V3", "CVSS_V4", "CVSS_V2"]:
                    score_str = sev.get("score", "")
                    
                    # Enhanced score extraction - look for numeric score in multiple places
                    score = None
                    
                    # Check for direct numeric score first
                    if isinstance(score_str, (int, float)):
                        score = float(score_str)
                    elif isinstance(score_str, str):
                        # Try to parse as float first
                        try:
                            score = float(score_str)
                        except ValueError:
                            # If not a direct number, parse the CVSS vector
                            if score_str.startswith("CVSS:"):
                                score = _parse_cvss_score(score_str)
                            else:
                                score = _to_float(score_str)
                    
                    # Look for numeric score in other fields of the severity object
                    if score is None or score <= 0:
                        # Check for baseScore, base_score, cvss_score fields
                        for score_field in ['baseScore', 'base_score', 'cvss_score', 'score_value']:
                            field_val = sev.get(score_field)
                            if field_val is not None:
                                try:
                                    score = float(field_val)
                                    self.logger.debug(f"Found CVSS score {score} in field '{score_field}'")
                                    break
                                except (ValueError, TypeError):
                                    continue
                    
                    # If we still don't have a score, try to calculate from vector
                    if score is None or score <= 0:
                        score = _to_float(score_str) if score_str else 7.5
                    
                    cvss_score = score
                    
                    # Classify severity based on actual CVSS score
                    if score >= 9.0:
                        severity_level = SeverityLevel.CRITICAL
                    elif score >= 7.0:
                        severity_level = SeverityLevel.HIGH
                    elif score >= 4.0:
                        severity_level = SeverityLevel.MEDIUM
                    elif score > 0:
                        severity_level = SeverityLevel.LOW
                    else:
                        severity_level = SeverityLevel.UNKNOWN
                    
                    self.logger.debug(f"CVSS score extraction: type={sev.get('type')}, score={score}, severity={severity_level.value}")
                    break

            # If no CVSS found, look for other severity descriptors (but don't assume scores)
            if cvss_score is None:
                for sev in severity_list:
                    severity_str = sev.get("severity", "").upper()
                    if severity_str in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                        severity_level = SeverityLevel(severity_str)
                        # Don't assign a score without actual data - leave it None to trigger lookup elsewhere
                        self.logger.debug(f"Found severity descriptor '{severity_str}' without numeric score")
                        break
                    if severity_str == "MODERATE":
                        severity_level = SeverityLevel.MEDIUM
                        self.logger.debug("Found 'MODERATE' severity descriptor")
                        break

        # Check database_specific severity (e.g., GitHub advisories)
        if cvss_score is None and db_specific and isinstance(db_specific, dict):
            # First try to find actual numeric scores in database_specific
            for score_field in ['cvss_score', 'base_score', 'score', 'cvss', 'severity_score']:
                score_val = _to_float(db_specific.get(score_field, 0))
                if score_val > 0:
                    cvss_score = score_val
                    if score_val >= 9.0:
                        severity_level = SeverityLevel.CRITICAL
                    elif score_val >= 7.0:
                        severity_level = SeverityLevel.HIGH
                    elif score_val >= 4.0:
                        severity_level = SeverityLevel.MEDIUM
                    else:
                        severity_level = SeverityLevel.LOW
                    self.logger.debug(f"Found CVSS score {score_val} in database_specific['{score_field}']")
                    break
            
            # If no numeric score found, check severity strings - but be more conservative
            if cvss_score is None:
                sev_str = db_specific.get("severity") or db_specific.get("github_severity")
                if isinstance(sev_str, str):
                    sev_str = sev_str.upper()
                    if sev_str in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                        severity_level = SeverityLevel(sev_str)
                        # Use more conservative estimates when we don't have actual scores
                        cvss_score = {"CRITICAL": 9.0, "HIGH": 7.0, "MEDIUM": 5.0, "LOW": 3.0}.get(sev_str)
                        self.logger.debug(f"Using conservative CVSS estimate {cvss_score} for severity '{sev_str}'")
                    elif sev_str == "MODERATE":
                        severity_level = SeverityLevel.MEDIUM
                        cvss_score = 5.0

        # Check ecosystem_specific data
        if cvss_score is None and ecosystem_specific and isinstance(ecosystem_specific, dict):
            score_val = _to_float(ecosystem_specific.get("score", 0))
            if score_val > 0:
                cvss_score = score_val
                if score_val >= 9.0:
                    severity_level = SeverityLevel.CRITICAL
                elif score_val >= 7.0:
                    severity_level = SeverityLevel.HIGH
                elif score_val >= 4.0:
                    severity_level = SeverityLevel.MEDIUM
                else:
                    severity_level = SeverityLevel.LOW

        return severity_level, cvss_score
    
    def _calculate_cvss31_score(self, metrics: dict[str, str]) -> float:
        """Calculate CVSS 3.1 base score from parsed metrics"""
        try:
            # Base metrics with defaults
            av = metrics.get('AV', 'N')  # Attack Vector
            ac = metrics.get('AC', 'L')  # Attack Complexity  
            pr = metrics.get('PR', 'N')  # Privileges Required
            ui = metrics.get('UI', 'N')  # User Interaction
            s = metrics.get('S', 'U')    # Scope
            c = metrics.get('C', 'N')    # Confidentiality Impact
            i = metrics.get('I', 'N')    # Integrity Impact
            a = metrics.get('A', 'N')    # Availability Impact
            
            # Convert to numeric values based on CVSS 3.1 specification
            av_score = {'N': 0.85, 'A': 0.62, 'L': 0.55, 'P': 0.2}.get(av, 0.85)
            ac_score = {'L': 0.77, 'H': 0.44}.get(ac, 0.77)
            
            # PR score depends on scope
            if s == 'C':  # Changed scope
                pr_score = {'N': 0.85, 'L': 0.68, 'H': 0.50}.get(pr, 0.85)
            else:  # Unchanged scope
                pr_score = {'N': 0.85, 'L': 0.62, 'H': 0.27}.get(pr, 0.85)
                
            ui_score = {'N': 0.85, 'R': 0.62}.get(ui, 0.85)
            
            # Impact scores
            c_impact = {'H': 0.56, 'L': 0.22, 'N': 0.0}.get(c, 0.0)
            i_impact = {'H': 0.56, 'L': 0.22, 'N': 0.0}.get(i, 0.0)
            a_impact = {'H': 0.56, 'L': 0.22, 'N': 0.0}.get(a, 0.0)
            
            # Calculate Impact Sub Score (ISS)
            impact_sub_score = 1 - ((1 - c_impact) * (1 - i_impact) * (1 - a_impact))
            
            # Calculate Impact Score
            if s == 'C':  # Changed scope
                impact_score = 7.52 * (impact_sub_score - 0.029) - 3.25 * pow(impact_sub_score - 0.02, 15)
            else:  # Unchanged scope
                impact_score = 6.42 * impact_sub_score
            
            # Calculate Exploitability Score
            exploitability = 8.22 * av_score * ac_score * pr_score * ui_score
            
            # Calculate Base Score
            if impact_sub_score <= 0:
                base_score = 0.0
            elif s == 'C':  # Changed scope
                base_score = min(10.0, impact_score + exploitability)
            else:  # Unchanged scope  
                base_score = min(10.0, impact_score + exploitability)
            
            # Round up to nearest 0.1
            base_score = round(base_score * 10) / 10.0
            
            self.logger.debug(f"CVSS 3.1 calculation: AV:{av} AC:{ac} PR:{pr} UI:{ui} S:{s} C:{c} I:{i} A:{a} -> {base_score}")
            return base_score
            
        except Exception as e:
            self.logger.debug(f"CVSS 3.1 calculation failed: {e}")
            return 7.5
    
    def _calculate_cvss_fallback(self, cvss_string: str) -> float:
        """Fallback CVSS calculation for non-3.1 vectors or when parsing fails"""
        try:
            # Simple heuristic based on vector content
            high_impact = any(x in cvss_string for x in ['C:H', 'I:H', 'A:H'])
            network_vector = 'AV:N' in cvss_string
            low_complexity = 'AC:L' in cvss_string
            no_privileges = 'PR:N' in cvss_string
            
            if high_impact and network_vector and low_complexity and no_privileges:
                # High impact, network accessible, low complexity, no privileges = likely 8.0+
                return 8.5
            elif high_impact and network_vector:
                return 7.5
            elif high_impact:
                return 6.5
            else:
                return 5.0
        except Exception:
            return 7.5
    
    def _extract_severity(self, severity_list: list[dict], db_specific: dict | None = None, ecosystem_specific: dict | None = None) -> SeverityLevel:
        """Extract and normalize severity from OSV data"""

        def _to_float(val) -> float:
            """Safely convert severity scores to float"""
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0
        
        def _parse_cvss_score(cvss_string: str) -> float:
            """Parse CVSS score from vector - simplified calculation"""
            try:
                # This is a simplified CVSS calculator - for production use a proper library
                
                # Base metrics extraction
                av_score = 0.85 if 'AV:N' in cvss_string else (0.62 if 'AV:A' in cvss_string else (0.55 if 'AV:L' in cvss_string else 0.2))
                ac_score = 0.77 if 'AC:L' in cvss_string else 0.44
                pr_score = 0.85 if 'PR:N' in cvss_string else (0.68 if 'PR:L' in cvss_string else 0.5)
                # Adjust PR score based on scope for CVSS v3
                if scope and 'PR:L' in cvss_string:
                    pr_score = 0.68
                elif scope and 'PR:H' in cvss_string:
                    pr_score = 0.5
                ui_score = 0.85 if 'UI:N' in cvss_string else 0.62
                scope = 'S:C' in cvss_string
                
                # Impact metrics
                c_impact = 0.56 if 'C:H' in cvss_string else (0.22 if 'C:L' in cvss_string else 0)
                i_impact = 0.56 if 'I:H' in cvss_string else (0.22 if 'I:L' in cvss_string else 0)
                a_impact = 0.56 if 'A:H' in cvss_string else (0.22 if 'A:L' in cvss_string else 0)
                
                # Impact calculation
                impact = 1 - ((1 - c_impact) * (1 - i_impact) * (1 - a_impact))
                
                # Exploitability calculation
                exploitability = 8.22 * av_score * ac_score * pr_score * ui_score
                
                # Base score calculation
                if impact <= 0:
                    return 0.0
                
                if scope:
                    # Changed scope
                    impact_score = 7.52 * (impact - 0.029) - 3.25 * pow((impact - 0.02), 15)
                else:
                    # Unchanged scope
                    impact_score = 6.42 * impact
                
                base_score = min(10.0, impact_score + exploitability)
                
                # Round up to next tenth
                return round(base_score * 10) / 10.0
                
            except (ValueError, TypeError):
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
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()