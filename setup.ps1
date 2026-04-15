# Webhook Setup Script - Start ngrok and FastAPI server with proper env vars
# Usage: .\setup.ps1

Write-Host "🚀 Starting agentic-review-gate webhook setup..." -ForegroundColor Cyan

# Activate virtual environment
Write-Host "`n📦 Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Load environment variables from .env if it exists
if (Test-Path ".env") {
    Write-Host "`n📋 Loading environment variables from .env..." -ForegroundColor Yellow
    foreach ($line in Get-Content .env) {
        if ($line -and -not $line.StartsWith("#")) {
            $parts = $line -split "=", 2
            if ($parts.Length -eq 2) {
                $key = $parts[0].Trim()
                $value = $parts[1].Trim()
                [Environment]::SetEnvironmentVariable($key, $value)
                # Don't echo sensitive values
                if ($key -match "TOKEN|SECRET|KEY|PASSWORD") {
                    Write-Host "  ✓ Set $key (***)" -ForegroundColor Green
                } else {
                    Write-Host "  ✓ Set $key = $value" -ForegroundColor Green
                }
            }
        }
    }
} else {
    Write-Host "`n⚠️  No .env file found. Using environment variables from shell." -ForegroundColor Yellow
}

# Validate required environment variables
Write-Host "`n🔐 Validating environment variables..." -ForegroundColor Yellow

$required_vars = @{
    "GITHUB_TOKEN" = "GitHub API token for PR comments and status checks"
    "GITHUB_OWNER" = "Repository owner (e.g., pvenkata-tech)"
    "GITHUB_REPO" = "Repository name (e.g., agentic-review-gate)"
    "ANTHROPIC_API_KEY" = "Anthropic Claude API key for code analysis"
}

$missing = @()
foreach ($var in $required_vars.GetEnumerator()) {
    $value = [Environment]::GetEnvironmentVariable($var.Key)
    if (-not $value) {
        Write-Host "  ❌ Missing: $($var.Key)" -ForegroundColor Red
        Write-Host "     $($var.Value)" -ForegroundColor Gray
        $missing += $var.Key
    } else {
        if ($var.Key -match "TOKEN|SECRET|KEY|PASSWORD") {
            Write-Host "  ✓ $($var.Key) = ***" -ForegroundColor Green
        } else {
            Write-Host "  ✓ $($var.Key) = $value" -ForegroundColor Green
        }
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`n❌ Missing environment variables: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "   Set them in .env file or shell before running setup.ps1" -ForegroundColor Yellow
    Write-Host "`n   Example .env:" -ForegroundColor Cyan
    Write-Host "   GITHUB_TOKEN=github_pat_xxxxx" -ForegroundColor Gray
    Write-Host "   GITHUB_OWNER=pvenkata-tech" -ForegroundColor Gray
    Write-Host "   GITHUB_REPO=agentic-review-gate" -ForegroundColor Gray
    Write-Host "   ANTHROPIC_API_KEY=sk-ant-xxxxx" -ForegroundColor Gray
    Write-Host "   GITHUB_WEBHOOK_SECRET=your_webhook_secret" -ForegroundColor Gray
    exit 1
}

# Set additional helpful variables
[Environment]::SetEnvironmentVariable("LOG_LEVEL", "INFO")
[Environment]::SetEnvironmentVariable("USE_LLM_LOGIC", "true")
[Environment]::SetEnvironmentVariable("USE_LLM_SECURITY", "true")

Write-Host "`n✅ All required variables set. Ready to start!" -ForegroundColor Green

# Check if ngrok is installed
$ngrokPath = Get-Command ngrok -ErrorAction SilentlyContinue
if (-not $ngrokPath) {
    Write-Host "`n❌ ngrok is not installed. Install it from: https://ngrok.com/download" -ForegroundColor Red
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
        Write-Host "`n📝 GitHub Webhook Configuration:" -ForegroundColor Cyan
        Write-Host "   Payload URL: $ngrokUrl/webhook/github" -ForegroundColor White
        Write-Host "   Content type: application/json" -ForegroundColor Gray
        Write-Host "   Events: Pull request" -ForegroundColor Gray
        Write-Host "   Active: ✓" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠️  Could not retrieve ngrok URL automatically. Check http://127.0.0.1:4040" -ForegroundColor Yellow
}

# Start FastAPI server
Write-Host "`n🔧 Starting FastAPI server..." -ForegroundColor Yellow
Write-Host "📍 Server running at: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "📊 API Docs at: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "📊 ngrok Web UI at: http://127.0.0.1:4040" -ForegroundColor Green
Write-Host "`n💡 Watch for webhook events in ngrok UI!" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# Cleanup on exit
Write-Host "`n🛑 Shutting down ngrok..." -ForegroundColor Yellow
Stop-Process -InputObject $ngrokProcess -ErrorAction SilentlyContinue
Write-Host "✅ Cleanup complete" -ForegroundColor Green
