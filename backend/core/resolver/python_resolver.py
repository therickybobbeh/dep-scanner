"""
Simplified Python dependency resolver

This module provides a clean, easy-to-follow interface for resolving Python
dependencies from various manifest and lockfile formats.
"""
from pathlib import Path
from typing import Union

from .base import ParseError
from .factories import PythonParserFactory
from ..models import Dep, Ecosystem


class PythonResolver:
    """
    Python dependency resolver
    
    Resolves dependencies using a prioritized approach:
    1. Lockfiles (poetry.lock, Pipfile.lock) - Most accurate
    2. Manifest files (pyproject.toml, Pipfile, requirements.txt) - Direct deps only
    
    Example usage:
        resolver = PythonResolver()
        
        # From repository directory
        deps = await resolver.resolve_dependencies("/path/to/repo")
        
        # From uploaded files
        files = {"pyproject.toml": content, "poetry.lock": content}
        deps = await resolver.resolve_dependencies(None, files)
    """
    
    def __init__(self):
        self.ecosystem: Ecosystem = "PyPI"
        self.parser_factory = PythonParserFactory()
    
    async def resolve_dependencies(
        self, 
        repo_path: str | None, 
        manifest_files: dict[str, str] | None = None
    ) -> list[Dep]:
        """
        Resolve Python dependencies from repository or manifest files
        
        Args:
            repo_path: Path to repository directory (None if using manifest_files)
            manifest_files: Dict of {filename: content} for uploaded files
            
        Returns:
            List of dependency objects with full transitive resolution when possible
            
        Raises:
            FileNotFoundError: If no supported dependency files found
            ParseError: If parsing fails
        """
        if manifest_files:
            return await self._resolve_from_uploaded_files(manifest_files)
        elif repo_path:
            return await self._resolve_from_repository(repo_path)
        else:
            raise ValueError("Either repo_path or manifest_files must be provided")
    
    async def _resolve_from_repository(self, repo_path: str) -> list[Dep]:
        """
        Resolve dependencies from a repository directory
        
        Priority order:
        1. poetry.lock (full transitive resolution)
        2. Pipfile.lock (full transitive resolution)
        3. pyproject.toml (direct dependencies only)
        4. Pipfile (direct dependencies only)
        5. requirements.txt files (direct dependencies only)
        """
        repo_path_obj = Path(repo_path)
        
        # Step 1: Try lockfiles first (most accurate)
        lockfiles = [
            ("poetry.lock", "poetry.lock"),
            ("Pipfile.lock", "Pipfile.lock")
        ]
        
        for filename, format_name in lockfiles:
            file_path = repo_path_obj / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    parser = self.parser_factory.get_parser(filename, content)
                    deps = await parser.parse(content)
                    
                    if deps:  # Successfully parsed with dependencies
                        return deps
                        
                except Exception as e:
                    # Log warning but continue to next method
                    print(f"Warning: Failed to parse {filename}: {e}")
                    continue
        
        # Step 2: Try manifest files (direct dependencies only)
        manifest_files = [
            ("pyproject.toml", "pyproject"),
            ("Pipfile", "pipfile"),
            ("requirements.txt", "requirements")
        ]
        
        for filename, format_name in manifest_files:
            file_path = repo_path_obj / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    parser = self.parser_factory.get_parser(filename, content)
                    deps = await parser.parse(content)
                    
                    if deps:
                        return deps
                        
                except Exception as e:
                    print(f"Warning: Failed to parse {filename}: {e}")
                    continue
        
        # Step 3: Look for any requirements files (dev-requirements.txt, etc.)
        deps = await self._try_requirements_files(repo_path_obj)
        if deps:
            return deps
        
        raise FileNotFoundError("No Python dependency files found in repository")
    
    async def _resolve_from_uploaded_files(self, manifest_files: dict[str, str]) -> list[Dep]:
        """
        Resolve dependencies from uploaded manifest files
        
        Uses the best available file format based on priority
        """
        if not manifest_files:
            raise ValueError("No manifest files provided")
        
        try:
            # Detect the best format to use
            filename, format_name = self.parser_factory.detect_best_format(manifest_files)
            content = manifest_files[filename]
            
            # Get appropriate parser and parse
            parser = self.parser_factory.get_parser(filename, content)
            deps = await parser.parse(content)
            
            # If using requirements.txt, try to merge multiple requirements files
            if format_name == "requirements":
                deps = await self._merge_requirements_files(manifest_files, deps)
            
            return deps
            
        except Exception as e:
            raise ParseError("Python manifest files", e)
    
    async def _try_requirements_files(self, repo_path: Path) -> list[Dep]:
        """
        Try to find and parse requirements files in repository
        
        Looks for:
        - requirements.txt
        - requirements/*.txt files
        - dev-requirements.txt, test-requirements.txt, etc.
        """
        deps = []
        requirements_parser = self.parser_factory.get_parser_by_format("requirements")
        
        # Check for main requirements.txt
        main_requirements = repo_path / "requirements.txt"
        if main_requirements.exists():
            try:
                content = main_requirements.read_text(encoding='utf-8')
                main_deps = await requirements_parser.parse(content)
                deps.extend(main_deps)
            except Exception as e:
                print(f"Warning: Failed to parse requirements.txt: {e}")
        
        # Check for requirements directory
        requirements_dir = repo_path / "requirements"
        if requirements_dir.exists() and requirements_dir.is_dir():
            for req_file in requirements_dir.glob("*.txt"):
                try:
                    content = req_file.read_text(encoding='utf-8')
                    is_dev = requirements_parser.detect_dev_requirements(req_file.name)
                    file_deps = await requirements_parser.parse(content, is_dev=is_dev)
                    deps.extend(file_deps)
                except Exception as e:
                    print(f"Warning: Failed to parse {req_file.name}: {e}")
        
        # Check for other requirements files (dev-requirements.txt, etc.)
        for req_file in repo_path.glob("*requirements*.txt"):
            if req_file.name == "requirements.txt":
                continue  # Already processed
                
            try:
                content = req_file.read_text(encoding='utf-8')
                is_dev = requirements_parser.detect_dev_requirements(req_file.name)
                file_deps = await requirements_parser.parse(content, is_dev=is_dev)
                deps.extend(file_deps)
            except Exception as e:
                print(f"Warning: Failed to parse {req_file.name}: {e}")
        
        return deps
    
    async def _merge_requirements_files(
        self, 
        manifest_files: dict[str, str], 
        initial_deps: list[Dep]
    ) -> list[Dep]:
        """
        Merge dependencies from multiple requirements files
        """
        all_deps = initial_deps.copy()
        requirements_parser = self.parser_factory.get_parser_by_format("requirements")
        
        # Process other requirements files
        for filename, content in manifest_files.items():
            if filename.endswith("requirements.txt") and filename != "requirements.txt":
                try:
                    is_dev = requirements_parser.detect_dev_requirements(filename)
                    file_deps = await requirements_parser.parse(content, is_dev=is_dev)
                    all_deps.extend(file_deps)
                except Exception as e:
                    print(f"Warning: Failed to parse {filename}: {e}")
        
        # Remove duplicates (same package name)
        seen_names = set()
        unique_deps = []
        
        for dep in all_deps:
            if dep.name not in seen_names:
                unique_deps.append(dep)
                seen_names.add(dep.name)
        
        return unique_deps
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported Python dependency file formats"""
        return self.parser_factory.get_supported_formats()
    
    def can_resolve_transitive_dependencies(self, filename: str) -> bool:
        """
        Check if a file format supports full transitive dependency resolution
        
        Args:
            filename: Name of dependency file
            
        Returns:
            True if format supports transitive dependencies
        """
        transitive_formats = {
            "poetry.lock": True,
            "Pipfile.lock": True,
            "pyproject.toml": False,  # Only direct dependencies
            "Pipfile": False,         # Only direct dependencies
            "requirements.txt": False # Only direct dependencies
        }
        
        return transitive_formats.get(filename, False)
    
    def get_resolution_info(self, filename: str) -> dict[str, Union[str, bool]]:
        """
        Get information about resolution capabilities for a file format
        
        Args:
            filename: Name of dependency file
            
        Returns:
            Dict with resolution information
        """
        resolution_info = {
            "poetry.lock": {
                "format": "poetry.lock",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "Poetry lockfile with full dependency tree and exact versions"
            },
            "Pipfile.lock": {
                "format": "Pipfile.lock",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "Pipenv lockfile with exact versions"
            },
            "pyproject.toml": {
                "format": "pyproject.toml",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "Python project manifest (PEP 621 or Poetry) with direct dependencies only"
            },
            "Pipfile": {
                "format": "Pipfile",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "Pipenv manifest with direct dependencies and version ranges only"
            },
            "requirements.txt": {
                "format": "requirements.txt",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "Pip requirements with direct dependencies only"
            }
        }
        
        return resolution_info.get(filename, {
            "format": "unknown",
            "transitive_resolution": False,
            "deterministic_versions": False,
            "description": "Unsupported format"
        })