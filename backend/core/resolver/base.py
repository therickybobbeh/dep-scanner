"""Base classes and interfaces for dependency parsing"""
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from ..models import Dep


@runtime_checkable
class DependencyParser(Protocol):
    """Protocol for dependency parsers"""
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """Parse dependency content and return list of dependencies"""
        ...
    
    @property
    def supported_formats(self) -> list[str]:
        """Return list of supported file formats"""
        ...


class BaseDependencyParser(ABC):
    """Abstract base class for dependency parsers"""
    
    def __init__(self, ecosystem: str):
        self.ecosystem = ecosystem
    
    @abstractmethod
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """Parse dependency content and return list of dependencies"""
        pass
    
    @property
    @abstractmethod 
    def supported_formats(self) -> list[str]:
        """Return list of supported file formats"""
        pass
    
    def _create_dependency(
        self, 
        name: str, 
        version: str, 
        path: list[str] | None = None,
        is_direct: bool = True,
        is_dev: bool = False
    ) -> Dep:
        """Helper method to create a Dep object with consistent defaults"""
        if path is None:
            path = [name]
        
        return Dep(
            name=name,
            version=version,
            ecosystem=self.ecosystem,
            path=path,
            is_direct=is_direct,
            is_dev=is_dev
        )


class ParseError(Exception):
    """Raised when parsing fails"""
    
    def __init__(self, format_name: str, original_error: Exception):
        self.format_name = format_name
        self.original_error = original_error
        super().__init__(f"Failed to parse {format_name}: {original_error}")


class FileFormatDetector:
    """Utility for detecting file formats from content and filenames"""
    
    @staticmethod
    def detect_js_format(filename: str, content: str) -> str:
        """Detect JavaScript dependency file format"""
        if filename == "package-lock.json":
            return "package-lock"
        elif filename == "yarn.lock":
            return "yarn-lock"
        elif filename == "package.json":
            return "package-json"
        else:
            raise ValueError(f"Unknown JavaScript format: {filename}")
    
    @staticmethod
    def detect_python_format(filename: str, content: str) -> str:
        """Detect Python dependency file format"""
        if filename == "poetry.lock":
            return "poetry-lock"
        elif filename == "Pipfile.lock":
            return "pipfile-lock"
        elif filename == "requirements.txt":
            return "requirements"
        elif filename == "pyproject.toml":
            return "pyproject"
        elif filename == "Pipfile":
            return "pipfile"
        else:
            raise ValueError(f"Unknown Python format: {filename}")
    
    @staticmethod
    def get_format_priority(format_name: str) -> int:
        """Get priority for format (lower = higher priority)"""
        # Lockfiles have highest priority
        lockfile_priority = {
            "package-lock": 1,
            "yarn-lock": 2,
            "poetry-lock": 1,
            "pipfile-lock": 2,
        }
        
        # Manifest files have lower priority
        manifest_priority = {
            "package-json": 10,
            "requirements": 10,
            "pyproject": 11,
            "pipfile": 12,
        }
        
        return lockfile_priority.get(format_name, manifest_priority.get(format_name, 99))