# Developer Setup Guide (Windows)

## Quick Start for Windows Development

This guide walks you through setting up and running the agentic-review-gate system on Windows.

### Prerequisites

- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/)
- **Git**: Download from [git-scm.com](https://git-scm.com/download/win)
- **VS Code** (optional): [code.visualstudio.com](https://code.visualstudio.com/)

### Step 1: Clone the Repository

```powershell
git clone https://github.com/your-org/agentic-review-gate.git
cd agentic-review-gate
```

### Step 2: Quick Start with Development Server Script

We've provided convenience scripts for Windows developers:

#### Option A: Using PowerShell (Recommended)

```powershell
# Make sure you're in the project root
cd c:\path\to\agentic-review-gate

# Run the PowerShell script
.\dev-server.ps1
```

**What this does:**
1. Creates a Python virtual environment if needed
2. Activates the virtual environment
3. Installs dependencies
4. Sets up development environment variables
5. Starts FastAPI with hot-reload enabled

#### Option B: Using Command Prompt (cmd.exe)

```cmd
# Make sure you're in the project root
cd c:\path\to\agentic-review-gate

# Run the batch script
dev-server.bat
```

### Step 3: Verify the Server is Running

Once started, you should see:

```
========================================
Code Reviewer - Development Server
========================================

Starting FastAPI development server...

Server will be available at: http://localhost:8000
API documentation at: http://localhost:8000/docs

Press CTRL+C to stop the server.
```

### Step 4: Test the API

Open your browser to:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Step 5: Configure GitHub Integration

To enable GitHub webhook integration, set these environment variables:

**Option A: Using PowerShell**

```powershell
$env:GITHUB_TOKEN = "ghp_your_token_here"
$env:GITHUB_OWNER = "your-org"
$env:GITHUB_REPO = "your-repo"
$env:GITHUB_WEBHOOK_SECRET = "your_webhook_secret"
```

**Option B: Using Command Prompt**

```cmd
set GITHUB_TOKEN=ghp_your_token_here
set GITHUB_OWNER=your-org
set GITHUB_REPO=your-repo
set GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

**Option C: Using .env file** (Recommended)

Create a `.env` file in the project root:

```env
# GitHub Configuration
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Development Settings
LOG_LEVEL=DEBUG
USE_LLM_LOGIC=false
USE_LLM_SECURITY=false

# LLM Providers (optional)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Step 6: Get GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens (classic)
2. Click "Generate new token"
3. Select these scopes:
   - `repo` (full control of private repositories)
   - `read:user` (read user profile data)
4. Copy the token and add to `.env` file

### Step 7: Create Webhook Secret

```powershell
# In PowerShell, generate a random secret
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

### Step 8: Configure GitHub Webhook

1. Go to your repository → Settings → Webhooks
2. Click "Add webhook"
3. Fill in the form:
   - **Payload URL**: `https://your-domain.com/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Use the secret from Step 7
   - **Events**: Select "Pull requests"
   - **Active**: Check this box
4. Click "Add webhook"

## Running Without the Dev Script

If you prefer manual setup:

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -e ".[dev,llm]"

# 4. Create .env file (see Step 5)

# 5. Start server
uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000
```

## Development Commands

### Run Tests

```powershell
# Activate venv first
.\venv\Scripts\Activate.ps1

# Run all tests
pytest

# Run with coverage
pytest --cov=src/code_reviewer

# Run specific test file
pytest tests/test_core.py -v
```

### Run Code Quality Tools

```powershell
# Format code
black src tests

# Lint code
ruff check src tests

# Type check
mypy src
```

### Run Examples

```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Run the examples
python examples.py
```

## Testing the Webhook Locally

For local testing without exposing to the internet, use a tunneling service:

### Option 1: ngrok (Free)

```powershell
# Download ngrok from https://ngrok.com/download

# Run ngrok to expose localhost:8000
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok.io
# Use this for your GitHub webhook Payload URL
```

### Option 2: Using curl to Test Webhook

```powershell
$payload = @{
    action = "opened"
    pull_request = @{
        number = 123
        title = "Test PR"
        user = @{ login = "testuser" }
    }
    repository = @{
        name = "test-repo"
        owner = @{ login = "test-org" }
    }
} | ConvertTo-Json

# Test without signature verification
curl -X POST http://localhost:8000/webhook/github `
  -H "Content-Type: application/json" `
  -d $payload
```

## Troubleshooting

### Problem: "python: command not found"
**Solution**: Python isn't in your PATH. Reinstall Python and make sure "Add Python to PATH" is checked.

### Problem: "venv not recognized"
**Solution**: Use full path: `.\venv\Scripts\Activate.ps1` or use Command Prompt instead.

### Problem: "Permission denied" when running .ps1
**Solution**: PowerShell execution policy. Run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: Port 8000 already in use
**Solution**: Either kill the process using the port or specify a different port:
```powershell
uvicorn src.code_reviewer.main:app --reload --port 8001
```

### Problem: ModuleNotFoundError
**Solution**: Make sure virtual environment is activated:
```powershell
.\venv\Scripts\Activate.ps1
```

### Problem: GitHub webhook not working
**Solution**: 
1. Check logs: `Get-EventLog -LogName Application -Source Python -Newest 10`
2. Verify signature: Add log statement in verify_github_webhook_signature
3. Check webhook deliveries in GitHub Settings → Webhooks → Recent Deliveries

## VS Code Integration

### Setup VS Code

1. Install Python extension: `ms-python.python`
2. Select Python interpreter: 
   - Press `Ctrl+Shift+P`
   - Type "Python: Select Interpreter"
   - Choose the one in `.\venv\Scripts\python.exe`

### Debug Configuration

Create `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI (uvicorn)",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "src.code_reviewer.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests/",
        "-v"
      ]
    }
  ]
}
```

### VSCode Extensions Recommended

- **Python**: ms-python.python
- **Pylance**: ms-python.vscode-pylance
- **Black Formatter**: ms-python.black-formatter
- **Ruff**: charliermarsh.ruff
- **REST Client**: humao.rest-client

## Performance Tips

1. **Disable LLM during development**: Set `USE_LLM_LOGIC=false` and `USE_LLM_SECURITY=false`
2. **Use caching**: Responses are cached during development
3. **Run tests in parallel**: `pytest -n auto`

## Next Steps

1. **Read the ARCHITECTURE.md** for deep understanding of the design
2. **Review examples.py** to see usage patterns
3. **Check out LLM_INTEGRATION.md** to integrate Claude or GPT-4
4. **Deploy to production** using DEPLOYMENT.md

## Getting Help

- **Issues**: Check [GitHub Issues](https://github.com/your-org/agentic-review-gate/issues)
- **Documentation**: See README.md, ARCHITECTURE.md, LLM_INTEGRATION.md
- **Logs**: Check console output and structured logs in JSON format

---

**Happy coding! 🚀**
