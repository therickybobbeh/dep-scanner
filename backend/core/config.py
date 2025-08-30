"""
Configuration management for DepScan

Centralized configuration handling with environment variable support,
security best practices, and production/development modes.
"""

import os
import logging
from pathlib import Path
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    APP_NAME: str = "DepScan"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API settings
    API_HOST: str = Field(default="127.0.0.1", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_RELOAD: bool = Field(default=False, env=["API_RELOAD", "RELOAD"])  # Support both env vars
    
    # Transitive resolution settings
    ENABLE_TRANSITIVE_RESOLUTION: bool = Field(default=False, env="ENABLE_TRANSITIVE_RESOLUTION")
    MAX_TRANSITIVE_DEPTH: int = Field(default=10, env="MAX_TRANSITIVE_DEPTH")
    MAX_CONCURRENT_REQUESTS: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    
    # OSV.dev API settings
    OSV_API_URL: str = Field(default="https://api.osv.dev", env="OSV_API_URL")
    OSV_RATE_LIMIT_CALLS: int = Field(default=100, env="OSV_RATE_LIMIT_CALLS")
    OSV_RATE_LIMIT_PERIOD: int = Field(default=60, env="OSV_RATE_LIMIT_PERIOD")
    
    # Security settings  
    ALLOWED_HOSTS: str = Field(default="localhost,127.0.0.1,127.0.0.1:8000,localhost:8000,0.0.0.0", env="ALLOWED_HOSTS")
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173", env="CORS_ORIGINS")
    MAX_REQUEST_SIZE: int = Field(default=16777216, env="MAX_REQUEST_SIZE")  # 16MB
    ENABLE_SECURITY_HEADERS: bool = Field(default=True, env="ENABLE_SECURITY_HEADERS")
    ENABLE_RATE_LIMITING: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    
    # Paths
    DATA_DIR: Path = Field(default=Path("data"), env="DATA_DIR")
    LOGS_DIR: Path = Field(default=Path("logs"), env="LOGS_DIR")
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
    
    @property
    def allowed_hosts_list(self) -> list[str]:
        """Parse ALLOWED_HOSTS string into a list"""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(',')]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


def setup_logging(settings: Settings) -> None:
    """Configure logging for the application."""
    
    # Create logs directory if it doesn't exist and filesystem is writable
    try:
        settings.LOGS_DIR.mkdir(exist_ok=True)
        file_logging_enabled = True
    except OSError as e:
        # Handle read-only filesystems or permission issues
        print(f"Warning: Cannot create logs directory ({e}). File logging disabled.")
        file_logging_enabled = False
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='\n%(levelname)s: %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter if not settings.DEBUG else detailed_formatter)
    root_logger.addHandler(console_handler)
    
    # File handlers (only if filesystem is writable)
    if file_logging_enabled:
        # File handler for warnings and errors
        file_handler = logging.FileHandler(
            settings.LOGS_DIR / "depscan.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Separate debug log in debug mode
        if settings.DEBUG:
            debug_handler = logging.FileHandler(
                settings.LOGS_DIR / "depscan-debug.log",
                encoding='utf-8'
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(debug_handler)
    
    # Configure third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


# Global settings instance
settings = Settings()

# Setup logging when module is imported
setup_logging(settings)