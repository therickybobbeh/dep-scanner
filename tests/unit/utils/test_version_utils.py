"""
Tests for version utility classes
"""
import pytest
from backend.app.resolver.utils.version_utils import VersionCleaner


class TestVersionCleaner:
    
    @pytest.fixture
    def cleaner(self):
        return VersionCleaner()
    
    def test_clean_exact_versions(self, cleaner):
        """Test cleaning exact version specifications"""
        test_cases = [
            ("1.0.0", "1.0.0"),
            ("2.15.3", "2.15.3"),
            ("10.0.0-beta.1", "10.0.0-beta.1"),
            ("1.0.0-alpha+build.1", "1.0.0-alpha+build.1"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_caret_versions(self, cleaner):
        """Test cleaning caret (^) version specifications"""
        test_cases = [
            ("^1.0.0", "1.0.0"),
            ("^2.15.3", "2.15.3"),
            ("^0.1.0", "0.1.0"),
            ("^10.20.30", "10.20.30"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_tilde_versions(self, cleaner):
        """Test cleaning tilde (~) version specifications"""
        test_cases = [
            ("~1.0.0", "1.0.0"),
            ("~2.15.3", "2.15.3"),
            ("~0.1.0", "0.1.0"),
            ("~1.2", "1.2.0"),  # Should expand partial versions
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_comparison_versions(self, cleaner):
        """Test cleaning comparison operators (>=, <=, >, <)"""
        test_cases = [
            (">=1.0.0", "1.0.0"),
            ("<=2.15.3", "2.15.3"),
            (">0.1.0", "0.1.0"),
            ("<10.0.0", "10.0.0"),
            (">=1.0.0,<2.0.0", "1.0.0"),  # Should take first version
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_range_versions(self, cleaner):
        """Test cleaning version ranges"""
        test_cases = [
            ("1.0.0 - 2.0.0", "1.0.0"),
            (">=1.2.3 <2.0.0", "1.2.3"),
            (">=1.0.0,<2.0.0", "1.0.0"),
            ("1.0.0 || 2.0.0", "1.0.0"),  # Should take first alternative
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_wildcard_versions(self, cleaner):
        """Test handling of wildcard versions"""
        wildcard_cases = [
            ("*", None),
            ("1.*", "1.0.0"),
            ("1.2.*", "1.2.0"),
            ("x", None),
            ("1.x", "1.0.0"),
            ("1.2.x", "1.2.0"),
        ]
        
        for input_version, expected in wildcard_cases:
            result = cleaner.clean_version(input_version)
            if expected is None:
                assert result is None or result == ""
            else:
                assert result == expected
    
    def test_clean_invalid_versions(self, cleaner):
        """Test handling of invalid or non-semver versions"""
        invalid_cases = [
            ("", None),
            ("   ", None),
            ("latest", None),
            ("next", None),
            ("beta", None),
            ("git+https://github.com/user/repo.git", None),
            ("file:../local-package", None),
            ("http://example.com/package.tar.gz", None),
            ("invalid-version-string", None),
        ]
        
        for input_version, expected in invalid_cases:
            result = cleaner.clean_version(input_version)
            assert result is None or result == ""
    
    def test_clean_prerelease_versions(self, cleaner):
        """Test cleaning versions with prerelease identifiers"""
        test_cases = [
            ("1.0.0-alpha", "1.0.0-alpha"),
            ("2.1.0-beta.1", "2.1.0-beta.1"),
            ("^1.0.0-rc.1", "1.0.0-rc.1"),
            ("~2.0.0-alpha.beta", "2.0.0-alpha.beta"),
            (">=1.0.0-beta", "1.0.0-beta"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_clean_build_metadata(self, cleaner):
        """Test cleaning versions with build metadata"""
        test_cases = [
            ("1.0.0+20130313144700", "1.0.0+20130313144700"),
            ("1.0.0-beta+exp.sha.5114f85", "1.0.0-beta+exp.sha.5114f85"),
            ("^1.0.0+build.123", "1.0.0+build.123"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.clean_version(input_version)
            assert result == expected
    
    def test_normalize_version_formats(self, cleaner):
        """Test normalization of different version formats"""
        # Test that partial versions are expanded
        test_cases = [
            ("1", "1.0.0"),
            ("1.2", "1.2.0"),
            ("1.2.3", "1.2.3"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.normalize_version(input_version)
            assert result == expected
    
    def test_is_valid_semver(self, cleaner):
        """Test semver validation"""
        valid_versions = [
            "1.0.0",
            "10.20.30",
            "1.1.2-prerelease+meta",
            "1.1.2+meta",
            "1.1.2+meta-valid",
            "1.0.0-alpha",
            "1.0.0-beta",
            "1.0.0-alpha.beta",
            "1.0.0-alpha.1",
            "1.0.0-alpha0.beta",
            "1.0.0-alpha.alpha",
            "1.0.0-alpha-a.b-c-somethinglong+metadata+meta.meta.meta.2"
        ]
        
        invalid_versions = [
            "",
            "1",
            "1.2",
            "1.2.3-",
            "1.2.3.4",
            "not-a-version",
            "1.2.3.DEV",
            "1.2-SNAPSHOT",
            "1.2.31.2.3----RC-SNAPSHOT.12.09.1--..12+788",
            "1.2-RC-SNAPSHOT",
        ]
        
        for version in valid_versions:
            assert cleaner.is_valid_semver(version), f"Should be valid: {version}"
        
        for version in invalid_versions:
            assert not cleaner.is_valid_semver(version), f"Should be invalid: {version}"
    
    def test_extract_base_version(self, cleaner):
        """Test extraction of base version from complex specifications"""
        test_cases = [
            ("^1.2.3", "1.2.3"),
            ("~1.2.3", "1.2.3"),
            (">=1.2.3", "1.2.3"),
            ("1.2.3 - 2.0.0", "1.2.3"),
            ("1.2.3 || 2.0.0", "1.2.3"),
            (">=1.2.3 <2.0.0", "1.2.3"),
        ]
        
        for input_version, expected in test_cases:
            result = cleaner.extract_base_version(input_version)
            assert result == expected
    
    def test_compare_versions(self, cleaner):
        """Test version comparison functionality"""
        comparison_tests = [
            ("1.0.0", "2.0.0", -1),  # 1.0.0 < 2.0.0
            ("2.0.0", "1.0.0", 1),   # 2.0.0 > 1.0.0
            ("1.0.0", "1.0.0", 0),   # 1.0.0 == 1.0.0
            ("1.0.0", "1.0.1", -1),  # 1.0.0 < 1.0.1
            ("1.1.0", "1.0.1", 1),   # 1.1.0 > 1.0.1
            ("1.0.0-alpha", "1.0.0", -1),  # prerelease < release
        ]
        
        for v1, v2, expected in comparison_tests:
            result = cleaner.compare_versions(v1, v2)
            if expected < 0:
                assert result < 0, f"{v1} should be less than {v2}"
            elif expected > 0:
                assert result > 0, f"{v1} should be greater than {v2}"
            else:
                assert result == 0, f"{v1} should equal {v2}"
    
    def test_version_cleaner_initialization(self, cleaner):
        """Test that version cleaner initializes correctly"""
        assert cleaner is not None
        assert hasattr(cleaner, 'clean_version')
        assert hasattr(cleaner, 'normalize_version')
        assert hasattr(cleaner, 'is_valid_semver')
    
    def test_edge_cases(self, cleaner):
        """Test edge cases and boundary conditions"""
        edge_cases = [
            (None, None),
            ("0.0.0", "0.0.0"),
            ("999.999.999", "999.999.999"),
            ("^0.0.0", "0.0.0"),
            ("~0.0.0", "0.0.0"),
        ]
        
        for input_version, expected in edge_cases:
            if input_version is None:
                result = cleaner.clean_version(input_version)
                assert result is None
            else:
                result = cleaner.clean_version(input_version)
                if expected is None:
                    assert result is None or result == ""
                else:
                    assert result == expected
    
    def test_performance_with_large_input(self, cleaner):
        """Test performance with large version strings"""
        # Test that very long version strings are handled gracefully
        long_version = "1.0.0-" + "alpha." * 100 + "1"
        
        # Should either clean it or return None, but not crash
        result = cleaner.clean_version(long_version)
        assert result is None or isinstance(result, str)
        
        # Test with many operators
        complex_version = ">=1.0.0,<2.0.0,!=1.5.0,!=1.6.0,!=1.7.0"
        result = cleaner.clean_version(complex_version)
        assert result is not None and result != ""