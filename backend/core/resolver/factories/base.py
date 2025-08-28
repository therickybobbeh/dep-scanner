"""Base factory for dependency parsers"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Set
from ..base import FileFormatDetector, DependencyParser


class BaseParserFactory(ABC):
    """
    Abstract base factory for creating dependency parsers
    
    Provides common functionality for parser factories including:
    - Format detection
    - Parser management
    - Error handling
    - Format priority handling
    """
    
    def __init__(self):
        self.detector = FileFormatDetector()
        self._parsers: Dict[str, any] = {}
        self._initialize_parsers()
    
    @abstractmethod
    def _initialize_parsers(self) -> None:
        """Initialize the parsers dictionary - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def _detect_format(self, filename: str, content: str) -> str:
        """Detect the format of the dependency file - must be implemented by subclasses"""
        pass
    
    def get_parser(self, filename: str, content: str = "") -> DependencyParser:
        """
        Get appropriate parser for dependency file
        
        Args:
            filename: Name of the dependency file
            content: File content (used for format detection)
            
        Returns:
            Parser instance for the detected format
            
        Raises:
            ValueError: If format is not supported
        """
        try:
            format_name = self._detect_format(filename, content)
            return self._get_parser_for_format(format_name, content)
        except (ValueError, KeyError) as e:
            raise ValueError(f"No parser available for {filename}: {e}")
    
    @abstractmethod
    def _get_parser_for_format(self, format_name: str, content: str = "") -> DependencyParser:
        """Get the parser for a specific format - must be implemented by subclasses"""
        pass
    
    def detect_best_format(self, manifest_files: Dict[str, str]) -> Optional[str]:
        """
        Detect the best format from available manifest files
        
        Args:
            manifest_files: Dict of filename -> content
            
        Returns:
            Best format name or None if no supported format found
        """
        if not manifest_files:
            return None
        
        # Get format priority from subclass
        format_priority = self._get_format_priority()
        
        available_files = set(manifest_files.keys())
        
        # Check formats in priority order
        for priority_file in format_priority:
            if priority_file in available_files:
                return priority_file
        
        # Fallback to any available supported file
        for filename in manifest_files:
            try:
                self._detect_format(filename, manifest_files[filename])
                return filename
            except (ValueError, KeyError):
                continue
        
        return None
    
    @abstractmethod
    def _get_format_priority(self) -> list:
        """Return the priority order of formats - must be implemented by subclasses"""
        pass
    
    def get_supported_formats(self) -> Set[str]:
        """Get set of supported file formats"""
        return self._get_supported_formats()
    
    @abstractmethod
    def _get_supported_formats(self) -> Set[str]:
        """Return set of supported formats - must be implemented by subclasses"""
        pass