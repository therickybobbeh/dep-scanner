"""Parser for poetry.lock files"""
import tomli
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import DependencyTreeBuilder, PathTracker
from ....models import Dep


class PoetryLockParser(BaseDependencyParser):
    """
    Parser for poetry.lock files
    
    Poetry lock format is TOML with package information:
    
    [[package]]
    name = "package-name"
    version = "1.0.0"
    category = "main"  # or "dev"
    optional = false
    python-versions = ">=3.8"
    
    [package.dependencies]
    dependency-name = "^2.0.0"
    """
    
    def __init__(self):
        super().__init__(ecosystem="PyPI")
        self.tree_builder = DependencyTreeBuilder(self.ecosystem)
        self.path_tracker = PathTracker()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["poetry.lock"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse poetry.lock content
        
        Args:
            content: Raw poetry.lock content
            **kwargs: Additional parsing options
            
        Returns:
            List of dependency objects
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            lock_data = tomli.loads(content)
            packages = lock_data.get("package", [])
            
            if not packages:
                return []
            
            # Build package map for dependency resolution
            package_map = {pkg["name"]: pkg for pkg in packages}
            
            # Process packages and build dependency tree
            deps = []
            for package in packages:
                name = package["name"]
                version = package["version"]
                is_dev = package.get("category") == "dev"
                
                # Build dependency relationships
                pkg_deps = package.get("dependencies", {})
                dep_paths = self._build_dependency_paths(name, pkg_deps, package_map)
                
                # Create main dependency
                main_dep = self._create_dependency(
                    name=name,
                    version=version,
                    path=[name],
                    is_direct=True,  # We'll refine this based on actual usage
                    is_dev=is_dev
                )
                deps.append(main_dep)
                
                # Add dependency relationships if needed
                # (This could be enhanced to show actual dependency chains)
            
            return self._enhance_direct_dependency_detection(deps, packages)
            
        except Exception as e:
            raise ParseError("poetry.lock", e)
    
    def _build_dependency_paths(
        self, 
        package_name: str, 
        dependencies: dict[str, Any], 
        package_map: dict[str, Any]
    ) -> list[list[str]]:
        """
        Build dependency paths for a package
        
        This shows which packages depend on the given package
        """
        paths = []
        
        for dep_name, dep_spec in dependencies.items():
            if dep_name in package_map:
                # Create path showing this dependency relationship
                path = [package_name, dep_name]
                paths.append(path)
        
        return paths
    
    def _enhance_direct_dependency_detection(
        self, 
        deps: list[Dep], 
        packages: list[dict[str, Any]]
    ) -> list[Dep]:
        """
        Enhance direct dependency detection by analyzing the dependency graph
        
        In poetry.lock, we need to infer which dependencies are direct vs transitive
        by looking at the dependency relationships.
        """
        # Build reverse dependency map (who depends on whom)
        dependents_map = {}
        
        for package in packages:
            name = package["name"]
            dependencies = package.get("dependencies", {})
            
            for dep_name in dependencies.keys():
                if dep_name not in dependents_map:
                    dependents_map[dep_name] = []
                dependents_map[dep_name].append(name)
        
        # Update direct/transitive status
        enhanced_deps = []
        for dep in deps:
            # If a package has no dependents in the lock file,
            # it's likely a direct dependency
            has_dependents = dep.name in dependents_map
            
            # Update dependency status
            # This is a heuristic - in practice, you'd want to cross-reference
            # with pyproject.toml to get accurate direct dependency info
            if not has_dependents:
                dep.is_direct = True
            else:
                # Check if it appears in any package's dependencies
                # If it does, it might be transitive
                dep.is_direct = not has_dependents
            
            enhanced_deps.append(dep)
        
        return enhanced_deps
    
    def get_lock_metadata(self, content: str) -> dict[str, Any]:
        """
        Extract metadata from poetry.lock file
        
        Returns:
            Dict with lock file metadata
        """
        try:
            lock_data = tomli.loads(content)
            metadata = lock_data.get("metadata", {})
            
            return {
                "lock_version": metadata.get("lock-version", ""),
                "python_versions": metadata.get("python-versions", ""),
                "content_hash": metadata.get("content-hash", ""),
                "files": metadata.get("files", {}),
            }
        except Exception:
            return {}