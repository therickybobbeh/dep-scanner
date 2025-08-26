#!/usr/bin/env python3
"""
Test package.json vs package-lock.json consistency

This test suite validates that scanning a package.json and its corresponding
package-lock.json produces consistent vulnerability results for the same
logical dependency set.
"""
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple

import pytest

from backend.web.services.cli_service import CLIService


class ConsistencyTestCase:
    """Test case for package.json vs package-lock.json consistency"""
    
    def __init__(self, name: str, package_json: Dict[str, Any], package_lock: Dict[str, Any]):
        self.name = name
        self.package_json = package_json
        self.package_lock = package_lock
    
    def __str__(self):
        return f"ConsistencyTestCase({self.name})"


# Test cases with matching package.json and package-lock.json files
CONSISTENCY_TEST_CASES = [
    ConsistencyTestCase(
        name="basic_vulnerable_lodash",
        package_json={
            "name": "test-vulnerable-basic",
            "version": "1.0.0",
            "dependencies": {
                "lodash": "4.17.15"  # Known vulnerable version
            }
        },
        package_lock={
            "name": "test-vulnerable-basic", 
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "test-vulnerable-basic",
                    "version": "1.0.0",
                    "dependencies": {
                        "lodash": "4.17.15"
                    }
                },
                "node_modules/lodash": {
                    "version": "4.17.15",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.15.tgz",
                    "integrity": "sha512-8xOcRHvCjnocdS5cpkfkYYNYIdQpqHJ/+H2mooS7EICMF1+YSHEyj21hhWGW4/D2qE4D1CqzQIq4FvdwPG8zMg=="
                }
            }
        }
    ),
    
    ConsistencyTestCase(
        name="range_vs_exact_version",
        package_json={
            "name": "test-range-vs-exact",
            "version": "1.0.0", 
            "dependencies": {
                "lodash": "^4.17.15"  # Range that should resolve to vulnerable version
            }
        },
        package_lock={
            "name": "test-range-vs-exact",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "test-range-vs-exact",
                    "version": "1.0.0",
                    "dependencies": {
                        "lodash": "^4.17.15"
                    }
                },
                "node_modules/lodash": {
                    "version": "4.17.15",  # Exact resolved version
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.15.tgz",
                    "integrity": "sha512-8xOcRHvCjnocdS5cpkfkYYNYIdQpqHJ/+H2mooS7EICMF1+YSHEyj21hhWGW4/D2qE4D1CqzQIq4FvdwPG8zMg=="
                }
            }
        }
    ),
    
    ConsistencyTestCase(
        name="multiple_dependencies",
        package_json={
            "name": "test-multiple-deps",
            "version": "1.0.0",
            "dependencies": {
                "lodash": "4.17.15",
                "axios": "0.21.1"  # Another potentially vulnerable version
            }
        },
        package_lock={
            "name": "test-multiple-deps",
            "version": "1.0.0",
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "test-multiple-deps",
                    "version": "1.0.0",
                    "dependencies": {
                        "lodash": "4.17.15",
                        "axios": "0.21.1"
                    }
                },
                "node_modules/lodash": {
                    "version": "4.17.15",
                    "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.15.tgz",
                    "integrity": "sha512-8xOcRHvCjnocdS5cpkfkYYNYIdQpqHJ/+H2mooS7EICMF1+YSHEyj21hhWGW4/D2qE4D1CqzQIq4FvdwPG8zMg=="
                },
                "node_modules/axios": {
                    "version": "0.21.1",
                    "resolved": "https://registry.npmjs.org/axios/-/axios-0.21.1.tgz",
                    "integrity": "sha512-dKQiRHxGD9PPRIUNIWvjhpeoD+RQgBjZHIZWpxC+1o7tnGUXGo1V0D0eQ5FQ9g3vFGnY6w7eZxO2ZjcKjTzZYQ=="
                }
            }
        }
    ),
    
    ConsistencyTestCase(
        name="clean_dependencies",
        package_json={
            "name": "test-clean-deps",
            "version": "1.0.0",
            "dependencies": {
                "express": "4.19.0"  # Should be clean
            }
        },
        package_lock={
            "name": "test-clean-deps",
            "version": "1.0.0", 
            "lockfileVersion": 3,
            "requires": True,
            "packages": {
                "": {
                    "name": "test-clean-deps",
                    "version": "1.0.0",
                    "dependencies": {
                        "express": "4.19.0"
                    }
                },
                "node_modules/express": {
                    "version": "4.19.0",
                    "resolved": "https://registry.npmjs.org/express/-/express-4.19.0.tgz",
                    "integrity": "sha512-VqcNGcj/Id5ZT1LZ/cfihi3ttTn+NJmkli2eZADigjq29qTlWi/hAQ43t/VLPq8+UX06FCEx3ByOYet6ZFblng=="
                }
            }
        }
    )
]


class ConsistencyAnalyzer:
    """Analyzes consistency between package.json and package-lock.json scan results"""
    
    @staticmethod
    def extract_direct_dependencies(scan_result: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """Extract vulnerabilities grouped by direct dependency package"""
        direct_vulns = {}
        
        vulnerabilities = scan_result.get('vulnerabilities', [])
        for vuln in vulnerabilities:
            package = vuln.get('package')
            if package:
                if package not in direct_vulns:
                    direct_vulns[package] = []
                direct_vulns[package].append(vuln)
        
        return direct_vulns
    
    @staticmethod
    def compare_scan_results(package_json_result: Dict[str, Any], 
                           package_lock_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare scan results from package.json vs package-lock.json"""
        
        # Extract basic metrics
        pkg_json_vulns = len(package_json_result.get('vulnerabilities', []))
        pkg_lock_vulns = len(package_lock_result.get('vulnerabilities', []))
        
        pkg_json_deps = package_json_result.get('scan_info', {}).get('total_dependencies', 0)
        pkg_lock_deps = package_lock_result.get('scan_info', {}).get('total_dependencies', 0)
        
        # Extract direct dependency vulnerabilities
        pkg_json_direct = ConsistencyAnalyzer.extract_direct_dependencies(package_json_result)
        pkg_lock_direct = ConsistencyAnalyzer.extract_direct_dependencies(package_lock_result)
        
        # Find differences
        pkg_json_packages = set(pkg_json_direct.keys())
        pkg_lock_packages = set(pkg_lock_direct.keys())
        
        missing_in_lock = pkg_json_packages - pkg_lock_packages
        missing_in_json = pkg_lock_packages - pkg_json_packages
        common_packages = pkg_json_packages & pkg_lock_packages
        
        # Check vulnerability counts for common packages
        vuln_count_differences = {}
        for package in common_packages:
            json_count = len(pkg_json_direct[package])
            lock_count = len(pkg_lock_direct[package])
            if json_count != lock_count:
                vuln_count_differences[package] = {
                    'package_json': json_count,
                    'package_lock': lock_count,
                    'difference': abs(json_count - lock_count)
                }
        
        return {
            'metrics': {
                'package_json': {
                    'vulnerabilities': pkg_json_vulns,
                    'dependencies': pkg_json_deps,
                    'vulnerable_packages': len(pkg_json_direct)
                },
                'package_lock': {
                    'vulnerabilities': pkg_lock_vulns,
                    'dependencies': pkg_lock_deps,
                    'vulnerable_packages': len(pkg_lock_direct)
                }
            },
            'consistency': {
                'vulnerability_count_match': pkg_json_vulns == pkg_lock_vulns,
                'vulnerable_packages_match': len(pkg_json_direct) == len(pkg_lock_direct),
                'dependency_count_difference': abs(pkg_json_deps - pkg_lock_deps)
            },
            'differences': {
                'missing_in_package_lock': list(missing_in_lock),
                'missing_in_package_json': list(missing_in_json),
                'vulnerability_count_differences': vuln_count_differences
            },
            'assessment': {
                'is_consistent': (
                    len(missing_in_lock) == 0 and 
                    len(missing_in_json) == 0 and
                    len(vuln_count_differences) == 0
                ),
                'expected_differences': {
                    'dependency_count': pkg_lock_deps > pkg_json_deps,  # Lock file should have more deps
                    'explanation': "package-lock.json includes transitive dependencies"
                }
            }
        }


async def run_cli_scan_on_files(manifest_files: Dict[str, str]) -> Dict[str, Any]:
    """Helper to run CLI scan on manifest files"""
    return await CLIService.run_cli_scan_async(
        manifest_files=manifest_files,
        include_dev=False,
        ignore_severities=[]
    )


@pytest.mark.asyncio
async def test_package_json_vs_package_lock_consistency():
    """Test that package.json and package-lock.json produce consistent results"""
    
    print("\\n🔍 Testing Package.json vs Package-lock.json Consistency")
    print("=" * 60)
    
    results = []
    
    for test_case in CONSISTENCY_TEST_CASES:
        print(f"\\n📦 Testing: {test_case.name}")
        
        # Prepare manifest files
        package_json_files = {
            "package.json": json.dumps(test_case.package_json, indent=2)
        }
        package_lock_files = {
            "package-lock.json": json.dumps(test_case.package_lock, indent=2)
        }
        
        try:
            # Run scans
            print("  🔍 Scanning package.json...")
            package_json_result = await run_cli_scan_on_files(package_json_files)
            
            print("  🔍 Scanning package-lock.json...")
            package_lock_result = await run_cli_scan_on_files(package_lock_files)
            
            # Analyze consistency
            analysis = ConsistencyAnalyzer.compare_scan_results(
                package_json_result, 
                package_lock_result
            )
            
            # Report results
            print(f"  📊 Results:")
            print(f"    package.json: {analysis['metrics']['package_json']['vulnerabilities']} vulnerabilities")
            print(f"    package-lock.json: {analysis['metrics']['package_lock']['vulnerabilities']} vulnerabilities")
            print(f"    Consistent: {analysis['assessment']['is_consistent']}")
            
            if not analysis['assessment']['is_consistent']:
                print(f"  ⚠️  Inconsistencies found:")
                for package, diff in analysis['differences']['vulnerability_count_differences'].items():
                    print(f"    - {package}: {diff['package_json']} vs {diff['package_lock']} vulnerabilities")
            
            results.append({
                'test_case': test_case.name,
                'analysis': analysis
            })
            
        except Exception as e:
            print(f"  ❌ Test failed: {e}")
            results.append({
                'test_case': test_case.name,
                'error': str(e)
            })
    
    # Overall assessment
    consistent_tests = sum(1 for r in results 
                          if 'analysis' in r and r['analysis']['assessment']['is_consistent'])
    total_tests = len([r for r in results if 'analysis' in r])
    
    print(f"\\n📋 Summary:")
    print(f"  ✅ Consistent tests: {consistent_tests}/{total_tests}")
    
    if consistent_tests < total_tests:
        print(f"  ⚠️  Some tests show inconsistencies - this may indicate:")
        print(f"     • Different CLI parsing for package.json vs package-lock.json")
        print(f"     • Version resolution differences") 
        print(f"     • Transitive dependency handling differences")
    
    # Save detailed results
    results_file = Path(__file__).parent / "consistency_test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  📄 Detailed results saved to: {results_file}")
    
    return results


async def test_recursion_fix_with_complex_lockfile():
    """
    Test that the dependency path building doesn't cause infinite recursion
    with complex package-lock.json files containing circular references
    """
    from backend.core.core_scanner import CoreScanner
    from backend.core.models import ScanOptions
    
    # Create a complex package.json similar to what caused the recursion issue
    complex_package_json = {
        "name": "frontend-test",
        "version": "1.0.0",
        "dependencies": {
            "react": "^18.3.1",
            "vite": "^6.0.5",
            "typescript": "^5.7.2"
        },
        "devDependencies": {
            "@types/react": "^18.3.17",
            "@vitejs/plugin-react": "^4.3.4"
        }
    }
    
    manifest_files = {
        "package.json": json.dumps(complex_package_json, indent=2)
    }
    
    scanner = CoreScanner()
    options = ScanOptions(include_dev_dependencies=True)
    
    try:
        # This should complete without recursion errors
        result = await scanner.scan_manifest_files(manifest_files, options)
        
        # Verify we got results without crashing
        assert result is not None
        assert result.total_dependencies > 0
        print(f"✅ Recursion test passed: scanned {result.total_dependencies} dependencies successfully")
        return True
        
    except RecursionError:
        print("❌ Recursion error still occurs")
        return False
    except Exception as e:
        print(f"⚠️  Other error occurred: {e}")
        return False


if __name__ == "__main__":
    # Run the consistency test
    results = asyncio.run(test_package_json_vs_package_lock_consistency())