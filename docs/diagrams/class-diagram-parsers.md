# Parser Architecture Class Diagram

```mermaid
classDiagram
    %% Base Parser Framework
    class BaseDependencyParser {
        <<abstract>>
        +Ecosystem ecosystem
        +parse(string)* Dep[]
        +can_parse(string)* bool
        +supports_transitive_dependencies()* bool
        +validate_content()
        +handle_parse_error()
    }
    
    class FileFormatDetector {
        <<abstract>>
        +detect_format(dict)* tuple
        +get_supported_formats()* string[]
        +get_format_priority() int
        +validate_format_combination(string[]) bool
    }

    %% JavaScript Parsers
    class PackageJsonParser {
        +VersionCleaner version_cleaner
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_extract_dependencies() dict
        -_is_valid_package_name(string) bool
        -_clean_version_spec(string) string
    }
    
    class PackageLockV1Parser {
        +DependencyTreeBuilder tree_builder
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_extract_dependencies_recursive(dict) Dep[]
        -_build_dependency_paths(dict) dict
    }
    
    class PackageLockV2Parser {
        +DependencyTreeBuilder tree_builder
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_extract_from_packages(dict) Dep[]
        -_resolve_dependency_tree(dict) dict
    }
    
    class YarnLockParser {
        +VersionCleaner version_cleaner
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_parse_package_entry(string) tuple
        -_extract_version_specs(string) string[]
        -_is_likely_direct(string) bool
    }
    
    class NpmLsParser {
        +DependencyTreeBuilder tree_builder
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_execute_npm_ls() string
        -_parse_npm_output(string) dict
    }

    %% Python Parsers
    class RequirementsParser {
        +VersionCleaner version_cleaner
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        +detect_dev_requirements() bool
        -_parse_requirement_line(string) tuple
        -_extract_version(string) string
        -_clean_package_name(string) string
    }
    
    class PoetryLockParser {
        +DependencyTreeBuilder tree_builder
        +PathTracker path_tracker
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_parse_toml_content(string) dict
        -_extract_dependencies(dict) Dep[]
        -_build_dependency_graph(dict) dict
    }
    
    class PyprojectParser {
        +VersionCleaner version_cleaner
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_detect_format(dict) string
        -_parse_pep621_format(dict) Dep[]
        -_parse_poetry_format(dict) Dep[]
    }
    
    class PipfileLockParser {
        +DependencyTreeBuilder tree_builder
        +parse(string) Dep[]
        +can_parse(string) bool
        +supports_transitive_dependencies() bool
        -_parse_json_content(string) dict
        -_extract_default_deps(dict) Dep[]
        -_extract_dev_deps(dict) Dep[]
    }

    %% Parser Factories
    class JavaScriptParserFactory {
        +dict parser_registry
        +get_parser(string, string) BaseDependencyParser
        +get_parser_by_format(string) BaseDependencyParser
        +detect_best_format(dict) tuple
        +get_supported_formats() string[]
        -_detect_package_lock_version(string) string
        -_get_format_priority() dict
        -_is_supported_format(string) bool
    }
    
    class PythonParserFactory {
        +dict parser_registry
        +get_parser(string, string) BaseDependencyParser
        +get_parser_by_format(string) BaseDependencyParser
        +detect_best_format(dict) tuple
        +get_supported_formats() string[]
        -_detect_pyproject_format(string) string
        -_get_format_priority() dict
        -_is_supported_format(string) bool
    }

    %% Utility Classes
    class VersionCleaner {
        +clean_version(string) string
        +normalize_version(string) string
        +is_valid_semver(string) bool
        +extract_base_version(string) string
        +compare_versions(string, string) int
        -_remove_operators() string
        -_handle_wildcards() string
    }
    
    class DependencyTreeBuilder {
        +build_tree(Dep[]) dict
        +find_paths(dict, string) string[]
        +calculate_depth(string) int
        +detect_cycles(dict) string[]
        -_build_adjacency_list() dict
        -_traverse_tree() dict
    }
    
    class PathTracker {
        +track_dependency_path(string, string) string[]
        +get_full_path(string) string[]
        +is_transitive(string) bool
        +get_root_dependencies() string[]
        -_build_path_map() dict
        -_find_shortest_path() string[]
    }

    %% Inheritance relationships
    BaseDependencyParser <|-- PackageJsonParser
    BaseDependencyParser <|-- PackageLockV1Parser
    BaseDependencyParser <|-- PackageLockV2Parser
    BaseDependencyParser <|-- YarnLockParser
    BaseDependencyParser <|-- NpmLsParser
    BaseDependencyParser <|-- RequirementsParser
    BaseDependencyParser <|-- PoetryLockParser
    BaseDependencyParser <|-- PyprojectParser
    BaseDependencyParser <|-- PipfileLockParser

    FileFormatDetector <|-- JavaScriptParserFactory
    FileFormatDetector <|-- PythonParserFactory

    %% Composition relationships
    JavaScriptParserFactory --> PackageJsonParser : creates
    JavaScriptParserFactory --> PackageLockV1Parser : creates
    JavaScriptParserFactory --> PackageLockV2Parser : creates
    JavaScriptParserFactory --> YarnLockParser : creates
    JavaScriptParserFactory --> NpmLsParser : creates

    PythonParserFactory --> RequirementsParser : creates
    PythonParserFactory --> PoetryLockParser : creates
    PythonParserFactory --> PyprojectParser : creates
    PythonParserFactory --> PipfileLockParser : creates

    %% Utility usage
    PackageJsonParser --> VersionCleaner : uses
    YarnLockParser --> VersionCleaner : uses
    RequirementsParser --> VersionCleaner : uses
    PyprojectParser --> VersionCleaner : uses

    PackageLockV1Parser --> DependencyTreeBuilder : uses
    PackageLockV2Parser --> DependencyTreeBuilder : uses
    NpmLsParser --> DependencyTreeBuilder : uses
    PoetryLockParser --> DependencyTreeBuilder : uses
    PipfileLockParser --> DependencyTreeBuilder : uses

    PoetryLockParser --> PathTracker : uses

    %% Styling
    classDef baseClass fill:#E3F2FD,stroke:#1976D2,stroke-width:2px
    classDef jsParser fill:#E8F5E8,stroke:#388E3C,stroke-width:2px
    classDef pyParser fill:#FFF3E0,stroke:#F57C00,stroke-width:2px
    classDef factoryClass fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    classDef utilityClass fill:#FFEBEE,stroke:#D32F2F,stroke-width:2px

    class BaseDependencyParser,FileFormatDetector baseClass
    class PackageJsonParser,PackageLockV1Parser,PackageLockV2Parser,YarnLockParser,NpmLsParser jsParser
    class RequirementsParser,PoetryLockParser,PyprojectParser,PipfileLockParser pyParser
    class JavaScriptParserFactory,PythonParserFactory factoryClass
    class VersionCleaner,DependencyTreeBuilder,PathTracker utilityClass
```

## Parser Architecture Overview

### **Factory Pattern Implementation**

The parser system uses the Factory Pattern for extensible format detection and parser creation:

- **Automatic Format Detection**: Files are analyzed to determine their format
- **Version-Specific Parser Selection**: Different parsers for package-lock.json v1/v2
- **Priority-Based Format Resolution**: Lockfiles preferred over manifest files
- **Extensible Design**: Easy to add new parsers and formats

### **JavaScript Parsers**

**`PackageJsonParser`** - Direct dependencies only
- Parses `package.json` manifest files
- Extracts both production and development dependencies
- Handles version range specifications

**`PackageLockV1Parser`** / **`PackageLockV2Parser`** - Transitive dependencies
- Full dependency tree from npm lockfiles
- Handles different lockfile versions automatically
- Builds complete dependency paths

**`YarnLockParser`** - Yarn lockfile support
- Parses Yarn's custom lockfile format
- Extracts transitive dependencies
- Handles Yarn-specific version resolution

**`NpmLsParser`** - Runtime dependency tree
- Executes `npm ls` to get actual installed dependencies
- Provides most accurate transitive dependency information

### **Python Parsers**

**`RequirementsParser`** - pip requirements files
- Supports `requirements.txt`, `requirements-dev.txt`
- Handles version specifications and constraints
- Direct dependencies only

**`PoetryLockParser`** - Poetry lockfile support  
- Full transitive dependency resolution
- Parses TOML format lockfiles
- Tracks dependency paths and relationships

**`PyprojectParser`** - Modern Python packaging
- Supports both PEP 621 and Poetry formats in `pyproject.toml`
- Auto-detects format type
- Handles optional dependencies

**`PipfileLockParser`** - Pipenv lockfile support
- Parses JSON format lockfiles
- Separates default and development dependencies
- Full transitive dependency information

### **Utility Classes**

**`VersionCleaner`** - Version string normalization
- Handles all semver and version specification formats
- Cleans operators (`^`, `~`, `>=`, etc.)
- Cross-ecosystem version comparison

**`DependencyTreeBuilder`** - Dependency graph analysis
- Builds complete dependency trees from flat lists
- Calculates dependency paths and depths
- Detects circular dependencies

**`PathTracker`** - Dependency relationship tracking
- Tracks how each dependency is reached
- Identifies direct vs transitive dependencies
- Calculates shortest dependency paths