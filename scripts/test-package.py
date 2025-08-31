#!/usr/bin/env python3
"""
Test script for verifying the multi-vuln-scanner package before publishing to PyPI.

This script performs comprehensive testing of the package build, installation,
and functionality to catch issues before they reach PyPI.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import json
from pathlib import Path


def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return the result."""
    print(f"🔧 Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=isinstance(cmd, str), 
            cwd=cwd, 
            capture_output=capture_output,
            text=True,
            check=True
        )
        if capture_output and result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if capture_output and e.stdout:
            print(f"   Stdout: {e.stdout}")
        if capture_output and e.stderr:
            print(f"   Stderr: {e.stderr}")
        raise


def test_build():
    """Test package building."""
    print("\n📦 Testing package build...")
    
    # Clean previous builds
    for dir_name in ['build', 'dist', '*.egg-info']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)
    
    # Install build tools
    run_command([sys.executable, '-m', 'pip', 'install', 'build', 'twine', 'check-manifest'])
    
    # Check manifest
    print("🔍 Checking manifest...")
    run_command(['check-manifest'])
    
    # Build package
    print("🔨 Building package...")
    run_command([sys.executable, '-m', 'build'])
    
    # Check package
    print("✅ Checking package integrity...")
    run_command(['twine', 'check', 'dist/*'])
    
    print("✅ Build successful!")
    return True


def test_installation():
    """Test package installation in a clean environment."""
    print("\n🧪 Testing package installation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_dir = Path(temp_dir) / 'test_venv'
        
        # Create virtual environment
        print("🏗️  Creating test virtual environment...")
        run_command([sys.executable, '-m', 'venv', str(venv_dir)])
        
        # Get python path in virtual environment
        if sys.platform == 'win32':
            python_path = venv_dir / 'Scripts' / 'python.exe'
            pip_path = venv_dir / 'Scripts' / 'pip.exe'
        else:
            python_path = venv_dir / 'bin' / 'python'
            pip_path = venv_dir / 'bin' / 'pip'
        
        # Install the built wheel
        wheel_files = list(Path('dist').glob('*.whl'))
        if not wheel_files:
            raise RuntimeError("No wheel file found in dist/")
        
        wheel_file = wheel_files[0]
        print(f"📦 Installing wheel: {wheel_file}")
        run_command([str(pip_path), 'install', str(wheel_file)])
        
        # Test basic functionality
        print("🔧 Testing CLI functionality...")
        run_command([str(python_path), '-m', 'backend.cli.main', '--help'])
        run_command([str(python_path), '-m', 'backend.cli.main', 'version'])
        
        # Test entry point
        if sys.platform != 'win32':  # Entry points work differently on Windows
            scanner_path = venv_dir / 'bin' / 'multi-vuln-scanner'
            dep_scan_path = venv_dir / 'bin' / 'dep-scan'  # Backward compatibility
            if scanner_path.exists():
                print("🎯 Testing main entry point...")
                run_command([str(scanner_path), '--help'])
            elif dep_scan_path.exists():
                print("🎯 Testing backward compatibility entry point...")
                run_command([str(dep_scan_path), '--help'])
            else:
                print("⚠️  Entry point not found, but module import works")
        
        print("✅ Installation test successful!")
        return True


def test_functionality():
    """Test core scanning functionality."""
    print("\n🛡️  Testing scanning functionality...")
    
    # Create test files
    test_files = {
        'package.json': {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "lodash": "4.17.15",  # Known vulnerabilities
                "axios": "0.21.1"     # Known vulnerabilities
            }
        },
        'requirements.txt': "requests==2.25.1\ndjango==3.2.13"  # Known vulnerabilities
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write test files
        for filename, content in test_files.items():
            file_path = temp_path / filename
            if isinstance(content, dict):
                file_path.write_text(json.dumps(content, indent=2))
            else:
                file_path.write_text(content)
        
        # Test JavaScript scanning
        print("🟨 Testing JavaScript scanning...")
        js_result = run_command([
            sys.executable, '-m', 'backend.cli.main', 'scan', 
            str(temp_path / 'package.json'), '--json', str(temp_path / 'js-results.json')
        ])
        
        # Verify JS results
        js_results_file = temp_path / 'js-results.json'
        if js_results_file.exists():
            with open(js_results_file) as f:
                js_data = json.load(f)
                js_vulns = len(js_data.get('vulnerabilities', []))
                print(f"   Found {js_vulns} JavaScript vulnerabilities")
        else:
            print("⚠️  JavaScript results file not created")
        
        # Test Python scanning
        print("🐍 Testing Python scanning...")
        py_result = run_command([
            sys.executable, '-m', 'backend.cli.main', 'scan',
            str(temp_path / 'requirements.txt'), '--json', str(temp_path / 'py-results.json')
        ])
        
        # Verify Python results
        py_results_file = temp_path / 'py-results.json'
        if py_results_file.exists():
            with open(py_results_file) as f:
                py_data = json.load(f)
                py_vulns = len(py_data.get('vulnerabilities', []))
                print(f"   Found {py_vulns} Python vulnerabilities")
        else:
            print("⚠️  Python results file not created")
        
        # Test directory scanning
        print("📁 Testing directory scanning...")
        run_command([
            sys.executable, '-m', 'backend.cli.main', 'scan',
            str(temp_path), '--json', str(temp_path / 'dir-results.json')
        ])
        
        print("✅ Functionality tests successful!")
        return True


def main():
    """Run all tests."""
    print("🚀 Starting multi-vuln-scanner package testing...")
    print("=" * 60)
    
    try:
        # Change to project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        os.chdir(project_root)
        
        print(f"📍 Working directory: {project_root}")
        
        # Run tests
        test_build()
        test_installation()
        test_functionality()
        
        print("\n" + "=" * 60)
        print("🎉 All tests passed! Package is ready for publishing to TestPyPI.")
        print("\nNext steps:")
        print("1. Commit your changes")
        print("2. Push to GitHub")
        print("3. Create a release or run the GitHub workflow manually")
        print("4. Monitor the TestPyPI publishing workflow")
        print("5. Test installation from TestPyPI")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        print("\nPlease fix the issues and run the tests again.")
        return 1


if __name__ == '__main__':
    sys.exit(main())