# Package.json and Package-lock.json Consistency Improvements

## Problem Statement

Previously, scanning the same project with `package.json` vs `package-lock.json` would produce inconsistent results due to:

1. **Different Version Resolution**: 
   - `package.json` contains version ranges (`^4.17.21`, `~1.2.3`) 
   - `package-lock.json` contains exact resolved versions (`4.17.21`)

2. **Different Dependency Trees**:
   - `package.json` only shows direct dependencies
   - `package-lock.json` shows full transitive dependency trees

3. **Version Representation Inconsistencies**:
   - Same package could appear with different version strings
   - No standardized comparison between range and resolved versions

## Solution Overview

The enhanced consistency system provides:

### 🔧 Enhanced Package Version Resolver
- **NPM Registry Integration**: Resolves version ranges to actual available versions
- **Semantic Version Matching**: Proper `^`, `~`, `>=` range resolution
- **Fallback Strategies**: Works offline with heuristic resolution
- **Caching**: Efficient version resolution with configurable TTL

### 📊 Scan Result Consistency Analysis
- **Dependency Comparison**: Identifies version mismatches and missing packages
- **Consistency Scoring**: Quantifies reliability between scan approaches
- **Detailed Reporting**: Actionable recommendations for improving consistency
- **Vulnerability Impact Analysis**: Shows how inconsistencies affect security findings

### ⚙️ Enhanced Package.json Parser
- **Optional Version Resolution**: Can resolve ranges to actual versions
- **Consistency Checking**: Compares against lockfile when available  
- **Resolution Source Tracking**: Records how each version was resolved
- **Metadata Preservation**: Maintains original ranges and resolution details

## Usage

### Basic Enhanced Scanning

```python
from core.core_scanner import CoreScanner
from core.models import ScanOptions

scanner = CoreScanner()

# Enable enhanced consistency checking
options = ScanOptions(
    enhanced_consistency=True,      # Use enhanced parsers
    resolve_versions=True,          # Resolve version ranges
    consistency_report=True         # Include analysis in results
)

manifest_files = {
    "package.json": package_json_content,
    "package-lock.json": package_lock_content
}

report = await scanner.scan_manifest_files(manifest_files, options)

# Access consistency analysis
if "consistency_analysis" in report.meta:
    consistency = report.meta["consistency_analysis"]
    print(f"Consistency score: {consistency['manifest_vs_lockfile']['consistency_score']:.1%}")
```

### Direct Resolver Usage

```python
from core.resolver.js_resolver import JavaScriptResolver

# Enhanced resolver with version resolution
resolver = JavaScriptResolver(
    enhanced_package_json=True,
    resolve_versions=True
)

# Get dependencies with consistency checking
deps, consistency_report = await resolver.resolve_with_consistency_check(
    manifest_files,
    check_consistency=True
)

print(f"Best source: {consistency_report['best_source']}")
print(f"Available sources: {consistency_report['available_sources']}")
```

### Version Resolution Only

```python
from core.resolver.utils.npm_version_resolver import PackageVersionResolver

resolver = PackageVersionResolver()

# Resolve single package version range
result = await resolver.resolve_version_range(
    "express", 
    "^4.18.0",
    use_registry=True
)

print(f"Resolved {result.original_range} to {result.resolved_version}")
print(f"Source: {result.source}")  # 'registry', 'cache', or 'fallback'

# Batch resolution
packages = {"express": "^4.18.0", "lodash": "~4.17.21"}
results = await resolver.resolve_multiple(packages)
```

## Configuration Options

### ScanOptions Fields

```python
class ScanOptions(BaseModel):
    # Existing options...
    include_dev_dependencies: bool = True
    ignore_severities: list[SeverityLevel] = []
    
    # New consistency options
    enhanced_consistency: bool = False      # Enable enhanced parsing
    resolve_versions: bool = False          # Resolve version ranges  
    consistency_report: bool = False        # Include analysis in results
```

### JavaScriptResolver Options

```python
resolver = JavaScriptResolver(
    enhanced_package_json=True,  # Use EnhancedPackageJsonParser
    resolve_versions=True        # Enable version range resolution
)
```

## API Response Structure

### Consistency Report Format

```json
{
  "enabled": true,
  "best_source": "package-lock.json",
  "available_sources": ["standard_package_json", "package_lock_json"],
  "manifest_vs_lockfile": {
    "consistency_score": 0.95,
    "matching_dependencies": 18,
    "version_mismatches": 1,
    "missing_in_manifest": 45,
    "missing_in_lockfile": 0,
    "recommendations": [
      "High consistency detected. Results should be reliable.",
      "45 dependencies found in lockfile but not in manifest. These are transitive dependencies."
    ]
  },
  "parsing_errors": {}
}
```

### Enhanced Dependency Metadata

Dependencies resolved with version resolution include additional metadata:

```python
dep = Dep(
    name="express",
    version="4.18.2",           # Resolved version
    ecosystem="npm",
    path=["express"],
    is_direct=True,
    is_dev=False
)

# Additional metadata stored in dep._metadata
{
    "original_range": "^4.18.0",
    "resolution_source": "registry",
    "available_versions": 156
}
```

## Implementation Details

### Version Resolution Priority

1. **Registry Resolution**: Query npm registry for available versions
2. **Semantic Matching**: Find best version satisfying the range
3. **Caching**: Store results with configurable TTL (default 1 hour)
4. **Fallback**: Heuristic resolution when registry unavailable

### Consistency Scoring

```
Consistency Score = Matching Dependencies / Total Unique Dependencies

Where:
- Matching = Same package name and version in both approaches
- Total = All unique packages found across both approaches
```

### File Priority Order

When multiple files are available:

1. `package-lock.json` (v2+) - Most accurate, full tree
2. `yarn.lock` - Accurate, different format
3. Enhanced `package.json` - Version resolved
4. Standard `package.json` - Direct dependencies only

## Performance Considerations

### Version Resolution Caching

- **Memory Cache**: In-memory cache with configurable TTL
- **Batch Resolution**: Concurrent API requests with semaphore limiting
- **Fallback Mode**: Works offline without registry access
- **Rate Limiting**: Respects npm registry rate limits

### Registry API Usage

```python
# Configure concurrent requests
resolver = PackageVersionResolver()
results = await resolver.resolve_multiple(
    packages,
    max_concurrent=10  # Limit concurrent requests
)
```

## Testing

### Run Consistency Tests

```bash
# Run all consistency-related tests
pytest backend/tests/unit/test_consistency_resolver.py -v

# Run specific test categories
pytest -k "consistency" -v
pytest -k "version_resolution" -v
```

### Demo Script

```bash
# Run the consistency demonstration
python backend/examples/consistency_demo.py
```

## Migration Guide

### Enabling Enhanced Consistency

For existing code, add the new options to your scan requests:

```python
# Old approach
options = ScanOptions(include_dev_dependencies=True)

# Enhanced approach  
options = ScanOptions(
    include_dev_dependencies=True,
    enhanced_consistency=True,      # Enable enhanced parsing
    resolve_versions=True,          # Resolve version ranges
    consistency_report=True         # Include analysis
)
```

### Web API Changes

The scan request format now supports consistency options:

```json
{
  "manifest_files": {
    "package.json": "...",
    "package-lock.json": "..."
  },
  "options": {
    "include_dev_dependencies": true,
    "enhanced_consistency": true,
    "resolve_versions": true,
    "consistency_report": true
  }
}
```

## Benefits

### For Users
- **More Reliable Results**: Consistent vulnerability counts across scan approaches
- **Better Understanding**: Clear explanation of differences and recommendations
- **Improved Accuracy**: Version resolution reduces false positives/negatives

### For Developers  
- **Debugging Support**: Detailed consistency analysis for troubleshooting
- **Flexible Configuration**: Enable/disable features as needed
- **Comprehensive Metadata**: Full context for version resolution decisions

### For Operations
- **Consistent CI/CD**: Same results whether scanning with manifest or lockfiles
- **Better Monitoring**: Consistency scores indicate scan reliability
- **Actionable Insights**: Clear recommendations for improving scan quality

## Cache Management

The version resolution system includes a comprehensive cache management system for optimal performance.

### Cache Endpoints

#### GET `/admin/cache/stats`
Get current cache statistics including entry count, size, and validity information.

```bash
curl http://localhost:8000/admin/cache/stats
```

Response:
```json
{
  "cache_stats": {
    "total_entries": 45,
    "size_kb": 12.3,
    "cache_type": "global"
  },
  "timestamp": 1703123456.789
}
```

#### POST `/admin/cache/clear`
Clear all cached version resolution data.

```bash
curl -X POST http://localhost:8000/admin/cache/clear
```

Response:
```json
{
  "success": true,
  "message": "NPM version resolution cache cleared successfully",
  "timestamp": 1703123456.789,
  "cache_type": "global"
}
```

#### POST `/admin/cache/cleanup`
Remove only expired cache entries while keeping valid ones.

```bash
curl -X POST http://localhost:8000/admin/cache/cleanup
```

Response:
```json
{
  "success": true,
  "message": "Cleaned up 12 expired cache entries",
  "expired_entries": 12,
  "remaining_entries": 33,
  "timestamp": 1703123456.789
}
```

### Makefile Commands

```bash
# Show cache statistics
make cache-stats

# Clear all cache data
make cache-clear

# Clean up expired entries only
make cache-cleanup

# Run cache management demo
make cache-demo
```

### Cache Configuration

```python
# Configure cache TTL (time-to-live)
resolver = PackageVersionResolver(
    cache_ttl=3600,        # 1 hour (default)
    use_global_cache=True  # Share cache across instances
)

# Disable caching entirely
resolver = PackageVersionResolver(cache_ttl=0)
```

### Global Cache Benefits

- **Shared Across Scans**: Multiple scans share the same cache
- **Memory Efficient**: Single cache instance regardless of resolver instances
- **Persistent**: Cache survives individual scan completion
- **Thread Safe**: Concurrent access from multiple requests

## Future Enhancements

- **Transitive Dependency Resolution**: Build full dependency trees from package.json
- **Multi-Registry Support**: Support private npm registries  
- **Persistent Cache**: Database-backed cache across server restarts
- **Cache Warming**: Proactively populate cache with popular packages
- **Vulnerability Consistency**: Analyze how dependency differences affect vulnerability findings
- **Performance Optimization**: Parallel parsing and resolution
- **Cache Analytics**: Detailed metrics on hit rates and performance gains