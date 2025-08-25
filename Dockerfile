# Multi-stage Docker build for DepScan
# Use bullseye (Debian) instead of Alpine for better ARM64 compatibility
FROM node:18-bullseye-slim AS frontend-builder

# Build frontend with better ARM64 compatibility
WORKDIR /app/frontend
COPY frontend/package*.json ./

# Install dependencies with explicit architecture support and clean cache
RUN npm ci --production=false --no-audit --no-fund && \
    npm cache clean --force

COPY frontend/ ./
RUN npm run build

# Python backend stage - Use latest Python for security
FROM python:3.12-slim AS backend

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/backend

# Install system dependencies and clean up in one layer for smaller image
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Create directories
RUN mkdir -p /app/backend /app/frontend/dist /app/data
WORKDIR /app

# Copy Python requirements first for better caching
COPY backend/requirements.txt backend/
RUN pip install -r backend/requirements.txt

# Copy backend code
COPY backend/ backend/

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist/ frontend/dist/

# Create cache directory and set permissions
RUN chown -R app:app /app
RUN mkdir -p /app/data && chown -R app:app /app/data

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check using curl (more reliable and lighter)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command runs the web server
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]