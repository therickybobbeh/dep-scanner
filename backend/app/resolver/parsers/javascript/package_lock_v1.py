"""Parser for package-lock.json version 1 format"""
import json
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import DependencyTreeBuilder
from ....models import Dep


class PackageLockV1Parser(BaseDependencyParser):
    """
    Parser for package-lock.json version 1 format
    
    Version 1 uses nested dependencies structure:
    {
        "dependencies": {
            "package-name": {
                "version": "1.0.0",
                "dependencies": {
                    "nested-package": { ... }
                }
            }
        }
    }
    """
    
    def __init__(self):
        super().__init__(ecosystem="npm")
        self.tree_builder = DependencyTreeBuilder(self.ecosystem)
    
    @property
    def supported_formats(self) -> list[str]:
        return ["package-lock.json"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse package-lock.json v1 content
        
        Args:
            content: Raw package-lock.json content
            **kwargs: Additional parsing options
            
        Returns:
            List of dependency objects
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            lock_data = json.loads(content)
            
            # Validate it's actually v1 format
            lockfile_version = lock_data.get("lockfileVersion", 1)
            if lockfile_version >= 2:
                raise ValueError(f"Expected v1 format, got v{lockfile_version}")
            
            # Extract dependencies
            dependencies = lock_data.get("dependencies", {})
            if not dependencies:
                return []
            
            # Build dependency tree recursively
            deps = self.tree_builder.build_tree_recursive(
                dependencies_dict=dependencies,
                parent_path=None,
                is_dev=False
            )
            
            # Deduplicate dependencies (same package might appear in multiple places)
            return self.tree_builder.deduplicate_dependencies(deps)
            
        except json.JSONDecodeError as e:
            raise ParseError("package-lock.json", e)
        except Exception as e:
            raise ParseError("package-lock.json v1", e)
    
    def _extract_dev_dependencies(self, dependencies: dict[str, Any]) -> list[Dep]:
        """Extract development dependencies if needed"""
        # In v1 format, dev dependencies are mixed in with regular dependencies
        # and marked with "dev": true
        dev_deps = []
        
        for name, info in dependencies.items():
            if info.get("dev", False):
                dep = self._create_dependency(
                    name=name,
                    version=info.get("version", ""),
                    is_dev=True
                )
                dev_deps.append(dep)
        
        return dev_deps