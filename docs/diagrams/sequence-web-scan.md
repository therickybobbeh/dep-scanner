# Web Interface Scanning Workflow

```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant API as FastAPI Backend
    participant WS as WebSocket Handler
    participant ScanSvc as Scan Service
    participant State as App State
    participant Scanner as DepScanner
    participant Resolvers
    participant OSV as OSV Scanner
    participant Cache as Cache Layer

    Note over User, Cache: Initial Setup Phase
    User->>React: open web dashboard
    React->>API: GET /
    API-->>React: serve React app
    React-->>User: dashboard loaded

    Note over User, Cache: File Upload Phase
    User->>React: drag & drop files

    Note right of React: Supported File Upload<br/>• package.json + package-lock.json<br/>• requirements.txt + poetry.lock<br/>• Multiple files simultaneously<br/>• Real-time validation

    React->>React: validate files client-side
    React->>+API: POST /scan/upload-files
    
    API->>+State: create_scan_job(job_id)
    State-->>-API: job created
    
    API-->>-React: {"job_id": "scan_12345", "status": "pending"}

    Note over User, Cache: WebSocket Connection Phase
    React->>+WS: connect to /ws/scan/{job_id}
    WS->>+State: register_connection(job_id, websocket)
    WS-->>-React: connection established
    State-->>-WS: registered

    Note over User, Cache: Background Scanning Phase
    API->>+ScanSvc: start_scan_async(job_id, files)
    
    ScanSvc->>State: update_progress(job_id, "initializing", 0%)
    State->>WS: broadcast_progress(job_id, progress)
    WS->>React: progress update
    React->>User: show progress bar
    
    ScanSvc->>+Scanner: create DepScanner()

    Note over User, Cache: Dependency Resolution Phase
    ScanSvc->>State: update_progress(job_id, "resolving_dependencies", 10%)
    State->>WS: broadcast_progress(job_id, progress)
    WS->>React: "Resolving dependencies..."
    
    ScanSvc->>Scanner: scan_uploaded_files(files, options)
    
    Scanner->>+Resolvers: resolve_dependencies(None, files)

    Note right of Resolvers: Smart Resolution<br/>• Automatic format detection<br/>• Priority-based parsing<br/>• Handles multiple ecosystems<br/>• Error-tolerant processing

    Resolvers->>Resolvers: detect_best_formats(files)
    Resolvers->>Resolvers: parse_all_dependencies()
    
    Resolvers-->>-Scanner: dependencies resolved
    
    Scanner-->>ScanSvc: dependencies found (count: N)
    ScanSvc->>State: update_progress(job_id, "found_N_deps", 30%)
    State->>WS: broadcast_progress(job_id, progress)
    WS->>React: "Found N dependencies"
    React->>User: update progress & stats

    Note over User, Cache: Vulnerability Scanning Phase
    ScanSvc->>State: update_progress(job_id, "scanning_vulnerabilities", 40%)
    State->>WS: broadcast_progress(job_id, progress)
    WS->>React: "Scanning for vulnerabilities..."
    
    Scanner->>+OSV: scan_dependencies(deps)
    
    OSV->>+Cache: check_cache_coverage(deps)
    Cache-->>-OSV: cache_status
    
    loop For each API batch
        ScanSvc->>State: update_progress(job_id, "querying_osv", progress%)
        State->>WS: broadcast_progress(job_id, progress)
        WS->>React: update progress bar
        
        OSV->>OSV: query OSV.dev API
        OSV->>Cache: store_results()
    end
    
    OSV-->>-Scanner: vulnerabilities found

    Note over User, Cache: Report Generation Phase
    ScanSvc->>State: update_progress(job_id, "generating_report", 90%)
    State->>WS: broadcast_progress(job_id, progress)
    WS->>React: "Generating report..."
    
    Scanner->>Scanner: create_report(deps, vulns, metadata)
    Scanner-->>-ScanSvc: final_report
    
    ScanSvc->>+State: store_results(job_id, report)
    ScanSvc->>State: update_progress(job_id, "completed", 100%)
    State->>WS: broadcast_completion(job_id, report_summary)
    State-->>-ScanSvc: stored
    
    WS-->>React: scan completed + summary
    React-->>User: show completion + results preview

    Note over User, Cache: Results Display Phase
    User->>React: view detailed results
    React->>+API: GET /scan/{job_id}/results
    API->>+State: get_scan_results(job_id)
    State-->>-API: full_report
    API-->>-React: detailed report data
    
    React->>React: render interactive report
    React-->>User: show detailed vulnerability report

    Note right of React: Interactive Report Features<br/>• Sortable vulnerability table<br/>• Severity filtering<br/>• Dependency path visualization<br/>• Export options (JSON, CSV)<br/>• Fix recommendations

    Note over User, Cache: Export Options Phase
    alt User requests JSON export
        User->>React: click "Export JSON"
        React->>+API: GET /scan/{job_id}/export/json
        API->>+State: get_scan_results(job_id)
        State-->>-API: report_data
        API-->>-React: JSON file download
        React-->>User: file downloaded
    end

    Note over User, Cache: Cleanup Phase
    ScanSvc-->>-State: cleanup_scan_job(job_id)
    WS-->>-React: connection cleanup

    Note over User, Cache: Web Interface Benefits<br/>✅ Real-time: Live progress updates via WebSocket<br/>✅ Interactive: Click, filter, sort, export<br/>✅ User-friendly: No command line knowledge required<br/>✅ Visual: Charts, graphs, color-coded severity<br/>✅ Collaborative: Shareable URLs and reports
```

## Web Interface Scanning Workflow Overview

### **Phase 1: Initial Setup**
- User accesses web dashboard in browser
- React application loads with intuitive drag-and-drop interface
- FastAPI backend serves the single-page application

### **Phase 2: File Upload**
- **Drag & Drop Interface**: User-friendly file upload with visual feedback
- **Client-Side Validation**: Immediate file type and format validation
- **Multi-File Support**: Handles multiple dependency files simultaneously
- **Format Detection**: Automatically identifies package.json, requirements.txt, etc.

### **Phase 3: WebSocket Connection**
- Real-time connection established between frontend and backend
- Job ID generated for tracking scan progress
- Connection registered in application state for broadcasting updates

### **Phase 4: Background Scanning**
- **Asynchronous Processing**: Scan runs in background without blocking UI
- **Live Progress Updates**: WebSocket provides real-time progress information
- **Visual Feedback**: Progress bar and status messages keep user informed

### **Phase 5: Dependency Resolution**
- **Smart Resolution**: Automatic format detection and parser selection
- **Multi-Ecosystem Support**: Handles JavaScript and Python dependencies
- **Progress Broadcasting**: Real-time updates on dependency discovery
- **Error Tolerance**: Graceful handling of malformed or incomplete files

### **Phase 6: Vulnerability Scanning**
- **Batch Processing**: Efficient API usage with grouped requests
- **Cache Integration**: Leverages cached vulnerability data for performance
- **Live Progress**: Progress bar updates as each batch is processed
- **Rate Limiting**: Respects OSV.dev API limits

### **Phase 7: Report Generation**
- **Comprehensive Report**: Complete scan results with metadata
- **State Storage**: Results stored for future retrieval and export
- **Completion Notification**: WebSocket notifies frontend of completion

### **Phase 8: Interactive Results Display**
- **Rich UI Components**: Interactive tables with sorting and filtering
- **Severity Color Coding**: Visual severity indicators for quick assessment
- **Dependency Path Visualization**: Shows how vulnerabilities are introduced
- **Real-Time Filtering**: Instant results as user applies filters

### **Phase 9: Export Capabilities**
- **Multiple Formats**: JSON for technical analysis, CSV for management
- **Download Integration**: Browser-native file downloads
- **Shareable Reports**: Results can be saved and shared with teams

### **Key Advantages**

**User Experience**
- Zero setup required - runs in any modern browser
- Intuitive drag-and-drop interface
- Real-time progress feedback with WebSocket updates
- Interactive data exploration with sorting and filtering

**Accessibility**
- No command-line knowledge required
- Visual progress indicators and status messages
- Color-coded severity levels for quick assessment
- Works on any device with a web browser

**Collaboration**
- Shareable scan results via URLs
- Export capabilities for team distribution
- Visual reports for stakeholder communication
- Integration-friendly JSON and CSV exports