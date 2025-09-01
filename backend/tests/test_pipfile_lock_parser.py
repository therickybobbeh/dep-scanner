"""Tests for PipfileLockParser functionality"""
import pytest
import json
from unittest.mock import AsyncMock, patch

from backend.core.resolver.parsers.python.pipfile_lock import PipfileLockParser
from backend.core.resolver.base import ParseError
from backend.core.models import Dep


class TestPipfileLockParser:
    """Test cases for PipfileLockParser"""
    
    @pytest.fixture
    def parser(self):
        """Create PipfileLockParser instance for testing"""
        return PipfileLockParser()
    
    @pytest.fixture
    def sample_pipfile_lock_content(self):
        """Sample Pipfile.lock content for testing transitive dependencies"""
        return {
            "_meta": {
                "hash": {"sha256": "test123"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            },
            "default": {
                # Direct dependencies (have "index": "pypi")
                "django": {
                    "hashes": ["sha256:abc123"],
                    "index": "pypi",
                    "version": "==3.2.13"
                },
                "requests": {
                    "hashes": ["sha256:def456"],
                    "index": "pypi", 
                    "version": "==2.25.1"
                },
                # Transitive dependencies (no "index": "pypi")
                "certifi": {
                    "hashes": ["sha256:ghi789"],
                    "version": "==2021.5.30"
                },
                "urllib3": {
                    "hashes": ["sha256:jkl012"],
                    "markers": "python_version >= '2.7'",
                    "version": "==1.25.8"
                }
            },
            "develop": {
                # Direct dev dependency
                "pytest": {
                    "hashes": ["sha256:mno345"],
                    "index": "pypi",
                    "version": "==6.2.4"
                },
                # Transitive dev dependency
                "pluggy": {
                    "hashes": ["sha256:pqr678"],
                    "version": "==0.13.1"
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_parse_pipfile_lock_transitive_classification(self, parser, sample_pipfile_lock_content):
        """Test that Pipfile.lock correctly classifies direct vs transitive dependencies"""
        content = json.dumps(sample_pipfile_lock_content)
        dependencies = await parser.parse(content)
        
        # Should parse exactly 6 dependencies
        assert len(dependencies) == 6
        
        # Check direct dependencies (production)
        direct_prod_deps = [dep for dep in dependencies if dep.is_direct and not dep.is_dev]
        assert len(direct_prod_deps) == 2
        direct_prod_names = [dep.name for dep in direct_prod_deps]
        assert "django" in direct_prod_names
        assert "requests" in direct_prod_names
        
        # Check transitive dependencies (production) 
        transitive_prod_deps = [dep for dep in dependencies if not dep.is_direct and not dep.is_dev]
        assert len(transitive_prod_deps) == 2
        transitive_prod_names = [dep.name for dep in transitive_prod_deps]
        assert "certifi" in transitive_prod_names
        assert "urllib3" in transitive_prod_names
        
        # Check direct dev dependencies
        direct_dev_deps = [dep for dep in dependencies if dep.is_direct and dep.is_dev]
        assert len(direct_dev_deps) == 1
        assert direct_dev_deps[0].name == "pytest"
        
        # Check transitive dev dependencies
        transitive_dev_deps = [dep for dep in dependencies if not dep.is_direct and dep.is_dev]
        assert len(transitive_dev_deps) == 1
        assert transitive_dev_deps[0].name == "pluggy"

    @pytest.mark.asyncio
    async def test_parse_pipfile_lock_dependency_paths(self, parser, sample_pipfile_lock_content):
        """Test that dependency paths are correctly set for direct vs transitive"""
        content = json.dumps(sample_pipfile_lock_content)
        dependencies = await parser.parse(content)
        
        # Direct dependencies should have single-element paths
        direct_deps = [dep for dep in dependencies if dep.is_direct]
        for dep in direct_deps:
            assert len(dep.path) == 1
            assert dep.path[0] == dep.name
            
        # Transitive dependencies should have multi-element paths
        transitive_deps = [dep for dep in dependencies if not dep.is_direct]
        for dep in transitive_deps:
            assert len(dep.path) == 2
            assert dep.path[0] == "unknown-parent"
            assert dep.path[1] == dep.name

    @pytest.mark.asyncio
    async def test_parse_pipfile_lock_versions(self, parser, sample_pipfile_lock_content):
        """Test that versions are parsed correctly with version prefix stripped"""
        content = json.dumps(sample_pipfile_lock_content)
        dependencies = await parser.parse(content)
        
        # Create a map for easier testing
        dep_versions = {dep.name: dep.version for dep in dependencies}
        
        expected_versions = {
            "django": "3.2.13",
            "requests": "2.25.1", 
            "certifi": "2021.5.30",
            "urllib3": "1.25.8",
            "pytest": "6.2.4",
            "pluggy": "0.13.1"
        }
        
        for name, expected_version in expected_versions.items():
            assert dep_versions[name] == expected_version, f"Wrong version for {name}: got {dep_versions[name]}, expected {expected_version}"

    @pytest.mark.asyncio
    async def test_parse_pipfile_lock_ecosystem(self, parser, sample_pipfile_lock_content):
        """Test that all dependencies have correct ecosystem"""
        content = json.dumps(sample_pipfile_lock_content)
        dependencies = await parser.parse(content)
        
        for dep in dependencies:
            assert dep.ecosystem == "PyPI"

    @pytest.mark.asyncio
    async def test_parse_empty_sections(self, parser):
        """Test parsing Pipfile.lock with empty default and develop sections"""
        empty_content = {
            "_meta": {
                "hash": {"sha256": "test123"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            },
            "default": {},
            "develop": {}
        }
        
        content = json.dumps(empty_content)
        dependencies = await parser.parse(content)
        assert len(dependencies) == 0

    @pytest.mark.asyncio
    async def test_parse_only_transitive_dependencies(self, parser):
        """Test parsing when all dependencies are transitive (no index markers)"""
        transitive_only_content = {
            "_meta": {
                "hash": {"sha256": "test123"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            },
            "default": {
                "certifi": {
                    "hashes": ["sha256:ghi789"],
                    "version": "==2021.5.30"
                },
                "urllib3": {
                    "hashes": ["sha256:jkl012"],
                    "version": "==1.25.8"
                }
            },
            "develop": {}
        }
        
        content = json.dumps(transitive_only_content)
        dependencies = await parser.parse(content)
        
        assert len(dependencies) == 2
        # All should be marked as transitive
        for dep in dependencies:
            assert dep.is_direct is False
            assert len(dep.path) == 2
            assert dep.path[0] == "unknown-parent"

    @pytest.mark.asyncio
    async def test_parse_only_direct_dependencies(self, parser):
        """Test parsing when all dependencies are direct (have index markers)"""
        direct_only_content = {
            "_meta": {
                "hash": {"sha256": "test123"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            },
            "default": {
                "django": {
                    "hashes": ["sha256:abc123"],
                    "index": "pypi",
                    "version": "==3.2.13"
                },
                "requests": {
                    "hashes": ["sha256:def456"],
                    "index": "pypi",
                    "version": "==2.25.1"
                }
            },
            "develop": {}
        }
        
        content = json.dumps(direct_only_content)
        dependencies = await parser.parse(content)
        
        assert len(dependencies) == 2
        # All should be marked as direct
        for dep in dependencies:
            assert dep.is_direct is True
            assert len(dep.path) == 1
            assert dep.path[0] == dep.name

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self, parser):
        """Test that invalid JSON raises ParseError"""
        invalid_json = "{ invalid json content"
        
        with pytest.raises(ParseError) as exc_info:
            await parser.parse(invalid_json)
        
        assert exc_info.value.format_name == "Pipfile.lock"
        assert isinstance(exc_info.value.original_error, json.JSONDecodeError)

    @pytest.mark.asyncio
    async def test_parse_missing_sections(self, parser):
        """Test parsing Pipfile.lock with missing default/develop sections"""
        minimal_content = {
            "_meta": {
                "hash": {"sha256": "test123"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            }
            # No default or develop sections
        }
        
        content = json.dumps(minimal_content)
        dependencies = await parser.parse(content)
        assert len(dependencies) == 0

    def test_supported_formats(self, parser):
        """Test that parser reports correct supported formats"""
        formats = parser.supported_formats
        assert "Pipfile.lock" in formats
        assert len(formats) == 1

    def test_parser_ecosystem(self, parser):
        """Test that parser has correct ecosystem"""
        assert parser.ecosystem == "PyPI"

    @pytest.mark.asyncio
    async def test_integration_with_real_pipfile_lock(self, parser):
        """Integration test using the actual test Pipfile.lock from the repo"""
        # This uses the actual test file to ensure real-world compatibility
        real_pipfile_content = {
            "_meta": {
                "hash": {"sha256": "4d3df10c7e9b8be45d6ee2dcf6a1c5b7d6ad3fd85f61b7a3c0f1a4d7b3b8c9e2"},
                "pipfile-spec": 6,
                "requires": {"python_version": "3.9"},
                "sources": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}]
            },
            "default": {
                "certifi": {
                    "hashes": ["sha256:78884e7c1d4b00ce3cea67b44566851c4343c120abd683433ce934a68ea58872"],
                    "version": "==2021.5.30"
                },
                "charset-normalizer": {
                    "hashes": ["sha256:2dee8e57f052ef5353cf608e0b4c871aee320dd637f0d7533d62336b0debb5c2"],
                    "markers": "python_version >= '3.5'",
                    "version": "==2.0.12"
                },
                "django": {
                    "hashes": ["sha256:502ae42b6ab1b612c933fb50d5ff850facf858a4c212f76946ecd8ea5b3bf2d9"],
                    "index": "pypi",
                    "version": "==3.2.13"
                },
                "idna": {
                    "hashes": ["sha256:84d9dd047ffa80596e0f246e2eab0b391788b0503584e8945f2368256d2735ff"],
                    "markers": "python_version >= '3.5'",
                    "version": "==3.3"
                },
                "requests": {
                    "hashes": ["sha256:27973dd4a904a4f13b263a19c866c13b92a39ed1c964655f025f3f8d3d75b804"],
                    "index": "pypi",
                    "version": "==2.25.1"
                },
                "urllib3": {
                    "hashes": ["sha256:2f3db8b19923a873b3e5256dc9c2dedfa883e33d87c690d9c7913e1f40673cdc"],
                    "markers": "python_version >= '2.7'",
                    "version": "==1.25.8"
                }
            },
            "develop": {}
        }
        
        content = json.dumps(real_pipfile_content)
        dependencies = await parser.parse(content)
        
        # Should parse exactly 6 dependencies
        assert len(dependencies) == 6
        
        # Check direct vs transitive classification
        direct_deps = [dep for dep in dependencies if dep.is_direct]
        transitive_deps = [dep for dep in dependencies if not dep.is_direct]
        
        # django and requests should be direct (have "index": "pypi")
        assert len(direct_deps) == 2
        direct_names = [dep.name for dep in direct_deps]
        assert "django" in direct_names
        assert "requests" in direct_names
        
        # certifi, charset-normalizer, idna, urllib3 should be transitive
        assert len(transitive_deps) == 4
        transitive_names = [dep.name for dep in transitive_deps]
        expected_transitive = ["certifi", "charset-normalizer", "idna", "urllib3"]
        for name in expected_transitive:
            assert name in transitive_names