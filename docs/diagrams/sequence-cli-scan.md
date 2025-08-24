# CLI Scanning Workflow

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Tool
    participant Scanner as DepScanner
    participant JSResolver as JS Resolver
    participant PyResolver as Python Resolver
    participant Factory as Parser Factory
    participant Parser as Package Parser
    participant OSV as OSV Scanner
    participant Cache as Cache Layer
    participant API as OSV.dev API
    participant FS as File System

    Note over User, FS: Initialization Phase
    User->>+CLI: python cli.py scan /path/to/project
    
    CLI->>+Scanner: create DepScanner()
    Scanner->>JSResolver: initialize()
    Scanner->>PyResolver: initialize()
    Scanner->>+OSV: initialize(cache_db)

    Note over User, FS: Dependency Resolution Phase
    CLI->>Scanner: scan_repository(repo_path, options)
    
    Scanner->>FS: check directory exists
    FS-->>Scanner: directory confirmed

    Note right of Scanner: Smart Format Detection<br/>Prioritizes lockfiles over manifests<br/>for accurate transitive dependencies

    Scanner->>+JSResolver: resolve_dependencies(repo_path)
    
    JSResolver->>FS: find JavaScript files
    FS-->>JSResolver: [package.json, package-lock.json]
    
    JSResolver->>+Factory: detect_best_format(files)
    Factory->>Factory: analyze file priority
    Factory-->>-JSResolver: ("package-lock.json", "package-lock.json")
    
    JSResolver->>+Factory: get_parser("package-lock.json", content)
    Factory->>+Parser: create PackageLockV2Parser()
    Factory-->>-JSResolver: parser instance
    
    JSResolver->>Parser: parse(content)
    Parser->>Parser: extract dependencies recursively
    Parser-->>-JSResolver: list[Dep] (with transitive)
    
    JSResolver-->>-Scanner: dependencies found
    
    Scanner->>+PyResolver: resolve_dependencies(repo_path)
    
    PyResolver->>FS: find Python files
    FS-->>PyResolver: [requirements.txt, poetry.lock]
    
    PyResolver->>+Factory: detect_best_format(files)
    Factory-->>-PyResolver: ("poetry.lock", "poetry.lock")
    
    PyResolver->>+Factory: get_parser("poetry.lock", content)
    Factory->>+Parser: create PoetryLockParser()
    Factory-->>-PyResolver: parser instance
    
    PyResolver->>Parser: parse(content)
    Parser->>Parser: parse TOML and build dependency tree
    Parser-->>-PyResolver: list[Dep] (with transitive)
    
    PyResolver-->>-Scanner: dependencies found
    
    Scanner->>Scanner: merge all dependencies
    Scanner->>Scanner: deduplicate dependencies

    Note over User, FS: Vulnerability Scanning Phase
    Note right of OSV: Batch Processing<br/>Groups dependencies by ecosystem<br/>for efficient API usage

    Scanner->>OSV: scan_dependencies(all_dependencies)
    
    OSV->>+Cache: check_cache(dependencies)
    Cache-->>-OSV: (cached_results, uncached_deps)
    
    alt Uncached dependencies exist
        OSV->>OSV: batch uncached dependencies
        
        loop For each batch
            OSV->>+API: POST /v1/querybatch
            API-->>-OSV: vulnerability data
            
            OSV->>+Cache: store_results(batch_results)
            Cache-->>-OSV: cached successfully
        end
    end
    
    OSV->>OSV: merge cached + fresh results
    OSV-->>Scanner: list[Vuln]

    Note over User, FS: Report Generation Phase
    Scanner->>Scanner: create Report(deps, vulns, meta)
    Scanner-->>CLI: return report

    Note over User, FS: Output Generation Phase
    CLI->>CLI: display progress summary
    CLI->>CLI: create vulnerability table
    CLI->>User: display formatted results

    Note right of CLI: Rich Console Output<br/>• Progress indicators<br/>• Formatted tables<br/>• Color-coded severity<br/>• Summary statistics

    alt JSON output requested
        CLI->>FS: write_json_report(report, filename)
        CLI->>User: "Report saved to filename"
    end

    Note over User, FS: Cleanup Phase
    CLI->>Scanner: close()
    Scanner->>-OSV: close()
    Scanner-->>-CLI: closed
    
    CLI-->>-User: scan completed

    Note over User, API: Key Benefits of CLI Workflow<br/>✅ Fast: Local execution, no network delays for UI<br/>✅ Scriptable: Easy CI/CD integration<br/>✅ Comprehensive: Full transitive dependency resolution<br/>✅ Cached: Intelligent caching reduces API calls<br/>✅ Professional: Rich formatting and error handling
```

## CLI Scanning Workflow Overview

### **Phase 1: Initialization**
- User executes CLI command with project path
- DepScanner initializes with resolvers and OSV scanner
- Cache layer is prepared for vulnerability lookups

### **Phase 2: Dependency Resolution**
- **Smart Format Detection**: Automatically prioritizes lockfiles over manifest files
- **Multi-Ecosystem Support**: Scans both JavaScript and Python dependencies simultaneously
- **Parser Factory**: Dynamically selects appropriate parsers based on file formats
- **Transitive Dependencies**: Extracts complete dependency trees when lockfiles are available

### **Phase 3: Vulnerability Scanning**
- **Batch Processing**: Groups dependencies by ecosystem for efficient API usage
- **Intelligent Caching**: Checks cache first to minimize API calls
- **Rate Limiting**: Respects OSV.dev API limits with proper throttling
- **Result Merging**: Combines cached and fresh vulnerability data

### **Phase 4: Report Generation**
- Creates comprehensive report with dependencies and vulnerabilities
- Calculates statistics and metadata for analysis
- Prepares data for console and file output

### **Phase 5: Output Generation**
- **Rich Console Output**: Formatted tables with color-coded severity levels
- **Progress Indicators**: Real-time feedback during scanning process
- **Multiple Formats**: Console display with optional JSON file export
- **Summary Statistics**: Overview of scan results and security status

### **Key Advantages**

**Performance**
- Local execution with no UI rendering overhead
- Intelligent caching reduces redundant API calls
- Batch API requests minimize network round-trips

**Integration**
- Perfect for CI/CD pipelines and automated workflows
- Scriptable with clear exit codes and structured output
- JSON export for integration with other security tools

**Accuracy**
- Prioritizes lockfiles for complete transitive dependency resolution
- Handles multiple package managers and file formats
- Cross-platform compatibility with consistent behavior