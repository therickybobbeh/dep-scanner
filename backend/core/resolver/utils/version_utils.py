"""Version cleaning and normalization utilities"""
import re


class VersionCleaner:
    """Utility for cleaning and normalizing version strings"""
    
    @staticmethod
    def clean_npm_version(version_spec: str) -> str:
        """
        Clean npm version specifier by removing prefixes like ^, ~, >=, etc.
        
        Examples:
            ^4.17.21 -> 4.17.21
            ~1.2.3 -> 1.2.3
            >=2.0.0 -> 2.0.0
            file:../local -> ../local
        """
        if not version_spec:
            return ""
        
        # Handle special cases
        if version_spec.startswith(("file:", "link:", "git+")):
            return version_spec
        
        # Remove common npm version prefixes
        cleaned = re.sub(r'^[~^>=<]+', '', version_spec)
        
        # Handle version ranges (take first version)
        if " - " in cleaned:
            cleaned = cleaned.split(" - ")[0]
        elif " || " in cleaned:
            cleaned = cleaned.split(" || ")[0]
        
        return cleaned.strip()
    
    @staticmethod
    def clean_python_version(version_spec: str) -> str:
        """
        Clean Python version specifier by removing comparison operators
        
        Examples:
            >=4.2.0,<5.0.0 -> 4.2.0
            ^2.5.1 -> 2.5.1
            ~=1.4.2 -> 1.4.2
        """
        if not version_spec:
            return ""
        
        # Handle special cases
        if version_spec.startswith(("file:", "git+", "-e")):
            return version_spec
        
        # Remove Python version operators
        cleaned = re.sub(r'^[~^>=<!]+', '', version_spec)
        
        # Handle version constraints (take first version)
        if "," in cleaned:
            cleaned = cleaned.split(",")[0]
        
        return cleaned.strip()
    
    @staticmethod
    def extract_version_from_url(url: str) -> str:
        """
        Extract version from URLs like git repositories
        
        Examples:
            git+https://github.com/user/repo@v1.0.0 -> v1.0.0
        """
        if "@" in url:
            return url.split("@")[-1]
        return url
    
    @staticmethod
    def is_valid_semantic_version(version: str) -> bool:
        """Check if version follows semantic versioning"""
        semver_pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?$'
        return bool(re.match(semver_pattern, version))