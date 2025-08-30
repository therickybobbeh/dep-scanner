"""Simplified application state management"""
from __future__ import annotations

import asyncio
from typing import Dict, Any
from ...core.models import ScanProgress


class AppState:
    """Simplified application state for CLI-based scanning"""
    
    def __init__(self):
        # Simple scan management
        self.scan_jobs: dict[str, ScanProgress] = {}
        self.scan_reports: dict[str, Dict[str, Any]] = {}  # Store CLI JSON directly
        self.scan_tasks: dict[str, asyncio.Task] = {}  # Track background tasks
    
    async def cleanup(self):
        """Clean up resources on shutdown"""
        # Cancel all running scan tasks
        for task in self.scan_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation
        if self.scan_tasks:
            await asyncio.gather(*self.scan_tasks.values(), return_exceptions=True)
        
        self.scan_jobs.clear()
        self.scan_reports.clear()
        self.scan_tasks.clear()


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Dependency injection function for FastAPI"""
    return app_state