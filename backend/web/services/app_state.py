"""Simplified application state management"""
from fastapi import WebSocket

from ...core.models import ScanProgress, Report


class AppState:
    """Simplified application state container for web service state"""
    
    def __init__(self):
        # Scan management  
        self.scan_jobs: dict[str, ScanProgress] = {}
        self.scan_reports: dict[str, Report] = {}  # Fixed naming consistency
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def cleanup(self):
        """Clean up resources on shutdown"""
        # Close all WebSocket connections
        for connections_list in self.active_connections.values():
            for ws in connections_list:
                try:
                    await ws.close()
                except:
                    pass
        
        # Clear state
        self.scan_jobs.clear()
        self.scan_reports.clear()
        self.active_connections.clear()


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Dependency injection function for FastAPI"""
    return app_state