"""Parser for npm ls command output"""
import json
import subprocess
from typing import Any

from ...base import BaseDependencyParser, ParseError
from ...utils import DependencyTreeBuilder
from ....models import Dep


class NpmLsParser(BaseDependencyParser):
    """
    Parser for npm ls command output
    
    This parser executes 'npm ls --all --json' and parses the resulting
    dependency tree. This provides the most accurate transitive dependency
    information when a project has been installed.
    
    Output structure:
    {
        "name": "project-name",
        "version": "1.0.0",
        "dependencies": {
            "package-name": {
                "version": "1.0.0",
                "dependencies": { ... }
            }
        }
    }
    """
    
    def __init__(self):
        super().__init__(ecosystem="npm")
        self.tree_builder = DependencyTreeBuilder(self.ecosystem)
    
    @property
    def supported_formats(self) -> list[str]:
        return ["npm-ls"]  # Special format identifier
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse npm ls JSON output
        
        Args:
            content: JSON output from npm ls command
            **kwargs: Additional options
                - repo_path: Path to run npm ls in (if content is empty)
            
        Returns:
            List of dependency objects
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            # If no content provided, try to run npm ls
            if not content.strip():
                repo_path = kwargs.get("repo_path")
                if repo_path:
                    content = await self._run_npm_ls(repo_path)
                else:
                    raise ValueError("No content provided and no repo_path specified")
            
            ls_data = json.loads(content)
            return self._parse_npm_ls_output(ls_data)
            
        except json.JSONDecodeError as e:
            raise ParseError("npm ls output", e)
        except Exception as e:
            raise ParseError("npm ls", e)
    
    async def _run_npm_ls(self, repo_path: str) -> str:
        """
        Execute npm ls command and return JSON output
        
        Args:
            repo_path: Directory to run npm ls in
            
        Returns:
            JSON output from npm ls
            
        Raises:
            RuntimeError: If npm ls fails
        """
        try:
            result = subprocess.run([
                "npm", "ls", "--all", "--json", "--long"
            ], cwd=repo_path, capture_output=True, text=True, check=True)
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            # npm ls can exit with non-zero code even with valid output
            if e.stdout:
                try:
                    # Validate that stdout contains valid JSON
                    json.loads(e.stdout)
                    return e.stdout
                except json.JSONDecodeError:
                    pass
            
            raise RuntimeError(f"Failed to run npm ls: {e.stderr or e}")
        except Exception as e:
            raise RuntimeError(f"Failed to execute npm ls: {e}")
    
    def _parse_npm_ls_output(self, ls_data: dict[str, Any]) -> list[Dep]:
        """
        Parse npm ls JSON output into dependency objects
        
        Args:
            ls_data: Parsed JSON from npm ls
            
        Returns:
            List of dependency objects
        """
        dependencies = []
        root_name = ls_data.get("name", "")
        
        # Extract dependencies recursively
        deps_dict = ls_data.get("dependencies", {})
        if deps_dict:
            dependencies = self._extract_dependencies_recursive(
                deps_dict, 
                parent_path=None, 
                root_name=root_name
            )
        
        return dependencies
    
    def _extract_dependencies_recursive(
        self, 
        deps_dict: dict[str, Any], 
        parent_path: list[str] | None = None,
        root_name: str = ""
    ) -> list[Dep]:
        """
        Recursively extract dependencies from npm ls output
        
        Args:
            deps_dict: Dependencies dictionary from npm ls
            parent_path: Path to parent dependency
            root_name: Name of root package (to skip)
            
        Returns:
            List of dependency objects
        """
        dependencies = []
        
        for name, info in deps_dict.items():
            version = info.get("version", "")
            
            # Skip the root package itself
            if name == root_name and parent_path is None:
                continue
            
            # Build dependency path
            if parent_path is None:
                current_path = [name]
                is_direct = True
            else:
                current_path = parent_path + [name]
                is_direct = False
            
            # Determine if it's a dev dependency
            is_dev = (
                info.get("dev", False) or 
                info.get("devDependencies", False) or
                info.get("extraneous", False)
            )
            
            # Create dependency object
            dep = self._create_dependency(
                name=name,
                version=version,
                path=current_path,
                is_direct=is_direct,
                is_dev=is_dev
            )
            dependencies.append(dep)
            
            # Recursively process nested dependencies
            nested_deps = info.get("dependencies", {})
            if nested_deps:
                nested_dependencies = self._extract_dependencies_recursive(
                    nested_deps, 
                    current_path, 
                    root_name
                )
                dependencies.extend(nested_dependencies)
        
        return dependencies
    
    def can_run_npm_ls(self, repo_path: str) -> bool:
        """
        Check if npm ls can be run in the given directory
        
        Args:
            repo_path: Directory to check
            
        Returns:
            True if npm ls can be executed
        """
        import os
        
        # Check if package.json exists
        package_json = os.path.join(repo_path, "package.json")
        if not os.path.exists(package_json):
            return False
        
        # Check if node_modules exists
        node_modules = os.path.join(repo_path, "node_modules")
        if not os.path.exists(node_modules):
            return False
        
        # Check if npm is available
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False