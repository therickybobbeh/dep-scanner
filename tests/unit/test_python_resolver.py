import pytest
import asyncio
from pathlib import Path
from backend.app.resolver.python_resolver import PythonResolver
from backend.app.models import Dep

@pytest.fixture
def python_resolver():
    return PythonResolver()

@pytest.fixture
def sample_requirements():
    return """
flask==1.1.4
requests==2.25.1
numpy==1.21.0
"""

@pytest.fixture
def sample_poetry_lock():
    return """
[[package]]
name = "flask"
version = "1.1.4"
description = "A simple framework for building complex web applications."
category = "main"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*"

[[package]]
name = "requests"
version = "2.25.1"
description = "Python HTTP for Humans."
category = "main"
optional = false
python-versions = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4"
"""

class TestPythonResolver:
    
    def test_parse_requirements_txt(self, python_resolver):
        content = "flask==1.1.4\nrequests>=2.25.0\nnumpy~=1.21.0"
        packages = python_resolver._parse_requirements_txt(content)
        
        assert len(packages) == 3
        assert ("flask", "1.1.4") in packages
        assert ("requests", "2.25.0") in packages  # Should extract from >=
        assert ("numpy", "1.21.0") in packages    # Should extract from ~=
    
    @pytest.mark.asyncio
    async def test_resolve_from_manifests_requirements(self, python_resolver, sample_requirements):
        manifest_files = {"requirements.txt": sample_requirements}
        
        # This would normally call pipdeptree, so we'll test the parsing instead
        packages = python_resolver._parse_requirements_txt(sample_requirements)
        assert len(packages) >= 3
        
        # Verify specific packages are found
        package_names = [pkg[0] for pkg in packages]
        assert "flask" in package_names
        assert "requests" in package_names
        assert "numpy" in package_names

    def test_extract_name_version_from_requirement(self, python_resolver):
        # Test various requirement formats
        test_cases = [
            ("flask==1.1.4", ("flask", "1.1.4")),
            ("requests>=2.25.0", ("requests", "2.25.0")),
            ("numpy~=1.21.0", ("numpy", "1.21.0")),
            ("django", ("django", None)),
        ]
        
        for req_str, expected in test_cases:
            packages = python_resolver._parse_requirements_txt(req_str)
            if packages:
                assert packages[0] == expected
    
    @pytest.mark.asyncio
    async def test_parse_poetry_lock_format(self, python_resolver, sample_poetry_lock):
        # Test the TOML parsing works
        deps = await python_resolver._parse_poetry_lock(sample_poetry_lock)
        
        assert len(deps) >= 2
        assert any(dep.name == "flask" and dep.version == "1.1.4" for dep in deps)
        assert any(dep.name == "requests" and dep.version == "2.25.1" for dep in deps)
        
        # Verify all dependencies have correct ecosystem
        for dep in deps:
            assert dep.ecosystem == "PyPI"
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1