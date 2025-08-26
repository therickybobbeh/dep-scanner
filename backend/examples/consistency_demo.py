#!/usr/bin/env python3
"""
Demonstration of Package.json and Package-lock.json Consistency Improvements

This script shows how the enhanced parsing and consistency checking 
resolves differences between manifest and lockfile scanning results.
"""
import asyncio
import json
from pathlib import Path
import sys

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.core_scanner import CoreScanner
from core.models import ScanOptions


async def demo_consistency_improvements():
    """Demonstrate consistency improvements with real examples"""
    
    print("🔍 DepScan Package.json vs Package-lock.json Consistency Demo")
    print("=" * 60)
    
    # Sample package.json with version ranges
    sample_package_json = {
        "name": "demo-project",
        "version": "1.0.0",
        "dependencies": {
            "express": "^4.18.0",
            "lodash": "~4.17.21", 
            "axios": ">=0.27.0",
            "moment": "^2.29.0"
        },
        "devDependencies": {
            "jest": "^28.0.0",
            "eslint": "^8.0.0"
        }
    }
    
    # Corresponding package-lock.json with resolved versions
    sample_package_lock = {
        "name": "demo-project",
        "version": "1.0.0",
        "lockfileVersion": 2,
        "packages": {
            "": {
                "name": "demo-project",
                "version": "1.0.0",
                "dependencies": {
                    "express": "^4.18.0",
                    "lodash": "~4.17.21",
                    "axios": ">=0.27.0",
                    "moment": "^2.29.0"
                },
                "devDependencies": {
                    "jest": "^28.0.0",
                    "eslint": "^8.0.0"
                }
            },
            "node_modules/express": {
                "version": "4.18.2"
            },
            "node_modules/lodash": {
                "version": "4.17.21"
            },
            "node_modules/axios": {
                "version": "0.27.2"
            },
            "node_modules/moment": {
                "version": "2.29.4"
            },
            "node_modules/jest": {
                "version": "28.1.3",
                "dev": True
            },
            "node_modules/eslint": {
                "version": "8.23.1",
                "dev": True
            }
        }
    }
    
    print("\n📋 Test Files:")
    print(f"Package.json: {len(sample_package_json['dependencies'])} prod deps, {len(sample_package_json['devDependencies'])} dev deps")
    print(f"Package-lock.json: {len([k for k in sample_package_lock['packages'].keys() if k.startswith('node_modules/')])} resolved packages")
    
    # Test 1: Standard scanning (old behavior)
    print("\n🔧 Test 1: Standard Scanning (Original Behavior)")
    print("-" * 50)
    
    scanner = CoreScanner()
    
    standard_options = ScanOptions(
        include_dev_dependencies=True,
        enhanced_consistency=False,
        resolve_versions=False,
        consistency_report=False
    )
    
    manifest_files = {
        "package.json": json.dumps(sample_package_json),
        "package-lock.json": json.dumps(sample_package_lock)
    }
    
    try:
        standard_report = await scanner.scan_manifest_files(manifest_files, standard_options)
        
        print(f"✅ Standard scan completed")
        print(f"   Total dependencies: {standard_report.total_dependencies}")
        print(f"   Vulnerable packages: {standard_report.vulnerable_count}")
        print(f"   Best source used: package-lock.json (priority order)")
        
        # Show some dependency versions
        print(f"\n   Sample dependency versions:")
        for dep in standard_report.dependencies[:4]:
            print(f"   - {dep.name}: {dep.version}")
    
    except Exception as e:
        print(f"❌ Standard scan failed: {e}")
    
    # Test 2: Enhanced scanning with version resolution
    print("\n🚀 Test 2: Enhanced Scanning with Version Resolution")
    print("-" * 50)
    
    enhanced_options = ScanOptions(
        include_dev_dependencies=True,
        enhanced_consistency=True,
        resolve_versions=True,
        consistency_report=True
    )
    
    try:
        enhanced_report = await scanner.scan_manifest_files(manifest_files, enhanced_options)
        
        print(f"✅ Enhanced scan completed")
        print(f"   Total dependencies: {enhanced_report.total_dependencies}")
        print(f"   Vulnerable packages: {enhanced_report.vulnerable_count}")
        
        # Check for consistency analysis in metadata
        if "consistency_analysis" in enhanced_report.meta:
            consistency = enhanced_report.meta["consistency_analysis"]
            print(f"\n   📊 Consistency Analysis:")
            print(f"   - Best source: {consistency.get('best_source', 'N/A')}")
            print(f"   - Available sources: {len(consistency.get('available_sources', []))}")
            
            if "manifest_vs_lockfile" in consistency:
                manifest_lockfile = consistency["manifest_vs_lockfile"]
                print(f"   - Consistency score: {manifest_lockfile.get('consistency_score', 0):.1%}")
                print(f"   - Matching dependencies: {manifest_lockfile.get('matching_dependencies', 0)}")
                print(f"   - Version mismatches: {manifest_lockfile.get('version_mismatches', 0)}")
                
                recommendations = manifest_lockfile.get('recommendations', [])
                if recommendations:
                    print(f"\n   💡 Recommendations:")
                    for i, rec in enumerate(recommendations[:2], 1):
                        print(f"   {i}. {rec}")
        
        print(f"\n   Sample dependency versions (resolved):")
        for dep in enhanced_report.dependencies[:4]:
            print(f"   - {dep.name}: {dep.version}")
            
    except Exception as e:
        print(f"❌ Enhanced scan failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Package.json only scanning comparison
    print("\n📦 Test 3: Package.json Only vs Lockfile Comparison")
    print("-" * 50)
    
    try:
        # Scan with package.json only (enhanced)
        package_json_only = {"package.json": json.dumps(sample_package_json)}
        
        package_json_report = await scanner.scan_manifest_files(
            package_json_only, 
            enhanced_options
        )
        
        print(f"✅ Package.json only scan completed")
        print(f"   Total dependencies: {package_json_report.total_dependencies}")
        print(f"   Vulnerable packages: {package_json_report.vulnerable_count}")
        
        # Compare with lockfile results
        dep_diff = abs(enhanced_report.total_dependencies - package_json_report.total_dependencies)
        vuln_diff = abs(enhanced_report.vulnerable_count - package_json_report.vulnerable_count)
        
        print(f"\n   📈 Comparison with lockfile scan:")
        print(f"   - Dependency count difference: {dep_diff}")
        print(f"   - Vulnerability count difference: {vuln_diff}")
        
        if dep_diff > 0:
            print(f"   ℹ️  Lockfile includes {dep_diff} additional transitive dependencies")
        if vuln_diff > 0:
            print(f"   ⚠️  Different vulnerability counts indicate scanning inconsistency")
    
    except Exception as e:
        print(f"❌ Package.json only scan failed: {e}")
    
    print("\n🎯 Summary:")
    print("-" * 50)
    print("✅ Enhanced consistency checking provides:")
    print("   - Version range resolution for better accuracy")
    print("   - Consistency analysis between manifest and lockfiles")
    print("   - Detailed recommendations for improving scan reliability")
    print("   - Standardized version representations across formats")
    print("\n💡 Use enhanced_consistency=True and resolve_versions=True")
    print("   for more reliable and consistent vulnerability scanning!")


if __name__ == "__main__":
    asyncio.run(demo_consistency_improvements())