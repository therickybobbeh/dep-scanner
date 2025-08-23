import pytest
import json
from backend.app.resolver.js_resolver import JavaScriptResolver
from backend.app.models import Dep

@pytest.fixture
def js_resolver():
    return JavaScriptResolver()

@pytest.fixture
def sample_package_json():
    return json.dumps({
        "name": "test-app",
        "version": "1.0.0",
        "dependencies": {
            "express": "4.17.1",
            "lodash": "4.17.20"
        },
        "devDependencies": {
            "jest": "27.0.0"
        }
    })

@pytest.fixture
def sample_package_lock_v1():
    return json.dumps({
        "lockfileVersion": 1,
        "dependencies": {
            "express": {
                "version": "4.17.1",
                "resolved": "https://registry.npmjs.org/express/-/express-4.17.1.tgz",
                "dependencies": {
                    "accepts": {
                        "version": "1.3.7",
                        "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.7.tgz"
                    }
                }
            },
            "lodash": {
                "version": "4.17.20",
                "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.20.tgz"
            }
        }
    })

@pytest.fixture
def sample_package_lock_v2():
    return json.dumps({
        "name": "test-app",
        "version": "1.0.0",
        "lockfileVersion": 2,
        "packages": {
            "": {
                "name": "test-app",
                "version": "1.0.0"
            },
            "node_modules/express": {
                "version": "4.17.1",
                "resolved": "https://registry.npmjs.org/express/-/express-4.17.1.tgz"
            },
            "node_modules/lodash": {
                "version": "4.17.20",
                "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.20.tgz"
            },
            "node_modules/express/node_modules/accepts": {
                "version": "1.3.7",
                "resolved": "https://registry.npmjs.org/accepts/-/accepts-1.3.7.tgz"
            }
        }
    })

class TestJavaScriptResolver:
    
    @pytest.mark.asyncio
    async def test_parse_package_json_only(self, js_resolver, sample_package_json):
        deps = await js_resolver._parse_package_json_only(sample_package_json)
        
        assert len(deps) == 3  # 2 prod deps + 1 dev dep
        
        # Check production dependencies
        express_dep = next((d for d in deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.version == "4.17.1"
        assert express_dep.is_direct is True
        assert express_dep.is_dev is False
        assert express_dep.ecosystem == "npm"
        
        # Check dev dependencies
        jest_dep = next((d for d in deps if d.name == "jest"), None)
        assert jest_dep is not None
        assert jest_dep.is_dev is True

    @pytest.mark.asyncio
    async def test_parse_package_lock_v1(self, js_resolver, sample_package_lock_v1):
        deps = await js_resolver._parse_package_lock(sample_package_lock_v1)
        
        # Should find both direct and transitive dependencies
        assert len(deps) >= 3
        
        # Check direct dependency
        express_dep = next((d for d in deps if d.name == "express"), None)
        assert express_dep is not None
        assert express_dep.version == "4.17.1"
        assert express_dep.is_direct is True
        
        # Check transitive dependency
        accepts_dep = next((d for d in deps if d.name == "accepts"), None)
        assert accepts_dep is not None
        assert accepts_dep.version == "1.3.7"
        assert accepts_dep.is_direct is False
        assert "express" in accepts_dep.path

    @pytest.mark.asyncio
    async def test_parse_package_lock_v2(self, js_resolver, sample_package_lock_v2):
        lock_data = json.loads(sample_package_lock_v2)
        packages = lock_data.get("packages", {})
        
        deps = await js_resolver._parse_package_lock_v2(packages, lock_data)
        
        # Should find all dependencies
        assert len(deps) >= 3
        
        # Verify all dependencies have correct ecosystem
        for dep in deps:
            assert dep.ecosystem == "npm"
            assert isinstance(dep.path, list)
            assert len(dep.path) >= 1

    def test_extract_version_from_spec(self, js_resolver):
        test_cases = [
            ("4.17.1", "4.17.1"),
            ("^4.17.1", "4.17.1"),
            ("~4.17.1", "4.17.1"),
            (">=4.17.1", "4.17.1"),
            ("git+https://github.com/user/repo.git", None),
            ("file:../local-package", None),
            ("", None)
        ]
        
        for spec, expected in test_cases:
            result = js_resolver._extract_version_from_spec(spec)
            if expected:
                assert result == expected
            else:
                assert result is None or result == ""

    @pytest.mark.asyncio
    async def test_resolve_from_manifests_package_json(self, js_resolver, sample_package_json):
        manifest_files = {"package.json": sample_package_json}
        
        deps = await js_resolver._resolve_from_manifests(manifest_files)
        
        assert len(deps) >= 2
        package_names = [dep.name for dep in deps]
        assert "express" in package_names
        assert "lodash" in package_names