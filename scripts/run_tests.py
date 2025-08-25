#!/usr/bin/env python3
"""
Comprehensive test runner for the DepScan application

This script runs all test suites and provides coverage reporting
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        return True
    else:
        print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        return False


def main():
    """Run comprehensive test suite"""
    print("🚀 Starting Comprehensive DepScan Test Suite")
    
    # Change to project root directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    success_count = 0
    total_tests = 0
    
    # Test categories to run
    test_categories = [
        {
            "command": "python -m pytest backend/tests/unit/parsers/ -v",
            "description": "Parser Class Tests"
        },
        {
            "command": "python -m pytest backend/tests/unit/factories/ -v", 
            "description": "Factory Pattern Tests"
        },
        {
            "command": "python -m pytest backend/tests/unit/utils/ -v",
            "description": "Utility Class Tests"
        },
        {
            "command": "python -m pytest backend/tests/unit/test_js_resolver_new.py -v",
            "description": "JavaScript Resolver Tests (New Architecture)"
        },
        {
            "command": "python -m pytest backend/tests/unit/test_python_resolver.py -v",
            "description": "Python Resolver Tests"
        },
        {
            "command": "python -m pytest backend/tests/unit/test_osv_scanner.py -v",
            "description": "OSV Scanner Tests"
        },
        {
            "command": "python -m pytest backend/tests/integration/ -v",
            "description": "Integration Tests"
        },
        {
            "command": "python scripts/test_resolvers.py",
            "description": "Architecture Verification Tests"
        }
    ]
    
    # Run each test category
    for test_category in test_categories:
        total_tests += 1
        if run_command(test_category["command"], test_category["description"]):
            success_count += 1
    
    # Run coverage report if pytest-cov is available
    total_tests += 1
    if run_command(
        "python -m pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term",
        "Coverage Report Generation"
    ):
        success_count += 1
        print("\n📊 Coverage report generated in htmlcov/index.html")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📋 Test Suite Summary")
    print(f"{'='*60}")
    print(f"✅ Passed: {success_count}/{total_tests}")
    print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! The new architecture is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())