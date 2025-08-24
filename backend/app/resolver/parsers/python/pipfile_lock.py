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
                dep = self._create_dependency(name, version, is_dev=False)
                deps.append(dep)
            
            # Parse develop (development) dependencies
            develop_deps = lock_data.get("develop", {})
            for name, info in develop_deps.items():
                version = info.get("version", "").lstrip("=")
                dep = self._create_dependency(name, version, is_dev=True)
                deps.append(dep)
            
            return deps
            
        except json.JSONDecodeError as e:
            raise ParseError("Pipfile.lock", e)
        except Exception as e:
            raise ParseError("Pipfile.lock", e)