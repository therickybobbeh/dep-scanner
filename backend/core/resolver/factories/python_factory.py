"""Factory for Python dependency parsers"""
from __future__ import annotations

from typing import Dict, Optional, Set
from .base import BaseParserFactory
from ..base import DependencyParser, FileFormatDetector
from ..parsers.python import (
    PoetryLockParser,
    PipfileLockParser,
    RequirementsParser
)


class PythonParserFactory(BaseParserFactory):
    """
    Factory for creating appropriate Python dependency parsers
    
    Simplified factory that focuses on requirements.txt and lock files only.
    - requirements.txt: Primary manifest format (as per Socket requirements)
    - Lock files: poetry.lock, Pipfile.lock (when provided directly)
    - Uses PyPI API for dependency resolution (no external tools needed)
    """
    
    def _initialize_parsers(self) -> None:
        """Initialize Python-specific parsers"""
        self._parsers = {
            "requirements": RequirementsParser(),
            "poetry-lock": PoetryLockParser(),
            "pipfile-lock": PipfileLockParser()
        }
    
    def _detect_format(self, filename: str, content: str) -> str:
        """Detect Python dependency file format"""
        return self.detector.detect_python_format(filename, content)
    
    def _get_parser_for_format(self, format_name: str, content: str = "") -> DependencyParser:
        """Get parser for specific Python format"""
        if format_name in self._parsers:
            return self._parsers[format_name]
        else:
            raise ValueError(f"No parser available for format: {format_name}")
    
    def _get_format_priority(self) -> list:
        """Return Python format priority order"""
        return [
            "requirements.lock",  # Generated lock file (most accurate)
            "poetry.lock",        # Poetry lockfile
            "Pipfile.lock",       # Pipenv lockfile  
            "requirements.txt"    # Requirements manifest (primary input)
        ]
    
    def _get_supported_formats(self) -> Set[str]:
        """Return set of supported Python formats"""
        return {
            "requirements.lock",
            "poetry.lock",
            "Pipfile.lock", 
            "requirements.txt"
        }
    
    def get_parser_by_format(self, format_name: str) -> DependencyParser:
        """
        Get parser by explicit format name
        
        Args:
            format_name: Explicit format identifier
            
        Returns:
            Parser instance
        """
        if format_name in self._parsers:
            return self._parsers[format_name]
        else:
            raise ValueError(f"Unknown format: {format_name}")
    
    def detect_best_format(self, available_files: dict[str, str]) -> tuple[str, str]:
        """
        Detect the best format to use from available files
        
        Priority: lock files > requirements.txt
        Lock files contain resolved dependencies, requirements.txt needs resolution.
        
        Args:
            available_files: Dict of {filename: content}
            
        Returns:
            Tuple of (best_filename, format_name)
        """
        # Check exact filename matches first (highest priority)
        exact_priority_mapping = [
            ("requirements.lock", "requirements"),
            ("poetry.lock", "poetry-lock"),
            ("Pipfile.lock", "pipfile-lock"),
            ("requirements.txt", "requirements")
        ]
        
        for filename, format_name in exact_priority_mapping:
            if filename in available_files:
                return filename, format_name
        
        # Check for flexible requirements file names
        for filename in available_files:
            if "requirements" in filename.lower() and filename.endswith(".txt"):
                return filename, "requirements"
        
        # Check for other supported files
        for filename in available_files:
            try:
                format_name = self._detect_format(filename, available_files[filename])
                return filename, format_name
            except ValueError:
                continue
        
        raise ValueError("No supported Python dependency files found")
    
    def can_handle_file(self, filename: str) -> bool:
        """Check if factory can handle the given filename"""
        try:
            self.detector.detect_python_format(filename, "")
            return True
        except ValueError:
            return False