#!/usr/bin/env python3
"""
Cache Management Demo

Demonstrates the cache management endpoints for npm version resolution.
"""
import asyncio
import httpx
import json
import time


async def demo_cache_management():
    """Demonstrate cache management functionality"""
    
    print("🗄️  NPM Version Resolution Cache Management Demo")
    print("=" * 55)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        
        # 1. Check initial cache stats
        print("\n📊 Step 1: Check initial cache statistics")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/admin/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                cache_stats = stats["cache_stats"]
                print(f"✅ Cache stats retrieved:")
                print(f"   Total entries: {cache_stats['total_entries']}")
                print(f"   Cache size: {cache_stats['size_kb']:.2f} KB")
                print(f"   Cache type: {cache_stats['cache_type']}")
            else:
                print(f"❌ Failed to get cache stats: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting cache stats: {e}")
        
        # 2. Trigger some scanning to populate cache (simulate)
        print("\n🔄 Step 2: Simulate cache population")
        print("-" * 40)
        
        # This would normally happen through scanning, but we can simulate
        # by calling the scan endpoint with some package files
        sample_package_json = {
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "~4.17.21",
                "axios": ">=0.27.0"
            }
        }
        
        scan_payload = {
            "manifest_files": {
                "package.json": json.dumps(sample_package_json)
            },
            "options": {
                "enhanced_consistency": True,
                "resolve_versions": True,
                "include_dev_dependencies": True
            }
        }
        
        try:
            print("📦 Triggering scan to populate version cache...")
            response = await client.post(f"{base_url}/scan", json=scan_payload)
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Scan triggered: {result.get('job_id', 'N/A')}")
                # Wait a moment for processing
                await asyncio.sleep(2)
            else:
                print(f"⚠️  Scan request failed: {response.status_code}")
                print("   (This is expected if enhanced resolution isn't fully configured)")
        except Exception as e:
            print(f"⚠️  Scan simulation failed: {e}")
            print("   (This is expected - we're just demonstrating cache endpoints)")
        
        # 3. Check cache stats after population
        print("\n📈 Step 3: Check cache stats after population")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/admin/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                cache_stats = stats["cache_stats"]
                print(f"✅ Updated cache stats:")
                print(f"   Total entries: {cache_stats['total_entries']}")
                print(f"   Cache size: {cache_stats['size_kb']:.2f} KB")
                
                if cache_stats['total_entries'] > 0:
                    print(f"   📝 Cache has been populated with version data!")
                else:
                    print(f"   📝 Cache is still empty (version resolution may not have run)")
            else:
                print(f"❌ Failed to get updated cache stats: {response.status_code}")
        except Exception as e:
            print(f"❌ Error getting updated cache stats: {e}")
        
        # 4. Clear the cache
        print("\n🧹 Step 4: Clear the cache")
        print("-" * 40)
        try:
            response = await client.post(f"{base_url}/admin/cache/clear")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Cache cleared successfully:")
                print(f"   Message: {result['message']}")
                print(f"   Cache type: {result['cache_type']}")
                print(f"   Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result['timestamp']))}")
            else:
                print(f"❌ Failed to clear cache: {response.status_code}")
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
        
        # 5. Verify cache is empty
        print("\n✅ Step 5: Verify cache is cleared")
        print("-" * 40)
        try:
            response = await client.get(f"{base_url}/admin/cache/stats")
            if response.status_code == 200:
                stats = response.json()
                cache_stats = stats["cache_stats"]
                print(f"✅ Cache stats after clearing:")
                print(f"   Total entries: {cache_stats['total_entries']}")
                print(f"   Cache size: {cache_stats['size_kb']:.2f} KB")
                
                if cache_stats['total_entries'] == 0:
                    print(f"   🎉 Cache successfully cleared!")
                else:
                    print(f"   ⚠️  Cache still contains {cache_stats['total_entries']} entries")
            else:
                print(f"❌ Failed to verify cache clearing: {response.status_code}")
        except Exception as e:
            print(f"❌ Error verifying cache clearing: {e}")
        
        # 6. Demonstrate cache cleanup
        print("\n🧽 Step 6: Demonstrate cache cleanup (expired entries)")
        print("-" * 40)
        try:
            response = await client.post(f"{base_url}/admin/cache/cleanup")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Cache cleanup completed:")
                print(f"   Message: {result['message']}")
                print(f"   Expired entries removed: {result['expired_entries']}")
                print(f"   Remaining entries: {result['remaining_entries']}")
            else:
                print(f"❌ Failed to cleanup cache: {response.status_code}")
        except Exception as e:
            print(f"❌ Error during cache cleanup: {e}")
    
    print("\n🎯 Cache Management Summary:")
    print("-" * 40)
    print("✅ Available cache management endpoints:")
    print("   GET  /admin/cache/stats   - Get cache statistics")
    print("   POST /admin/cache/clear   - Clear all cache entries")
    print("   POST /admin/cache/cleanup - Remove expired entries only")
    print("\n💡 Use these endpoints for:")
    print("   - Development: Clear cache to test fresh version resolution")
    print("   - Testing: Ensure clean state between test runs")
    print("   - Maintenance: Remove expired entries to free memory")
    print("   - Monitoring: Track cache usage and effectiveness")


async def test_cache_endpoints_directly():
    """Test cache endpoints without needing full server"""
    print("\n🧪 Direct Cache Function Testing")
    print("-" * 40)
    
    from backend.core.resolver.utils.npm_version_resolver import PackageVersionResolver
    
    # Test resolver cache functions directly
    resolver = PackageVersionResolver()
    
    print("📊 Initial cache stats:")
    stats = resolver.get_cache_stats()
    print(f"   Entries: {stats['total_entries']}")
    print(f"   Size: {stats['size_kb']:.2f} KB")
    
    # Simulate adding some cache data
    resolver._cache_version("test@^1.0.0", "1.2.3", {"source": "test"})
    resolver._cache_version("another@~2.0.0", "2.1.5", {"source": "test"})
    
    print("\n📈 After adding test entries:")
    stats = resolver.get_cache_stats()
    print(f"   Entries: {stats['total_entries']}")
    print(f"   Size: {stats['size_kb']:.2f} KB")
    
    # Test global cache functions
    print(f"\n🌍 Global cache stats:")
    global_stats = PackageVersionResolver.get_global_cache_stats()
    print(f"   Entries: {global_stats['total_entries']}")
    print(f"   Size: {global_stats['size_kb']:.2f} KB")
    
    # Clear cache
    PackageVersionResolver.clear_global_cache()
    print(f"\n🧹 After clearing global cache:")
    global_stats = PackageVersionResolver.get_global_cache_stats()
    print(f"   Entries: {global_stats['total_entries']}")
    print(f"   Size: {global_stats['size_kb']:.2f} KB")


if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Test cache endpoints via HTTP (requires server running)")
    print("2. Test cache functions directly")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nMake sure the DepScan server is running on http://localhost:8000")
        input("Press Enter to continue...")
        asyncio.run(demo_cache_management())
    elif choice == "2":
        asyncio.run(test_cache_endpoints_directly())
    else:
        print("Invalid choice. Running direct function tests...")
        asyncio.run(test_cache_endpoints_directly())