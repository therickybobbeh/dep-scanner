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
        
        # Apply deduplication to remove duplicate dependencies
        return self.deduplicate_dependencies(deps)
    
    def build_tree_flat(
        self, 
        packages_dict: dict, 
        root_dependencies: dict | None = None
    ) -> list[Dep]:
        """
        Build dependency tree from flat package structure with proper parent tracking
        
        Used for package-lock.json v2/v3 format and similar flat structures
        
        Args:
            packages_dict: Dict of {"node_modules/package": package_info}
            root_dependencies: Root package dependencies for detecting direct deps
            
        Returns:
            List of Dep objects representing the tree with proper parent relationships
        """
        deps = []
        
        # Build dependency relationships map to track parent-child relationships
        dependency_relationships = self._build_dependency_relationships(packages_dict, root_dependencies or {})
        
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
            
            # Build proper path based on dependency relationships
            path = self._build_dependency_path(name, dependency_relationships, root_dependencies or {})
            
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=path,
                is_direct=is_direct,
                is_dev=is_dev
            )
            deps.append(dep)
        
        # Apply deduplication to remove duplicate dependencies
        return self.deduplicate_dependencies(deps)
    
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
        
        # Apply deduplication to remove duplicate dependencies
        return self.deduplicate_dependencies(deps)
    
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
        Also handles nested paths like 'node_modules/parent/node_modules/child'
        """
        if not package_path.startswith("node_modules/"):
            return ""
        
        # Handle nested node_modules paths
        # e.g., "node_modules/vite/node_modules/fdir" should return "fdir"
        if "/node_modules/" in package_path:
            # Find the last occurrence of node_modules/
            last_node_modules = package_path.rfind("/node_modules/")
            # Extract everything after the last node_modules/
            remaining_path = package_path[last_node_modules + 14:]  # +14 for "/node_modules/"
            return self._extract_package_name("node_modules/" + remaining_path)
        
        path_parts = package_path[13:].split("/")  # Remove "node_modules/"
        
        if len(path_parts) == 1:
            return path_parts[0]  # Simple package
        elif len(path_parts) == 2 and path_parts[0].startswith("@"):
            return "/".join(path_parts[:2])  # Scoped package like @babel/core
        else:
            # For other cases (like nested paths), take the first part
            # This handles edge cases where there might be other path structures
            return path_parts[0]
    
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
    
    def _build_dependency_relationships(self, packages_dict: dict, root_deps: dict) -> dict:
        """
        Build a comprehensive map of parent-child dependency relationships
        
        Args:
            packages_dict: Flat packages structure from package-lock.json
            root_deps: Root package dependencies
            
        Returns:
            Dict mapping each package to its direct parents
        """
        relationships = {}  # package_name -> list of parent packages
        
        # First, map all packages and their dependencies
        for package_path, info in packages_dict.items():
            if package_path == "":  # Root package
                # Root dependencies are direct children of the project
                for dep_name in root_deps:
                    if dep_name not in relationships:
                        relationships[dep_name] = []
                    relationships[dep_name].append("__root__")  # Special marker for direct deps
                continue
            
            package_name = self._extract_package_name(package_path)
            if not package_name:
                continue
            
            # Initialize entry for this package if not exists
            if package_name not in relationships:
                relationships[package_name] = []
            
            # Map this package's dependencies as its children
            dependencies = info.get("dependencies", {})
            for dep_name in dependencies:
                if dep_name not in relationships:
                    relationships[dep_name] = []
                relationships[dep_name].append(package_name)
        
        return relationships
    
    def _build_dependency_path(
        self, 
        package_name: str, 
        relationships: dict, 
        root_deps: dict,
        visited: set[str] | None = None,
        max_depth: int = 10
    ) -> list[str]:
        """
        Build the dependency path showing how a package was included
        
        Args:
            package_name: Name of the package to trace
            relationships: Parent-child relationship map
            root_deps: Root dependencies
            visited: Set of already visited packages (for cycle detection)
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Path list showing the dependency chain
        """
        # Initialize visited set for cycle detection
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if package_name in visited or max_depth <= 0:
            return [package_name]
        
        # If it's a direct dependency, path is just the package name
        if package_name in root_deps:
            return [package_name]
        
        # Find the shortest path to a root dependency
        parents = relationships.get(package_name, [])
        
        if not parents:
            # No known parents, treat as direct (fallback)
            return [package_name]
        
        # Add current package to visited set
        visited_copy = visited.copy()
        visited_copy.add(package_name)
        
        # Try to find the most direct path through parents
        shortest_path = None
        
        for parent in parents:
            if parent == "__root__":
                # Direct dependency
                return [package_name]
            elif parent in root_deps:
                # Parent is a direct dependency
                path = [parent, package_name]
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
            elif parent not in visited_copy:  # Only recurse if not already visited
                # Recursively build path through parent
                parent_path = self._build_dependency_path(
                    parent, relationships, root_deps, visited_copy, max_depth - 1
                )
                if parent_path:
                    full_path = parent_path + [package_name]
                    if shortest_path is None or len(full_path) < len(shortest_path):
                        shortest_path = full_path
        
        return shortest_path if shortest_path else [package_name]