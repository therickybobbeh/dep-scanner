"""Parser for Pipfile files"""
import tomli
from typing import Any

from ...base import BaseDependencyParser, ParseError  
from ...utils import VersionCleaner
from ....models import Dep


class PipfileParser(BaseDependencyParser):
    """Parser for Pipfile files (pipenv manifest format)"""
    
    def __init__(self):
        super().__init__(ecosystem="PyPI")
        self.version_cleaner = VersionCleaner()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["Pipfile"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """Parse Pipfile content"""
        try:
            data = tomli.loads(content)
            deps = []
            
            # Parse packages (production dependencies)
            packages = data.get("packages", {})
            for name, spec in packages.items():
                version = self._extract_version_from_spec(spec)
                dep = self._create_dependency(name, version, is_dev=False)
                deps.append(dep)
            
            # Parse dev-packages (development dependencies)
            dev_packages = data.get("dev-packages", {})
            for name, spec in dev_packages.items():
                version = self._extract_version_from_spec(spec)
                dep = self._create_dependency(name, version, is_dev=True)
                deps.append(dep)
            
            return deps
            
        except Exception as e:
            raise ParseError("Pipfile", e)
    
    def _extract_version_from_spec(self, spec: Any) -> str:
        """Extract version from Pipfile dependency specification"""
        if isinstance(spec, str):
            return self.version_cleaner.clean_python_version(spec)
        elif isinstance(spec, dict):
            version = spec.get("version", "")
            return self.version_cleaner.clean_python_version(version)
        return ""