@echo off
REM Development server startup script for Windows
REM Usage: dev-server.bat

echo ========================================
echo Code Reviewer - Development Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies if needed
echo Installing/updating dependencies...
pip install -e ".[dev,llm]" -q
echo.

REM Set environment variables for development
set GITHUB_TOKEN=test_token_placeholder
set GITHUB_OWNER=your-org
set GITHUB_REPO=your-repo
set LOG_LEVEL=DEBUG
set USE_LLM_LOGIC=false
set USE_LLM_SECURITY=false

echo ========================================
echo Starting FastAPI development server...
echo ========================================
echo.
echo Server will be available at: http://localhost:8000
echo API documentation at: http://localhost:8000/docs
echo.
echo Press CTRL+C to stop the server.
echo.

REM Start the development server with reload
uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000

REM Keep window open on error
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Server failed to start!
    echo Press any key to continue...
    pause
)
