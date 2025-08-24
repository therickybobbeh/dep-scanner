# Web Interface User Journey

```mermaid
flowchart TD
    Start([User needs to scan dependencies]) --> Discover[🔍 Discovers DepScan web interface<br/>• Team colleague shares URL<br/>• Security tools directory<br/>• Local setup]
    
    Discover --> Dashboard[🌐 Opens web dashboard<br/>React application loads]
    
    Dashboard --> FirstTime{👤 First time user?}
    
    FirstTime -->|Yes| Welcome[📖 Views welcome screen<br/>• Quick start guide<br/>• Demo video/tour<br/>• Interface overview]
    FirstTime -->|No| Prepare
    
    Welcome --> Prepare[📁 Prepares project files<br/>• Locates dependency files<br/>• package.json, requirements.txt<br/>• Multiple files if mixed project]
    
    Prepare --> Upload[🎯 Drag & drop files<br/>onto interface]
    
    Upload --> Validate{✅ Interface validates files}
    
    Validate -->|Valid| Accepted[✅ Files accepted<br/>• Shows file preview<br/>• Displays ecosystem detected<br/>• Configuration options]
    Validate -->|Invalid| Invalid[❌ Invalid files<br/>• Helpful error message<br/>• Suggests correct file types<br/>• User tries again]
    
    Invalid --> Upload
    
    Accepted --> Configure[⚙️ Configure scan options<br/>☑️ Include dev dependencies<br/>☑️ Show all severity levels<br/>☐ Ignore LOW severity]
    
    Configure --> StartScan[🚀 Start scan<br/>Click "Start Security Scan" button]
    
    StartScan --> Progress[⏳ Watch real-time progress<br/>• WebSocket live updates<br/>• Visual progress bar<br/>• Status messages<br/>• User stays engaged]
    
    Progress --> Results{📊 View scan results}
    
    Results -->|Vulnerabilities found| VulnDashboard[⚠️ Interactive vulnerability dashboard<br/>• Browse vulnerability table<br/>• Sort by severity<br/>• Filter by package name<br/>• Click for details]
    Results -->|No vulnerabilities| Success[🎉 No vulnerabilities detected<br/>Project is secure]
    
    VulnDashboard --> VulnDetails[🔍 Review individual vulnerability<br/>• Package: lodash@4.17.20<br/>• CVE: CVE-2020-8203<br/>• Severity: HIGH<br/>• Fix: Upgrade to >=4.17.21]
    
    VulnDetails --> RiskLevel{🎯 Risk assessment}
    
    RiskLevel -->|Critical| Critical[🚨 Critical security issues<br/>• Priority remediation needed<br/>• Export report for dev team]
    RiskLevel -->|Medium/Low| Warning[⚠️ Security issues found<br/>• Plan updates for next sprint<br/>• Monitor for patches]
    
    Success --> Interactive
    Critical --> Interactive
    Warning --> Interactive
    
    Interactive[🎮 Explore interactive features<br/>• Click dependency paths<br/>• View dependency tree<br/>• Filter by ecosystem<br/>• Search specific packages<br/>• Sortable columns<br/>• Real-time filtering]
    
    Interactive --> Export{📤 Need to share results?}
    
    Export -->|Yes| ExportFormat[📄 Choose export format]
    Export -->|No| Screenshots[📷 Use web interface results<br/>Take screenshots if needed]
    
    ExportFormat --> JSON[📋 JSON export<br/>• Download detailed report<br/>• Share with developers]
    ExportFormat --> CSV[📊 CSV export<br/>• Download for spreadsheet<br/>• Share with management]
    
    JSON --> FollowUp
    CSV --> FollowUp
    Screenshots --> FollowUp
    
    FollowUp{🔄 Follow up actions}
    
    FollowUp -->|Vulnerabilities found| Actions[📋 Create action plan<br/>• Create tickets for dev team<br/>• Schedule security update sprint<br/>• Set reminder to re-scan]
    FollowUp -->|No vulnerabilities| Schedule[📅 Schedule regular scans<br/>• Set monthly reminder<br/>• Bookmark interface]
    
    Actions --> Rescan[🔄 Re-scan after fixes<br/>• Upload updated files<br/>• Verify vulnerabilities resolved]
    
    Rescan --> StillVuln{⚠️ Still vulnerable?}
    
    StillVuln -->|Yes| Continue[🔄 Continue remediation<br/>Back to action planning]
    StillVuln -->|No| Resolved[✅ Security issues resolved<br/>Success confirmation]
    
    Continue --> Actions
    
    Schedule --> Regular
    Resolved --> Regular
    
    Regular[🎖️ Become regular user<br/>• Bookmarks web interface<br/>• Uses for all project audits<br/>• Recommends to team<br/>• Requests new features]
    
    Regular --> End([✅ Success])

    %% Styling
    classDef successStyle fill:#d4edda,stroke:#28a745,stroke-width:2px
    classDef warningStyle fill:#fff3cd,stroke:#ffc107,stroke-width:2px
    classDef errorStyle fill:#f8d7da,stroke:#dc3545,stroke-width:2px
    classDef processStyle fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef decisionStyle fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px

    class Accepted,Success,Resolved,Regular,End successStyle
    class VulnDashboard,Warning,Continue warningStyle
    class Invalid,Critical errorStyle
    class Discover,Dashboard,Welcome,Prepare,Upload,Configure,StartScan,Progress,VulnDetails,Interactive,JSON,CSV,Screenshots,Actions,Schedule,Rescan processStyle
    class FirstTime,Validate,Results,RiskLevel,Export,FollowUp,StillVuln decisionStyle
```

## Web Interface User Journey Overview

### **Phase 1: Discovery & Initial Access**
**User Context:**
- Non-technical team members
- Frontend developers
- Security audit requirements
- GUI interface preference
- One-time or occasional usage

**Access Methods:**
- Colleague shares company security tools URL
- Direct link from security documentation
- Local setup with browser access

### **Phase 2: First Experience**
**Dashboard Loading:**
- React application loads in browser
- Clean, intuitive interface presentation
- No setup or installation required

**New User Onboarding:**
- Welcome screen with quick start guide
- Demo video or interactive tour
- Interface feature overview
- Clear call-to-action buttons

### **Phase 3: File Upload & Configuration**
**File Preparation:**
- User locates dependency files on computer
- Supports multiple file types (package.json, requirements.txt, etc.)
- Mixed ecosystem project support

**Drag & Drop Interface:**
- Intuitive file upload mechanism
- Real-time file validation
- Clear feedback on accepted/rejected files
- Helpful error messages for invalid formats

**Scan Configuration:**
- Simple checkbox options
- Development dependency inclusion toggle
- Severity level filtering
- User-friendly option descriptions

### **Phase 4: Real-Time Scanning**
**Live Progress Updates:**
- WebSocket-powered real-time updates
- Visual progress bar with percentages
- Descriptive status messages
- User engagement through visual feedback

**Progress Stages:**
- 🔍 Analyzing files... (10%)
- 📦 Resolving dependencies... (30%)
- 🛡️ Checking security database... (60%)
- 📊 Generating report... (90%)
- ✅ Scan complete! (100%)

### **Phase 5: Interactive Results Exploration**
**Vulnerability Dashboard:**
- Interactive table with sorting and filtering
- Color-coded severity levels
- Click-through for detailed information
- Package-specific vulnerability details

**Interactive Features:**
- Sortable columns for prioritization
- Real-time filtering as user types
- Dependency path visualization
- Ecosystem-based filtering
- Package search functionality

### **Phase 6: Risk Assessment & Action Planning**
**Vulnerability Analysis:**
- **Critical**: Immediate action required, priority remediation
- **Medium/Low**: Planned updates for next sprint
- **None**: Security confirmation and success messaging

**Detailed Vulnerability Information:**
- Package name and version
- CVE identifiers
- Severity classification
- Vulnerability descriptions
- Fix recommendations and version ranges

### **Phase 7: Export & Collaboration**
**Export Options:**
- **JSON**: Detailed technical report for developers
- **CSV**: Spreadsheet format for management reporting
- **Screenshots**: Visual documentation for stakeholders

**Sharing Capabilities:**
- Download reports for offline analysis
- Team collaboration through shared files
- Integration with project management tools

### **Phase 8: Follow-Up & Continuous Usage**
**Action Planning:**
- Ticket creation for development team
- Security update sprint planning
- Remediation timeline establishment
- Re-scan scheduling after fixes

**Ongoing Usage:**
- Regular security audit scheduling
- Interface bookmarking for easy access
- Team recommendation and advocacy
- Feature request submission

## User Characteristics

### **Primary Web Interface Users**
- **Product Managers**: High-level security oversight
- **QA Engineers**: Quality assurance validation
- **Frontend Developers**: JavaScript ecosystem focus
- **Security Analysts**: Vulnerability assessment
- **Non-technical Stakeholders**: Executive reporting

### **Web Interface Strengths**
- **Zero Setup**: No installation or configuration required
- **Visual Appeal**: Intuitive interface with progress indicators
- **Real-Time Feedback**: WebSocket updates keep users engaged
- **Interactive Exploration**: Click, sort, filter, and drill down
- **Collaboration**: Easy sharing and export capabilities
- **Accessibility**: Works on any device with modern browser

### **Key Differentiators**
- **Drag & Drop Simplicity**: Intuitive file upload mechanism
- **Visual Progress**: Real-time scanning updates
- **Interactive Data**: Dynamic result exploration
- **Multiple Export Formats**: Flexible sharing options
- **No Technical Expertise**: Command line knowledge not required