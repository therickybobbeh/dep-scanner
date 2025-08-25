"""Parser for package-lock.json version 2+ format"""
import json
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import DependencyTreeBuilder
from ....models import Dep


class PackageLockV2Parser(BaseDependencyParser):
    """
    Parser for package-lock.json version 2 and 3 format
    
    Version 2+ uses flat packages structure:
    {
        "packages": {
            "": { "name": "root", "dependencies": {...} },
            "node_modules/package": { "version": "1.0.0" },
            "node_modules/@scope/package": { "version": "2.0.0" }
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
        Parse package-lock.json v2+ content
        
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
            
            # Validate it's actually v2+ format
            lockfile_version = lock_data.get("lockfileVersion", 1)
            if lockfile_version < 2:
                raise ValueError(f"Expected v2+ format, got v{lockfile_version}")
            
            # Extract packages
            packages = lock_data.get("packages", {})
            if not packages:
                return []
            
            # Get root dependencies to identify direct vs transitive
            root_package = packages.get("", {})
            root_dependencies = {
                **root_package.get("dependencies", {}),
                **root_package.get("devDependencies", {})
            }
            
            # Build dependency tree from flat structure
            deps = self.tree_builder.build_tree_flat(
                packages_dict=packages,
                root_dependencies=root_dependencies
            )
            
            # Enhance with better path tracking if needed
            deps = self._enhance_dependency_paths(deps, packages, root_dependencies)
            
            return deps
            
        except json.JSONDecodeError as e:
            raise ParseError("package-lock.json", e)
        except Exception as e:
            raise ParseError("package-lock.json v2+", e)
    
    def _enhance_dependency_paths(
        self, 
        deps: list[Dep], 
        packages: dict[str, Any], 
        root_deps: dict[str, str]
    ) -> list[Dep]:
        """
        Enhance dependency paths with actual dependency relationships
        
        This is more complex for v2+ format since dependencies are flattened
        """
        # For now, keep simple paths but mark direct dependencies correctly
        enhanced_deps = []
        
        for dep in deps:
            # Update direct dependency status based on root dependencies
            dep.is_direct = dep.name in root_deps
            
            # For transitive dependencies, try to build better paths
            if not dep.is_direct:
                # This could be enhanced to build actual dependency chains
                # by analyzing the dependency relationships in packages
                pass
            
            enhanced_deps.append(dep)
        
        return enhanced_deps
    
    def _find_dependency_chain(
        self, 
        target_package: str, 
        packages: dict[str, Any],
        visited: set[str] | None = None
    ) -> list[str]:
        """
        Find dependency chain to a target package (for future enhancement)
        
        This could be used to build accurate dependency paths showing
        how a transitive dependency is reached.
        """
        if visited is None:
            visited = set()
        
        # This is a placeholder for more sophisticated path tracking
        # that could analyze the dependency graph to show actual chains
        return [target_package]