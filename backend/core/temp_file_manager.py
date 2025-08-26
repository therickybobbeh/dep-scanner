"""
Temporary file and directory management for DepScan

Handles creation, management, and cleanup of temporary files and directories
used during dependency scanning operations.
"""
import os
import tempfile
import shutil
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Dict, Optional

logger = logging.getLogger(__name__)


class TempFileManager:
    """
    Manager for temporary files and directories used during scanning
    
    Provides safe creation and automatic cleanup of temporary resources.
    """
    
    def __init__(self):
        self._temp_dirs: Dict[str, Path] = {}
        self._temp_files: Dict[str, Path] = {}
    
    @contextmanager
    def temp_directory(self, prefix: str = "depscan_") -> Generator[Path, None, None]:
        """
        Create a temporary directory with automatic cleanup
        
        Args:
            prefix: Prefix for the temporary directory name
            
        Yields:
            Path to the temporary directory
            
        Example:
            with temp_manager.temp_directory("npm_install_") as temp_dir:
                # Use temp_dir for operations
                package_json_path = temp_dir / "package.json"
                # Directory is automatically cleaned up on exit
        """
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
            logger.debug(f"Created temp directory: {temp_dir}")
            yield temp_dir
        finally:
            if temp_dir and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    @contextmanager
    def temp_file(self, suffix: str = "", prefix: str = "depscan_") -> Generator[Path, None, None]:
        """
        Create a temporary file with automatic cleanup
        
        Args:
            suffix: File extension (e.g., ".json", ".txt")
            prefix: Prefix for the temporary file name
            
        Yields:
            Path to the temporary file
        """
        temp_file = None
        try:
            fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
            os.close(fd)  # Close the file descriptor
            temp_file = Path(temp_path)
            logger.debug(f"Created temp file: {temp_file}")
            yield temp_file
        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file {temp_file}: {e}")
    
    def write_manifest_files(self, temp_dir: Path, manifest_files: Dict[str, str]) -> Dict[str, Path]:
        """
        Write manifest files to a temporary directory
        
        Args:
            temp_dir: Path to temporary directory
            manifest_files: Dict of {filename: content}
            
        Returns:
            Dict mapping filenames to their temporary file paths
            
        Example:
            files = {"package.json": json_content, "requirements.txt": req_content}
            file_paths = manager.write_manifest_files(temp_dir, files)
            # file_paths = {"package.json": temp_dir/package.json, ...}
        """
        file_paths = {}
        
        for filename, content in manifest_files.items():
            file_path = temp_dir / filename
            try:
                file_path.write_text(content, encoding='utf-8')
                file_paths[filename] = file_path
                logger.debug(f"Wrote manifest file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to write manifest file {filename}: {e}")
                raise
        
        return file_paths
    
    def copy_file_to_temp(self, source_path: Path, temp_dir: Path, filename: Optional[str] = None) -> Path:
        """
        Copy a file to a temporary directory
        
        Args:
            source_path: Path to source file
            temp_dir: Destination temporary directory
            filename: Optional custom filename (uses source filename if not provided)
            
        Returns:
            Path to the copied file in temp directory
        """
        if filename is None:
            filename = source_path.name
        
        dest_path = temp_dir / filename
        try:
            shutil.copy2(source_path, dest_path)
            logger.debug(f"Copied {source_path} to {dest_path}")
            return dest_path
        except Exception as e:
            logger.error(f"Failed to copy {source_path} to {dest_path}: {e}")
            raise
    
    def ensure_directory_exists(self, directory: Path) -> Path:
        """
        Ensure a directory exists, creating it if necessary
        
        Args:
            directory: Directory path to ensure exists
            
        Returns:
            Path to the directory
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")
            raise


# Global temp file manager instance
temp_manager = TempFileManager()