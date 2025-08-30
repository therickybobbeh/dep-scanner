# 🔄 Scanning Process Workflows

> **Comprehensive workflow documentation with sequence diagrams for the DepScan vulnerability scanner**

This document details the end-to-end scanning processes, from initial file detection through final report generation. It covers both CLI and web interface workflows with detailed sequence diagrams and error handling scenarios.

## 🎯 Overview

The DepScan scanning process involves multiple coordinated steps across different system components, with support for various input formats and scanning modes. The workflow is designed to be robust, efficient, and user-friendly.

## 📊 High-Level Process Flow

```mermaid
flowchart TD
    START[📤 User Input<br/>Files/Repository] --> VALIDATE[✅ Input Validation<br/>File Types & Content]
    
    VALIDATE --> FORMAT_DETECT[🔍 Format Detection<br/>Ecosystem & File Type]
    FORMAT_DETECT --> LOCK_GEN[🔒 Lock File Generation<br/>Ensure Consistency]
    
    LOCK_GEN --> PARSE[📄 Dependency Parsing<br/>Extract Package Info]
    PARSE --> RESOLVE[🧩 Dependency Resolution<br/>Build Complete Tree]
    
    RESOLVE --> SCAN[🛡️ Vulnerability Scanning<br/>Query OSV.dev Database]
    SCAN --> FILTER[🔧 Result Filtering<br/>Apply User Preferences]
    
    FILTER --> REPORT[📋 Report Generation<br/>Multiple Output Formats]
    REPORT --> OUTPUT[📤 Output Delivery<br/>Console/JSON/HTML/API]
    
    %% Error handling paths
    VALIDATE -.->|Invalid Input| ERROR[❌ Error Handling]
    FORMAT_DETECT -.->|Unsupported Format| ERROR
    PARSE -.->|Parse Failure| ERROR
    SCAN -.->|API Failure| ERROR
    
    ERROR --> GRACEFUL[🔄 Graceful Degradation<br/>Partial Results]
    GRACEFUL --> OUTPUT
    
    classDef process fill:#e1f5fe
    classDef error fill:#fce4ec
    classDef output fill:#e8f5e8
    
    class START,VALIDATE,FORMAT_DETECT,LOCK_GEN,PARSE,RESOLVE,SCAN,FILTER,REPORT process
    class ERROR,GRACEFUL error
    class OUTPUT output
```

## 🖥️ CLI Scanning Workflow

### Complete CLI Scanning Sequence

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI Scanner
    participant Core as Core Scanner
    participant PythonResolver
    participant JSResolver
    participant LockGen as Lock Generator
    participant Parser as File Parser
    participant OSV as OSV Scanner
    participant Formatter
    
    User->>CLI: dep-scan /path/to/project
    
    Note over CLI: Argument Validation
    CLI->>CLI: Parse command arguments
    CLI->>CLI: Validate scan options
    
    Note over CLI,Core: Scanner Initialization
    CLI->>Core: Initialize CoreScanner
    CLI->>Formatter: Initialize CLIFormatter
    
    Note over CLI: Progress Display Setup
    CLI->>CLI: Setup Rich progress bar
    CLI->>User: Display "📦 Resolving dependency tree..."
    
    Note over Core: File Discovery & Validation
    Core->>Core: Detect file vs directory
    Core->>Core: Validate path exists
    
    alt Directory Scan
        Core->>Core: Discover dependency files
        Core->>CLI: Progress: "Scanning for dependency files..."
    else Single File Scan
        Core->>Core: Validate file format
        Core->>CLI: Progress: "Processing file..."
    end
    
    Note over Core,LockGen: Lock File Generation
    Core->>LockGen: ensure_lock_files()
    
    alt NPM Lock Generation Needed
        LockGen->>LockGen: Check for package.json without lock
        LockGen-->>User: API call to npm registry
        LockGen->>Core: Enhanced manifest files
    end
    
    alt Python Lock Generation Needed
        LockGen->>LockGen: Check for requirements.txt
        LockGen-->>User: API call to PyPI
        LockGen->>Core: Enhanced manifest files
    end
    
    Note over Core: Ecosystem Resolution
    par Python Dependencies
        Core->>PythonResolver: resolve_dependencies()
        PythonResolver->>Parser: Parse Python files
        Parser->>PythonResolver: Python dependency list
        PythonResolver->>Core: Python dependencies
    and JavaScript Dependencies
        Core->>JSResolver: resolve_dependencies()
        JSResolver->>Parser: Parse JS files  
        Parser->>JSResolver: JS dependency list
        JSResolver->>Core: JS dependencies
    end
    
    Core->>CLI: Progress: "Found X dependencies"
    
    Note over Core,OSV: Vulnerability Scanning
    Core->>OSV: scan_dependencies(all_deps)
    CLI->>User: Display "🛡️ Querying OSV database..."
    
    OSV->>OSV: Deduplicate packages
    OSV->>OSV: Batch dependencies (100/batch)
    
    loop For each batch
        OSV-->>User: HTTP POST to OSV.dev API
        User-->>OSV: Vulnerability data
        CLI->>User: Progress update
    end
    
    OSV->>Core: List of vulnerabilities
    
    Note over Core: Result Processing
    Core->>Core: Apply severity filters
    Core->>Core: Generate scan report
    Core->>CLI: Complete report
    
    CLI->>User: Progress: "Scan completed!"
    
    Note over CLI,Formatter: Output Generation
    CLI->>Formatter: create_vulnerability_table(report)
    Formatter->>CLI: Rich table with vulnerabilities
    
    CLI->>Formatter: print_scan_summary(report)
    Formatter->>User: Display summary statistics
    
    CLI->>User: Display vulnerability table
    
    opt JSON Export Requested
        CLI->>CLI: export_json_report()
        CLI->>User: "✓ JSON report saved"
    end
    
    opt HTML Report Requested
        CLI->>CLI: generate_html_report()
        CLI->>User: "✓ HTML report generated"
        
        opt Open in Browser
            CLI->>User: Open browser with report
        end
    end
    
    Note over CLI: Exit with Status
    alt Vulnerabilities Found
        CLI->>User: Exit code 1
    else No Vulnerabilities
        CLI->>User: Exit code 0
    end
```

## 🌐 Web Interface Scanning Workflow

### Complete Web Scanning Sequence

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant ScanService
    participant CLIService
    participant Core as Core Scanner
    participant OSV as OSV Scanner
    
    User->>Frontend: Upload files + options
    
    Note over Frontend: Client-side Validation
    Frontend->>Frontend: Validate file types
    Frontend->>Frontend: Validate file content
    Frontend->>Frontend: Check file sizes
    
    Frontend->>API: POST /scan (manifest_files, options)
    
    Note over API: Request Processing
    API->>API: Validate request schema
    API->>API: Apply rate limiting
    API->>API: Security headers
    
    API->>ScanService: start_scan(scan_request)
    ScanService->>ScanService: Generate unique job_id
    
    Note over ScanService: Background Task Setup
    ScanService->>ScanService: Initialize ScanProgress
    ScanService->>ScanService: Store progress in AppState
    ScanService->>ScanService: Create async task
    
    ScanService->>API: job_id
    API->>Frontend: {job_id: "uuid"}
    Frontend->>Frontend: Navigate to /report/{job_id}
    
    Note over ScanService: Background Scanning
    ScanService->>CLIService: run_cli_scan_async()
    
    Note over ScanService: Progress Callbacks
    ScanService->>ScanService: Setup progress callback
    
    CLIService->>Core: CoreScanner.scan_manifest_files()
    
    Note over Frontend: Progress Polling
    loop Every 2 seconds
        Frontend->>API: GET /status/{job_id}
        API->>ScanService: get_progress(job_id)
        ScanService->>API: ScanProgress object
        API->>Frontend: Progress update
        
        Frontend->>Frontend: Update progress bar
        Frontend->>User: Display current step
        
        Note over Core,OSV: Concurrent Scanning
        Core-->>OSV: Vulnerability queries
        
        Note over ScanService: Progress Updates
        Core->>CLIService: Progress callback
        CLIService->>ScanService: Update progress
        ScanService->>ScanService: Store in AppState
    end
    
    Note over Core: Scan Completion
    Core->>CLIService: Complete report
    CLIService->>ScanService: CLI result with job_id
    ScanService->>ScanService: Store in AppState
    ScanService->>ScanService: Mark as completed
    
    Note over Frontend: Final Results
    Frontend->>API: GET /status/{job_id}
    API->>Frontend: {status: "completed"}
    
    Frontend->>API: GET /report/{job_id}
    API->>ScanService: get_report(job_id)
    ScanService->>API: Complete CLI report
    API->>Frontend: Full scan results
    
    Frontend->>User: Display vulnerability table
    Frontend->>User: Display statistics
    Frontend->>User: Show export options
    
    opt User Downloads Report
        User->>Frontend: Click download JSON
        Frontend->>User: Download report file
    end
```

## 🐍 Python Dependency Resolution Workflow

### Detailed Python Resolution Process

```mermaid
sequenceDiagram
    participant Core as Core Scanner
    participant PythonResolver
    participant Factory as Python Factory
    participant LockGen as Python Lock Generator
    participant Parser as File Parser
    participant PyPIAPI as PyPI API
    
    Core->>PythonResolver: resolve_dependencies(repo_path)
    
    Note over PythonResolver: File Discovery
    PythonResolver->>PythonResolver: Scan for Python files
    PythonResolver->>PythonResolver: Collect manifest files
    
    alt Repository Scan
        PythonResolver->>PythonResolver: Find requirements.txt, poetry.lock, etc.
    else Uploaded Files
        PythonResolver->>PythonResolver: Process uploaded file dict
    end
    
    Note over PythonResolver,LockGen: Lock File Generation
    PythonResolver->>LockGen: ensure_requirements_lock()
    
    alt Has requirements.txt but no .lock
        LockGen->>PyPIAPI: Resolve version ranges
        PyPIAPI-->>LockGen: Exact versions + dependencies
        LockGen->>LockGen: Generate requirements.lock
        LockGen->>PythonResolver: Enhanced files
    else Has poetry.lock
        LockGen->>PythonResolver: Use existing lock
    else Has Pipfile.lock
        LockGen->>PythonResolver: Use existing lock
    end
    
    Note over PythonResolver,Factory: Format Detection
    PythonResolver->>Factory: detect_best_format(files)
    
    Factory->>Factory: Priority: requirements.lock > poetry.lock > requirements.txt
    Factory->>PythonResolver: (filename, format)
    
    Note over PythonResolver,Parser: Parsing
    PythonResolver->>Factory: get_parser(filename, content)
    Factory->>Parser: Create specific parser
    
    alt requirements.lock (pip-compile format)
        Parser->>Parser: Parse "# via package" comments
        Parser->>Parser: Build dependency paths
        Parser->>Parser: Set is_direct = false for transitive
    else poetry.lock
        Parser->>Parser: Parse TOML structure
        Parser->>Parser: Extract dependency graph
    else requirements.txt
        Parser->>Parser: Parse requirements format
        Parser->>Parser: Mark all as is_direct = true
    end
    
    Parser->>PythonResolver: List[Dep] with full metadata
    PythonResolver->>Core: Python dependencies
```

## 📦 JavaScript Dependency Resolution Workflow

### Detailed JavaScript Resolution Process

```mermaid
sequenceDiagram
    participant Core as Core Scanner
    participant JSResolver as JavaScript Resolver
    participant Factory as JS Factory
    participant LockGen as NPM Lock Generator
    participant Parser as File Parser
    participant NPMAPI as NPM Registry API
    
    Core->>JSResolver: resolve_dependencies(repo_path)
    
    Note over JSResolver: File Discovery
    JSResolver->>JSResolver: Scan for JS files
    JSResolver->>JSResolver: Collect manifest files
    
    alt Repository Scan
        JSResolver->>JSResolver: Find package.json, package-lock.json, yarn.lock
    else Uploaded Files
        JSResolver->>JSResolver: Process uploaded file dict
    end
    
    Note over JSResolver,LockGen: Lock File Generation
    JSResolver->>LockGen: ensure_lock_file()
    
    alt Has package.json but no lock file
        LockGen->>NPMAPI: Resolve dependencies
        NPMAPI-->>LockGen: Full dependency tree
        LockGen->>LockGen: Generate package-lock.json structure
        LockGen->>JSResolver: Enhanced files
    else Has package-lock.json
        LockGen->>JSResolver: Use existing lock
    else Has yarn.lock
        LockGen->>JSResolver: Use existing lock
    end
    
    Note over JSResolver,Factory: Format Detection
    JSResolver->>Factory: detect_best_format(files)
    
    Factory->>Factory: Priority: package-lock.json > yarn.lock > package.json
    Factory->>JSResolver: (filename, format)
    
    Note over JSResolver,Parser: Parsing
    JSResolver->>Factory: get_parser(filename, content)
    Factory->>Parser: Create specific parser
    
    alt package-lock.json (v1/v2/v3)
        Parser->>Parser: Parse lockfile version
        Parser->>Parser: Extract dependency tree
        Parser->>Parser: Build dependency paths
        Parser->>Parser: Set is_direct based on tree level
    else yarn.lock
        Parser->>Parser: Parse Yarn format
        Parser->>Parser: Extract dependency relationships
    else package.json
        Parser->>Parser: Parse dependencies + devDependencies
        Parser->>Parser: Mark all as is_direct = true
    end
    
    Parser->>JSResolver: List[Dep] with full metadata
    JSResolver->>Core: JavaScript dependencies
```

## 🛡️ Vulnerability Scanning Workflow

### OSV.dev Integration Process

```mermaid
sequenceDiagram
    participant Core as Core Scanner
    participant OSV as OSV Scanner
    participant Batcher
    participant RateLimit as Rate Limiter
    participant HTTPClient as HTTP Client
    participant OSVAPIBatch as OSV.dev Batch API
    participant OSVAPIIndiv as OSV.dev Individual API
    participant Enricher
    
    Core->>OSV: scan_dependencies(all_dependencies)
    
    Note over OSV: Preprocessing
    OSV->>OSV: Deduplicate by (ecosystem, name, version)
    OSV->>Core: Progress: "Querying OSV database..."
    
    Note over OSV,Batcher: Batch Processing
    OSV->>Batcher: Split into batches of 100
    
    loop For each batch
        Batcher->>RateLimit: Check rate limits
        RateLimit->>RateLimit: Apply delay if needed
        
        Batcher->>HTTPClient: Prepare batch request
        HTTPClient->>OSVAPIBatch: POST /v1/querybatch
        
        Note over HTTPClient,OSVAPIBatch: Request/Response
        OSVAPIBatch-->>HTTPClient: Vulnerability data
        
        alt Success Response
            HTTPClient->>Batcher: Vulnerability results
        else Rate Limited (429)
            HTTPClient->>HTTPClient: Exponential backoff
            HTTPClient->>OSVAPIBatch: Retry request
        else Network Error
            HTTPClient->>HTTPClient: Retry with backoff
        end
        
        Batcher->>OSV: Batch results
        OSV->>Core: Progress update
    end
    
    Note over OSV: Result Processing
    OSV->>OSV: Flatten batch results
    OSV->>OSV: Check for minimal responses
    
    alt Detailed Data Available
        OSV->>Enricher: Convert to Vuln objects
    else Minimal Data Only
        OSV->>OSV: Identify vulnerabilities needing details
        
        loop For each minimal result
            OSV->>RateLimit: Check rate limits
            OSV->>HTTPClient: GET /v1/vulns/{vuln_id}
            HTTPClient->>OSVAPIIndiv: Individual vulnerability
            OSVAPIIndiv-->>HTTPClient: Detailed vulnerability data
            HTTPClient->>OSV: Enhanced vulnerability
        end
        
        OSV->>Enricher: Convert enhanced data
    end
    
    Note over Enricher: Data Enrichment
    Enricher->>Enricher: Extract CVSS scores
    Enricher->>Enricher: Parse severity levels
    Enricher->>Enricher: Extract CVE IDs
    Enricher->>Enricher: Build advisory URLs
    Enricher->>Enricher: Parse fixed version ranges
    
    Enricher->>OSV: List[Vuln] with full metadata
    OSV->>Core: Complete vulnerability list
```

## 🔧 Error Handling Workflows

### Graceful Error Recovery

```mermaid
stateDiagram-v2
    [*] --> NormalFlow
    
    state "Normal Scanning Flow" as NormalFlow {
        [*] --> FileValidation
        FileValidation --> DependencyResolution
        DependencyResolution --> VulnerabilityScanning
        VulnerabilityScanning --> ReportGeneration
        ReportGeneration --> [*]
    }
    
    state "Error Handling" as ErrorHandling {
        state "File Errors" as FileErrors {
            [*] --> InvalidFormat
            [*] --> FileNotFound
            [*] --> PermissionDenied
            InvalidFormat --> PartialResults
            FileNotFound --> UserError
            PermissionDenied --> UserError
        }
        
        state "Network Errors" as NetworkErrors {
            [*] --> OSVTimeout
            [*] --> RateLimited
            [*] --> RegistryUnavailable
            OSVTimeout --> RetryLogic
            RateLimited --> BackoffRetry
            RegistryUnavailable --> CachedResults
        }
        
        state "Processing Errors" as ProcessingErrors {
            [*] --> ParseError
            [*] --> ResolverError
            [*] --> OutOfMemory
            ParseError --> FallbackParser
            ResolverError --> PartialResults
            OutOfMemory --> ReducedBatch
        }
    }
    
    FileValidation --> FileErrors : validation_fails
    DependencyResolution --> NetworkErrors : api_failure
    DependencyResolution --> ProcessingErrors : parse_failure
    VulnerabilityScanning --> NetworkErrors : osv_failure
    
    FileErrors --> PartialResults : recoverable
    FileErrors --> UserError : unrecoverable
    
    NetworkErrors --> RetryLogic : temporary
    RetryLogic --> NormalFlow : success
    RetryLogic --> PartialResults : max_retries
    
    ProcessingErrors --> FallbackParser : parse_issue
    ProcessingErrors --> PartialResults : processing_issue
    
    FallbackParser --> NormalFlow : success
    FallbackParser --> PartialResults : fallback_failed
    
    PartialResults --> ReportGeneration
    CachedResults --> ReportGeneration
    UserError --> [*]
    
    note right of RetryLogic
        Exponential backoff
        with jitter
    end note
    
    note right of PartialResults
        Continue with available
        data, warn user
    end note
```

## 📊 Performance Optimization Workflows

### Concurrent Processing Strategy

```mermaid
graph TB
    subgraph "Parallel Processing"
        INPUT[📥 Input Files] --> SPLIT[🔄 Split by Ecosystem]
        
        SPLIT --> PY_THREAD[🐍 Python Thread]
        SPLIT --> JS_THREAD[📦 JavaScript Thread]
        
        PY_THREAD --> PY_PARSE[📄 Parse Python Files]
        JS_THREAD --> JS_PARSE[📄 Parse JS Files]
        
        PY_PARSE --> PY_RESOLVE[🧩 Resolve Python Deps]
        JS_PARSE --> JS_RESOLVE[🧩 Resolve JS Deps]
    end
    
    subgraph "Batched API Calls"
        PY_RESOLVE --> MERGE[🔄 Merge Dependencies]
        JS_RESOLVE --> MERGE
        
        MERGE --> DEDUPE[🔍 Deduplicate Packages]
        DEDUPE --> BATCH[📦 Batch for OSV API]
        
        BATCH --> OSV_BATCH1[🛡️ OSV Batch 1<br/>100 packages]
        BATCH --> OSV_BATCH2[🛡️ OSV Batch 2<br/>100 packages]
        BATCH --> OSV_BATCHN[🛡️ OSV Batch N<br/>remaining]
    end
    
    subgraph "Connection Pooling"
        OSV_BATCH1 --> HTTP_POOL[🏊 HTTP Connection Pool]
        OSV_BATCH2 --> HTTP_POOL
        OSV_BATCHN --> HTTP_POOL
        
        HTTP_POOL --> OSV_API[🌐 OSV.dev API]
    end
    
    subgraph "Result Processing"
        OSV_API --> COLLECT[📋 Collect Results]
        COLLECT --> ENRICH[⭐ Enrich Data]
        ENRICH --> FILTER[🔧 Apply Filters]
        FILTER --> REPORT[📊 Generate Report]
    end
    
    classDef parallel fill:#e1f5fe
    classDef batch fill:#e8f5e8
    classDef pool fill:#fff3e0
    classDef result fill:#fce4ec
    
    class INPUT,SPLIT,PY_THREAD,JS_THREAD,PY_PARSE,JS_PARSE,PY_RESOLVE,JS_RESOLVE parallel
    class MERGE,DEDUPE,BATCH,OSV_BATCH1,OSV_BATCH2,OSV_BATCHN batch
    class HTTP_POOL,OSV_API pool
    class COLLECT,ENRICH,FILTER,REPORT result
```

## 🔄 State Transitions

### Scan Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Pending : start_scan()
    
    Pending --> Running : begin_processing
    Pending --> Failed : validation_error
    
    state Running {
        [*] --> FileDiscovery
        FileDiscovery --> LockGeneration
        LockGeneration --> DependencyResolution
        DependencyResolution --> VulnerabilityScanning
        VulnerabilityScanning --> ResultProcessing
        ResultProcessing --> [*]
        
        state VulnerabilityScanning {
            [*] --> Batching
            Batching --> OSVQuerying
            OSVQuerying --> DataEnrichment
            DataEnrichment --> [*]
        }
    }
    
    Running --> Completed : scan_success
    Running --> Failed : scan_error
    
    state Completed {
        [*] --> ReportAvailable
        ReportAvailable --> [*]
    }
    
    state Failed {
        [*] --> ErrorLogged
        ErrorLogged --> PartialResults
        ErrorLogged --> [*]
        PartialResults --> [*]
    }
    
    Completed --> [*] : cleanup_after_retention
    Failed --> [*] : cleanup_after_retention
    
    note right of Pending
        Job queued
        Progress: 0%
        Status visible to user
    end note
    
    note right of Running
        Active processing
        Progress: 1-99%
        Real-time updates
    end note
    
    note right of Completed
        Scan finished successfully
        Progress: 100%
        Full report available
    end note
    
    note right of Failed
        Error occurred
        Error message available
        Partial results may exist
    end note
```

## 📈 Progress Tracking Workflow

### Real-time Progress Updates

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Scanner as Background Scanner
    participant Progress as Progress Tracker
    
    Note over User,Progress: Scan Initiation
    User->>Frontend: Start scan
    Frontend->>API: POST /scan
    API->>Scanner: Start background scan
    API->>Frontend: job_id
    
    Note over Scanner,Progress: Progress Setup
    Scanner->>Progress: Initialize progress (0%)
    Progress->>Progress: Set status = "pending"
    
    Scanner->>Scanner: Begin processing
    Scanner->>Progress: Update status = "running"
    
    Note over Frontend: Polling Setup
    Frontend->>Frontend: Navigate to report page
    Frontend->>Frontend: Start polling timer (2s interval)
    
    Note over Scanner,Progress: Processing with Updates
    loop Every processing step
        Scanner->>Scanner: Process dependencies
        Scanner->>Progress: Update progress %
        Scanner->>Progress: Update current step
        
        Note over Frontend: Client Polling
        Frontend->>API: GET /status/{job_id}
        API->>Progress: Get current progress
        Progress->>API: Progress data
        API->>Frontend: Progress response
        Frontend->>User: Update progress bar
        Frontend->>User: Update status text
    end
    
    Note over Scanner,Progress: Completion
    Scanner->>Progress: Set status = "completed"
    Scanner->>Progress: Set progress = 100%
    Scanner->>Progress: Store final results
    
    Note over Frontend: Final Update
    Frontend->>API: GET /status/{job_id}
    API->>Progress: Get final status
    Progress->>API: Completed status
    API->>Frontend: Completion response
    
    Frontend->>API: GET /report/{job_id}
    API->>Progress: Get report data
    Progress->>API: Full report
    API->>Frontend: Report data
    Frontend->>User: Display results
```

---

## 🔗 Related Documentation

- **[Backend Architecture](../architecture/backend-architecture.md)** - Implementation details of scanning components
- **[Frontend Architecture](../architecture/frontend-architecture.md)** - Web interface workflow implementation
- **[REST API Reference](../api/rest-api.md)** - API endpoints used in web workflows
- **[CLI Interface](../api/cli-interface.md)** - Command-line workflow usage
- **[Component Documentation](../components/core-components.md)** - Detailed component specifications

This comprehensive workflow documentation provides detailed insights into the DepScan scanning process, enabling developers to understand, maintain, and extend the system effectively.