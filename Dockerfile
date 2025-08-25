# Multi-stage Docker build for DepScan
FROM node:18-alpine AS frontend-builder

# Build frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend/ ./
RUN npm run build

# Python backend stage
FROM python:3.11-slim AS backend

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
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

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=10)"

# Default command runs the web server
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]