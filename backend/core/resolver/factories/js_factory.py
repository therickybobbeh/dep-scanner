"""Factory for JavaScript dependency parsers"""
from __future__ import annotations

from typing import Dict, Optional, Set
import json
from .base import BaseParserFactory
from ..base import DependencyParser
from ..parsers.javascript import (
    PackageLockV1Parser,
    PackageLockV2Parser, 
    YarnLockParser,
    PackageJsonParser,
    NpmLsParser
)


class JavaScriptParserFactory(BaseParserFactory):
    """
    Factory for creating appropriate JavaScript dependency parsers
    
    Simplified factory that focuses on the core parsers needed for 
    dependency resolution.
    """
    
    def _initialize_parsers(self) -> None:
        """Initialize JavaScript-specific parsers"""
        self._parsers = {
            "package-lock": {
                "v1": PackageLockV1Parser(),
                "v2": PackageLockV2Parser()
            },
            "yarn-lock": YarnLockParser(),
            "package-json": PackageJsonParser(),
            "npm-ls": NpmLsParser()
        }
    
    def _detect_format(self, filename: str, content: str) -> str:
        """Detect JavaScript dependency file format"""
        return self.detector.detect_js_format(filename, content)
    
    def _get_parser_for_format(self, format_name: str, content: str = "") -> DependencyParser:
        """Get parser for specific JavaScript format"""
        if format_name == "package-lock":
            # Detect package-lock.json version
            version = self._detect_package_lock_version(content)
            return self._parsers["package-lock"][version]
        elif format_name in self._parsers:
            return self._parsers[format_name]
        else:
            raise ValueError(f"No parser available for format: {format_name}")
    
    def _get_format_priority(self) -> list:
        """Return JavaScript format priority order"""
        return [
            "package-lock.json",  # NPM lockfile (most accurate)
            "yarn.lock",          # Yarn lockfile
            "package.json"        # Package manifest
        ]
    
    def _get_supported_formats(self) -> Set[str]:
        """Return set of supported JavaScript formats"""
        return {
            "package-lock.json",
            "yarn.lock",
            "package.json"
        }
    
    def get_parser_by_format(self, format_name: str) -> DependencyParser:
        """
        Get parser by explicit format name
        
        Args:
            format_name: Explicit format identifier
            
        Returns:
            Parser instance
        """
        if format_name == "npm-ls":
            return self._parsers["npm-ls"]
        elif format_name == "package-lock-v1":
            return self._parsers["package-lock"]["v1"]
        elif format_name == "package-lock-v2":
            return self._parsers["package-lock"]["v2"]
        elif format_name in self._parsers:
            return self._parsers[format_name]
        else:
            raise ValueError(f"Unknown format: {format_name}")
    
    def detect_best_format(self, available_files: dict[str, str]) -> tuple[str, str]:
        """
        Detect the best format to use from available files
        
        Priority: lockfiles first (most accurate), then manifests
        
        Args:
            available_files: Dict of {filename: content}
            
        Returns:
            Tuple of (best_filename, format_name)
        """
        # Priority order mapping filename to format name
        priority_mapping = [
            ("package-lock.json", "package-lock"),
            ("yarn.lock", "yarn-lock"),
            ("package.json", "package-json")
        ]
        
        for filename, format_name in priority_mapping:
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
            data = json.loads(content)
            lockfile_version = data.get("lockfileVersion", 1)
            
            if lockfile_version >= 2:
                return "v2"
            else:
                return "v1"
                
        except json.JSONDecodeError:
            return "v1"  # Default to v1 if parsing fails
    
    def can_handle_file(self, filename: str) -> bool:
        """Check if factory can handle the given filename"""
        try:
            self.detector.detect_js_format(filename, "")
            return True
        except ValueError:
            return False