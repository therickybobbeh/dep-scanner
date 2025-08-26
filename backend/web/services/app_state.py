"""Simplified application state management"""
from typing import Dict, Any
from ...core.models import ScanProgress


class AppState:
    """Simplified application state for CLI-based scanning"""
    
    def __init__(self):
        # Simple scan management
        self.scan_jobs: dict[str, ScanProgress] = {}
        self.scan_reports: dict[str, Dict[str, Any]] = {}  # Store CLI JSON directly
    
    async def cleanup(self):
        """Clean up resources on shutdown"""
        self.scan_jobs.clear()
        self.scan_reports.clear()


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Dependency injection function for FastAPI"""
    return app_state