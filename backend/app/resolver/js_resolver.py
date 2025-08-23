import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set
import re

from ..models import Dep, Ecosystem

class JavaScriptResolver:
    """Resolves JavaScript/Node.js dependencies from various manifest formats"""
    
    def __init__(self):
        self.ecosystem: Ecosystem = "npm"
    
    async def resolve_dependencies(self, repo_path: str, manifest_files: Optional[Dict[str, str]] = None) -> List[Dep]:
        """
        Resolve JavaScript dependencies from repository or manifest files
        Priority: lockfiles > npm ls > manifest files
        """
        if manifest_files:
            return await self._resolve_from_manifests(manifest_files)
        else:
            return await self._resolve_from_repo(repo_path)
    
    async def _resolve_from_repo(self, repo_path: str) -> List[Dep]:
        """Resolve dependencies from a repository directory"""
        repo_path_obj = Path(repo_path)
        
        # Try lockfiles first (deterministic)
        package_lock = repo_path_obj / "package-lock.json"
        yarn_lock = repo_path_obj / "yarn.lock"
        
        if package_lock.exists():
            return await self._parse_package_lock(package_lock.read_text())
        elif yarn_lock.exists():
            return await self._parse_yarn_lock(yarn_lock.read_text())
        
        # Try npm ls if package.json exists and node_modules is present
        package_json = repo_path_obj / "package.json"
        node_modules = repo_path_obj / "node_modules"
        
        if package_json.exists() and node_modules.exists():
            return await self._resolve_with_npm_ls(repo_path)
        elif package_json.exists():
            return await self._parse_package_json_only(package_json.read_text())
        
        raise FileNotFoundError("No JavaScript dependency files found in repository")
    
    async def _resolve_from_manifests(self, manifest_files: Dict[str, str]) -> List[Dep]:
        """Resolve dependencies from provided manifest file contents"""
        
        # Priority: lockfiles first
        if "package-lock.json" in manifest_files:
            return await self._parse_package_lock(manifest_files["package-lock.json"])
        elif "yarn.lock" in manifest_files:
            return await self._parse_yarn_lock(manifest_files["yarn.lock"])
        elif "package.json" in manifest_files:
            # Without lockfiles or node_modules, we can only get direct dependencies
            return await self._parse_package_json_only(manifest_files["package.json"])
        
        raise ValueError("No supported JavaScript dependency files provided")
    
    async def _parse_package_lock(self, content: str) -> List[Dep]:
        """Parse package-lock.json to extract full dependency tree"""
        try:
            lock_data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse package-lock.json: {e}")
        
        dependencies = []
        
        # Handle both lockfileVersion 1 and 2/3 formats
        lockfile_version = lock_data.get("lockfileVersion", 1)
        
        if lockfile_version >= 2:
            # v2/v3 format has packages object
            packages = lock_data.get("packages", {})
            return await self._parse_package_lock_v2(packages, lock_data)
        else:
            # v1 format has dependencies object
            deps = lock_data.get("dependencies", {})
            return await self._parse_package_lock_v1(deps)
    
    async def _parse_package_lock_v1(self, dependencies: Dict) -> List[Dep]:
        """Parse package-lock.json v1 format"""
        deps = []
        
        def extract_deps(dep_dict: Dict, path: List[str] = None) -> None:
            if path is None:
                path = []
            
            for name, info in dep_dict.items():
                version = info.get("version", "")
                current_path = path + [name]
                
                dep = Dep(
                    name=name,
                    version=version,
                    ecosystem=self.ecosystem,
                    path=current_path,
                    is_direct=len(path) == 0,
                    is_dev=info.get("dev", False)
                )
                deps.append(dep)
                
                # Recursively process nested dependencies
                nested_deps = info.get("dependencies", {})
                if nested_deps:
                    extract_deps(nested_deps, current_path)
        
        extract_deps(dependencies)
        return deps
    
    async def _parse_package_lock_v2(self, packages: Dict, lock_data: Dict) -> List[Dep]:
        """Parse package-lock.json v2/v3 format"""
        deps = []
        root_name = lock_data.get("name", "")
        
        for package_path, info in packages.items():
            if package_path == "":  # Skip root package
                continue
            
            # Extract package name from path
            name = package_path.split("/")[-1] if "/" in package_path else package_path
            name = name.replace("node_modules/", "")
            
            version = info.get("version", "")
            is_dev = info.get("dev", False) or info.get("devOptional", False)
            
            # Build path from package location
            path_parts = package_path.split("/node_modules/")
            if len(path_parts) > 1:
                # Transitive dependency
                parent_chain = [p for p in path_parts[:-1] if p and p != ""]
                current_path = parent_chain + [name]
            else:
                # Direct dependency
                current_path = [name]
            
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=current_path,
                is_direct=len(current_path) == 1,
                is_dev=is_dev
            )
            deps.append(dep)
        
        return deps
    
    async def _parse_yarn_lock(self, content: str) -> List[Dep]:
        """Parse yarn.lock file to extract dependencies"""
        dependencies = []
        
        # Parse yarn.lock format (simplified parser)
        entries = self._parse_yarn_entries(content)
        
        for entry in entries:
            name, version = self._extract_name_version_from_yarn_entry(entry)
            if name and version:
                dep = Dep(
                    name=name,
                    version=version,
                    ecosystem=self.ecosystem,
                    path=[name],  # Yarn.lock doesn't provide full dependency paths easily
                    is_direct=True,  # Simplified - would need package.json to determine this
                    is_dev=False
                )
                dependencies.append(dep)
        
        return dependencies
    
    def _parse_yarn_entries(self, content: str) -> List[Dict[str, str]]:
        """Parse yarn.lock content into individual package entries"""
        entries = []
        current_entry = {}
        in_entry = False
        
        for line in content.splitlines():
            line = line.rstrip()
            
            if line and not line.startswith(" ") and not line.startswith("\t"):
                # New entry
                if current_entry:
                    entries.append(current_entry)
                current_entry = {"header": line}
                in_entry = True
            elif in_entry and line.strip():
                # Entry property
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_entry[key.strip()] = value.strip().strip('"')
        
        if current_entry:
            entries.append(current_entry)
        
        return entries
    
    def _extract_name_version_from_yarn_entry(self, entry: Dict[str, str]) -> tuple[str, str]:
        """Extract package name and version from a yarn.lock entry"""
        header = entry.get("header", "")
        version = entry.get("version", "")
        
        # Parse header like: "package@^1.0.0", "package@npm:other@1.0.0"
        if "@" in header:
            parts = header.split("@")
            if len(parts) >= 2:
                name = parts[0].strip('"')
                return name, version
        
        return "", ""
    
    async def _resolve_with_npm_ls(self, repo_path: str) -> List[Dep]:
        """Use npm ls to get installed dependency tree"""
        try:
            result = subprocess.run([
                "npm", "ls", "--all", "--json", "--long"
            ], cwd=repo_path, capture_output=True, text=True, check=True)
            
            ls_data = json.loads(result.stdout)
            return self._parse_npm_ls_output(ls_data)
            
        except subprocess.CalledProcessError as e:
            # npm ls can exit with non-zero code even with valid output
            if e.stdout:
                try:
                    ls_data = json.loads(e.stdout)
                    return self._parse_npm_ls_output(ls_data)
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Failed to run npm ls: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to resolve dependencies with npm ls: {e}")
    
    def _parse_npm_ls_output(self, ls_data: Dict) -> List[Dep]:
        """Parse npm ls JSON output to create Dep objects"""
        dependencies = []
        
        def extract_deps(node: Dict, path: List[str] = None) -> None:
            if path is None:
                path = []
            
            name = node.get("name", "")
            version = node.get("version", "")
            
            if name and version and name != ls_data.get("name"):  # Skip root package
                current_path = path + [name]
                is_dev = node.get("dev", False) or node.get("devDependencies", False)
                
                dep = Dep(
                    name=name,
                    version=version,
                    ecosystem=self.ecosystem,
                    path=current_path,
                    is_direct=len(path) == 0,
                    is_dev=is_dev
                )
                dependencies.append(dep)
                
                # Process dependencies
                deps = node.get("dependencies", {})
                for dep_name, dep_info in deps.items():
                    extract_deps(dep_info, current_path)
        
        # Start processing from root
        root_deps = ls_data.get("dependencies", {})
        for dep_name, dep_info in root_deps.items():
            extract_deps(dep_info, [])
        
        return dependencies
    
    async def _parse_package_json_only(self, content: str) -> List[Dep]:
        """Parse package.json to get only direct dependencies (without versions)"""
        try:
            package_data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse package.json: {e}")
        
        dependencies = []
        
        # Production dependencies
        prod_deps = package_data.get("dependencies", {})
        for name, version_spec in prod_deps.items():
            # Extract version from spec (simplified)
            version = self._extract_version_from_spec(version_spec)
            dep = Dep(
                name=name,
                version=version or "unknown",
                ecosystem=self.ecosystem,
                path=[name],
                is_direct=True,
                is_dev=False
            )
            dependencies.append(dep)
        
        # Development dependencies
        dev_deps = package_data.get("devDependencies", {})
        for name, version_spec in dev_deps.items():
            version = self._extract_version_from_spec(version_spec)
            dep = Dep(
                name=name,
                version=version or "unknown",
                ecosystem=self.ecosystem,
                path=[name],
                is_direct=True,
                is_dev=True
            )
            dependencies.append(dep)
        
        return dependencies
    
    def _extract_version_from_spec(self, version_spec: str) -> Optional[str]:
        """Extract specific version from version specifier"""
        # Handle exact versions, git URLs, file paths, etc.
        if not version_spec:
            return None
        
        # Remove common prefixes
        spec = version_spec.lstrip("^~>=<")
        
        # Extract version-like strings
        version_pattern = r'\d+\.\d+\.\d+(?:-[\w.-]+)?'
        match = re.search(version_pattern, spec)
        
        return match.group(0) if match else None