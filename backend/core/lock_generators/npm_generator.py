"""
NPM lock file generator for ensuring consistency

Generates package-lock.json files from package.json to ensure consistent
dependency resolution during vulnerability scanning.
"""
import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

from ..temp_file_manager import temp_manager

logger = logging.getLogger(__name__)


class NpmLockGenerator:
    """
    Generator for NPM lock files to ensure consistent dependency resolution
    
    When scanning a package.json file, this generator can create a corresponding
    package-lock.json file by running npm install in a temporary directory.
    This ensures that the vulnerability scan uses the exact same dependency
    tree that would be installed from the package.json.
    """
    
    def __init__(self):
        self._npm_available = None
    
    async def is_npm_available(self) -> bool:
        """
        Check if npm is available on the system
        
        Returns:
            True if npm command is available, False otherwise
        """
        if self._npm_available is not None:
            return self._npm_available
        
        try:
            result = await asyncio.create_subprocess_exec(
                "npm", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            self._npm_available = result.returncode == 0
        except FileNotFoundError:
            self._npm_available = False
        except Exception as e:
            logger.warning(f"Error checking npm availability: {e}")
            self._npm_available = False
        
        return self._npm_available
    
    async def generate_lock_file(self, package_json_content: str, progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        Generate package-lock.json content from package.json content
        
        Args:
            package_json_content: Content of package.json file
            
        Returns:
            Content of generated package-lock.json file, or None if generation failed
            
        Raises:
            RuntimeError: If npm is not available
            ValueError: If package.json content is invalid
        """
        if not await self.is_npm_available():
            raise RuntimeError("npm is not available on this system")
        
        # Validate package.json content
        try:
            package_data = json.loads(package_json_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid package.json content: {e}")
        
        with temp_manager.temp_directory("npm_lock_gen_") as temp_dir:
            # Write package.json to temp directory
            package_json_path = temp_dir / "package.json"
            package_json_path.write_text(package_json_content, encoding='utf-8')
            
            # Run npm install to generate package-lock.json
            try:
                if progress_callback:
                    progress_callback("Running npm install to generate package-lock.json...")
                else:
                    logger.info("Running npm install to generate package-lock.json...")
                
                # Run npm install with --package-lock-only flag for faster execution
                result = await asyncio.create_subprocess_exec(
                    "npm", "install", "--package-lock-only", "--no-audit", "--no-fund",
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    logger.error(f"npm install failed: {stderr.decode()}")
                    return None
                
                # Read the generated package-lock.json
                package_lock_path = temp_dir / "package-lock.json"
                if not package_lock_path.exists():
                    logger.error("package-lock.json was not generated")
                    return None
                
                lock_content = package_lock_path.read_text(encoding='utf-8')
                if progress_callback:
                    progress_callback("Successfully generated package-lock.json")
                else:
                    logger.info("Successfully generated package-lock.json")
                return lock_content
                
            except Exception as e:
                logger.error(f"Error generating package-lock.json: {e}")
                return None
    
    async def generate_from_directory(self, repo_path: Path) -> Optional[Path]:
        """
        Generate package-lock.json in an existing repository directory
        
        Args:
            repo_path: Path to repository containing package.json
            
        Returns:
            Path to generated package-lock.json file, or None if generation failed
        """
        if not await self.is_npm_available():
            raise RuntimeError("npm is not available on this system")
        
        package_json_path = repo_path / "package.json"
        if not package_json_path.exists():
            raise ValueError(f"package.json not found in {repo_path}")
        
        package_lock_path = repo_path / "package-lock.json"
        
        try:
            logger.info(f"Running npm install in {repo_path} to generate package-lock.json...")
            
            result = await asyncio.create_subprocess_exec(
                "npm", "install", "--package-lock-only", "--no-audit", "--no-fund",
                cwd=repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"npm install failed: {stderr.decode()}")
                return None
            
            if not package_lock_path.exists():
                logger.error("package-lock.json was not generated")
                return None
            
            logger.info("Successfully generated package-lock.json")
            return package_lock_path
            
        except Exception as e:
            logger.error(f"Error generating package-lock.json: {e}")
            return None
    
    async def ensure_lock_file(self, manifest_files: Dict[str, str], progress_callback: Optional[callable] = None) -> Dict[str, str]:
        """
        Ensure package-lock.json exists for package.json files
        
        Args:
            manifest_files: Dict of {filename: content} 
            
        Returns:
            Updated dict with generated lock file if needed
            
        Example:
            files = {"package.json": content}
            result = await generator.ensure_lock_file(files)
            # result = {"package.json": content, "package-lock.json": generated_content}
        """
        result = manifest_files.copy()
        
        # Check if we have package.json but no package-lock.json
        if "package.json" in manifest_files and "package-lock.json" not in manifest_files:
            if progress_callback:
                progress_callback("package.json found without package-lock.json, generating lock file...")
            else:
                logger.info("package.json found without package-lock.json, generating lock file...")
            
            try:
                lock_content = await self.generate_lock_file(manifest_files["package.json"], progress_callback)
                if lock_content:
                    result["package-lock.json"] = lock_content
                    if progress_callback:
                        progress_callback("Successfully added generated package-lock.json")
                    else:
                        logger.info("Successfully added generated package-lock.json")
                else:
                    logger.warning("Failed to generate package-lock.json, proceeding with package.json only")
            except Exception as e:
                logger.warning(f"Error generating package-lock.json: {e}, proceeding with package.json only")
        
        return result


# Global NPM lock generator instance
npm_lock_generator = NpmLockGenerator()