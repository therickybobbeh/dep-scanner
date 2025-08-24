"""Factory for JavaScript dependency parsers"""
from ..base import FileFormatDetector, DependencyParser
from ..parsers.javascript import (
    PackageLockV1Parser,
    PackageLockV2Parser, 
    YarnLockParser,
    PackageJsonParser,
    NpmLsParser
)


class JavaScriptParserFactory:
    """
    Factory for creating appropriate JavaScript dependency parsers
    
    Handles format detection and parser selection based on file type
    and content analysis.
    """
    
    def __init__(self):
        self.detector = FileFormatDetector()
        self._parsers = {
            "package-lock": {
                "v1": PackageLockV1Parser(),
                "v2": PackageLockV2Parser()
            },
            "yarn-lock": YarnLockParser(),
            "package-json": PackageJsonParser(),
            "npm-ls": NpmLsParser()
        }
    
    def get_parser(self, filename: str, content: str = "") -> DependencyParser:
        """
        Get appropriate parser for JavaScript dependency file
        
        Args:
            filename: Name of the dependency file
            content: File content (used for format detection)
            
        Returns:
            Parser instance for the detected format
            
        Raises:
            ValueError: If format is not supported
        """
        try:
            format_name = self.detector.detect_js_format(filename, content)
            
            if format_name == "package-lock":
                # Detect package-lock.json version
                version = self._detect_package_lock_version(content)
                return self._parsers["package-lock"][version]
            
            elif format_name == "yarn-lock":
                return self._parsers["yarn-lock"]
            
            elif format_name == "package-json":
                return self._parsers["package-json"]
            
            else:
                raise ValueError(f"Unsupported JavaScript format: {format_name}")
                
        except Exception as e:
            raise ValueError(f"Could not determine JavaScript parser for {filename}: {e}")
    
    def get_parser_by_format(self, format_name: str, **kwargs) -> DependencyParser:
        """
        Get parser by explicit format name
        
        Args:
            format_name: Explicit format identifier
            **kwargs: Additional format-specific options
            
        Returns:
            Parser instance
        """
        if format_name == "npm-ls":
            return self._parsers["npm-ls"]
        elif format_name == "package-lock-v1":
            return self._parsers["package-lock"]["v1"]
        elif format_name == "package-lock-v2":
            return self._parsers["package-lock"]["v2"]
        elif format_name == "yarn-lock":
            return self._parsers["yarn-lock"]
        elif format_name == "package-json":
            return self._parsers["package-json"]
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
            ("package-lock.json", "package-lock"),
            ("yarn.lock", "yarn-lock"),
            ("package.json", "package-json")
        ]
        
        for filename, format_name in priority_order:
            if filename in available_files:
                return filename, format_name
        
        raise ValueError("No supported JavaScript dependency files found")
    
    def _detect_package_lock_version(self, content: str) -> str:
        """
        Detect package-lock.json version from content
        
        Args:
            content: package-lock.json content
            
        Returns:
            Version identifier ("v1" or "v2")
        """
        if not content.strip():
            return "v1"  # Default to v1 if empty
        
        try:
            import json
            data = json.loads(content)
            lockfile_version = data.get("lockfileVersion", 1)
            
            if lockfile_version >= 2:
                return "v2"
            else:
                return "v1"
                
        except json.JSONDecodeError:
            return "v1"  # Default to v1 if parsing fails
    
    def get_supported_formats(self) -> list[str]:
        """Get list of all supported JavaScript formats"""
        return [
            "package-lock.json",
            "yarn.lock", 
            "package.json"
        ]
    
    def can_handle_file(self, filename: str) -> bool:
        """Check if factory can handle the given filename"""
        try:
            self.detector.detect_js_format(filename, "")
            return True
        except ValueError:
            return False