"""Parser for yarn.lock files"""
import re
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ....models import Dep


class YarnLockParser(BaseDependencyParser):
    """
    Parser for yarn.lock files
    
    Yarn lock format is a custom text format:
    
    package-name@^1.0.0:
      version "1.0.1"
      resolved "https://registry.yarnpkg.com/..."
      integrity sha512-...
      dependencies:
        dep-name "^2.0.0"
    """
    
    def __init__(self):
        super().__init__(ecosystem="npm")
        self.version_cleaner = VersionCleaner()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["yarn.lock"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse yarn.lock content
        
        Args:
            content: Raw yarn.lock content
            **kwargs: Additional parsing options
            
        Returns:
            List of dependency objects
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            # Parse yarn.lock entries
            entries = self._parse_yarn_entries(content)
            deps = []
            
            for entry in entries:
                name, version = self._extract_name_version_from_yarn_entry(entry)
                if not name or not version:
                    continue
                
                # For yarn.lock, all dependencies are effectively at the same level
                # since yarn flattens the dependency tree
                dep = self._create_dependency(
                    name=name,
                    version=version,
                    path=[name],
                    is_direct=True,  # Yarn lock doesn't distinguish direct vs transitive clearly
                    is_dev=False     # Dev status would need to come from package.json
                )
                deps.append(dep)
            
            return deps
            
        except Exception as e:
            raise ParseError("yarn.lock", e)
    
    def _parse_yarn_entries(self, content: str) -> list[dict[str, str]]:
        """
        Parse yarn.lock content into individual package entries
        
        Returns:
            List of dictionaries representing each package entry
        """
        entries = []
        current_entry = {}
        
        for line in content.split('\n'):
            line = line.rstrip()
            
            if not line or line.startswith('#'):
                continue
            
            # Check if this is a new package entry (starts without indentation and ends with :)
            if not line.startswith((' ', '\t')) and line.endswith(':'):
                # Save previous entry
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
                
                # Start new entry - extract package name and version specifier
                package_spec = line[:-1].strip().strip('"')  # Remove trailing : and quotes
                current_entry['package_spec'] = package_spec
                continue
            
            # Parse indented properties
            if line.startswith((' ', '\t')):
                stripped = line.strip()
                
                # Handle key-value pairs with colons
                if ':' in stripped:
                    # Split on first colon only to handle URLs
                    key, value = stripped.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    current_entry[key] = value
                    
                # Handle special case: version "x.y.z" (no colon)
                elif stripped.startswith('version '):
                    version_value = stripped[8:].strip().strip('"')  # Remove 'version ' prefix
                    current_entry['version'] = version_value
                    
                # Handle special case: integrity (no colon)
                elif stripped.startswith('integrity '):
                    integrity_value = stripped[10:].strip()  # Remove 'integrity ' prefix
                    current_entry['integrity'] = integrity_value
                    
                # Handle dependency lines under dependencies:
                elif stripped and 'dependencies' in current_entry and current_entry['dependencies'] == '':
                    # This is a dependency line under dependencies:
                    if 'dependency_list' not in current_entry:
                        current_entry['dependency_list'] = []
                    # Parse dependency line like: "@babel/highlight" "^7.22.13"
                    parts = stripped.split()
                    if len(parts) >= 2:
                        dep_name = parts[0].strip('"')
                        dep_version = parts[1].strip('"')
                        current_entry['dependency_list'].append((dep_name, dep_version))
        
        # Don't forget the last entry
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    def _extract_name_version_from_yarn_entry(self, entry: dict[str, str]) -> tuple[str, str]:
        """
        Extract package name and version from yarn.lock entry
        
        Args:
            entry: Dictionary representing a yarn.lock entry
            
        Returns:
            Tuple of (package_name, version)
        """
        package_spec = entry.get('package_spec', '')
        version = entry.get('version', '')
        
        if not package_spec or not version:
            return "", ""
        
        # Parse package spec like "package-name@^1.0.0, package-name@~1.0.1"
        # Take the first part before the version specifier
        if '@' in package_spec:
            # Handle scoped packages like "@babel/core@^7.0.0"
            if package_spec.startswith('@'):
                # Find the second @ which separates package name from version
                parts = package_spec.split('@')
                if len(parts) >= 3:
                    name = '@' + parts[1]
                else:
                    name = '@' + parts[1].split('@')[0] if len(parts) > 1 else ""
            else:
                # Regular package like "lodash@^4.17.21"
                name = package_spec.split('@')[0]
        else:
            name = package_spec
        
        return name.strip(), version.strip()
    
    def _detect_dev_dependencies(self, entries: list[dict], package_json_content: str = "") -> set[str]:
        """
        Detect development dependencies by cross-referencing with package.json
        
        Since yarn.lock doesn't mark dev dependencies, we need package.json
        to determine which dependencies are dev dependencies.
        """
        if not package_json_content:
            return set()
        
        try:
            import json
            package_data = json.loads(package_json_content)
            dev_deps = set(package_data.get("devDependencies", {}).keys())
            return dev_deps
        except json.JSONDecodeError:
            return set()