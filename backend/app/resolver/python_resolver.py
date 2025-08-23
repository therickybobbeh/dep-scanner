import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import tomli
import re
from packaging.requirements import Requirement
from packaging.version import Version

from ..models import Dep, Ecosystem

class PythonResolver:
    """Resolves Python dependencies from various manifest formats"""
    
    def __init__(self):
        self.ecosystem: Ecosystem = "PyPI"
    
    async def resolve_dependencies(self, repo_path: str, manifest_files: Optional[Dict[str, str]] = None) -> List[Dep]:
        """
        Resolve Python dependencies from repository or manifest files
        Priority: lockfiles > manifest files > materialized environment
        """
        if manifest_files:
            return await self._resolve_from_manifests(manifest_files)
        else:
            return await self._resolve_from_repo(repo_path)
    
    async def _resolve_from_repo(self, repo_path: str) -> List[Dep]:
        """Resolve dependencies from a repository directory"""
        repo_path_obj = Path(repo_path)
        
        # Try lockfiles first (deterministic)
        poetry_lock = repo_path_obj / "poetry.lock"
        pipfile_lock = repo_path_obj / "Pipfile.lock"
        
        if poetry_lock.exists():
            return await self._parse_poetry_lock(poetry_lock.read_text())
        elif pipfile_lock.exists():
            return await self._parse_pipfile_lock(pipfile_lock.read_text())
        
        # Fall back to manifest files
        pyproject_toml = repo_path_obj / "pyproject.toml"
        pipfile = repo_path_obj / "Pipfile"
        requirements_txt = repo_path_obj / "requirements.txt"
        
        if pyproject_toml.exists():
            return await self._materialize_from_pyproject(pyproject_toml.read_text(), repo_path)
        elif pipfile.exists():
            return await self._materialize_from_pipfile(pipfile.read_text(), repo_path)
        elif requirements_txt.exists():
            return await self._materialize_from_requirements(requirements_txt.read_text(), repo_path)
        
        raise FileNotFoundError("No Python dependency files found in repository")
    
    async def _resolve_from_manifests(self, manifest_files: Dict[str, str]) -> List[Dep]:
        """Resolve dependencies from provided manifest file contents"""
        
        # Priority: lockfiles first
        if "poetry.lock" in manifest_files:
            return await self._parse_poetry_lock(manifest_files["poetry.lock"])
        elif "Pipfile.lock" in manifest_files:
            return await self._parse_pipfile_lock(manifest_files["Pipfile.lock"])
        
        # Fall back to manifest files (requires materialization)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write manifest files to temp directory
            for filename, content in manifest_files.items():
                (temp_path / filename).write_text(content)
            
            if "pyproject.toml" in manifest_files:
                return await self._materialize_from_pyproject(manifest_files["pyproject.toml"], temp_dir)
            elif "Pipfile" in manifest_files:
                return await self._materialize_from_pipfile(manifest_files["Pipfile"], temp_dir)
            elif "requirements.txt" in manifest_files:
                return await self._materialize_from_requirements(manifest_files["requirements.txt"], temp_dir)
        
        raise ValueError("No supported Python dependency files provided")
    
    async def _parse_poetry_lock(self, content: str) -> List[Dep]:
        """Parse poetry.lock file to extract dependencies with versions"""
        try:
            lock_data = tomli.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse poetry.lock: {e}")
        
        dependencies = []
        packages = lock_data.get("package", [])
        
        # Build dependency graph
        package_map = {pkg["name"]: pkg for pkg in packages}
        
        for package in packages:
            name = package["name"]
            version = package["version"]
            is_dev = package.get("category") == "dev"
            
            # Get dependencies of this package
            pkg_deps = package.get("dependencies", {})
            
            # Create dependency object
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=[name],  # Will be updated with full paths
                is_direct=False,  # Will be determined later
                is_dev=is_dev
            )
            dependencies.append(dep)
        
        # TODO: Build proper provenance paths by analyzing dependency relationships
        # For now, mark all as direct (this is a simplification)
        for dep in dependencies:
            dep.is_direct = True
        
        return dependencies
    
    async def _parse_pipfile_lock(self, content: str) -> List[Dep]:
        """Parse Pipfile.lock to extract dependencies"""
        try:
            lock_data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse Pipfile.lock: {e}")
        
        dependencies = []
        
        # Parse default (production) dependencies
        default_deps = lock_data.get("default", {})
        for name, info in default_deps.items():
            version = info.get("version", "").lstrip("==")
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=[name],
                is_direct=True,
                is_dev=False
            )
            dependencies.append(dep)
        
        # Parse development dependencies
        dev_deps = lock_data.get("develop", {})
        for name, info in dev_deps.items():
            version = info.get("version", "").lstrip("==")
            dep = Dep(
                name=name,
                version=version,
                ecosystem=self.ecosystem,
                path=[name],
                is_direct=True,
                is_dev=True
            )
            dependencies.append(dep)
        
        return dependencies
    
    async def _materialize_from_requirements(self, content: str, repo_path: str) -> List[Dep]:
        """Materialize dependencies from requirements.txt using pipdeptree"""
        return await self._materialize_with_pipdeptree(repo_path, ["requirements.txt"])
    
    async def _materialize_from_pyproject(self, content: str, repo_path: str) -> List[Dep]:
        """Materialize dependencies from pyproject.toml"""
        return await self._materialize_with_pipdeptree(repo_path, ["pyproject.toml"])
    
    async def _materialize_from_pipfile(self, content: str, repo_path: str) -> List[Dep]:
        """Materialize dependencies from Pipfile"""
        return await self._materialize_with_pipdeptree(repo_path, ["Pipfile"])
    
    async def _materialize_with_pipdeptree(self, repo_path: str, manifest_files: List[str]) -> List[Dep]:
        """
        Create a temporary virtual environment and use pipdeptree to resolve dependencies
        This is used when we only have manifest files without lockfiles
        """
        dependencies = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "venv"
            
            try:
                # Create virtual environment
                subprocess.run([
                    "python", "-m", "venv", str(venv_path)
                ], check=True, capture_output=True, text=True)
                
                # Determine pip install command based on manifest type
                pip_cmd = [str(venv_path / "bin" / "pip"), "install"]
                
                if "requirements.txt" in manifest_files:
                    pip_cmd.extend(["-r", os.path.join(repo_path, "requirements.txt")])
                elif "pyproject.toml" in manifest_files:
                    pip_cmd.append(repo_path)  # Install from directory
                elif "Pipfile" in manifest_files:
                    # For Pipfile, we'd need pipenv, which complicates things
                    # For now, skip materialization for Pipfile without Pipfile.lock
                    raise NotImplementedError("Pipfile materialization requires pipenv")
                
                # Install dependencies
                subprocess.run(pip_cmd, check=True, capture_output=True, text=True, cwd=repo_path)
                
                # Use pipdeptree to get dependency graph
                pipdeptree_cmd = [str(venv_path / "bin" / "pipdeptree"), "--json-tree"]
                result = subprocess.run(pipdeptree_cmd, check=True, capture_output=True, text=True)
                
                # Parse pipdeptree output
                tree_data = json.loads(result.stdout)
                dependencies = self._parse_pipdeptree_output(tree_data)
                
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to materialize Python dependencies: {e}")
            except Exception as e:
                raise RuntimeError(f"Unexpected error during dependency materialization: {e}")
        
        return dependencies
    
    def _parse_pipdeptree_output(self, tree_data: List[Dict]) -> List[Dep]:
        """Parse pipdeptree JSON output to create Dep objects"""
        dependencies = []
        
        def extract_deps(node: Dict, path: List[str] = None) -> None:
            if path is None:
                path = []
            
            name = node.get("package_name", "")
            version = node.get("installed_version", "")
            
            if name and version:
                current_path = path + [name]
                dep = Dep(
                    name=name,
                    version=version,
                    ecosystem=self.ecosystem,
                    path=current_path,
                    is_direct=len(path) == 0,
                    is_dev=False  # pipdeptree doesn't distinguish dev deps
                )
                dependencies.append(dep)
                
                # Recursively process dependencies
                for child in node.get("dependencies", []):
                    extract_deps(child, current_path)
        
        # Process all root packages
        for root_package in tree_data:
            extract_deps(root_package)
        
        return dependencies
    
    def _parse_requirements_txt(self, content: str) -> List[Tuple[str, Optional[str]]]:
        """Parse requirements.txt content to extract package names and version constraints"""
        packages = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            try:
                req = Requirement(line)
                # Extract version from specifiers (simplified)
                version = None
                if req.specifier:
                    for spec in req.specifier:
                        if spec.operator in ("==", ">="):
                            version = spec.version
                            break
                
                packages.append((req.name, version))
            except Exception:
                # Skip invalid requirements
                continue
        
        return packages