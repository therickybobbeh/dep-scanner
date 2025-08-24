"""Application state management for dependency injection"""
from typing import Any
from fastapi import WebSocket

from ..models import ScanProgress, Report
from ..resolver import PythonResolver, JavaScriptResolver
from ..scanner import OSVScanner


class AppState:
    """Application state container for dependency injection"""
    
    def __init__(self):
        # Scan management
        self.scan_jobs: dict[str, ScanProgress] = {}
        self.scan_results: dict[str, Report] = {}
        self.active_connections: dict[str, list[WebSocket]] = {}
        
        # Core services
        self.python_resolver = PythonResolver()
        self.js_resolver = JavaScriptResolver()
        self.osv_scanner = OSVScanner()
    
    async def cleanup(self):
        """Clean up resources on shutdown"""
        await self.osv_scanner.close()
        
        # Close all WebSocket connections
        for connections_list in self.active_connections.values():
            for ws in connections_list:
                try:
                    await ws.close()
                except:
                    pass
        
        # Clear state
        self.scan_jobs.clear()
        self.scan_results.clear()
        self.active_connections.clear()


# Global app state instance
app_state = AppState()


def get_app_state() -> AppState:
    """Dependency injection function for FastAPI"""
    return app_state