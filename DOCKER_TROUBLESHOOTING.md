# Docker Troubleshooting Guide

## Common Issues and Solutions

### 1. Import Errors in Backend

**Symptoms:**
- `ModuleNotFoundError` or `ImportError` when starting backend container
- Missing transitive resolver modules

**Solutions:**
```bash
# Rebuild without cache to ensure all modules are included
docker compose -f docker-compose.dev.yml build --no-cache backend

# Check if all Python modules have proper __init__.py files
find backend -name "*.py" -path "*/resolver/*" | head -10
```

### 2. Frontend Build Issues

**Symptoms:**
- npm install fails in frontend container
- Missing package-lock.json errors
- Vite dev server won't start

**Solutions:**
```bash
# Clear frontend cache and rebuild
docker compose -f docker-compose.dev.yml build --no-cache frontend

# Check that package-lock.json is properly mounted
docker compose -f docker-compose.dev.yml exec frontend ls -la /app/

# Verify Node.js version compatibility
docker compose -f docker-compose.dev.yml exec frontend node --version
```

### 3. Volume Mount Issues

**Symptoms:**
- Changes to source code not reflected in container
- Permission denied errors
- Missing files in container

**Solutions:**
```bash
# Check volume mounts
docker compose -f docker-compose.dev.yml config | grep -A 10 volumes

# Fix permissions (Linux/macOS)
sudo chown -R $USER:$USER ./backend ./frontend ./data ./logs

# Remove existing volumes and recreate
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

### 4. Environment Variable Issues

**Symptoms:**
- Configuration not loading correctly
- Cache settings not applied
- API endpoints not working

**Solutions:**
```bash
# Check environment variables in container
docker compose -f docker-compose.dev.yml exec backend env | grep -E "(API_|CACHE_|NPM_|PYPI_)"

# Copy and customize environment file
cp .env.dev .env
# Edit .env as needed

# Restart with new environment
docker compose -f docker-compose.dev.yml restart
```

### 5. Network Connectivity Issues

**Symptoms:**
- Frontend can't reach backend API
- WebSocket connections fail
- Health checks timeout

**Solutions:**
```bash
# Check network configuration
docker compose -f docker-compose.dev.yml exec frontend ping backend

# Verify port mappings
docker compose -f docker-compose.dev.yml ps

# Check backend health endpoint
curl -f http://localhost:8000/health

# Check frontend proxy configuration
docker compose -f docker-compose.dev.yml logs frontend | grep -i proxy
```

### 6. Database/Cache Issues

**Symptoms:**
- OSV cache database errors
- Version resolution cache problems
- SQLite database locked

**Solutions:**
```bash
# Clear cache database
rm -f data/osv_cache.db
docker compose -f docker-compose.dev.yml restart backend

# Check cache directory permissions
ls -la data/
mkdir -p data logs
chown -R $USER:$USER data logs
```

### 7. Performance Issues

**Symptoms:**
- Slow startup times
- High memory usage
- Container resource limits hit

**Solutions:**
```bash
# Increase Docker resources in Docker Desktop
# Memory: 4GB+ recommended
# CPU: 2+ cores recommended

# Check resource usage
docker stats

# Optimize development settings
# Reduce MAX_TRANSITIVE_DEPTH in development
# Lower MAX_CONCURRENT_REQUESTS
```

## Debugging Commands

### View Container Logs
```bash
# All services
docker compose -f docker-compose.dev.yml logs

# Specific service
docker compose -f docker-compose.dev.yml logs backend
docker compose -f docker-compose.dev.yml logs frontend

# Follow logs in real-time
docker compose -f docker-compose.dev.yml logs -f backend
```

### Execute Commands in Containers
```bash
# Backend Python shell
docker compose -f docker-compose.dev.yml exec backend python -c "import backend.core.resolver; print('OK')"

# Frontend shell
docker compose -f docker-compose.dev.yml exec frontend sh

# Check Python imports
docker compose -f docker-compose.dev.yml exec backend python -c "
from backend.core.resolver.utils.npm_transitive_resolver import NpmTransitiveDependencyResolver
print('Transitive resolver imported successfully')
"
```

### Container Inspection
```bash
# Check container status
docker compose -f docker-compose.dev.yml ps

# Inspect volumes
docker volume ls | grep dep-scanner
docker volume inspect frontend_node_modules

# Check network
docker network ls | grep dep-scanner
```

## Fresh Start Procedure

If all else fails, completely reset the Docker environment:

```bash
# Stop all containers
docker compose -f docker-compose.dev.yml down

# Remove volumes
docker compose -f docker-compose.dev.yml down -v

# Remove images
docker compose -f docker-compose.dev.yml down --rmi all

# Prune system (careful - affects other projects)
docker system prune -f

# Rebuild everything
docker compose -f docker-compose.dev.yml build --no-cache
docker compose -f docker-compose.dev.yml up
```

## Production/Staging Issues

For staging environment issues, replace `docker-compose.dev.yml` with `docker-compose.staging.yml` in the above commands.

Additional staging checks:
```bash
# Check Nginx configuration
docker compose -f docker-compose.staging.yml exec nginx nginx -t

# Verify SSL certificates (if used)
docker compose -f docker-compose.staging.yml exec nginx ls -la /etc/nginx/ssl/

# Check frontend build
docker compose -f docker-compose.staging.yml exec frontend ls -la /usr/share/nginx/html/
```

## Getting Help

1. Run the validation script: `./scripts/validate-docker.sh`
2. Check logs: `docker compose -f docker-compose.dev.yml logs`
3. Verify configuration: `docker compose -f docker-compose.dev.yml config`
4. Test individual components: Use the debugging commands above