# 🖥️ CLI Usage Guide

Complete reference for using DepScan's command-line interface.

## 🚀 Quick Start

```bash
# Basic scan of current directory
python cli.py scan .

# Scan specific project with JSON output
python cli.py scan /path/to/project --json report.json

# Include development dependencies
python cli.py scan . --include-dev
```

---

## 📋 Command Reference

### `scan` Command

The primary command for scanning project dependencies.

#### Basic Syntax
```bash
python cli.py scan <PATH> [OPTIONS]
```

#### Arguments

**`PATH`** *(required)*
- Path to project directory or specific dependency file
- Can be absolute or relative path
- Examples: `.`, `../my-project`, `/home/user/app`

#### Options

**`--json, -j <filename>`**
- Export detailed report as JSON file  
- Includes all vulnerability data, metadata, and statistics
- Example: `--json security-report.json`

**`--include-dev / --no-include-dev`**
- Include or exclude development dependencies
- Default: `--include-dev` (includes dev dependencies)
- Example: `--no-include-dev` for production-only scan

**`--ignore-severity <LEVEL>`** *(multiple)*
- Ignore vulnerabilities of specified severity levels
- Options: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`
- Can be used multiple times
- Example: `--ignore-severity LOW --ignore-severity MEDIUM`

**`--open, -o`**
- Start web server and open browser after scan
- Useful for interactive result exploration
- Example: `--open`

**`--port, -p <PORT>`**
- Specify port for web server (when using `--open`)
- Default: `8000`
- Example: `--port 8080`

#### Examples

```bash
# Basic project scan
python cli.py scan /home/user/my-app

# Production dependencies only
python cli.py scan . --no-include-dev

# Ignore low-severity vulnerabilities  
python cli.py scan . --ignore-severity LOW

# Export detailed JSON report
python cli.py scan . --json detailed-report.json

# Multiple options combined
python cli.py scan ./backend --no-include-dev --ignore-severity LOW --json prod-security.json

# Open web interface after scan
python cli.py scan . --open --port 8080
```

### `version` Command

Display version and system information.

```bash
python cli.py version
```

Output:
```
DepScan - Dependency Vulnerability Scanner
Version: 1.0.0
Made with ♥ by DepScan Team
```

---

## 📊 Output Formats

### Console Output

Default rich console output with formatted tables and colors.

```
🔍 Scanning JavaScript dependencies...
✅ Found dependencies in: JavaScript  
📦 Scanning 47 dependencies...

🚨 3 vulnerabilities found:

┌──────────────────────────────────────────────────────────────────────┐
│                        Vulnerability Report                          │
├─────────────┬─────────┬──────────────┬──────────┬──────────────────────┤
│ Package     │ Version │ Severity     │ CVE      │ Fix Available        │
├─────────────┼─────────┼──────────────┼──────────┼──────────────────────┤
│ lodash      │ 4.17.20 │ HIGH         │ CVE-2020 │ >=4.17.21           │
│ minimist    │ 0.0.8   │ CRITICAL     │ CVE-2020 │ >=1.2.5             │
│ node-fetch  │ 2.6.0   │ MEDIUM       │ CVE-2022 │ >=2.6.7             │  
└─────────────┴─────────┴──────────────┴──────────┴──────────────────────┘

📈 Summary: 3 vulnerable / 47 total (6.4% vulnerable)
```

### JSON Output

Structured JSON report for integration and further processing.

```json
{
  "job_id": "cli_1640995200",
  "status": "COMPLETED", 
  "total_dependencies": 47,
  "vulnerable_count": 3,
  "vulnerable_packages": [
    {
      "package": "lodash",
      "version": "4.17.20",
      "ecosystem": "npm",
      "vulnerability_id": "GHSA-35jh-r3h4-6jhm",
      "severity": "HIGH",
      "cve_ids": ["CVE-2020-8203"],
      "summary": "Prototype Pollution in lodash",
      "description": "lodash versions prior to 4.17.21 are vulnerable to Prototype Pollution.",
      "advisory_url": "https://github.com/advisories/GHSA-35jh-r3h4-6jhm",
      "fixed_range": ">=4.17.21",
      "published": "2020-05-08T18:25:00Z",
      "modified": "2021-01-08T19:02:00Z"
    }
  ],
  "dependencies": [
    {
      "name": "lodash",
      "version": "4.17.20", 
      "ecosystem": "npm",
      "path": ["my-app", "express", "lodash"],
      "is_direct": false,
      "is_dev": false
    }
  ],
  "suppressed_count": 0,
  "meta": {
    "generated_at": "2024-01-01T12:00:00Z",
    "ecosystems": ["npm"],
    "scan_options": {
      "include_dev_dependencies": true,
      "ignore_severities": [],
      "ignore_rules": []
    }
  }
}
```

---

## 🎯 Supported File Types

DepScan automatically detects and processes these dependency files:

### JavaScript/Node.js
- ✅ `package.json` (manifest)
- ✅ `package-lock.json` v1, v2, v3 (npm lockfile)  
- ✅ `yarn.lock` (Yarn lockfile)

### Python  
- ✅ `requirements.txt` (pip)
- ✅ `poetry.lock` (Poetry lockfile)
- ✅ `pyproject.toml` (Poetry/PEP 621)
- ✅ `Pipfile` + `Pipfile.lock` (Pipenv)

### Smart File Detection

DepScan uses intelligent prioritization:

1. **Lockfiles first** - Most accurate transitive dependencies
   - `poetry.lock` > `pyproject.toml`
   - `package-lock.json` > `package.json`
   - `yarn.lock` > `package.json`

2. **Manifest fallback** - Direct dependencies only
   - Used when no lockfiles available
   - Less comprehensive but still valuable

3. **Multi-ecosystem support** - Single command scans all ecosystems
   - Automatically detects Python AND JavaScript files
   - Combines results into unified report

---

## 🔧 Advanced Usage

### Environment Variables

Configure DepScan behavior via environment variables:

```bash
# Cache configuration
export CACHE_TTL_HOURS=48
export CACHE_CLEANUP_INTERVAL=12

# API rate limiting
export OSV_RATE_LIMIT_CALLS=50
export OSV_RATE_LIMIT_PERIOD=60

# Run scan
python cli.py scan .
```

### Batch Processing

Scan multiple projects efficiently:

```bash
#!/bin/bash
# scan-all-projects.sh

PROJECTS=(
    "/home/user/project1"
    "/home/user/project2" 
    "/home/user/project3"
)

for project in "${PROJECTS[@]}"; do
    echo "Scanning $project..."
    python cli.py scan "$project" --json "$(basename "$project")-report.json"
done
```

### CI/CD Integration

#### GitHub Actions

```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install DepScan
        run: |
          git clone https://github.com/therickybobbeh/dep-scanner.git
          cd dep-scanner/backend
          pip install -r requirements.txt
          
      - name: Run Security Scan
        run: |
          cd dep-scanner
          python backend/cli.py scan ${{ github.workspace }} --json security-report.json
          
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: security-report
          path: dep-scanner/security-report.json
```

#### Jenkins

```groovy
pipeline {
    agent any
    
    stages {
        stage('Security Scan') {
            steps {
                sh '''
                    python3 -m venv venv
                    source venv/bin/activate
                    
                    git clone https://github.com/therickybobbeh/dep-scanner.git
                    cd dep-scanner/backend
                    pip install -r requirements.txt
                    
                    python cli.py scan ${WORKSPACE} --json security-report.json
                '''
                
                archiveArtifacts artifacts: 'dep-scanner/security-report.json'
                
                script {
                    def report = readJSON file: 'dep-scanner/security-report.json'
                    if (report.vulnerable_count > 0) {
                        currentBuild.result = 'UNSTABLE'
                        echo "Found ${report.vulnerable_count} vulnerabilities"
                    }
                }
            }
        }
    }
}
```

### Custom Scanning Scripts

#### Severity-based Actions

```python
#!/usr/bin/env python3
"""
Custom scanning script with severity-based actions
"""
import json
import subprocess
import sys

def run_scan(project_path):
    """Run DepScan and return parsed results"""
    cmd = [
        "python", "cli.py", "scan", project_path, 
        "--json", "temp-report.json"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    with open("temp-report.json") as f:
        return json.load(f)

def main():
    report = run_scan(".")
    
    critical_count = sum(1 for vuln in report["vulnerable_packages"] 
                        if vuln["severity"] == "CRITICAL")
    
    high_count = sum(1 for vuln in report["vulnerable_packages"] 
                    if vuln["severity"] == "HIGH")
    
    if critical_count > 0:
        print(f"❌ CRITICAL: {critical_count} critical vulnerabilities found!")
        sys.exit(1)
    elif high_count > 3:
        print(f"⚠️ WARNING: {high_count} high-severity vulnerabilities found!")
        sys.exit(1)  
    else:
        print("✅ Security scan passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
```

---

## 🐛 Troubleshooting

### Common Issues

#### No Dependencies Found
```
Error: No dependencies found in repository
```

**Causes & Solutions:**
- **Missing files**: Ensure dependency files exist (`package.json`, `requirements.txt`, etc.)
- **Wrong directory**: Check you're in the correct project directory
- **Unsupported format**: Verify file format is supported

#### Permission Denied
```
Error: Permission denied accessing /path/to/project
```

**Solutions:**
- Check file permissions: `ls -la /path/to/project`
- Run with appropriate permissions
- Ensure virtual environment is activated

#### API Rate Limiting
```
Warning: Rate limited by OSV.dev API
```

**Solutions:**
- Wait a few minutes and retry
- Results are cached, subsequent scans will be faster
- Reduce scan frequency if scanning frequently

#### Memory Issues
```
Error: Out of memory during dependency resolution
```

**Solutions:**
- Use lockfiles instead of manifest files (more efficient)
- Scan smaller projects individually
- Increase system memory
- Process in batches

### Performance Optimization

#### Use Lockfiles
```bash
# Slower (resolves transitive dependencies manually)
python cli.py scan . --no-include-dev

# Faster (uses pre-resolved lockfile)  
# Ensure package-lock.json or poetry.lock exists
python cli.py scan .
```

#### Cache Management
```bash
# Cache statistics
python -c "
import sqlite3
conn = sqlite3.connect('backend/osv_cache.db')
print(f'Cache entries: {conn.execute(\"SELECT COUNT(*) FROM cache\").fetchone()[0]}')
"

# Clear cache if needed
rm backend/osv_cache.db
```

### Getting Help

1. **Verbose Output**: Add debug information to identify issues
2. **Log Files**: Check backend logs for detailed error messages  
3. **Test Environment**: Run `./run_tests.py` to verify installation
4. **GitHub Issues**: Report bugs at [repository issues](https://github.com/therickybobbeh/dep-scanner/issues)

---

## 📚 Next Steps

- **🌐 [Web Interface Guide](web-interface.md)** - Use the interactive dashboard
- **⚙️ [Configuration Guide](configuration.md)** - Customize DepScan behavior  
- **🔧 [Development Setup](../development/setup.md)** - Contribute to DepScan
- **📊 [API Documentation](../api/endpoints.md)** - Integrate with other tools