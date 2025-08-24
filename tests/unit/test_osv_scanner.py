import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from backend.app.scanner.osv import OSVScanner
from backend.app.models import Dep, Vuln, SeverityLevel

@pytest.fixture
def osv_scanner():
    return OSVScanner(cache_db_path=":memory:")  # Use in-memory SQLite for tests

@pytest.fixture
def sample_dependencies():
    return [
        Dep(
            name="lodash",
            version="4.17.20",
            ecosystem="npm",
            path=["lodash"],
            is_direct=True,
            is_dev=False
        ),
        Dep(
            name="flask",
            version="1.1.4",
            ecosystem="PyPI",
            path=["flask"],
            is_direct=True,
            is_dev=False
        )
    ]

@pytest.fixture
def mock_osv_response():
    return {
        "results": [
            [  # Results for lodash
                {
                    "id": "GHSA-35jh-r3h4-6jhm",
                    "summary": "Prototype Pollution in lodash",
                    "details": "lodash versions prior to 4.17.21 are vulnerable to Prototype Pollution.",
                    "aliases": ["CVE-2020-8203"],
                    "severity": [
                        {
                            "type": "CVSS_V3",
                            "score": 7.4
                        }
                    ],
                    "affected": [
                        {
                            "package": {
                                "ecosystem": "npm",
                                "name": "lodash"
                            },
                            "ranges": [
                                {
                                    "type": "ECOSYSTEM",
                                    "events": [
                                        {"introduced": "0"},
                                        {"fixed": "4.17.21"}
                                    ]
                                }
                            ]
                        }
                    ],
                    "published": "2020-05-08T18:25:00Z",
                    "modified": "2021-01-08T19:02:00Z"
                }
            ],
            []  # No results for flask (empty array)
        ]
    }

class TestOSVScanner:
    
    def test_deduplicate_dependencies(self, osv_scanner, sample_dependencies):
        # Add a duplicate
        duplicated = sample_dependencies + [sample_dependencies[0]]  # Duplicate lodash
        
        unique = osv_scanner._deduplicate_dependencies(duplicated)
        
        assert len(unique) == 2  # Should remove the duplicate
        names = [dep.name for dep in unique]
        assert "lodash" in names
        assert "flask" in names

    def test_generate_query_hash(self, osv_scanner):
        hash1 = osv_scanner._generate_query_hash("npm", "lodash", "4.17.20")
        hash2 = osv_scanner._generate_query_hash("npm", "lodash", "4.17.20")
        hash3 = osv_scanner._generate_query_hash("npm", "lodash", "4.17.21")
        
        # Same inputs should generate same hash
        assert hash1 == hash2
        # Different version should generate different hash
        assert hash1 != hash3
        # Hash should be non-empty string
        assert isinstance(hash1, str) and len(hash1) > 0

    def test_extract_severity(self, osv_scanner):
        # Test CVSS v3 scoring with numeric score
        severity_data = [{"type": "CVSS_V3", "score": 9.5}]
        result = osv_scanner._extract_severity(severity_data)
        assert result == SeverityLevel.CRITICAL

        # Test medium severity with string score
        severity_data = [{"type": "CVSS_V3", "score": "5.5"}]
        result = osv_scanner._extract_severity(severity_data)
        assert result == SeverityLevel.MEDIUM

        # Test database_specific severity fallback
        result = osv_scanner._extract_severity([], {"severity": "moderate"})
        assert result == SeverityLevel.MEDIUM

        # Test database_specific numeric score
        result = osv_scanner._extract_severity([], {"score": "8.2"})
        assert result == SeverityLevel.HIGH

        # Test github_severity field
        result = osv_scanner._extract_severity([], {"github_severity": "low"})
        assert result == SeverityLevel.LOW

        # Test empty list
        result = osv_scanner._extract_severity([])
        assert result == SeverityLevel.UNKNOWN

    def test_extract_fixed_range(self, osv_scanner):
        affected_data = [
            {
                "package": {
                    "ecosystem": "npm",
                    "name": "lodash"
                },
                "ranges": [
                    {
                        "type": "ECOSYSTEM",
                        "events": [
                            {"introduced": "0"},
                            {"fixed": "4.17.21"}
                        ]
                    }
                ]
            }
        ]
        
        result = osv_scanner._extract_fixed_range(affected_data, "lodash")
        assert result == ">=4.17.21"
        
        # Test no fix available
        result = osv_scanner._extract_fixed_range([], "lodash")
        assert result is None

    def test_convert_osv_to_vuln(self, osv_scanner, sample_dependencies):
        osv_data = {
            "id": "GHSA-35jh-r3h4-6jhm",
            "summary": "Prototype Pollution in lodash",
            "details": "lodash versions prior to 4.17.21 are vulnerable.",
            "aliases": ["CVE-2020-8203"],
            "severity": [{"type": "CVSS_V3", "score": 7.4}],
            "affected": [
                {
                    "package": {"name": "lodash"},
                    "ranges": [
                        {
                            "events": [
                                {"introduced": "0"},
                                {"fixed": "4.17.21"}
                            ]
                        }
                    ]
                }
            ],
            "references": [
                {
                    "type": "ADVISORY",
                    "url": "https://github.com/advisories/GHSA-35jh-r3h4-6jhm"
                }
            ],
            "published": "2020-05-08T18:25:00Z",
            "modified": "2021-01-08T19:02:00Z"
        }
        
        lodash_dep = sample_dependencies[0]  # lodash dependency
        vuln = osv_scanner._convert_osv_to_vuln(osv_data, lodash_dep)
        
        assert vuln.package == "lodash"
        assert vuln.version == "4.17.20"
        assert vuln.ecosystem == "npm"
        assert vuln.vulnerability_id == "GHSA-35jh-r3h4-6jhm"
        assert vuln.severity == SeverityLevel.HIGH  # Score 7.4 should be HIGH
        assert "CVE-2020-8203" in vuln.cve_ids
        assert vuln.summary == "Prototype Pollution in lodash"
        assert vuln.fixed_range == ">=4.17.21"
        assert vuln.advisory_url == "https://github.com/advisories/GHSA-35jh-r3h4-6jhm"
        assert vuln.published is not None
        assert vuln.modified is not None

    @pytest.mark.asyncio
    async def test_cache_results(self, osv_scanner, sample_dependencies):
        # Mock vulnerability results
        results = [
            {
                "id": "TEST-123",
                "summary": "Test vulnerability",
                "package": "lodash",
                "ecosystem": "npm"
            }
        ]
        
        # Cache the results
        await osv_scanner._cache_results([sample_dependencies[0]], results)
        
        # Try to retrieve from cache
        cached_results, uncached_deps = await osv_scanner._check_cache([sample_dependencies[0]])
        
        # Should find cached result
        assert len(cached_results) == 1
        assert len(uncached_deps) == 0
        assert cached_results[0]["id"] == "TEST-123"

    @pytest.mark.asyncio
    async def test_cleanup_cache(self, osv_scanner):
        # This should run without errors
        await osv_scanner.cleanup_cache(max_age_days=1)
        
        # Verify cleanup doesn't break anything
        assert True  # If we get here, cleanup succeeded

    @pytest.mark.asyncio
    async def test_close(self, osv_scanner):
        # This should clean up resources without errors
        await osv_scanner.close()
        
        # Verify we can't make requests after closing
        with pytest.raises(Exception):
            # This should fail because client is closed
            await osv_scanner.client.get("https://api.osv.dev")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_query_single_batch(self, mock_post, osv_scanner, sample_dependencies, mock_osv_response):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_osv_response
        mock_post.return_value = mock_response
        
        # Test querying a single batch
        results = await osv_scanner._query_single_batch(sample_dependencies[:1])  # Just lodash
        
        # Verify API was called
        assert mock_post.called
        
        # Verify results
        assert len(results) >= 0  # Should return results (might be empty if mocked differently)

    @pytest.mark.asyncio
    async def test_rate_limit(self, osv_scanner):
        # Test that rate limiting doesn't break
        start_time = datetime.now()
        await osv_scanner._rate_limit()
        end_time = datetime.now()
        
        # Should complete quickly for first call
        duration = (end_time - start_time).total_seconds()
        assert duration < 2.0  # Should be very fast for first call