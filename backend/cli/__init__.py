"""
DepScan CLI package - Modular command-line interface
"""
from .scanner import DepScanner
from .formatter import CLIFormatter
from .reports import generate_modern_html_report

__all__ = ['DepScanner', 'CLIFormatter', 'generate_modern_html_report']