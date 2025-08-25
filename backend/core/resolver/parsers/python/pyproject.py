"""Parser for pyproject.toml files"""
import tomli
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ....models import Dep


class PyprojectParser(BaseDependencyParser):
    """Parser for pyproject.toml files (PEP 621 and Poetry format)"""
    
    def __init__(self):
        super().__init__(ecosystem="PyPI")
        self.version_cleaner = VersionCleaner()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["pyproject.toml"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """Parse pyproject.toml content"""
        try:
            data = tomli.loads(content)
            deps = []
            
            # Try PEP 621 format first
            if "project" in data:
                deps.extend(self._parse_pep621_format(data["project"]))
            
            # Try Poetry format
            elif "tool" in data and "poetry" in data["tool"]:
                deps.extend(self._parse_poetry_format(data["tool"]["poetry"]))
            
            return deps
            
        except Exception as e:
            raise ParseError("pyproject.toml", e)
    
    def _parse_pep621_format(self, project_data: dict[str, Any]) -> list[Dep]:
        """Parse PEP 621 format dependencies"""
        deps = []
        
        # Main dependencies
        dependencies = project_data.get("dependencies", [])
        for dep_spec in dependencies:
            name, version = self._parse_dependency_spec(dep_spec)
            if name:
                dep = self._create_dependency(name, version, is_dev=False)
                deps.append(dep)
        
        # Optional dependencies (dev, test, etc.)
        optional_deps = project_data.get("optional-dependencies", {})
        for group_name, group_deps in optional_deps.items():
            is_dev = group_name.lower() in ["dev", "development", "test", "testing"]
            for dep_spec in group_deps:
                name, version = self._parse_dependency_spec(dep_spec)
                if name:
                    dep = self._create_dependency(name, version, is_dev=is_dev)
                    deps.append(dep)
        
        return deps
    
    def _parse_poetry_format(self, poetry_data: dict[str, Any]) -> list[Dep]:
        """Parse Poetry format dependencies"""
        deps = []
        
        # Main dependencies
        dependencies = poetry_data.get("dependencies", {})
        for name, spec in dependencies.items():
            if name == "python":  # Skip Python version constraint
                continue
            version = self._extract_version_from_poetry_spec(spec)
            dep = self._create_dependency(name, version, is_dev=False)
            deps.append(dep)
        
        # Dev dependencies
        dev_dependencies = poetry_data.get("group", {}).get("dev", {}).get("dependencies", {})
        for name, spec in dev_dependencies.items():
            version = self._extract_version_from_poetry_spec(spec)
            dep = self._create_dependency(name, version, is_dev=True)
            deps.append(dep)
        
        return deps
    
    def _parse_dependency_spec(self, spec: str) -> tuple[str, str]:
        """Parse PEP 621 dependency specification"""
        try:
            from packaging.requirements import Requirement
            req = Requirement(spec)
            name = req.name
            version = str(req.specifier) if req.specifier else ""
            return name, self.version_cleaner.clean_python_version(version)
        except:
            return "", ""
    
    def _extract_version_from_poetry_spec(self, spec: Any) -> str:
        """Extract version from Poetry dependency specification"""
        if isinstance(spec, str):
            return self.version_cleaner.clean_python_version(spec)
        elif isinstance(spec, dict):
            return self.version_cleaner.clean_python_version(spec.get("version", ""))
        return ""