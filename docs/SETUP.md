# Setup and Installation Guide

Complete guide for installing and configuring agentic-review-gate on Windows and other platforms.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher (download from [python.org](https://www.python.org/downloads/))
- **Git**: Latest version (download from [git-scm.com](https://git-scm.com/))
- **Memory**: 2GB RAM minimum
- **Disk Space**: 500MB for installation and dependencies

### Windows-Specific

- **PowerShell** 5.0+ (included with Windows 10+)
- **Administrator access** (to install Python and Git)

### Optional

- **VS Code**: [code.visualstudio.com](https://code.visualstudio.com/) (recommended editor)
- **Postman**: For API testing

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/pvenkata-tech/agentic-review-gate.git
cd agentic-review-gate
```

### Step 2: Create Python Virtual Environment

**Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt)**:
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS/Linux**:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements-dev.txt

# For Claude (Anthropic)
pip install anthropic>=0.7.0

# For GPT-4 (OpenAI) - optional alternative
pip install openai>=1.0.0

# For Redis caching - optional
pip install redis>=5.0.0
```

### Step 4: Using Development Server Scripts (Windows)

We provide convenient scripts to automate setup and start the server.

#### PowerShell (Recommended)

```powershell
# From project root
.\dev-server.ps1
```

**What it does:**
1. Creates virtual environment if needed
2. Activates virtual environment
3. Installs dependencies
4. Loads environment variables from .env
5. Starts FastAPI server with hot-reload

#### Command Prompt

```cmd
dev-server.bat
```

## Configuration

### Step 1: Set Up Environment Variables

Create `.env` file in project root:

```env
# GitHub Configuration (REQUIRED)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# LLM Provider - Choose ONE (OPTIONAL)
ANTHROPIC_API_KEY=sk-ant-xxxx       # For Claude (recommended)
# OPENAI_API_KEY=sk-xxxx             # For GPT-4 (alternative)

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO                      # DEBUG for verbose logging

# Cache Configuration
CACHE_BACKEND=memory                # memory, file, or redis
# REDIS_URL=redis://localhost:6379  # If using Redis

# Review Configuration
MAX_FINDINGS_PER_AGENT=10
AGENT_TIMEOUT_SECONDS=60
```

### Step 2: Verify Environment Setup

```bash
# Check Python version
python --version              # Should be 3.10+

# Check virtual environment is active
# Should see (venv) in command prompt

# Check pip packages
pip list | grep -E "fastapi|httpx|anthropic|openai"
```

### Step 3: Get Required API Keys

#### GitHub Token

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✓ `repo` - Full control of private repositories
   - ✓ `read:user` - Read user profile data
4. Click "Generate token"
5. Copy token to `.env`: `GITHUB_TOKEN=ghp_xxxx`

#### Anthropic (Claude) - Recommended

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Create API key in account settings
4. Copy key to `.env`: `ANTHROPIC_API_KEY=sk-ant-xxxx`

#### OpenAI (GPT-4) - Alternative

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Create API key
4. Copy key to `.env`: `OPENAI_API_KEY=sk-xxxx`

## Verification

### Check Installation

```bash
# Verify all dependencies installed
python -c "import fastapi; import httpx; print('✓ Core deps OK')"

# Verify LLM client available
python -c "import anthropic; print('✓ Claude available')" # or openai
```

### Start Development Server

```bash
# Windows (PowerShell)
.\dev-server.ps1

# Windows (Command Prompt)
dev-server.bat

# Other platforms
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Test Server

```bash
# In another terminal/PowerShell window
curl http://localhost:8000/docs

# Should return HTML docs page
```

## Directory Structure After Setup

```
agentic-review-gate/
├── venv/                          # Virtual environment
├── src/code_reviewer/
│   ├── agents/                    # Agent implementations
│   ├── core/                      # Core classes and interfaces
│   ├── llm/                       # LLM integrations
│   ├── utils/                     # Utilities
│   └── main.py                    # FastAPI entrypoint
├── tests/                         # Test suite
├── docs/                          # This documentation
├── .env                           # Your configuration (DON'T COMMIT)
├── requirements-dev.txt           # Python dependencies
└── pyproject.toml                 # Project metadata
```

## Troubleshooting

### "Python not found"

Install Python from [python.org](https://www.python.org/downloads/) and add to PATH:
```powershell
# Verify installation
python --version
```

### "Module not found" errors

Activate virtual environment and reinstall:
```bash
# Windows
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt
```

### "GITHUB_TOKEN not set"

```bash
# Verify .env file exists in project root
Test-Path .env

# Check token is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('GITHUB_TOKEN')[:20]+'...')"
```

### "Server won't start"

```bash
# Check port 8000 isn't in use
netstat -ano | findstr :8000

# Try different port
python -m uvicorn src.code_reviewer.main:app --port 8001
```

### "API key invalid"

1. Verify key format:
   - Claude: Should start with `sk-ant-`
   - OpenAI: Should start with `sk-`
2. Check key hasn't expired (regenerate if needed)
3. Verify key is in `.env` and not hardcoded in code

## Next Steps

1. **[Set up GitHub integration](INTEGRATION.md)** - Configure webhooks
2. **[Run tests](OPERATIONS.md#testing)** - Verify system works
3. **[Deploy to production](OPERATIONS.md#deployment)** - Go live
4. **[Read architecture](ARCHITECTURE.md)** - Understand the design

## Quick Reference

| Command | Purpose |
|---------|---------|
| `.\dev-server.ps1` | Start dev server (Windows) |
| `python -m venv venv` | Create virtual environment |
| `pip install -r requirements-dev.txt` | Install dependencies |
| `python tests/diagnose.py` | Run diagnostics |
| `python tests/examples.py` | See examples |
| `pytest tests/` | Run unit tests |

## Performance Tips

- Use Claude 3 Sonnet for best speed/cost balance
- Enable Redis caching for repeated analyses
- Set `LOG_LEVEL=WARNING` in production
- Use `CACHE_BACKEND=redis` for distributed deployments

## Getting Help

- Check [OPERATIONS.md](OPERATIONS.md#troubleshooting) for runtime issues
- Run `python tests/diagnose.py` for system diagnostics
- See [README.md](README.md) for documentation index
