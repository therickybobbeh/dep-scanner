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
    Unified Python lock file generator using pip-tools for consistent dependency resolution
    
    Converts all Python dependency formats to requirements.lock for unified processing:
    - requirements.txt → requirements.lock (via pip-compile)
    - poetry.lock + pyproject.toml → requirements.lock (via poetry export + pip-compile)  
    - Pipfile.lock + Pipfile → requirements.lock (via pipenv requirements + pip-compile)
    - pyproject.toml → requirements.lock (via pip-compile for non-poetry projects)
    
    This approach ensures all Python dependency files produce consistent transitive
    dependency resolution using pip-tools, similar to how JavaScript uses package-lock.json.
    """
    
    def __init__(self):
        self._pip_tools_available = None
        self._poetry_available = None
        self._pipenv_available = None
    
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
    
    async def is_pipenv_available(self) -> bool:
        """Check if pipenv is available"""
        if self._pipenv_available is not None:
            return self._pipenv_available
        
        try:
            result = await asyncio.create_subprocess_exec(
                "pipenv", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            self._pipenv_available = result.returncode == 0
        except FileNotFoundError:
            self._pipenv_available = False
        except Exception as e:
            logger.warning(f"Error checking pipenv availability: {e}")
            self._pipenv_available = False
        
        return self._pipenv_available
    
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
    
    async def poetry_lock_to_requirements_lock(self, poetry_lock_content: str, pyproject_content: str = None) -> Optional[str]:
        """
        Convert poetry.lock to requirements.lock using poetry export + pip-compile
        
        Args:
            poetry_lock_content: Content of poetry.lock file
            pyproject_content: Content of pyproject.toml file (needed for poetry export)
            
        Returns:
            Content of generated requirements.lock, or None if conversion failed
        """
        if not await self.is_poetry_available():
            logger.warning("Poetry not available, cannot convert poetry.lock")
            return None
            
        if not await self.is_pip_tools_available():
            logger.warning("pip-tools not available, cannot generate requirements.lock")
            return None
        
        with temp_manager.temp_directory("poetry_to_req_") as temp_dir:
            try:
                # Write poetry.lock and pyproject.toml (both needed for poetry export)
                poetry_lock_path = temp_dir / "poetry.lock"
                poetry_lock_path.write_text(poetry_lock_content, encoding='utf-8')
                
                if pyproject_content:
                    pyproject_path = temp_dir / "pyproject.toml" 
                    pyproject_path.write_text(pyproject_content, encoding='utf-8')
                
                # Step 1: Export poetry.lock to requirements.txt
                logger.info("Converting poetry.lock to requirements.txt...")
                req_path = temp_dir / "requirements.txt"
                
                export_result = await asyncio.create_subprocess_exec(
                    "poetry", "export", "--format", "requirements.txt", 
                    "--output", str(req_path), "--without-hashes",
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await export_result.communicate()
                
                if export_result.returncode != 0:
                    logger.error(f"poetry export failed: {stderr.decode()}")
                    return None
                
                if not req_path.exists():
                    logger.error("requirements.txt was not generated by poetry export")
                    return None
                
                # Step 2: Convert requirements.txt to requirements.lock using pip-compile
                logger.info("Converting requirements.txt to requirements.lock...")
                requirements_content = req_path.read_text(encoding='utf-8')
                return await self.generate_requirements_lock(requirements_content)
                
            except Exception as e:
                logger.error(f"Error converting poetry.lock to requirements.lock: {e}")
                return None
    
    async def pipfile_lock_to_requirements_lock(self, pipfile_lock_content: str, pipfile_content: str = None) -> Optional[str]:
        """
        Convert Pipfile.lock to requirements.lock using pipenv requirements + pip-compile
        
        Args:
            pipfile_lock_content: Content of Pipfile.lock file
            pipfile_content: Content of Pipfile (needed for pipenv requirements)
            
        Returns:
            Content of generated requirements.lock, or None if conversion failed
        """
        if not await self.is_pipenv_available():
            logger.warning("pipenv not available, cannot convert Pipfile.lock")
            return None
            
        if not await self.is_pip_tools_available():
            logger.warning("pip-tools not available, cannot generate requirements.lock")
            return None
        
        with temp_manager.temp_directory("pipfile_to_req_") as temp_dir:
            try:
                # Write Pipfile.lock and Pipfile (both needed for pipenv requirements)
                pipfile_lock_path = temp_dir / "Pipfile.lock"
                pipfile_lock_path.write_text(pipfile_lock_content, encoding='utf-8')
                
                if pipfile_content:
                    pipfile_path = temp_dir / "Pipfile"
                    pipfile_path.write_text(pipfile_content, encoding='utf-8')
                
                # Step 1: Export Pipfile.lock to requirements.txt
                logger.info("Converting Pipfile.lock to requirements.txt...")
                
                req_result = await asyncio.create_subprocess_exec(
                    "pipenv", "requirements", "--exclude-markers",
                    cwd=temp_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await req_result.communicate()
                
                if req_result.returncode != 0:
                    logger.error(f"pipenv requirements failed: {stderr.decode()}")
                    return None
                
                requirements_content = stdout.decode('utf-8').strip()
                if not requirements_content:
                    logger.error("No requirements generated from Pipfile.lock")
                    return None
                
                # Step 2: Convert requirements.txt to requirements.lock using pip-compile
                logger.info("Converting requirements.txt to requirements.lock...")
                return await self.generate_requirements_lock(requirements_content)
                
            except Exception as e:
                logger.error(f"Error converting Pipfile.lock to requirements.lock: {e}")
                return None
    
    async def ensure_requirements_lock(self, manifest_files: Dict[str, str]) -> Dict[str, str]:
        """
        Ensure requirements.lock exists for all Python manifest files using unified pip-tools approach
        
        This is the unified method that converts all Python dependency formats to requirements.lock:
        - requirements.txt → requirements.lock (via pip-compile)  
        - poetry.lock + pyproject.toml → requirements.lock (via poetry export + pip-compile)
        - Pipfile.lock + Pipfile → requirements.lock (via pipenv requirements + pip-compile)
        
        Args:
            manifest_files: Dict of {filename: content}
            
        Returns:
            Updated dict with requirements.lock generated from available files
        """
        result = manifest_files.copy()
        
        # Skip if requirements.lock already exists
        if "requirements.lock" in manifest_files:
            logger.info("requirements.lock already exists, no conversion needed")
            return result
        
        # Priority 1: Convert poetry.lock to requirements.lock (if available)
        if "poetry.lock" in manifest_files:
            logger.info("Converting poetry.lock to requirements.lock...")
            try:
                pyproject_content = manifest_files.get("pyproject.toml")
                lock_content = await self.poetry_lock_to_requirements_lock(
                    manifest_files["poetry.lock"], pyproject_content
                )
                if lock_content:
                    result["requirements.lock"] = lock_content
                    logger.info("Successfully converted poetry.lock to requirements.lock")
                    return result
            except Exception as e:
                logger.warning(f"Failed to convert poetry.lock: {e}")
        
        # Priority 2: Convert Pipfile.lock to requirements.lock (if available)
        if "Pipfile.lock" in manifest_files:
            logger.info("Converting Pipfile.lock to requirements.lock...")
            try:
                pipfile_content = manifest_files.get("Pipfile")
                lock_content = await self.pipfile_lock_to_requirements_lock(
                    manifest_files["Pipfile.lock"], pipfile_content
                )
                if lock_content:
                    result["requirements.lock"] = lock_content
                    logger.info("Successfully converted Pipfile.lock to requirements.lock")
                    return result
            except Exception as e:
                logger.warning(f"Failed to convert Pipfile.lock: {e}")
        
        # Priority 3: Generate requirements.lock from requirements.txt (if available)
        if "requirements.txt" in manifest_files:
            logger.info("Generating requirements.lock from requirements.txt...")
            try:
                lock_content = await self.generate_requirements_lock(manifest_files["requirements.txt"])
                if lock_content:
                    result["requirements.lock"] = lock_content
                    logger.info("Successfully generated requirements.lock from requirements.txt")
                    return result
            except Exception as e:
                logger.warning(f"Failed to generate requirements.lock: {e}")
        
        # Priority 4: Generate requirements.lock from pyproject.toml (if available)
        if "pyproject.toml" in manifest_files:
            logger.info("Generating requirements.lock from pyproject.toml...")
            try:
                lock_content = await self.generate_pyproject_requirements_lock(manifest_files["pyproject.toml"])
                if lock_content:
                    result["requirements.lock"] = lock_content
                    logger.info("Successfully generated requirements.lock from pyproject.toml")
                    return result
            except Exception as e:
                logger.warning(f"Failed to generate requirements.lock from pyproject.toml: {e}")
        
        logger.warning("No Python manifest files could be converted to requirements.lock")
        return result
    
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