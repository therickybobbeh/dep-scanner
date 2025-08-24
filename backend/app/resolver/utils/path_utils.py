"""Path tracking utilities for dependency trees"""


class PathTracker:
    """Utility for tracking dependency paths and relationships"""
    
    @staticmethod
    def create_path(parent_path: list[str] | None, package_name: str) -> list[str]:
        """
        Create a new dependency path by appending package name to parent path
        
        Args:
            parent_path: Path to parent dependency, or None for root
            package_name: Name of current package
        
        Returns:
            New path list showing dependency chain
        """
        if parent_path is None:
            return [package_name]
        return parent_path + [package_name]
    
    @staticmethod
    def is_direct_dependency(path: list[str]) -> bool:
        """
        Check if dependency is direct (path length = 1)
        
        Args:
            path: Dependency path list
            
        Returns:
            True if direct dependency, False if transitive
        """
        return len(path) == 1
    
    @staticmethod
    def get_depth(path: list[str]) -> int:
        """
        Get dependency depth (0 = direct, 1 = first-level transitive, etc.)
        
        Args:
            path: Dependency path list
            
        Returns:
            Depth level (0-indexed)
        """
        return max(0, len(path) - 1)
    
    @staticmethod
    def get_parent(path: list[str]) -> str | None:
        """
        Get immediate parent package name
        
        Args:
            path: Dependency path list
            
        Returns:
            Parent package name, or None if direct dependency
        """
        if len(path) <= 1:
            return None
        return path[-2]
    
    @staticmethod
    def format_path_string(path: list[str], separator: str = " → ") -> str:
        """
        Format dependency path as human-readable string
        
        Args:
            path: Dependency path list
            separator: String to use between path elements
            
        Returns:
            Formatted path string
        """
        return separator.join(path)
    
    @staticmethod
    def detect_circular_dependency(path: list[str], new_package: str) -> bool:
        """
        Check if adding a package would create circular dependency
        
        Args:
            path: Current dependency path
            new_package: Package to potentially add
            
        Returns:
            True if would create circular dependency
        """
        return new_package in path