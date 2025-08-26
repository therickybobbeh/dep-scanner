# IntelliJ IDEA Setup for DepScan

This document explains how to set up and debug the DepScan application using IntelliJ IDEA.

## Prerequisites

1. **IntelliJ IDEA Ultimate** (required for full stack development)
2. **Python Plugin** (usually pre-installed)
3. **Node.js Plugin** (usually pre-installed)
4. **Python interpreter** configured for the project
5. **Node.js** installed locally

## Project Structure

```
socketTest/
├── backend/           # Python FastAPI backend
├── frontend/          # React TypeScript frontend
├── tests/            # E2E tests
└── .idea/            # IntelliJ configurations
```

## Run Configurations

The project includes several pre-configured run configurations:

### 1. **Backend Server**
- **Purpose**: Runs the FastAPI backend server
- **Command**: `uvicorn backend.web.main:app --host 0.0.0.0 --port 8000 --reload`
- **URL**: http://localhost:8000
- **Auto-reload**: Enabled for development

### 2. **Frontend Dev Server** 
- **Purpose**: Runs the React development server with hot reload
- **Command**: `npm run dev` (from frontend directory)
- **URL**: http://localhost:3000
- **Proxy**: API calls automatically proxied to backend

### 3. **Full Stack App** (Compound)
- **Purpose**: Runs both backend and frontend simultaneously
- **Components**: Backend Server + Frontend Dev Server
- **Recommended**: Use this for full stack development

### 4. **Backend Debug**
- **Purpose**: Runs backend with enhanced debugging
- **Features**: 
  - Debug logging enabled
  - Breakpoint support
  - Environment variables for debugging

### 5. **Run Tests**
- **Purpose**: Runs Python unit tests using pytest
- **Target**: `backend/tests/` directory

### 6. **E2E Tests**
- **Purpose**: Runs Playwright end-to-end tests
- **Command**: `npm run test:e2e`

## Setup Instructions

### 1. Open Project
1. Open IntelliJ IDEA
2. File → Open → Select the `socketTest` directory
3. Choose "Trust Project" if prompted

### 2. Configure Python Interpreter
1. File → Project Structure → SDKs
2. Add Python SDK (recommended: Python 3.11+)
3. Point to your virtual environment or system Python
4. Apply changes

### 3. Configure Node.js
1. File → Settings → Languages & Frameworks → Node.js
2. Set Node.js interpreter path
3. Verify npm/yarn is detected

### 4. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

## Development Workflow

### Quick Start
1. Select **"Full Stack App"** configuration
2. Click Run button (▶️)
3. Both servers will start automatically
4. Open http://localhost:3000 in browser

### Debugging Backend
1. Set breakpoints in Python code
2. Select **"Backend Debug"** configuration  
3. Click Debug button (🐛)
4. Use IntelliJ's debugger features

### Debugging Frontend
1. Select **"Frontend Dev Server"** configuration
2. Click Run button
3. Use browser dev tools for frontend debugging
4. React DevTools extension recommended

## Useful Features

### Code Navigation
- **Ctrl+Click** (Cmd+Click on Mac): Go to definition
- **Ctrl+Shift+F** (Cmd+Shift+F): Global search
- **Ctrl+F12** (Cmd+F12): File structure view

### Debugging
- **F8**: Step over
- **F7**: Step into  
- **F9**: Resume
- **Ctrl+F8** (Cmd+F8): Toggle breakpoint

### Running Tests
- Right-click test files → Run/Debug
- Use **"Run Tests"** configuration for all backend tests
- Use **"E2E Tests"** configuration for integration tests

## Environment Variables

The following environment variables can be set in run configurations:

**Backend:**
- `DEBUG=true` - Enable debug mode
- `LOG_LEVEL=DEBUG` - Set logging level
- `PYTHONPATH=$PROJECT_DIR$` - Python module path

**Frontend:**
- `VITE_API_URL` - Override backend API URL

## Troubleshooting

### Backend Won't Start
1. Check Python interpreter is configured
2. Ensure dependencies are installed: `pip install -r backend/requirements.txt`
3. Verify PYTHONPATH includes project root

### Frontend Won't Start
1. Check Node.js is configured
2. Install dependencies: `npm install` in frontend directory
3. Clear cache: `npm run clean` if available

### Proxy Issues
1. Ensure backend is running on port 8000
2. Check Vite proxy configuration in `frontend/vite.config.ts`
3. Verify no firewall blocking localhost connections

### Tests Failing
1. Ensure both servers are running for E2E tests
2. Check test fixtures exist in `tests/e2e/fixtures/`
3. Install test dependencies: `npm install` in tests directory

## Production Builds

### Build Frontend
```bash
cd frontend
npm run build
```

### Docker Builds
```bash
# Development
docker-compose -f docker-compose.dev.yml up

# Staging  
docker-compose -f docker-compose.staging.yml up
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Playwright Testing](https://playwright.dev/)
- [IntelliJ IDEA Help](https://www.jetbrains.com/help/idea/)

## Support

If you encounter issues:
1. Check this README first
2. Review console logs in IntelliJ
3. Check browser console for frontend issues
4. Verify all dependencies are installed