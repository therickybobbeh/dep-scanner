# 🚀 DepScan Deployment Guide

DepScan offers multiple deployment options to fit different use cases, from simple pip installation to production AWS deployment.

## 📦 Quick Install (Recommended for Most Users)

### Option 1: Install from TestPyPI (Current)
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner
```

Then use anywhere:
```bash
multi-vuln-scanner scan ./package.json
multi-vuln-scanner scan ./requirements.txt --output csv
# Backward compatibility
dep-scan scan ./package.json
```

> **Note**: We currently publish only to TestPyPI. Production PyPI installation will be available in the future.

### Option 2: Local Development Install
```bash
git clone <your-repository-url>
cd socketTest/backend
pip install -e .
```

## 🏗️ Production Deployment Options

### 🌐 AWS MVP Deployment

**For Simple Web Applications**

Deploy the web interface to AWS using minimal infrastructure:

```bash
# 1. Configure your deployment
cd deploy/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your settings

# 2. Deploy infrastructure  
terraform init
terraform apply

# 3. Set up GitHub Actions
# Add AWS_ROLE_ARN secret to GitHub repository

# 4. Push to deploy
git push origin main
```

**📖 Full AWS Guide:** [deploy/README.md](deploy/README.md)

**MVP Features:**
- 🔄 CI/CD with GitHub Actions
- 🐳 ECS Fargate serverless containers
- 🔒 AWS Secrets Manager for config
- 📦 ECR for container images
- 💰 ~$17-27/month estimated cost

### 🐳 Docker Deployment

**For Self-Hosted Environments**

```bash
# Backend only
docker build -f deploy/docker/Dockerfile.backend -t dep-scan-api .
docker run -p 8000:8000 dep-scan-api

# Full stack with frontend
docker-compose -f deploy/docker/docker-compose.yml up
```

### 📊 Package Distribution

**For Library/CLI Distribution**

Publish to TestPyPI (production PyPI coming later):

```bash
# Build package
make -f Makefile.publish build

# Test locally
make -f Makefile.publish test-package

# Publish to TestPyPI
make -f Makefile.publish publish-test

# Production PyPI (disabled for now)
# make -f Makefile.publish publish-prod
```

**📖 Full TestPyPI Guide:** [.github/PYPI_SETUP.md](.github/PYPI_SETUP.md)

## 🎯 Choose Your Deployment

| Use Case | Recommended Option | Cost | Complexity |
|----------|-------------------|------|------------|
| Personal CLI usage | TestPyPI install | Free | ⭐ |
| Team CLI usage | TestPyPI package | Free | ⭐⭐ |
| Internal web app | Docker Compose | Server costs | ⭐⭐ |
| Simple web service | AWS ECS MVP | ~$17-27/month | ⭐⭐⭐ |
| Enterprise deployment | Custom scaling | Varies | ⭐⭐⭐⭐ |

> **Note**: CLI installation currently uses TestPyPI. Production PyPI will be available once testing is complete.

## 🔧 Configuration Options

### Environment Variables

```bash
# Backend API configuration
export DEPSCAN_API_HOST=0.0.0.0
export DEPSCAN_API_PORT=8000
export DEPSCAN_CORS_ORIGINS="https://yourdomain.com"

# Security settings
export DEPSCAN_ALLOWED_HOSTS="yourdomain.com,localhost"
export DEPSCAN_LOG_LEVEL=INFO

# Database (optional, uses SQLite by default)
export DEPSCAN_DATABASE_URL="postgresql://user:pass@localhost/depscan"
```

### CLI Configuration

Create `~/.depscan/config.yaml`:
```yaml
# Default scan options
default_output: json
ignore_severities: [LOW]
include_dev: false

# Output settings
output_directory: ./scan-results/
timestamp_files: true

# API settings (for web interface)
api_host: localhost
api_port: 8000
```

## 📁 Project Structure

```
your-project/
├── package.json          # JavaScript dependencies
├── requirements.txt      # Python dependencies  
├── .depscan/            # Configuration directory
│   └── config.yaml      # CLI configuration
└── scan-results/        # Default output directory
    ├── latest.json      # Most recent scan
    ├── vulnerabilities.csv
    └── history/         # Previous scans
```

## 🔒 Security Considerations

### Production Security Checklist

- [ ] **HTTPS enabled** (automatic with AWS deployment)
- [ ] **Secrets management** (AWS Secrets Manager / environment variables)
- [ ] **Network security** (VPC, security groups, firewall rules)
- [ ] **Authentication** (implement if needed for your use case)
- [ ] **Rate limiting** (included in web API)
- [ ] **Input validation** (built into scanner)
- [ ] **Container scanning** (automatic in CI/CD pipeline)
- [ ] **Dependency updates** (monitor with scanner itself!)

### CLI Security

- **No credentials required** for basic scanning
- **Local-only processing** (no data sent to external services)
- **Open source** (full code transparency)
- **Offline capable** (after initial OSV database sync)

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check API health
curl https://your-deployment.com/health

# Check CLI health
dep-scan --version
dep-scan scan --dry-run package.json
```

### Updates

```bash
# Update CLI (TestPyPI)
pip install --upgrade --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner

# Update AWS deployment
git push origin main  # Triggers automatic deployment

# Update TestPyPI package
# Increment version in pyproject.toml, then:
make -f Makefile.publish build
make -f Makefile.publish publish-test
```

### Monitoring

- **AWS**: CloudWatch dashboards and alarms
- **CLI**: Built-in performance metrics
- **API**: Health endpoints and structured logging

## 🆘 Support & Troubleshooting

### Common Issues

1. **Installation fails**: Check Python version (3.10+ required)
2. **Scan fails**: Verify file format and accessibility
3. **AWS deployment fails**: Check AWS credentials and permissions
4. **Package publishing fails**: Verify PyPI credentials

### Getting Help

- **📖 Documentation**: Check this guide and README.md
- **🐛 Issues**: Create GitHub Issues in your repository
- **💬 Discussions**: Use GitHub Discussions for questions
- **📧 Security**: Report security issues through your repository

## 🚀 Quick Start Commands

```bash
# Try it out immediately (TestPyPI)
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ multi-vuln-scanner
multi-vuln-scanner scan package.json

# Self-host with Docker
docker run -p 8000:8000 dep-scan:latest

# Deploy to AWS (production)
cd deploy && ./scripts/deploy.sh deploy

# Publish new version to TestPyPI
make -f Makefile.publish build && make -f Makefile.publish publish-test
```

## 📈 Scaling & Performance

### Performance Characteristics

- **CLI**: Scans 100-500 dependencies in 5-15 seconds
- **API**: Handles 10-50 concurrent scans
- **Memory**: ~100-500MB per scan (depends on dependency count)
- **Storage**: Minimal (only scan results and OSV cache)

### Scaling Options

1. **Horizontal**: Multiple API instances behind load balancer
2. **Vertical**: Increase CPU/memory allocation
3. **Caching**: Redis for scan result caching
4. **Database**: PostgreSQL for high-concurrency scenarios

---

*Choose the deployment option that best fits your needs. Start simple with pip install, then scale up as required.*