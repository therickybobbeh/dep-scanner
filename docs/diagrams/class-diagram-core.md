# Core Class Diagram

```mermaid
classDiagram
    %% Domain Models
    class Dep {
        +string name
        +string version
        +Ecosystem ecosystem
        +string[] path
        +bool is_direct
        +bool is_dev
        +__init__()
        +__str__()
        +to_dict()
    }
    
    class Vuln {
        +string package
        +string version
        +Ecosystem ecosystem
        +string vulnerability_id
        +SeverityLevel severity
        +string[] cve_ids
        +string summary
        +string description
        +string advisory_url
        +string fixed_range
        +datetime published
        +datetime modified
        +__init__()
        +is_critical() bool
        +get_fix_suggestion() string
    }
    
    class Report {
        +string job_id
        +JobStatus status
        +int total_dependencies
        +int vulnerable_count
        +Vuln[] vulnerable_packages
        +Dep[] dependencies
        +int suppressed_count
        +dict meta
        +__init__()
        +get_summary() dict
        +to_json() string
        +get_severity_stats() dict
    }
    
    class SeverityLevel {
        <<enumeration>>
        CRITICAL
        HIGH
        MEDIUM
        LOW
        UNKNOWN
        +get_numeric_value() int
        +get_color() string
    }
    
    class Ecosystem {
        <<enumeration>>
        PYPI : "PyPI"
        NPM : "npm"
        +get_registry_url() string
        +get_supported_formats() string[]
    }
    
    class JobStatus {
        <<enumeration>>
        PENDING
        IN_PROGRESS
        COMPLETED
        FAILED
        +is_final() bool
        +can_transition_to(JobStatus) bool
    }

    %% Scan Configuration
    class ScanOptions {
        +bool include_dev_dependencies
        +SeverityLevel[] ignore_severities
        +IgnoreRule[] ignore_rules
        +int max_depth
        +int timeout_seconds
        +__init__()
        +should_ignore_vuln(Vuln) bool
        +should_include_dep(Dep) bool
    }
    
    class IgnoreRule {
        +string rule_type
        +string identifier
        +string reason
        +datetime expiry
        +__init__()
        +matches(Vuln) bool
        +is_expired() bool
    }
    
    class ScanProgress {
        +string job_id
        +JobStatus status
        +string current_step
        +int progress_percent
        +int dependencies_found
        +int vulnerabilities_found
        +datetime start_time
        +datetime end_time
        +string error_message
        +__init__()
        +update_progress(int, string)
        +mark_completed()
        +mark_failed(string)
    }

    %% Parser Base Classes
    class BaseDependencyParser {
        <<abstract>>
        +Ecosystem ecosystem
        +parse(string)* Dep[]
        +can_parse(string)* bool
        +supports_transitive_dependencies()* bool
        +validate_content(string)
        +handle_parse_error(Exception)
    }
    
    class ParseError {
        +string file_type
        +Exception original_error
        +int line_number
        +string context
        +__init__()
        +get_user_message() string
    }
    
    class FileFormatDetector {
        <<abstract>>
        +detect_format(dict)* tuple
        +get_supported_formats()* string[]
        +get_format_priority() int
        +validate_format_combination(string[]) bool
    }

    %% Relationships
    Report ||--o{ Dep : contains
    Report ||--o{ Vuln : contains
    Vuln ||--|| SeverityLevel : has
    Dep ||--|| Ecosystem : ecosystem
    Vuln ||--|| Ecosystem : ecosystem
    Report ||--|| JobStatus : status
    ScanProgress ||--|| JobStatus : status
    
    ScanOptions ||--o{ IgnoreRule : contains
    IgnoreRule --> SeverityLevel : references
    
    BaseDependencyParser --> Ecosystem : uses
    BaseDependencyParser --> Dep : creates
    BaseDependencyParser ..> ParseError : throws

    %% Styling
    classDef domainModel fill:#E3F2FD,stroke:#1976D2,stroke-width:2px
    classDef enumClass fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    classDef configClass fill:#E8F5E8,stroke:#388E3C,stroke-width:2px
    classDef parserClass fill:#FFF3E0,stroke:#F57C00,stroke-width:2px

    class Dep,Vuln,Report domainModel
    class SeverityLevel,Ecosystem,JobStatus enumClass
    class ScanOptions,IgnoreRule,ScanProgress configClass
    class BaseDependencyParser,ParseError,FileFormatDetector parserClass
```

## Class Descriptions

### **Domain Models**

**`Dep`** - Core dependency representation
- Normalized across ecosystems (npm, PyPI)
- Tracks dependency paths for transitive dependencies
- Supports development/production distinction

**`Vuln`** - Vulnerability information
- OSV.dev compatible format
- Severity classification with color coding
- Remediation guidance and fix suggestions

**`Report`** - Comprehensive scan results
- Contains all dependencies and vulnerabilities found
- Statistics and metadata for reporting
- Exportable to multiple formats (JSON, CSV, SBOM)

### **Enumerations**

**`SeverityLevel`** - Vulnerability severity levels
- CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN
- Numeric values for sorting and comparison
- Color mapping for UI display

**`Ecosystem`** - Package ecosystem identifiers
- Currently supports npm (JavaScript) and PyPI (Python)
- Registry URL mapping for metadata lookups
- Supported file format lists

**`JobStatus`** - Scan job lifecycle states
- State transition validation
- Final state identification for cleanup

### **Configuration**

**`ScanOptions`** - Scan behavior configuration
- Development dependency inclusion control
- Severity-based filtering
- Custom ignore rules with expiration

**`ScanProgress`** - Real-time scan progress tracking
- WebSocket-compatible progress updates
- Error state management
- Performance metrics collection

### **Parser Architecture**

**`BaseDependencyParser`** - Extensible parser base
- Factory pattern support for easy extension
- Format-specific implementations
- Standardized error handling with contextual information