"""
Lock file generators for ensuring consistency between manifest and lock files

This package provides utilities to generate lock files from manifest files
to ensure consistent dependency resolution during vulnerability scanning.
"""

from .npm_generator import NpmLockGenerator
from .python_generator import PythonLockGenerator

__all__ = ["NpmLockGenerator", "PythonLockGenerator"]