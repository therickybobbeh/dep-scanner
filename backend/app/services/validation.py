"""
Input validation and sanitization middleware
"""
import re
from typing import Any, Dict
from fastapi import HTTPException, Request
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class InputValidator:
    """Validates and sanitizes user inputs"""
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'/\.\.',
        r'\\\.\.',
        r'\.\.%2f',
        r'\.\.%5c',
        r'%2e%2e%2f',
        r'%2e%2e%5c'
    ]
    
    # Dangerous characters in paths
    DANGEROUS_PATH_CHARS = ['<', '>', '|', '*', '?', '"', ':', ';']
    
    @classmethod
    def validate_path(cls, path: str) -> str:
        """Validate and sanitize file paths"""
        if not path or not isinstance(path, str):
            raise HTTPException(status_code=400, detail="Invalid path parameter")
        
        # Check for path traversal attempts
        path_lower = path.lower()
        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path_lower, re.IGNORECASE):
                logger.warning(f"Path traversal attempt detected: {path}")
                raise HTTPException(status_code=400, detail="Invalid path: path traversal not allowed")
        
        # Check for dangerous characters
        for char in cls.DANGEROUS_PATH_CHARS:
            if char in path:
                logger.warning(f"Dangerous character in path: {path}")
                raise HTTPException(status_code=400, detail=f"Invalid path: character '{char}' not allowed")
        
        # Normalize path
        try:
            normalized_path = Path(path).resolve()
            return str(normalized_path)
        except (OSError, ValueError) as e:
            logger.warning(f"Path normalization failed for {path}: {e}")
            raise HTTPException(status_code=400, detail="Invalid path format")
    
    @classmethod
    def validate_job_id(cls, job_id: str) -> str:
        """Validate job ID format"""
        if not job_id or not isinstance(job_id, str):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        # Job IDs should be UUIDs - validate format
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        if not uuid_pattern.match(job_id):
            logger.warning(f"Invalid job ID format: {job_id}")
            raise HTTPException(status_code=400, detail="Invalid job ID format")
        
        return job_id
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail="Invalid string parameter")
        
        # Trim whitespace
        value = value.strip()
        
        # Check length
        if len(value) > max_length:
            raise HTTPException(status_code=400, detail=f"String too long (max {max_length} characters)")
        
        # Remove null bytes and control characters
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        return value


async def validate_scan_request(request: Request, call_next):
    """Middleware to validate scan requests"""
    if request.url.path.startswith("/scan") and request.method == "POST":
        # The request body will be validated by Pydantic models
        # This middleware handles additional security validation
        logger.debug(f"Validating scan request from {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    return response


async def validate_path_parameters(request: Request, call_next):
    """Middleware to validate path parameters"""
    # Validate job_id in path parameters
    if "job_id" in request.path_params:
        job_id = request.path_params["job_id"]
        validated_job_id = InputValidator.validate_job_id(job_id)
        request.path_params["job_id"] = validated_job_id
    
    response = await call_next(request)
    return response