"""
Enhanced Parser for requirements.txt files with transitive resolution

This parser extends the basic requirements.txt parser to support:
- Transitive dependency resolution via PyPI API
- Version range resolution
- Better consistency with lockfile-based scanning
"""
import logging
from typing import Optional, List
from packaging.requirements import Requirement, InvalidRequirement

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ...utils.pypi_transitive_resolver import PyPiTransitiveDependencyResolver
from ....models import Dep

logger = logging.getLogger(__name__)


class EnhancedRequirementsParser(BaseDependencyParser):
    """
    Enhanced parser for requirements.txt files
    
    Features:
    - Transitive dependency resolution using PyPI registry
    - Version range resolution
    - Consistent version handling with lockfiles
    - Fallback modes for offline usage
    """
    
    def __init__(
        self, 
        enable_transitive: bool = False,
        use_registry: bool = True,
        max_depth: int = 10
    ):
        super().__init__(ecosystem="PyPI")
        self.version_cleaner = VersionCleaner()
        self.enable_transitive = enable_transitive
        self.use_registry = use_registry
        self.max_depth = max_depth
        self._transitive_resolver: Optional[PyPiTransitiveDependencyResolver] = None
        
        if self.enable_transitive:
            self._transitive_resolver = PyPiTransitiveDependencyResolver(
                max_depth=max_depth,
                include_dev_deps=True  # Will be controlled by parse kwargs
            )
    
    @property
    def supported_formats(self) -> list[str]:
        return ["requirements.txt"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse requirements.txt content with optional transitive resolution
        
        Args:
            content: Raw requirements.txt content
            **kwargs: Additional parsing options
                - include_dev: Whether to include dev dependencies (default: True)
                - enable_transitive: Override instance setting for transitive resolution
                - use_registry: Override instance setting for registry usage
                - bypass_cache: Force fresh registry lookups
                - max_concurrent: Max concurrent registry requests (default: 5)
            
        Returns:
            List of dependency objects with transitive dependencies when enabled
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            if not content or not content.strip():
                raise ValueError("requirements.txt is empty or contains only whitespace")
            
            # Extract options
            include_dev = kwargs.get("include_dev", True)
            enable_transitive = kwargs.get("enable_transitive", self.enable_transitive)
            use_registry = kwargs.get("use_registry", self.use_registry)
            bypass_cache = kwargs.get("bypass_cache", False)
            max_concurrent = kwargs.get("max_concurrent", 5)
            
            # Check if transitive resolution is requested and available
            if enable_transitive and self._transitive_resolver and use_registry:
                logger.info("Using PyPI transitive dependency resolution")
                
                # Configure transitive resolver based on options
                self._transitive_resolver.include_dev_deps = include_dev
                
                # Use transitive resolver
                result = await self._transitive_resolver.resolve_from_requirements_txt(
                    content,
                    use_registry=use_registry,
                    bypass_cache=bypass_cache
                )
                
                if result.errors:
                    logger.warning(f"Transitive resolution had errors: {result.errors}")
                
                logger.info(f"Transitive resolution stats: {result.resolution_stats}")
                return result.dependencies
            
            # Fall back to standard resolution
            logger.info("Using standard requirements.txt parsing")
            return await self._parse_standard(content, include_dev)
            
        except Exception as e:
            raise ParseError("requirements.txt enhanced", e)
    
    async def _parse_standard(self, content: str, include_dev: bool = True) -> List[Dep]:
        """Standard requirements.txt parsing (direct dependencies only)"""
        lines = content.strip().split('\n')
        deps = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Handle special pip options
            if line.startswith('-'):
                dep = self._parse_pip_option(line, line_num)
                if dep:
                    deps.append(dep)
            else:
                # Parse regular requirement
                dep = self._parse_requirement_line(line, line_num)
                if dep:
                    deps.append(dep)
        
        if not deps:
            raise ValueError("No valid dependencies found in requirements.txt")
        
        return deps
    
    def _parse_requirement_line(self, line: str, line_num: int) -> Dep | None:
        """Parse a single requirement line"""
        try:
            # Handle inline comments
            if '#' in line:
                line = line.split('#')[0].strip()
            
            if not line:
                return None
            
            # Parse using packaging.requirements
            req = Requirement(line)
            
            name = req.name
            version = self._extract_version_from_requirement(req)
            
            if not name:
                return None
            
            return self._create_dependency(
                name=name,
                version=version,
                path=[name],
                is_direct=True,
                is_dev=self._is_dev_requirement(line)
            )
            
        except InvalidRequirement as e:
            logger.warning(f"Invalid requirement on line {line_num}: {line} ({e})")
            return None
        except Exception as e:
            logger.warning(f"Failed to parse line {line_num}: {line} ({e})")
            return None
    
    def _parse_pip_option(self, line: str, line_num: int) -> Dep | None:
        """Parse pip option lines like -e, -r, etc."""
        # Handle editable installs (-e)
        if line.startswith('-e ') or line.startswith('--editable '):
            url = line.split(' ', 1)[1].strip()
            name, version = self._parse_vcs_url(url)
            
            if name:
                return self._create_dependency(
                    name=name,
                    version=version,
                    path=[name],
                    is_direct=True,
                    is_dev=False
                )
        
        # Handle requirements file inclusion (-r)
        elif line.startswith('-r ') or line.startswith('--requirement '):
            # Skip nested requirements files for now
            return None
        
        # Skip other pip options
        return None
    
    def _extract_version_from_requirement(self, req: Requirement) -> str:
        """Extract version from parsed requirement"""
        if not req.specifier:
            return ""
        
        # Get the first version specifier
        specs = list(req.specifier)
        if specs:
            # Take the first version and clean it
            version_spec = str(specs[0]).replace(specs[0].operator, '')
            return self.version_cleaner.clean_python_version(version_spec)
        
        return ""
    
    def _parse_vcs_url(self, url: str) -> tuple[str, str]:
        """Parse VCS URL to extract package name and version"""
        name = ""
        version = ""
        
        # Handle different VCS URL formats
        if url.startswith('git+'):
            # git+https://github.com/user/repo@v1.0.0
            clean_url = url[4:]  # Remove 'git+'
            
            # Extract version from @tag
            if '@' in clean_url:
                clean_url, version = clean_url.rsplit('@', 1)
            
            # Extract name from URL path
            if '/' in clean_url:
                name = clean_url.split('/')[-1]
                if name.endswith('.git'):
                    name = name[:-4]
        
        elif url.startswith('hg+') or url.startswith('svn+'):
            # Similar handling for other VCS
            pass
        
        else:
            # Local path
            if '/' in url:
                name = url.split('/')[-1]
        
        return name, version
    
    def _is_dev_requirement(self, requirement_str: str) -> bool:
        """Simple heuristic to detect dev requirements"""
        dev_markers = ['extra == "dev"', 'extra == "test"', 'extra == "testing"', 
                      'extra == "lint"', 'extra == "docs"', 'extra == "build"']
        return any(marker in requirement_str for marker in dev_markers)
    
    def supports_transitive_resolution(self) -> bool:
        """Check if this parser instance supports transitive dependency resolution"""
        return self.enable_transitive
    
    def get_resolution_capabilities(self) -> dict:
        """Get information about this parser's resolution capabilities"""
        return {
            "transitive_resolution": self.enable_transitive,
            "max_transitive_depth": self.max_depth if self.enable_transitive else 0,
            "use_registry": self.use_registry,
            "version_source_tracking": True,
            "circular_dependency_handling": self.enable_transitive,
            "version_conflict_resolution": self.enable_transitive,
            "ecosystem": "PyPI"
        }