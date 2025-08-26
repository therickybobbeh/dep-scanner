"""
Python lock file generator for ensuring consistency

Generates lock files from Python manifest files to ensure consistent
dependency resolution during vulnerability scanning.
"""
import asyncio
import json
import logging
import subprocess
import tempfile
import toml
from pathlib import Path
from typing import Dict, Optional, List

from ..temp_file_manager import temp_manager

logger = logging.getLogger(__name__)


class PythonLockGenerator:
    """
    Generator for Python lock files to ensure consistent dependency resolution
    
    Supports generating lock files for:
    - requirements.txt → requirements.lock (using pip-tools)
    - pyproject.toml → poetry.lock (using poetry)
    - pyproject.toml → requirements.lock (using pip-tools for non-poetry projects)
    """
    
    def __init__(self):
        self._pip_tools_available = None
        self._poetry_available = None
    
    async def is_pip_tools_available(self) -> bool:
        """Check if pip-tools (pip-compile) is available"""
        if self._pip_tools_available is not None:
            return self._pip_tools_available
        
        try:
            result = await asyncio.create_subprocess_exec(
                "pip-compile", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            self._pip_tools_available = result.returncode == 0
        except FileNotFoundError:
            self._pip_tools_available = False
        except Exception as e:
            logger.warning(f"Error checking pip-tools availability: {e}")
            self._pip_tools_available = False
        
        return self._pip_tools_available
    
    async def is_poetry_available(self) -> bool:
        """Check if poetry is available"""
        if self._poetry_available is not None:
            return self._poetry_available
        
        try:
            result = await asyncio.create_subprocess_exec(
                "poetry", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            self._poetry_available = result.returncode == 0
        except FileNotFoundError:
            self._poetry_available = False
        except Exception as e:
            logger.warning(f"Error checking poetry availability: {e}")
            self._poetry_available = False
        
        return self._poetry_available
    
    def _is_poetry_project(self, pyproject_content: str) -> bool:
        """Check if pyproject.toml is a Poetry project"""
        try:
            data = toml.loads(pyproject_content)
            return "tool" in data and "poetry" in data["tool"]
        except Exception:
            return False
    
    async def generate_requirements_lock(self, requirements_content: str) -> Optional[str]:
        """
        Generate requirements.lock from requirements.txt using pip-compile
        
        Args:
            requirements_content: Content of requirements.txt
            
        Returns:
            Content of generated requirements.lock, or None if generation failed
        """
        if not await self.is_pip_tools_available():
            logger.warning("pip-tools not available, cannot generate requirements.lock")
            return None
        
        with temp_manager.temp_directory("pip_compile_") as temp_dir:
            # Write requirements.txt
            req_path = temp_dir / "requirements.in"  # pip-compile expects .in extension
            req_path.write_text(requirements_content, encoding='utf-8')
            
            try:
                logger.info("Running pip-compile to generate requirements.lock...")
                
                result = await asyncio.create_subprocess_exec(
                    "pip-compile", 
                    str(req_path),
                    "--output-file", str(temp_dir / "requirements.lock"),
                    "--quiet",
                    "--no-emit-index-url",
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    logger.error(f"pip-compile failed: {stderr.decode()}")
                    return None
                
                lock_path = temp_dir / "requirements.lock"
                if not lock_path.exists():
                    logger.error("requirements.lock was not generated")
                    return None
                
                lock_content = lock_path.read_text(encoding='utf-8')
                logger.info("Successfully generated requirements.lock")
                return lock_content
                
            except Exception as e:
                logger.error(f"Error generating requirements.lock: {e}")
                return None
    
    async def generate_poetry_lock(self, pyproject_content: str) -> Optional[str]:
        """
        Generate poetry.lock from pyproject.toml using poetry
        
        Args:
            pyproject_content: Content of pyproject.toml
            
        Returns:
            Content of generated poetry.lock, or None if generation failed
        """
        if not await self.is_poetry_available():
            logger.warning("Poetry not available, cannot generate poetry.lock")
            return None
        
        if not self._is_poetry_project(pyproject_content):
            logger.info("pyproject.toml is not a Poetry project")
            return None
        
        with temp_manager.temp_directory("poetry_lock_") as temp_dir:
            # Write pyproject.toml
            pyproject_path = temp_dir / "pyproject.toml"
            pyproject_path.write_text(pyproject_content, encoding='utf-8')
            
            try:
                logger.info("Running poetry lock to generate poetry.lock...")
                
                result = await asyncio.create_subprocess_exec(
                    "poetry", "lock", "--no-update",
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await result.communicate()
                
                if result.returncode != 0:
                    logger.error(f"poetry lock failed: {stderr.decode()}")
                    return None
                
                lock_path = temp_dir / "poetry.lock"
                if not lock_path.exists():
                    logger.error("poetry.lock was not generated")
                    return None
                
                lock_content = lock_path.read_text(encoding='utf-8')
                logger.info("Successfully generated poetry.lock")
                return lock_content
                
            except Exception as e:
                logger.error(f"Error generating poetry.lock: {e}")
                return None
    
    async def generate_pyproject_requirements_lock(self, pyproject_content: str) -> Optional[str]:
        """
        Generate requirements.lock from pyproject.toml using pip-tools
        
        This is useful for pyproject.toml files that aren't Poetry projects
        but use PEP 621 dependencies specification.
        
        Args:
            pyproject_content: Content of pyproject.toml
            
        Returns:
            Content of generated requirements.lock, or None if generation failed
        """
        if not await self.is_pip_tools_available():
            logger.warning("pip-tools not available, cannot generate requirements.lock from pyproject.toml")
            return None
        
        try:
            # Parse pyproject.toml and extract dependencies
            data = toml.loads(pyproject_content)
            
            dependencies = []
            if "project" in data and "dependencies" in data["project"]:
                dependencies = data["project"]["dependencies"]
            elif "build-system" in data and "requires" in data["build-system"]:
                dependencies = data["build-system"]["requires"]
            
            if not dependencies:
                logger.warning("No dependencies found in pyproject.toml")
                return None
            
            # Create a temporary requirements.txt from dependencies
            requirements_content = "\n".join(dependencies)
            return await self.generate_requirements_lock(requirements_content)
            
        except Exception as e:
            logger.error(f"Error processing pyproject.toml: {e}")
            return None
    
    async def ensure_lock_files(self, manifest_files: Dict[str, str]) -> Dict[str, str]:
        """
        Ensure lock files exist for Python manifest files
        
        Args:
            manifest_files: Dict of {filename: content}
            
        Returns:
            Updated dict with generated lock files if possible
        """
        result = manifest_files.copy()
        
        # Handle requirements.txt → requirements.lock
        if "requirements.txt" in manifest_files and "requirements.lock" not in manifest_files:
            logger.info("requirements.txt found without lock file, attempting to generate...")
            try:
                lock_content = await self.generate_requirements_lock(manifest_files["requirements.txt"])
                if lock_content:
                    result["requirements.lock"] = lock_content
                    logger.info("Successfully added generated requirements.lock")
            except Exception as e:
                logger.warning(f"Failed to generate requirements.lock: {e}")
        
        # Handle pyproject.toml → poetry.lock (for Poetry projects)
        if "pyproject.toml" in manifest_files:
            if "poetry.lock" not in manifest_files:
                logger.info("pyproject.toml found without poetry.lock, checking if Poetry project...")
                try:
                    lock_content = await self.generate_poetry_lock(manifest_files["pyproject.toml"])
                    if lock_content:
                        result["poetry.lock"] = lock_content
                        logger.info("Successfully added generated poetry.lock")
                    else:
                        # Try pip-tools approach for non-Poetry pyproject.toml
                        logger.info("Not a Poetry project, trying pip-tools approach...")
                        lock_content = await self.generate_pyproject_requirements_lock(manifest_files["pyproject.toml"])
                        if lock_content:
                            result["requirements.lock"] = lock_content
                            logger.info("Successfully added generated requirements.lock from pyproject.toml")
                except Exception as e:
                    logger.warning(f"Failed to generate lock file from pyproject.toml: {e}")
        
        return result


# Global Python lock generator instance
python_lock_generator = PythonLockGenerator()