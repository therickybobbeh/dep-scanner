"""Parser for Pipfile.lock files"""
import json
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import DependencyTreeBuilder
from ....models import Dep


class PipfileLockParser(BaseDependencyParser):
    """Parser for Pipfile.lock files (pipenv lockfile format)"""
    
    def __init__(self):
        super().__init__(ecosystem="PyPI")
        self.tree_builder = DependencyTreeBuilder(self.ecosystem)
    
    @property
    def supported_formats(self) -> list[str]:
        return ["Pipfile.lock"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """Parse Pipfile.lock content"""
        try:
            lock_data = json.loads(content)
            deps = []
            
            # Parse default (production) dependencies
            default_deps = lock_data.get("default", {})
            for name, info in default_deps.items():
                version = info.get("version", "").lstrip("=")
                # Check if this is a direct dependency (explicitly added to Pipfile)
                # Direct dependencies typically have "index": "pypi" or are explicitly listed
                is_direct = "index" in info and info["index"] == "pypi"
                
                # Create appropriate path for transitive dependencies
                if is_direct:
                    path = [name]  # Direct dependency: single-element path
                else:
                    path = ["unknown-parent", name]  # Transitive: multi-element path
                
                dep = self._create_dependency(
                    name=name, 
                    version=version, 
                    path=path,
                    is_direct=is_direct,
                    is_dev=False
                )
                deps.append(dep)
            
            # Parse develop (development) dependencies  
            develop_deps = lock_data.get("develop", {})
            for name, info in develop_deps.items():
                version = info.get("version", "").lstrip("=")
                # Development dependencies with "index": "pypi" are direct dev dependencies
                is_direct = "index" in info and info["index"] == "pypi"
                
                # Create appropriate path for transitive dev dependencies
                if is_direct:
                    path = [name]  # Direct dev dependency: single-element path  
                else:
                    path = ["unknown-parent", name]  # Transitive dev: multi-element path
                
                dep = self._create_dependency(
                    name=name,
                    version=version,
                    path=path, 
                    is_direct=is_direct,
                    is_dev=True
                )
                deps.append(dep)
            
            return deps
            
        except json.JSONDecodeError as e:
            raise ParseError("Pipfile.lock", e)
        except Exception as e:
            raise ParseError("Pipfile.lock", e)