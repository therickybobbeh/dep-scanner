# DepScan CLI Usage Guide

## Enhanced CLI Features

### Default Behavior
The CLI displays full URLs for vulnerabilities in the Advisory URL column, making it suitable for CI/CD pipelines and automated environments.

**Default vulnerability table:**
```
┌─────────┬─────────┬──────────┬────────┬──────────────────┬──────────┬─────────────────────────────────────────┐
│ Package │ Version │ Type     │ Source │ Vulnerability ID │ Severity │ Advisory URL                            │
├─────────┼─────────┼──────────┼────────┼──────────────────┼──────────┼─────────────────────────────────────────┤
│ lodash  │ 4.17.15 │ direct   │ direct │ GHSA-jf85-cpcp   │ HIGH     │ https://osv.dev/vulnerability/GHSA-...  │
└─────────┴─────────┴──────────┴────────┴──────────────────┴──────────┴─────────────────────────────────────────┘
```

#### `--verbose` / `-v` - Show detailed file processing
Shows which dependency files are being processed during the scan.

```bash
# Standard output
python -m backend.cli.main scan

# Verbose output with file details
python -m backend.cli.main scan --verbose
python -m backend.cli.main scan -v
```

**Verbose output example:**
```
⠋ Starting scan...
Scanning for Python dependency files...
Processing file: requirements.txt
Processing file: poetry.lock
Found 25 Python dependencies
Scanning for JavaScript dependency files...
Processing file: package.json
Processing file: package-lock.json  
Found 127 JavaScript dependencies
⠋ Querying vulnerabilities for 152 dependencies...
✓ Scan completed!
```

### Verbose Usage

```bash
# Show detailed file processing information
python -m backend.cli.main scan --verbose

# Short form
python -m backend.cli.main scan -v
```

### All Available Commands

#### Basic Scan
```bash
# Scan current directory
python -m backend.cli.main scan

# Scan specific path
python -m backend.cli.main scan /path/to/project

# Include development dependencies
python -m backend.cli.main scan --include-dev
```

#### Export Options
```bash
# Export to JSON
python -m backend.cli.main scan --json results.json

# Generate HTML report
python -m backend.cli.main scan --output report.html

# Generate and open HTML report
python -m backend.cli.main scan --open
```

#### Filtering Options
```bash
# Ignore specific severity levels
python -m backend.cli.main scan --ignore-severity low
python -m backend.cli.main scan --ignore-severity medium
```

#### Complete Example
```bash
# Comprehensive scan with all options
python -m backend.cli.main scan /path/to/project \
  --include-dev \
  --verbose \
  --json scan-results.json \
  --output scan-report.html \
  --open
```

### Integration Examples

#### CI/CD Pipeline
```bash
#!/bin/bash
# CI script that fails on vulnerabilities and exports results

python -m backend.cli.main scan \
  --json vulnerability-report.json \
  --ignore-severity low

# Exit code is non-zero if vulnerabilities found
if [ $? -ne 0 ]; then
    echo "❌ Vulnerabilities found - check vulnerability-report.json"
    exit 1
else  
    echo "✅ No vulnerabilities detected"
fi
```

#### Automated Reporting
```bash
# Generate reports with full URLs for documentation
python -m backend.cli.main scan \
  --verbose \
  --output "security-audit-$(date +%Y%m%d).html" \
  --json "security-data-$(date +%Y%m%d).json"
```

### Exit Codes

- **0**: No vulnerabilities found
- **1**: Vulnerabilities found or scan error

### Supported File Types

**Python:**
- requirements.txt
- poetry.lock  
- Pipfile.lock
- pyproject.toml

**JavaScript:**
- package.json
- package-lock.json
- yarn.lock

### Pro Tips

1. **Use `--verbose` during development** to see exactly which files are being processed
2. **URLs are always displayed** in the Advisory URL column, making it perfect for CI/CD and automated environments
3. **Combine with `--json` export** for integration with other tools
4. **Use `--ignore-severity low`** to focus on critical issues in CI pipelines