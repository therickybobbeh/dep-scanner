"""
Simplified Python dependency resolver

This module provides a clean, easy-to-follow interface for resolving Python
dependencies from various manifest and lockfile formats using pip-tools for consistency.
"""
from pathlib import Path
from typing import Union

from .base import ParseError
from .factories.python_factory import PythonParserFactory
from ..models import Dep, Ecosystem


class PythonResolver:
    """
    Python dependency resolver using unified pip-tools approach
    
    Resolves dependencies by converting all formats to requirements.lock:
    1. requirements.lock (pip-tools output) - Most accurate
    2. Lock files (poetry.lock, Pipfile.lock) → requirements.lock
    3. Manifest files (requirements.txt, pyproject.toml, Pipfile) → requirements.lock
    
    This ensures consistent transitive dependency resolution across all Python formats.
    
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
            repo_path: Path to repository directory (optional)
            manifest_files: Dict of {filename: content} (optional)
            
        Returns:
            List of resolved dependencies with transitive dependencies
            
        Note: 
            Provide either repo_path OR manifest_files, not both.
            When only manifest files are provided, pip-tools will generate
            requirements.lock automatically for consistent resolution.
        """
        if repo_path and manifest_files:
            raise ValueError("Provide either repo_path OR manifest_files, not both")
        
        if repo_path:
            return await self._resolve_from_repository(repo_path)
        elif manifest_files:
            return await self._resolve_from_uploaded_files(manifest_files)
        else:
            raise ValueError("Must provide either repo_path or manifest_files")
    
    async def _resolve_from_repository(self, repo_path: str) -> list[Dep]:
        """Resolve dependencies from repository directory"""
        repo_path_obj = Path(repo_path)
        
        if not repo_path_obj.exists() or not repo_path_obj.is_dir():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")
        
        # Find Python dependency files in repository
        manifest_files = {}
        
        supported_files = [
            "requirements.lock",    # pip-tools output (preferred)
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
                    # Skip files we can't read
                    continue
        
        if not manifest_files:
            raise ValueError(f"No supported Python dependency files found in {repo_path}")
        
        return await self._resolve_from_uploaded_files(manifest_files)
    
    async def _resolve_from_uploaded_files(self, manifest_files: dict[str, str]) -> list[Dep]:
        """
        Resolve dependencies from manifest files with pip-tools conversion
        
        This method ensures all Python dependency formats are converted to 
        requirements.lock for consistent transitive dependency resolution.
        """
        # Use pip-tools to ensure requirements.lock exists for consistent resolution
        from ..lock_generators.python_generator import python_lock_generator
        
        enhanced_files = await python_lock_generator.ensure_requirements_lock(manifest_files)
        
        # Select the best file to parse (prioritizing requirements.lock)
        try:
            filename, format_name = self.parser_factory.detect_best_format(enhanced_files)
        except ValueError as e:
            raise ParseError(f"No parseable Python dependency files found: {e}")
        
        # Get the appropriate parser
        parser = self.parser_factory.get_parser(filename, enhanced_files[filename])
        
        try:
            # Parse dependencies
            dependencies = await parser.parse(
                content=enhanced_files[filename],
                include_dev_dependencies=True  # Include dev dependencies by default
            )
            
            return dependencies
            
        except Exception as e:
            raise ParseError(f"Failed to parse {filename}: {e}")
    
    def get_supported_formats(self) -> list[str]:
        """Get list of supported Python dependency file formats"""
        return self.parser_factory.get_supported_formats()
    
    def can_resolve_files(self, filenames: list[str]) -> bool:
        """Check if resolver can handle the given filenames"""
        return any(self.parser_factory.can_handle_file(filename) for filename in filenames)