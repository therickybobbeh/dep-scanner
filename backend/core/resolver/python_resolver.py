"""
Simplified Python dependency resolver

This module provides a clean, easy-to-follow interface for resolving Python
dependencies from various manifest and lockfile formats.
"""
from pathlib import Path
from typing import Union

from .base import ParseError
from .factories.python_factory import PythonParserFactory
from ..models import Dep, Ecosystem


class PythonResolver:
    """
    Python dependency resolver using unified pip approach
    
    Resolves dependencies by converting all formats to requirements.lock using pip:
    1. requirements.lock (pip output) - Most accurate 
    2. Lock files (poetry.lock, Pipfile.lock) → requirements.lock
    3. Manifest files (requirements.txt, pyproject.toml, Pipfile) → requirements.lock
    
    Example usage:
        resolver = PythonResolver()
        
        # From repository directory
        deps = await resolver.resolve_dependencies("/path/to/repo")
        
        # From uploaded files
        files = {"pyproject.toml": content}
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
            List of dependency objects with full transitive resolution
            
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
        1. requirements.lock (full transitive resolution)
        2. poetry.lock (full transitive resolution)
        3. Pipfile.lock (full transitive resolution) 
        4. requirements.txt, pyproject.toml, Pipfile (converted to requirements.lock)
        """
        repo_path_obj = Path(repo_path)
        
        if not repo_path_obj.exists() or not repo_path_obj.is_dir():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")
        
        # Find and collect Python dependency files
        manifest_files = {}
        supported_files = [
            "requirements.lock",
            "poetry.lock", 
            "Pipfile.lock",
            "requirements.txt",
            "pyproject.toml", 
            "Pipfile"
        ]
        
        for filename in supported_files:
            file_path = repo_path_obj / filename
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8')
                    manifest_files[filename] = content
                except Exception as e:
                    # Log warning but continue
                    print(f"Warning: Failed to read {filename}: {e}")
                    continue
        
        if not manifest_files:
            raise FileNotFoundError("No Python dependency files found in repository")
        
        return await self._resolve_from_uploaded_files(manifest_files)
    
    async def _resolve_from_uploaded_files(self, manifest_files: dict[str, str]) -> list[Dep]:
        """
        Resolve dependencies from uploaded manifest files
        
        Uses pip to ensure consistent dependency resolution by converting
        all formats to requirements.lock when needed.
        """
        if not manifest_files:
            raise ValueError("No manifest files provided")
        
        # Use pip to ensure requirements.lock exists for consistent resolution
        from ..lock_generators.python_generator import python_lock_generator
        
        enhanced_files = await python_lock_generator.ensure_requirements_lock(manifest_files)
        
        try:
            # Detect the best format to use with clear priority
            filename, format_name = self.parser_factory.detect_best_format(enhanced_files)
            content = enhanced_files[filename]
            
            # Get appropriate parser and parse
            parser = self.parser_factory.get_parser(filename, content)
            deps = await parser.parse(content, include_dev_dependencies=True)
            
            return deps
            
        except Exception as e:
            raise ParseError("Python manifest files", e)
    
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
            "requirements.lock": True,
            "poetry.lock": True,
            "Pipfile.lock": True,
            "requirements.txt": False,  # Only direct dependencies
            "pyproject.toml": False,   # Only direct dependencies
            "Pipfile": False           # Only direct dependencies
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
        if filename == "requirements.lock":
            return {
                "format": "requirements.lock",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "pip lockfile with full dependency tree and exact versions"
            }
        elif filename == "poetry.lock":
            return {
                "format": "poetry.lock",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "Poetry lockfile with full dependency tree and exact versions"
            }
        elif filename == "Pipfile.lock":
            return {
                "format": "Pipfile.lock",
                "transitive_resolution": True,
                "deterministic_versions": True,
                "description": "Pipenv lockfile with dependency tree and exact versions"
            }
        elif filename in ["requirements.txt", "pyproject.toml", "Pipfile"]:
            return {
                "format": filename,
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": f"Python manifest with direct dependencies only (converted to requirements.lock for full resolution)"
            }
        else:
            return {
                "format": "unknown",
                "transitive_resolution": False,
                "deterministic_versions": False,
                "description": "Unsupported format"
            }