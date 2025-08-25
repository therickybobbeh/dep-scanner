"""
Rate limiting service for API endpoints
"""
import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from ..config import settings


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""
    
    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._max_requests = 60  # requests per window
        self._window_seconds = 60  # 1 minute window
    
    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Use X-Forwarded-For header if behind proxy, otherwise use client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_requests(self, client_id: str) -> None:
        """Remove requests older than the time window"""
        if client_id not in self._requests:
            return
            
        current_time = time.time()
        self._requests[client_id] = [
            req_time for req_time in self._requests[client_id]
            if current_time - req_time < self._window_seconds
        ]
    
    def is_allowed(self, request: Request) -> bool:
        """Check if request is allowed based on rate limits"""
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Initialize client requests list if not exists
        if client_id not in self._requests:
            self._requests[client_id] = []
        
        # Clean up old requests
        self._cleanup_old_requests(client_id)
        
        # Check if limit exceeded
        if len(self._requests[client_id]) >= self._max_requests:
            return False
        
        # Add current request
        self._requests[client_id].append(current_time)
        return True
    
    def get_remaining_requests(self, request: Request) -> Tuple[int, int]:
        """Get remaining requests and reset time"""
        client_id = self._get_client_id(request)
        self._cleanup_old_requests(client_id)
        
        remaining = max(0, self._max_requests - len(self._requests.get(client_id, [])))
        reset_time = int(time.time()) + self._window_seconds
        
        return remaining, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request):
    """Rate limiting dependency for FastAPI endpoints"""
    if not rate_limiter.is_allowed(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    # Add rate limit headers
    remaining, reset_time = rate_limiter.get_remaining_requests(request)
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = reset_time