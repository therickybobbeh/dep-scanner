@echo off
REM DepScan Development Environment Setup Script for Windows
REM This script sets up the development environment for DepScan on Windows

setlocal enabledelayedexpansion

echo ========================================
echo DepScan Development Environment Setup
echo ========================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.11+ from: https://python.org
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version') do echo [INFO] Python version: %%i
)

REM Check Node.js
echo Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18+ from: https://nodejs.org
    pause
    exit /b 1
) else (
    for /f %%i in ('node --version') do echo [INFO] Node.js version: %%i
)

REM Check npm
echo Checking npm installation...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed or not in PATH
    pause
    exit /b 1
) else (
    for /f %%i in ('npm --version') do echo [INFO] npm version: %%i
)

echo [SUCCESS] All required dependencies are installed!
echo.

REM Setup environment files
echo ========================================
echo Setting Up Environment Files
echo ========================================

if not exist ".env" (
    echo Creating backend .env file from template...
    copy ".env.development" ".env" >nul
    echo [SUCCESS] Backend .env file created
) else (
    echo [INFO] Backend .env file already exists
)

if not exist "frontend\.env" (
    echo Creating frontend .env file from template...
    copy "frontend\.env.development" "frontend\.env" >nul
    echo [SUCCESS] Frontend .env file created
) else (
    echo [INFO] Frontend .env file already exists
)

echo.

REM Create data directories
echo ========================================
echo Creating Data Directories
echo ========================================

mkdir data 2>nul
mkdir logs 2>nul
mkdir backend\data 2>nul
mkdir backend\logs 2>nul
echo [SUCCESS] Data directories created
echo.

REM Setup backend
echo ========================================
echo Setting Up Backend
echo ========================================

cd backend

if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install backend dependencies
    pause
    exit /b 1
)

echo [SUCCESS] Backend dependencies installed
cd ..
echo.

REM Setup frontend
echo ========================================
echo Setting Up Frontend
echo ========================================

cd frontend
echo Installing frontend dependencies...
npm install

if %errorlevel% neq 0 (
    echo [ERROR] Failed to install frontend dependencies
    pause
    exit /b 1
)

echo [SUCCESS] Frontend dependencies installed
cd ..
echo.

REM Show next steps
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo [SUCCESS] Your DepScan development environment is ready!
echo.
echo Quick Start Options:
echo.
echo Option 1: Manual Development
echo    # Terminal 1 (Backend):
echo    cd backend
echo    .venv\Scripts\activate.bat
echo    python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo    # Terminal 2 (Frontend):
echo    cd frontend
echo    npm run dev
echo.
echo Development URLs:
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo For more commands, check the Makefile or README.md
echo.

pause