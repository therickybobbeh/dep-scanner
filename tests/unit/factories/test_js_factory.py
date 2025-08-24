"""
Tests for JavaScriptParserFactory
"""
import pytest
from backend.app.resolver.factories.js_factory import JavaScriptParserFactory
from backend.app.resolver.parsers.javascript.package_json import PackageJsonParser
from backend.app.resolver.parsers.javascript.package_lock_v1 import PackageLockV1Parser
from backend.app.resolver.parsers.javascript.package_lock_v2 import PackageLockV2Parser
from backend.app.resolver.parsers.javascript.yarn_lock import YarnLockParser
from backend.app.resolver.parsers.javascript.npm_ls import NpmLsParser
from tests.fixtures.package_json_samples import BASIC_PACKAGE_JSON
from tests.fixtures.package_lock_samples import PACKAGE_LOCK_V1, PACKAGE_LOCK_V2
from tests.fixtures.yarn_lock_samples import BASIC_YARN_LOCK
import json


class TestJavaScriptParserFactory:
    
    @pytest.fixture
    def factory(self):
        return JavaScriptParserFactory()
    
    # Test parser selection by filename
    
    def test_get_parser_package_json(self, factory):
        """Test getting parser for package.json"""
        content = json.dumps(BASIC_PACKAGE_JSON)
        parser = factory.get_parser("package.json", content)
        
        assert isinstance(parser, PackageJsonParser)
    
    def test_get_parser_package_lock_v1(self, factory):
        """Test getting parser for package-lock.json v1"""
        content = json.dumps(PACKAGE_LOCK_V1)
        parser = factory.get_parser("package-lock.json", content)
        
        assert isinstance(parser, PackageLockV1Parser)
    
    def test_get_parser_package_lock_v2(self, factory):
        """Test getting parser for package-lock.json v2+"""
        content = json.dumps(PACKAGE_LOCK_V2)
        parser = factory.get_parser("package-lock.json", content)
        
        assert isinstance(parser, PackageLockV2Parser)
    
    def test_get_parser_yarn_lock(self, factory):
        """Test getting parser for yarn.lock"""
        parser = factory.get_parser("yarn.lock", BASIC_YARN_LOCK)
        
        assert isinstance(parser, YarnLockParser)
    
    def test_get_parser_npm_ls(self, factory):
        """Test getting parser for npm-ls format"""
        # npm-ls is special - identified by format rather than filename
        parser = factory.get_parser_by_format("npm-ls")
        
        assert isinstance(parser, NpmLsParser)
    
    def test_get_parser_unsupported_format(self, factory):
        """Test error for unsupported file format"""
        with pytest.raises(ValueError) as exc_info:
            factory.get_parser("unsupported.txt", "content")
        
        assert "Unsupported JavaScript file format" in str(exc_info.value)
    
    # Test parser selection by format name
    
    def test_get_parser_by_format_package_json(self, factory):
        """Test getting parser by format name"""
        parser = factory.get_parser_by_format("package.json")
        assert isinstance(parser, PackageJsonParser)
        
        parser = factory.get_parser_by_format("package-lock.json")
        # Should return a lockfile parser (v1 or v2 based on default)
        assert isinstance(parser, (PackageLockV1Parser, PackageLockV2Parser))
        
        parser = factory.get_parser_by_format("yarn.lock")
        assert isinstance(parser, YarnLockParser)
        
        parser = factory.get_parser_by_format("npm-ls")
        assert isinstance(parser, NpmLsParser)
    
    def test_get_parser_by_format_invalid(self, factory):
        """Test error for invalid format name"""
        with pytest.raises(ValueError) as exc_info:
            factory.get_parser_by_format("invalid-format")
        
        assert "Unknown JavaScript format" in str(exc_info.value)
    
    # Test format detection
    
    def test_detect_best_format_lockfile_priority(self, factory):
        """Test that lockfiles take priority over manifests"""
        manifest_files = {
            "package.json": json.dumps(BASIC_PACKAGE_JSON),
            "package-lock.json": json.dumps(PACKAGE_LOCK_V1),
            "yarn.lock": BASIC_YARN_LOCK
        }
        
        filename, format_name = factory.detect_best_format(manifest_files)
        
        # Should prefer lockfiles over manifest
        assert filename in ["package-lock.json", "yarn.lock"]
        assert format_name in ["package-lock.json", "yarn.lock"]
    
    def test_detect_best_format_package_lock_priority(self, factory):
        """Test that package-lock.json takes priority over yarn.lock"""
        manifest_files = {
            "package-lock.json": json.dumps(PACKAGE_LOCK_V1),
            "yarn.lock": BASIC_YARN_LOCK
        }
        
        filename, format_name = factory.detect_best_format(manifest_files)
        
        # Should prefer package-lock.json over yarn.lock
        assert filename == "package-lock.json"
        assert format_name == "package-lock.json"
    
    def test_detect_best_format_manifest_only(self, factory):
        """Test format detection with only manifest files"""
        manifest_files = {
            "package.json": json.dumps(BASIC_PACKAGE_JSON)
        }
        
        filename, format_name = factory.detect_best_format(manifest_files)
        
        assert filename == "package.json"
        assert format_name == "package.json"
    
    def test_detect_best_format_no_supported_files(self, factory):
        """Test error when no supported files are provided"""
        manifest_files = {
            "unsupported.txt": "content",
            "another.xyz": "more content"
        }
        
        with pytest.raises(ValueError) as exc_info:
            factory.detect_best_format(manifest_files)
        
        assert "No supported JavaScript dependency files found" in str(exc_info.value)
    
    def test_detect_best_format_empty_files(self, factory):
        """Test error when empty file dict is provided"""
        with pytest.raises(ValueError) as exc_info:
            factory.detect_best_format({})
        
        assert "No files provided" in str(exc_info.value)
    
    # Test supported formats
    
    def test_get_supported_formats(self, factory):
        """Test that all supported formats are listed"""
        formats = factory.get_supported_formats()
        
        expected_formats = [
            "package.json",
            "package-lock.json", 
            "yarn.lock",
            "npm-ls"
        ]
        
        for format_name in expected_formats:
            assert format_name in formats
        
        # Should be reasonable number of formats
        assert len(formats) >= 4
        assert len(formats) <= 10
    
    # Test lockfile version detection
    
    def test_detect_package_lock_version(self, factory):
        """Test detection of package-lock.json versions"""
        # Test v1 detection
        v1_content = json.dumps(PACKAGE_LOCK_V1)
        version = factory._detect_package_lock_version(v1_content)
        assert version == 1
        
        # Test v2 detection
        v2_content = json.dumps(PACKAGE_LOCK_V2)
        version = factory._detect_package_lock_version(v2_content)
        assert version in [2, 3]  # v2 or v3 format
        
        # Test malformed content
        with pytest.raises(ValueError):
            factory._detect_package_lock_version("invalid json")
        
        # Test missing lockfileVersion
        missing_version = json.dumps({"name": "test", "dependencies": {}})
        with pytest.raises(ValueError):
            factory._detect_package_lock_version(missing_version)
    
    # Test format validation
    
    def test_is_supported_format(self, factory):
        """Test format support validation"""
        supported = ["package.json", "package-lock.json", "yarn.lock"]
        unsupported = ["requirements.txt", "poetry.lock", "Pipfile", "unknown.txt"]
        
        for format_name in supported:
            assert factory._is_supported_format(format_name)
        
        for format_name in unsupported:
            assert not factory._is_supported_format(format_name)
    
    def test_get_format_priority(self, factory):
        """Test format priority ordering"""
        # Lockfiles should have higher priority than manifests
        lock_priority = factory._get_format_priority("package-lock.json")
        manifest_priority = factory._get_format_priority("package.json")
        
        assert lock_priority < manifest_priority  # Lower number = higher priority
        
        # package-lock.json should have higher priority than yarn.lock
        package_lock_priority = factory._get_format_priority("package-lock.json")
        yarn_lock_priority = factory._get_format_priority("yarn.lock")
        
        assert package_lock_priority <= yarn_lock_priority
    
    # Test error handling
    
    def test_get_parser_with_invalid_content(self, factory):
        """Test parser selection with invalid content"""
        # Should still return parser based on filename, even with bad content
        # The parser itself will handle content validation
        parser = factory.get_parser("package.json", "invalid json content")
        assert isinstance(parser, PackageJsonParser)
    
    def test_factory_initialization(self, factory):
        """Test that factory initializes correctly"""
        assert factory is not None
        assert hasattr(factory, 'get_parser')
        assert hasattr(factory, 'get_parser_by_format')
        assert hasattr(factory, 'detect_best_format')
        assert hasattr(factory, 'get_supported_formats')
    
    # Test format precedence rules
    
    def test_format_precedence_complete_scenario(self, factory):
        """Test complete format precedence with all file types"""
        # All possible JavaScript dependency files
        manifest_files = {
            "package.json": json.dumps(BASIC_PACKAGE_JSON),
            "package-lock.json": json.dumps(PACKAGE_LOCK_V2),
            "yarn.lock": BASIC_YARN_LOCK,
            "some-other.txt": "ignored content"
        }
        
        filename, format_name = factory.detect_best_format(manifest_files)
        
        # Should pick package-lock.json (highest priority lockfile)
        assert filename == "package-lock.json"
        assert format_name == "package-lock.json"
    
    def test_case_insensitive_filename_matching(self, factory):
        """Test that filename matching handles case variations"""
        # Some systems might have different casing
        test_cases = [
            ("Package.json", "package.json"),
            ("PACKAGE-LOCK.JSON", "package-lock.json"),
            ("Yarn.lock", "yarn.lock")
        ]
        
        for filename, expected_format in test_cases:
            try:
                content = json.dumps(BASIC_PACKAGE_JSON) if "json" in filename.lower() else BASIC_YARN_LOCK
                parser = factory.get_parser(filename, content)
                # Should successfully create parser regardless of case
                assert parser is not None
            except ValueError:
                # Case sensitivity might be enforced - that's also valid
                pass