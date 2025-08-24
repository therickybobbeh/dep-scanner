"""Parser for package.json manifest files"""
import json

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ....models import Dep


class PackageJsonParser(BaseDependencyParser):
    """
    Parser for package.json manifest files
    
    Note: This only extracts DIRECT dependencies since package.json
    doesn't contain information about transitive dependencies.
    
    Structure:
    {
        "dependencies": {
            "package-name": "^1.0.0"
        },
        "devDependencies": {
            "dev-package": "~2.0.0"
        }
    }
    """
    
    def __init__(self):
        super().__init__(ecosystem="npm")
        self.version_cleaner = VersionCleaner()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["package.json"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse package.json content
        
        Args:
            content: Raw package.json content
            **kwargs: Additional parsing options
                - include_dev: Whether to include dev dependencies (default: True)
            
        Returns:
            List of dependency objects (direct dependencies only)
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            package_data = json.loads(content)
            deps = []
            
            include_dev = kwargs.get("include_dev", True)
            
            # Parse production dependencies
            prod_deps = package_data.get("dependencies", {})
            for name, version_spec in prod_deps.items():
                clean_version = self.version_cleaner.clean_npm_version(version_spec)
                
                dep = self._create_dependency(
                    name=name,
                    version=clean_version,
                    path=[name],
                    is_direct=True,
                    is_dev=False
                )
                deps.append(dep)
            
            # Parse development dependencies if requested
            if include_dev:
                dev_deps = package_data.get("devDependencies", {})
                for name, version_spec in dev_deps.items():
                    clean_version = self.version_cleaner.clean_npm_version(version_spec)
                    
                    dep = self._create_dependency(
                        name=name,
                        version=clean_version,
                        path=[name],
                        is_direct=True,
                        is_dev=True
                    )
                    deps.append(dep)
            
            # Parse peer dependencies if present (optional)
            peer_deps = package_data.get("peerDependencies", {})
            for name, version_spec in peer_deps.items():
                clean_version = self.version_cleaner.clean_npm_version(version_spec)
                
                dep = self._create_dependency(
                    name=name,
                    version=clean_version,
                    path=[name],
                    is_direct=True,
                    is_dev=False
                )
                # Note: peer deps are marked as direct but could be handled specially
                deps.append(dep)
            
            if not deps:
                # Could be a valid package.json with no dependencies
                return []
            
            return deps
            
        except json.JSONDecodeError as e:
            raise ParseError("package.json", e)
        except Exception as e:
            raise ParseError("package.json", e)
    
    def get_package_info(self, content: str) -> dict:
        """
        Extract basic package information from package.json
        
        Returns:
            Dict with name, version, description, etc.
        """
        try:
            data = json.loads(content)
            return {
                "name": data.get("name", ""),
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "main": data.get("main", ""),
                "scripts": data.get("scripts", {}),
            }
        except json.JSONDecodeError:
            return {}
    
    def has_lockfile_reference(self, content: str) -> bool:
        """
        Check if package.json suggests a lockfile should be present
        
        Returns:
            True if lockfile is expected (has dependencies)
        """
        try:
            data = json.loads(content)
            has_deps = bool(
                data.get("dependencies") or 
                data.get("devDependencies") or
                data.get("peerDependencies")
            )
            return has_deps
        except json.JSONDecodeError:
            return False