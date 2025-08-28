# Class Diagrams

This document provides detailed class diagrams for DepScan, illustrating the relationships between core models, parsers, scanners, and other key components.

## Core Data Models

```mermaid
classDiagram
    class Dep {
        +str name
        +str version
        +Ecosystem ecosystem
        +List~str~ path
        +bool is_direct
        +bool is_dev
        +__init__(name, version, ecosystem, path, is_direct, is_dev)
        +__str__() str
        +__repr__() str
    }
    
    class Vuln {
        +str package
        +str version
        +Ecosystem ecosystem
        +str vulnerability_id
        +SeverityLevel severity
        +float cvss_score
        +List~str~ cve_ids
        +str summary
        +str details
        +str advisory_url
        +str fixed_range
        +datetime published
        +datetime modified
        +List~str~ aliases
        +__init__(...)
        +is_critical() bool
        +is_high() bool
        +is_fixable() bool
    }
    
    class Report {
        +str job_id
        +JobStatus status
        +int total_dependencies
        +int vulnerable_count
        +List~Vuln~ vulnerable_packages
        +List~Dep~ dependencies
        +int suppressed_count
        +Dict~str, Any~ meta
        +__init__(...)
        +get_severity_counts() Dict
        +get_ecosystems() List~str~
        +get_scan_duration() float
    }
    
    class ScanOptions {
        +bool include_dev_dependencies
        +List~SeverityLevel~ ignore_severities
        +__init__(...)
        +should_ignore_severity(severity) bool
        +should_include_dev() bool
    }
    
    class ScanRequest {
        +str repo_path
        +Dict~str, str~ manifest_files
        +ScanOptions options
        +__init__(...)
        +has_repo_path() bool
        +has_manifest_files() bool
        +validate() bool
    }
    
    class ScanProgress {
        +str job_id
        +JobStatus status
        +float progress_percent
        +str current_step
        +int total_dependencies
        +int scanned_dependencies
        +int vulnerabilities_found
        +datetime started_at
        +datetime completed_at
        +str error_message
        +__init__(...)
        +update_progress(percent, step)
        +mark_completed()
        +mark_failed(error)
    }

    Report *-- Vuln : contains many
    Report *-- Dep : contains many
    Report *-- ScanOptions : configured by
    ScanRequest *-- ScanOptions : includes
    
    <<enumeration>> SeverityLevel
    SeverityLevel : CRITICAL
    SeverityLevel : HIGH
    SeverityLevel : MEDIUM
    SeverityLevel : LOW
    SeverityLevel : UNKNOWN
    
    <<enumeration>> JobStatus
    JobStatus : PENDING
    JobStatus : RUNNING
    JobStatus : COMPLETED
    JobStatus : FAILED
    
    <<type>> Ecosystem
    Ecosystem : npm
    Ecosystem : PyPI
    
    Dep --> Ecosystem
    Vuln --> Ecosystem
    Vuln --> SeverityLevel
    Report --> JobStatus
    ScanProgress --> JobStatus
```

## Core Scanner Architecture

```mermaid
classDiagram
    class CoreScanner {
        +PythonResolver python_resolver
        +JavaScriptResolver js_resolver
        +OSVScanner osv_scanner
        +NpmLockGenerator npm_lock_generator
        +PythonLockGenerator python_lock_generator
        +__init__()
        +scan_repository(repo_path, options, callback) Report
        +scan_manifest_files(files, options, callback) Report
        -_scan_dependencies(repo_path, files, options, callback) Report
        -_ensure_lock_files(files, callback) Dict
        -_resolve_all_dependencies(repo_path, files, callback) List~Dep~
        -_scan_vulnerabilities(deps, callback) List~Vuln~
        -_create_report(deps, vulns, options) Report
    }
    
    class CLIScanner {
        +bool verbose
        +CoreScanner core_scanner
        +__init__(verbose)
        +scan_path(path, options) Report
        +scan_directory(dir_path, options) Report
        +scan_file(file_path, options) Report
        -_print_progress(message)
        -_validate_path(path) bool
    }
    
    class OSVScanner {
        +str cache_db_path
        +HTTPXClient http_client
        +CacheManager cache_manager
        +__init__(cache_db_path)
        +scan_dependencies(deps) List~Vuln~
        +query_vulnerabilities(queries) List~OSVVulnerability~
        -_batch_queries(deps) List~OSVBatchQuery~
        -_process_osv_responses(responses) List~Vuln~
        -_check_cache(deps) Tuple~List, List~
        -_store_cache_results(deps, vulns)
        +close()
    }
    
    class CacheManager {
        +str db_path
        +Connection connection
        +__init__(db_path)
        +get_cached_vulnerabilities(deps) List~Vuln~
        +store_vulnerabilities(deps, vulns)
        +cleanup_expired()
        +get_cache_stats() Dict
        -_create_tables()
        -_is_expired(timestamp) bool
        +close()
    }

    CoreScanner --> PythonResolver
    CoreScanner --> JavaScriptResolver
    CoreScanner --> OSVScanner
    CoreScanner --> NpmLockGenerator
    CoreScanner --> PythonLockGenerator
    CLIScanner --> CoreScanner
    OSVScanner --> CacheManager
```

## Dependency Resolution Architecture

```mermaid
classDiagram
    class BaseResolver {
        <<abstract>>
        +str name
        +__init__(name)
        +resolve_dependencies(repo_path, manifest_files) List~Dep~*
        +get_supported_files() List~str~*
        -_find_dependency_files(repo_path) List~str~
        -_validate_files(files) bool
    }
    
    class PythonResolver {
        +ParserFactory parser_factory
        +__init__()
        +resolve_dependencies(repo_path, manifest_files) List~Dep~
        +get_supported_files() List~str~
        -_detect_python_files(path) List~str~
        -_prioritize_formats(files) List~str~
        -_merge_results(results) List~Dep~
    }
    
    class JavaScriptResolver {
        +ParserFactory parser_factory
        +__init__()
        +resolve_dependencies(repo_path, manifest_files) List~Dep~
        +get_supported_files() List~str~
        -_detect_js_files(path) List~str~
        -_prioritize_formats(files) List~str~
        -_handle_workspaces(package_json) List~Dep~
    }
    
    class ParserFactory {
        +Dict~str, Type~ parser_registry
        +__init__()
        +detect_format(filename, content) str
        +get_parser(format_type, content) BaseParser
        +register_parser(format_type, parser_class)
        +list_supported_formats() List~str~
        -_analyze_content(filename, content) str
        -_get_priority_score(format_type) int
    }

    BaseResolver <|-- PythonResolver
    BaseResolver <|-- JavaScriptResolver
    PythonResolver --> ParserFactory
    JavaScriptResolver --> ParserFactory
```

## Parser Class Hierarchy

```mermaid
classDiagram
    class BaseParser {
        <<abstract>>
        +str format_name
        +str content
        +__init__(content)
        +parse() List~Dep~*
        +validate_content() bool*
        +get_metadata() Dict*
        -_parse_version(version_str) str
        -_normalize_name(name) str
        -_create_dependency(name, version, **kwargs) Dep
    }
    
    class PackageJsonParser {
        +Dict parsed_json
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_dependencies(deps_dict, is_dev) List~Dep~
        -_handle_workspace_dependencies(deps) List~Dep~
        -_resolve_version_range(range_str) str
    }
    
    class PackageLockV2Parser {
        +Dict parsed_json
        +Dict packages
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_packages_section() List~Dep~
        -_build_dependency_tree() Dict
        -_extract_transitive_deps(package_info) List~Dep~
    }
    
    class YarnLockParser {
        +str content
        +Dict parsed_entries
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_yarn_format() Dict
        -_resolve_yarn_entry(entry) Dep
        -_handle_yarn_patterns(patterns) List~str~
    }
    
    class RequirementsParser {
        +List~str~ lines
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_requirement_line(line) Dep
        -_handle_constraints(line) str
        -_parse_version_specifier(spec) str
    }
    
    class PoetryLockParser {
        +Dict parsed_toml
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_package_entries() List~Dep~
        -_build_poetry_dependency_tree() Dict
        -_extract_poetry_metadata(package) Dict
    }
    
    class PyprojectParser {
        +Dict parsed_toml
        +__init__(content)
        +parse() List~Dep~
        +validate_content() bool
        +get_metadata() Dict
        -_parse_dependencies_section() List~Dep~
        -_parse_optional_dependencies() List~Dep~
        -_handle_pep621_format() Dict
    }

    BaseParser <|-- PackageJsonParser
    BaseParser <|-- PackageLockV2Parser
    BaseParser <|-- YarnLockParser
    BaseParser <|-- RequirementsParser
    BaseParser <|-- PoetryLockParser
    BaseParser <|-- PyprojectParser
    
    PackageJsonParser : +JavaScript/NPM
    PackageLockV2Parser : +JavaScript/NPM
    YarnLockParser : +JavaScript/NPM
    RequirementsParser : +Python/PyPI
    PoetryLockParser : +Python/PyPI
    PyprojectParser : +Python/PyPI
```

## Lock File Generator Architecture

```mermaid
classDiagram
    class BaseLockGenerator {
        <<abstract>>
        +str ecosystem
        +__init__(ecosystem)
        +generate_lock_file(manifest_content) Tuple~str, str~*
        +can_generate(manifest_filename) bool*
        +get_dependencies(manifest_content) List~Dep~*
        -_validate_manifest(content) bool
        -_create_temp_file(content) str
        -_cleanup_temp_file(path)
    }
    
    class NpmLockGenerator {
        +__init__()
        +generate_lock_file(package_json) Tuple~str, str~
        +can_generate(filename) bool
        +get_dependencies(package_json) List~Dep~
        -_run_npm_install(temp_dir) str
        -_parse_npm_ls_output(output) List~Dep~
        -_handle_npm_errors(error) Exception
        -_validate_npm_environment() bool
    }
    
    class PythonLockGenerator {
        +__init__()
        +generate_lock_file(requirements_txt) Tuple~str, str~
        +can_generate(filename) bool
        +get_dependencies(requirements_txt) List~Dep~
        -_create_virtual_env() str
        -_install_dependencies(venv_path, requirements) str
        -_run_pipdeptree(venv_path) str
        -_parse_pipdeptree_output(output) List~Dep~
        -_cleanup_virtual_env(venv_path)
    }

    BaseLockGenerator <|-- NpmLockGenerator
    BaseLockGenerator <|-- PythonLockGenerator
```

## Web API Models

```mermaid
classDiagram
    class AppState {
        +Dict~str, ScanProgress~ active_jobs
        +Dict~str, Report~ completed_reports
        +Dict~str, WebSocket~ websocket_connections
        +int max_concurrent_jobs
        +__init__()
        +create_job(scan_request) str
        +update_progress(job_id, progress)
        +complete_job(job_id, report)
        +fail_job(job_id, error)
        +get_job_progress(job_id) ScanProgress
        +get_job_report(job_id) Report
        +cleanup_old_jobs()
        -_generate_job_id() str
        -_is_job_expired(job_id) bool
    }
    
    class ScanService {
        +AppState app_state
        +CoreScanner core_scanner
        +__init__(app_state)
        +start_scan(scan_request) str
        +get_progress(job_id) ScanProgress
        +get_report(job_id) Report
        -_run_scan_async(job_id, scan_request)
        -_progress_callback(job_id, percent, step)
        -_handle_scan_error(job_id, error)
    }
    
    class RateLimiter {
        +Dict~str, List~ request_history
        +int max_requests
        +int time_window
        +__init__(max_requests, time_window)
        +check_rate_limit(client_ip) bool
        +add_request(client_ip)
        +get_remaining_requests(client_ip) int
        +get_reset_time(client_ip) datetime
        -_cleanup_old_requests()
        -_get_current_window_requests(client_ip) int
    }

    ScanService --> AppState
    ScanService --> CoreScanner
    AppState *-- ScanProgress : manages
    AppState *-- Report : stores
```

## Key Design Patterns

### 🏭 **Factory Pattern**
- **ParserFactory**: Dynamically creates appropriate parsers based on file format detection
- **Centralized Logic**: Single point of control for parser selection and instantiation
- **Extensibility**: Easy to add new parsers without modifying existing code

### 📦 **Strategy Pattern** 
- **BaseResolver**: Different resolution strategies for Python vs JavaScript ecosystems
- **BaseParser**: Different parsing strategies for various file formats
- **BaseLockGenerator**: Different lock file generation strategies per ecosystem

### 🔍 **Observer Pattern**
- **Progress Callbacks**: CoreScanner notifies UI components of scan progress
- **WebSocket Updates**: Real-time progress updates for web interface
- **Event-driven Architecture**: Loose coupling between components

### 💾 **Repository Pattern**
- **CacheManager**: Abstracts database operations for vulnerability caching
- **AppState**: Manages in-memory storage of job states and results
- **Consistent Interface**: Uniform data access patterns across the application

### 🛡️ **Decorator Pattern**
- **Rate Limiting**: Middleware decorates API endpoints with rate limiting logic
- **Security Headers**: Middleware adds security headers to all responses
- **Input Validation**: Decorates request handlers with validation logic

## Class Relationship Summary

1. **Data Flow**: `ScanRequest` → `CoreScanner` → `Resolvers` → `Parsers` → `OSVScanner` → `Report`
2. **Dependency Injection**: Services depend on abstractions, not concrete implementations
3. **Single Responsibility**: Each class has a focused, well-defined purpose
4. **Composition over Inheritance**: Prefer object composition for flexibility
5. **Interface Segregation**: Small, focused interfaces rather than monolithic ones

This architecture promotes maintainability, testability, and extensibility while following established design patterns and SOLID principles.