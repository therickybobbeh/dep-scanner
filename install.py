#!/usr/bin/env python3
"""
DepScan Installation Script

This script automates the installation of DepScan from PyPI or from source.
Provides a user-friendly installation experience with progress feedback.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description="", check=True):
    """Run a command with optional description and error handling."""
    if description:
        print(f"🔄 {description}...")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr and check:
            print(f"⚠️  {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr}")
        return False


def check_python_version():
    """Verify Python version is compatible."""
    if sys.version_info < (3, 10):
        print(f"❌ Python {sys.version} is not supported. Please use Python 3.10 or later.")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} is supported.")
    return True


def install_from_pypi():
    """Install DepScan from PyPI."""
    print("\n📦 Installing DepScan from PyPI...")
    
    # Try to install
    success = run_command("pip install dep-scan", "Installing dep-scan")
    
    if success:
        print("\n✅ DepScan installed successfully from PyPI!")
        print("\n🚀 Try it out:")
        print("   dep-scan --help")
        print("   dep-scan scan .")
        return True
    else:
        print("\n❌ Failed to install from PyPI.")
        return False


def install_from_source():
    """Install DepScan from source code."""
    print("\n🔧 Installing DepScan from source...")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Not in DepScan source directory. Please run this from the project root.")
        return False
    
    # Check if Node.js is available for frontend
    node_available = run_command("node --version", check=False)
    if not node_available:
        print("⚠️  Node.js not found. Frontend will not be built.")
        print("   Install Node.js from https://nodejs.org/")
    else:
        # Build frontend
        if Path("frontend/package.json").exists():
            print("\n🏗️  Building frontend...")
            os.chdir("frontend")
            if run_command("npm ci", "Installing frontend dependencies"):
                run_command("npm run build", "Building frontend")
            os.chdir("..")
    
    # Install Python package
    success = run_command("pip install -e .", "Installing DepScan from source")
    
    if success:
        print("\n✅ DepScan installed successfully from source!")
        print("\n🚀 Try it out:")
        print("   dep-scan --help")
        print("   dep-scan scan .")
        return True
    else:
        print("\n❌ Failed to install from source.")
        return False


def main():
    """Main installation workflow."""
    print("🛡️  DepScan Installation Script")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check if pip is available
    if not run_command("pip --version", check=False):
        print("❌ pip is not available. Please install pip first.")
        sys.exit(1)
    
    # Determine installation method
    if len(sys.argv) > 1 and sys.argv[1] == "--source":
        success = install_from_source()
    else:
        print("\n🎯 Installation Options:")
        print("1. Install from PyPI (recommended)")
        print("2. Install from source")
        
        while True:
            choice = input("\nChoose option (1/2) [1]: ").strip() or "1"
            if choice == "1":
                success = install_from_pypi()
                break
            elif choice == "2":
                success = install_from_source()
                break
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
    
    if success:
        print("\n🎉 Installation complete!")
        print("\n📚 Next steps:")
        print("   • Read the documentation: docs/user-guide/")
        print("   • Scan your first project: dep-scan scan /path/to/project")
        print("   • Generate HTML report: dep-scan scan . --open")
        print("   • Get help: dep-scan --help")
    else:
        print("\n💔 Installation failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()