# DepScan Architecture Overview

## System Architecture

DepScan is a multi-layered application designed for scanning dependency vulnerabilities in Python and JavaScript projects. The architecture follows a clean separation of concerns with distinct layers for resolving dependencies, scanning for vulnerabilities, and presenting results.

```
┌─────────────────────────────────────────────────┐
│                 User Interfaces                 │
├─────────────────────────────────────────────────┤
│  CLI Tool          │    Web Dashboard (React)   │
│  (Rich Console)    │    (Interactive UI)        │
├────────────────────┼────────────────────────────┤
│                FastAPI REST API                 │
│        (WebSocket + HTTP Endpoints)             │
├─────────────────────────────────────────────────┤
│               Core Business Logic               │
├─────────────────────────────────────────────────┤
│  Dependency Resolvers  │  Vulnerability Scanner │
│  • Python Resolver     │  • OSV.dev Client      │
│  • JavaScript Resolver │  • Caching Layer       │
├────────────────────────┼────────────────────────┤
│  External Dependencies │    Storage Layer       │
│  • OSV.dev API        │  • SQLite Cache        │
│  • Package Registries │  • File System         │
└────────────────────────┴─────────────────────────┘
```

## Core Components

### 1. Dependency Resolvers
Responsible for parsing and resolving dependency trees from various package managers:

- **PythonResolver**: Handles Python ecosystems
  - `requirements.txt` (pip)
  - `pyproject.toml` (Poetry, PEP 621)
  - `Pipfile` (pipenv)  
  - `poetry.lock`, `Pipfile.lock` (lockfiles)

- **JavaScriptResolver**: Handles JavaScript/Node.js ecosystems
  - `package.json` (npm, yarn)
  - `package-lock.json` (npm)
  - `yarn.lock` (yarn)

### 2. Vulnerability Scanner (OSVScanner)
Interfaces with OSV.dev API for vulnerability data:

- **Batch Processing**: Groups queries for efficiency
- **Intelligent Caching**: SQLite-based cache with TTL
- **Rate Limiting**: Exponential backoff and request throttling
- **Error Handling**: Retry logic with circuit breaker patterns

### 3. API Layer (FastAPI)
Provides REST API and WebSocket endpoints:

- **Scan Management**: Asynchronous job processing
- **Real-time Updates**: WebSocket progress notifications
- **Export Capabilities**: JSON/CSV report generation
- **Static File Serving**: Serves React frontend

### 4. CLI Interface
Rich console application for direct usage:

- **Interactive Output**: Formatted tables and progress bars
- **Multiple Output Formats**: Console, JSON
- **Error Handling**: User-friendly error messages

### 5. Web Dashboard (React)
Modern web interface for interactive scanning:

- **File Upload**: Drag-and-drop manifest files
- **Real-time Progress**: WebSocket-powered updates  
- **Interactive Reports**: Filtering, sorting, export
- **Responsive Design**: Works on desktop and mobile

## Data Flow

### 1. Dependency Resolution
```
Input Files → Parser → Dependency Graph → Normalized Dependencies
```

### 2. Vulnerability Scanning  
```
Dependencies → Cache Check → API Queries → Vulnerability Data → Report
```

### 3. Result Processing
```
Raw Vulnerabilities → Severity Analysis → Filtering → Final Report
```

## Key Design Principles

### 1. **Lockfile-First Resolution**
Prioritizes deterministic lockfiles over manifest files for accuracy:
- Poetry.lock/Pipfile.lock over pyproject.toml/Pipfile
- package-lock.json/yarn.lock over package.json

### 2. **Separation of Concerns**
- Resolvers focus only on dependency parsing
- Scanner handles only vulnerability detection
- API layer manages only request/response logic
- UI components handle only presentation

### 3. **Async-First Design**
- All I/O operations use async/await patterns
- Non-blocking API calls and file operations
- Concurrent processing where possible

### 4. **Resilience & Reliability**
- Comprehensive error handling at every layer
- Graceful degradation when services are unavailable
- Input validation and sanitization
- Rate limiting and backoff strategies

### 5. **Performance Optimization**
- Dependency deduplication to minimize API calls
- Intelligent caching with configurable TTL
- Batch processing to reduce network overhead
- Efficient data structures and algorithms

## Security Considerations

### 1. **Input Validation**
- All manifest file contents are validated
- File size limits enforced
- Malicious content detection

### 2. **Network Security**
- HTTPS-only external API calls
- Request timeout and size limits
- Local-only web server binding (127.0.0.1)

### 3. **Data Protection**
- No sensitive data logging
- Temporary file cleanup
- Secure cache storage

## Scalability Features

### 1. **Horizontal Scaling**
- Stateless API design
- External cache storage capability
- Load balancer compatibility

### 2. **Vertical Scaling**
- Configurable batch sizes
- Adjustable rate limits
- Memory-efficient data structures

### 3. **Extensibility**
- Plugin architecture for new resolvers
- Configurable vulnerability sources
- Modular component design