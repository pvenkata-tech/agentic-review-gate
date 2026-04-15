# Webhook Setup Script - Start ngrok and FastAPI server
# Usage: .\setup.ps1

Write-Host "🚀 Starting agentic-review-gate webhook setup..." -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Check if ngrok is installed
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokPath) {
    Write-Host "❌ ngrok is not installed. Install it from: https://ngrok.com/download" -ForegroundColor Red
    exit 1
}

# Start ngrok in background
Write-Host "`n🌐 Starting ngrok on port 8000..." -ForegroundColor Yellow
$ngrokProcess = Start-Process ngrok -ArgumentList "http 8000" -PassThru -NoNewWindow

# Wait for ngrok to start
Start-Sleep -Seconds 3

# Get ngrok public URL
try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -ErrorAction SilentlyContinue
    $ngrokUrl = $response.tunnels[0].public_url
    if ($ngrokUrl) {
        Write-Host "✅ ngrok is running at: $ngrokUrl" -ForegroundColor Green
        Write-Host "`n📝 Update your GitHub webhook with:" -ForegroundColor Cyan
        Write-Host "   Payload URL: $ngrokUrl/webhook/github" -ForegroundColor White
    }
} catch {
    Write-Host "⚠️  Could not retrieve ngrok URL automatically. Check http://127.0.0.1:4040" -ForegroundColor Yellow
}

# Start FastAPI server
Write-Host "`n🔧 Starting FastAPI server..." -ForegroundColor Yellow
Write-Host "📍 Server running at: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "📊 Docs at: http://127.0.0.1:8000/docs" -ForegroundColor Green

python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# Cleanup on exit
Write-Host "`n🛑 Shutting down ngrok..." -ForegroundColor Yellow
Stop-Process -InputObject $ngrokProcess -ErrorAction SilentlyContinue
Write-Host "✅ Cleanup complete" -ForegroundColor Green
