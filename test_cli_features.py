#!/usr/bin/env python3
"""
Test script for CLI enhancements
"""
import sys
import subprocess
from pathlib import Path

def run_cli_test(args, description):
    """Run a CLI command and show results"""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Command: python -m backend.cli.main {' '.join(args)}")
    print('='*60)
    
    try:
        # Run the CLI command
        result = subprocess.run(
            [sys.executable, "-m", "backend.cli.main"] + args,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            timeout=30
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        print(f"Exit code: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
    except Exception as e:
        print(f"❌ Error running command: {e}")

def main():
    """Test the enhanced CLI features"""
    print("DepScan CLI Enhancement Tests")
    print("Testing enhanced CLI with verbose output and URL display")
    
    # Test 1: Help command
    run_cli_test(["scan", "--help"], "Show help with new options")
    
    # Test 2: Version command  
    run_cli_test(["version"], "Show version information")
    
    # Test 3: Basic scan (should work even with no dependencies)
    run_cli_test(["scan", ".", "--verbose"], "Verbose scan of current directory")
    
    # Test 4: Basic scan without verbose
    run_cli_test(["scan", "."], "Standard scan of current directory")

if __name__ == "__main__":
    main()