"""Parser for requirements.txt files"""
from packaging.requirements import Requirement, InvalidRequirement

from ...base import BaseDependencyParser, ParseError
from ...utils import VersionCleaner
from ....models import Dep


class RequirementsParser(BaseDependencyParser):
    """
    Parser for requirements.txt files
    
    Requirements.txt format supports various specifications:
    - package==1.0.0
    - package>=1.0.0,<2.0.0
    - package[extra]==1.0.0
    - git+https://github.com/user/repo@v1.0.0
    - -e git+https://github.com/user/repo
    - -r other-requirements.txt
    
    Note: This only extracts DIRECT dependencies since requirements.txt
    doesn't contain transitive dependency information.
    """
    
    def __init__(self):
        super().__init__(ecosystem="PyPI")
        self.version_cleaner = VersionCleaner()
    
    @property
    def supported_formats(self) -> list[str]:
        return ["requirements.txt"]
    
    async def parse(self, content: str, **kwargs) -> list[Dep]:
        """
        Parse requirements.txt content
        
        Args:
            content: Raw requirements.txt content
            **kwargs: Additional parsing options
                - repo_path: Base path for resolving relative file references
            
        Returns:
            List of dependency objects (direct dependencies only)
            
        Raises:
            ParseError: If parsing fails
        """
        try:
            if not content or not content.strip():
                raise ValueError("requirements.txt is empty or contains only whitespace")
            
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
            
        except Exception as e:
            raise ParseError("requirements.txt", e)
    
    def _parse_requirement_line(self, line: str, line_num: int) -> Dep | None:
        """
        Parse a single requirement line
        
        Args:
            line: Requirement line to parse
            line_num: Line number for error reporting
            
        Returns:
            Dep object or None if line should be skipped
        """
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
                is_dev=False  # requirements.txt doesn't distinguish dev deps
            )
            
        except InvalidRequirement as e:
            # Log warning but don't fail the entire parse
            print(f"Warning: Invalid requirement on line {line_num}: {line} ({e})")
            return None
        except Exception as e:
            print(f"Warning: Failed to parse line {line_num}: {line} ({e})")
            return None
    
    def _parse_pip_option(self, line: str, line_num: int) -> Dep | None:
        """
        Parse pip option lines like -e, -r, etc.
        
        Args:
            line: Option line to parse
            line_num: Line number for error reporting
            
        Returns:
            Dep object or None if not a dependency
        """
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
            # We could potentially parse nested requirements files here
            # but for now, just skip them
            return None
        
        # Handle other options (--find-links, --index-url, etc.)
        else:
            # Skip other pip options
            return None
        
        return None
    
    def _extract_version_from_requirement(self, req: Requirement) -> str:
        """
        Extract version from parsed requirement
        
        Args:
            req: Parsed Requirement object
            
        Returns:
            Clean version string
        """
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
        """
        Parse VCS URL to extract package name and version
        
        Args:
            url: VCS URL (git+https://..., etc.)
            
        Returns:
            Tuple of (package_name, version)
        """
        # Extract name from URL
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
    
    def detect_dev_requirements(self, filename: str) -> bool:
        """
        Detect if this is likely a dev requirements file
        
        Args:
            filename: Name of requirements file
            
        Returns:
            True if likely contains dev dependencies
        """
        dev_patterns = [
            'dev', 'test', 'testing', 'development', 'lint', 
            'format', 'doc', 'docs', 'build'
        ]
        
        filename_lower = filename.lower()
        return any(pattern in filename_lower for pattern in dev_patterns)