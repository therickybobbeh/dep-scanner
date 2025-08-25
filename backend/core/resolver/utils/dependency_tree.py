"""Dependency tree building utilities"""
from ...models import Dep
from .path_utils import PathTracker


class DependencyTreeBuilder:
    """Utility for building and manipulating dependency trees"""
    
    def __init__(self, ecosystem: str):
        self.ecosystem = ecosystem
        self.path_tracker = PathTracker()
    
    def build_tree_recursive(
        self, 
        dependencies_dict: dict, 
        parent_path: list[str] | None = None,
        is_dev: bool = False
    ) -> list[Dep]:
        """
        Recursively build dependency tree from nested dictionary structure
        
        Used for package-lock.json v1 format and similar nested structures
        
        Args:
            dependencies_dict: Dict of {package_name: package_info}
            parent_path: Path to parent dependency
            is_dev: Whether these are dev dependencies
            
        Returns:
            List of Dep objects representing the tree
        """
        deps = []
        
        for name, info in dependencies_dict.items():
            version = info.get("version", "")
            current_path = self.path_tracker.create_path(parent_path, name)
            
            # Create dependency object
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=current_path,
                is_direct=self.path_tracker.is_direct_dependency(current_path),
                is_dev=is_dev or info.get("dev", False)
            )
            deps.append(dep)
            
            # Recursively process nested dependencies
            nested_deps = info.get("dependencies", {})
            if nested_deps:
                # Check for circular dependencies
                if not self.path_tracker.detect_circular_dependency(current_path, name):
                    child_deps = self.build_tree_recursive(
                        nested_deps, 
                        current_path, 
                        is_dev
                    )
                    deps.extend(child_deps)
        
        return deps
    
    def build_tree_flat(
        self, 
        packages_dict: dict, 
        root_dependencies: dict | None = None
    ) -> list[Dep]:
        """
        Build dependency tree from flat package structure
        
        Used for package-lock.json v2/v3 format and similar flat structures
        
        Args:
            packages_dict: Dict of {"node_modules/package": package_info}
            root_dependencies: Root package dependencies for detecting direct deps
            
        Returns:
            List of Dep objects representing the tree
        """
        deps = []
        
        # Build dependency relationships map
        dependency_map = self._build_dependency_map(packages_dict, root_dependencies or {})
        
        for package_path, info in packages_dict.items():
            if package_path == "":  # Skip root package
                continue
            
            # Extract package name from path
            name = self._extract_package_name(package_path)
            if not name:
                continue
            
            version = info.get("version", "")
            is_dev = info.get("dev", False)
            
            # Determine if direct dependency
            is_direct = name in root_dependencies if root_dependencies else True
            
            # Create basic path (could be enhanced with actual dependency relationships)
            path = [name]
            
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=path,
                is_direct=is_direct,
                is_dev=is_dev
            )
            deps.append(dep)
        
        return deps
    
    def build_tree_from_list(
        self, 
        packages_list: list[dict], 
        parent_name: str | None = None
    ) -> list[Dep]:
        """
        Build dependency tree from list structure
        
        Used for poetry.lock and Pipfile.lock formats
        
        Args:
            packages_list: List of package dictionaries
            parent_name: Name of parent package (for nested calls)
            
        Returns:
            List of Dep objects
        """
        deps = []
        
        for package_info in packages_list:
            name = package_info.get("name", "")
            version = package_info.get("version", "")
            
            if not name:
                continue
            
            # Determine dev dependency status
            is_dev = (
                package_info.get("category") == "dev" or
                package_info.get("develop", False) or
                package_info.get("dev", False)
            )
            
            # Simple path for now (could be enhanced with relationship tracking)
            path = [name] if not parent_name else [parent_name, name]
            
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=path,
                is_direct=parent_name is None,
                is_dev=is_dev
            )
            deps.append(dep)
        
        return deps
    
    def _build_dependency_map(self, packages_dict: dict, root_deps: dict) -> dict:
        """Build map of dependency relationships"""
        dependency_map = {}
        
        for package_path, info in packages_dict.items():
            if package_path == "":
                continue
                
            name = self._extract_package_name(package_path)
            if name:
                dependencies = info.get("dependencies", {})
                dependency_map[name] = list(dependencies.keys())
        
        return dependency_map
    
    def _extract_package_name(self, package_path: str) -> str:
        """
        Extract package name from path like 'node_modules/package' or 'node_modules/@scope/package'
        """
        if not package_path.startswith("node_modules/"):
            return ""
        
        path_parts = package_path[13:].split("/")  # Remove "node_modules/"
        
        if len(path_parts) == 1:
            return path_parts[0]  # Simple package
        elif len(path_parts) == 2 and path_parts[0].startswith("@"):
            return "/".join(path_parts[:2])  # Scoped package like @babel/core
        else:
            return path_parts[0]  # Fallback to first part
    
    def deduplicate_dependencies(self, deps: list[Dep]) -> list[Dep]:
        """
        Remove duplicate dependencies based on (ecosystem, name, version)
        Keep the one with the shortest path (most direct)
        """
        seen = {}
        unique_deps = []
        
        for dep in deps:
            key = (dep.ecosystem, dep.name, dep.version)
            
            if key not in seen:
                seen[key] = dep
                unique_deps.append(dep)
            else:
                # Keep the one with shorter path (more direct)
                existing = seen[key]
                if len(dep.path) < len(existing.path):
                    # Replace existing with more direct dependency
                    unique_deps[unique_deps.index(existing)] = dep
                    seen[key] = dep
        
        return unique_deps