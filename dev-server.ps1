# Development server startup script for Windows PowerShell
# Usage: .\dev-server.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Code Reviewer - Development Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host ""

# Install dependencies if needed
Write-Host "Installing/updating dependencies..." -ForegroundColor Yellow
pip install -e ".[dev,llm]" -q
Write-Host ""

# Set environment variables for development
$env:GITHUB_TOKEN = "test_token_placeholder"
$env:GITHUB_OWNER = "your-org"
$env:GITHUB_REPO = "your-repo"
$env:LOG_LEVEL = "DEBUG"
$env:USE_LLM_LOGIC = "false"
$env:USE_LLM_SECURITY = "false"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting FastAPI development server..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server will be available at: " -NoNewline
Write-Host "http://localhost:8000" -ForegroundColor Green
Write-Host "API documentation at: " -NoNewline
Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "Press CTRL+C to stop the server."
Write-Host ""

# Start the development server with reload
uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000

# Handle errors
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Server failed to start!" -ForegroundColor Red
    Write-Host "Press Enter to continue..."
    Read-Host
}
