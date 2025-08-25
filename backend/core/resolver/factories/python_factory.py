"""Factory for Python dependency parsers"""
from ..base import FileFormatDetector, DependencyParser
from ..parsers.python import (
    PoetryLockParser,
    PipfileLockParser,
    RequirementsParser,
    PyprojectParser,
    PipfileParser
)


class PythonParserFactory:
    """
    Factory for creating appropriate Python dependency parsers
    
    Handles format detection and parser selection based on file type
    and content analysis.
    """
    
    def __init__(self):
        self.detector = FileFormatDetector()
        self._parsers = {
            "poetry-lock": PoetryLockParser(),
            "pipfile-lock": PipfileLockParser(),
            "requirements": RequirementsParser(),
            "pyproject": PyprojectParser(),
            "pipfile": PipfileParser()
        }
    
    def get_parser(self, filename: str, content: str = "") -> DependencyParser:
        """
        Get appropriate parser for Python dependency file
        
        Args:
            filename: Name of the dependency file
            content: File content (used for additional validation)
            
        Returns:
            Parser instance for the detected format
            
        Raises:
            ValueError: If format is not supported
        """
        try:
            format_name = self.detector.detect_python_format(filename, content)
            
            if format_name in self._parsers:
                return self._parsers[format_name]
            else:
                raise ValueError(f"Unsupported Python format: {format_name}")
                
        except Exception as e:
            raise ValueError(f"Could not determine Python parser for {filename}: {e}")
    
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
        
        Args:
            available_files: Dict of {filename: content}
            
        Returns:
            Tuple of (best_filename, format_name)
        """
        # Priority order: lockfiles first, then manifests
        priority_order = [
            ("poetry.lock", "poetry-lock"),
            ("Pipfile.lock", "pipfile-lock"),
            ("pyproject.toml", "pyproject"),
            ("Pipfile", "pipfile"),
            ("requirements.txt", "requirements")
        ]
        
        for filename, format_name in priority_order:
            if filename in available_files:
                return filename, format_name
        
        # Check for dev requirements files as fallback
        for filename in available_files:
            if filename.endswith("requirements.txt"):
                return filename, "requirements"
        
        raise ValueError("No supported Python dependency files found")
    
    def detect_requirements_files(self, available_files: dict[str, str]) -> list[tuple[str, bool]]:
        """
        Detect all requirements.txt files and classify them
        
        Args:
            available_files: Dict of {filename: content}
            
        Returns:
            List of (filename, is_dev) tuples
        """
        requirements_files = []
        
        for filename in available_files:
            if filename.endswith("requirements.txt") or filename.endswith(".txt"):
                parser = self._parsers["requirements"]
                is_dev = parser.detect_dev_requirements(filename)
                requirements_files.append((filename, is_dev))
        
        return requirements_files
    
    def get_supported_formats(self) -> list[str]:
        """Get list of all supported Python formats"""
        return [
            "poetry.lock",
            "Pipfile.lock",
            "pyproject.toml",
            "Pipfile",
            "requirements.txt"
        ]
    
    def can_handle_file(self, filename: str) -> bool:
        """Check if factory can handle the given filename"""
        try:
            self.detector.detect_python_format(filename, "")
            return True
        except ValueError:
            return False
    
    def get_format_priority(self, format_name: str) -> int:
        """
        Get priority for format (lower = higher priority)
        
        Args:
            format_name: Format identifier
            
        Returns:
            Priority value (lower = higher priority)
        """
        return self.detector.get_format_priority(format_name)