# Operations Guide - Testing, Deployment, and Monitoring

Complete guide for testing, deploying, optimizing, and monitoring agentic-review-gate.

## Table of Contents

1. [Testing](#testing)
2. [Performance & Caching](#performance--caching)
3. [Deployment](#deployment)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)

---

## Testing

### Unit Tests

Run core component tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v
pytest tests/test_agents_e2e.py -v

# Run with coverage
pytest tests/ --cov=src/code_reviewer --cov-report=html

# Run specific test class
pytest tests/test_core.py::TestReviewState -v
```

**Test Coverage**:
- ReviewState (Blackboard pattern)
- Agent implementations
- Webhook signature validation
- LLM integration
- Cache operations
- Coordinator workflows

### Integration Tests

Test full system workflows:

```bash
# End-to-end agent testing
pytest tests/test_agents_e2e.py -v

# Test against real PR
python tests/examples.py direct --pr-number 15
```

### Direct API Testing

Test the /review endpoint:

```bash
# Start server first
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# In another terminal, test PR review
python tests/examples.py direct --pr-number 15

# Expected output:
# ✓ Review completed successfully!
# Results:
#   Total Findings: X
#   Is Blocked: True/False
#   Status Check: Created
```

### Webhook Testing

Test webhook integration without public URL:

```bash
# Simulate webhook locally
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --pr-number 15
```

Or test with real webhook (see [INTEGRATION.md](INTEGRATION.md#webhook-testing)).

### Diagnostic Tool

Comprehensive system diagnostics:

```bash
# Full diagnostics
python tests/diagnose.py

# Check specific PR
python tests/diagnose.py --pr-number 15

# Run specific check
python tests/diagnose.py --check token     # GitHub auth
python tests/diagnose.py --check server    # Server health
python tests/diagnose.py --check merged    # Merged PRs
```

### Testing Checklist

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Server starts: `python -m uvicorn src.code_reviewer.main:app`
- [ ] Direct review works: `python tests/examples.py direct --pr-number 15`
- [ ] Diagnostics pass: `python tests/diagnose.py`
- [ ] GitHub token valid: `python tests/diagnose.py --check token`
- [ ] Server responds: `curl http://localhost:8000/docs`

---

## v1.1 Refinements (Critical Enhancements)

### A. Enhanced Diff Noise Filter

**Problem**: Sending lockfiles and auto-generated code to LLMs wastes tokens and adds noise.

**Solution**: Filter out non-code files before analysis:
- ✅ Lockfiles: `package-lock.json`, `poetry.lock`, `yarn.lock`, `Gemfile.lock`, etc.
- ✅ Minified files: `*.min.js`, `*.min.css`
- ✅ Generated/built: `dist/`, `build/`, `.next/`, `node_modules/`
- ✅ Config directories: `.git/`, `.github/`, `.vscode/`

**Implementation**: `GitHubClient._should_include_file()` filters at source before LLM processing.

**Token Savings**:
- Typical PR: 10-30% fewer tokens sent to LLM
- Claude: Save ~$0.01-0.05 per PR
- Large PRs (30+ files): Save ~20% of analysis time

### B. Idempotency & Smart Comment Updates

**Problem**: Each new commit creates duplicate comments; PR conversation becomes cluttered.

**Solution**: Detect and update existing bot comments instead of creating new ones.

**How It Works**:
1. Check if bot already commented on PR (looks for markers like "Automated Code Review")
2. If found: Edit the comment with new findings
3. If not found: Create new comment

**Markers Used**:
- "Automated Code Review"
- "code-reviewer/analysis"
- "## Code Review Analysis"
- "## Review Results"

**Result**: Clean PR conversations with findings progressively updated as commits are pushed.

### C. Rate Limiting & Concurrency Control

**Problem**: If 10 developers push code simultaneously, LLM rate limits get hit.

**Solution**: Semaphore to limit concurrent LLM requests.

**Configuration**:
```bash
# Default: 5 concurrent requests
# Override with environment variable:
export AGENT_SEMAPHORE_LIMIT=3  # For stricter limits
```

**How It Works**:
```
Developer 1 → Request 1 ✓ (Executing)
Developer 2 → Request 2 ✓ (Executing)
Developer 3 → Request 3 ✓ (Executing)
Developer 4 → Request 4 ✓ (Executing)
Developer 5 → Request 5 ✓ (Executing)
Developer 6 → Request 6 ⏳ (Queued - waiting for slot)
Developer 7 → Request 7 ⏳ (Queued)
Developer 8 → Request 8 ⏳ (Queued)
```

Max concurrent LLM calls = 5. Remaining requests queue automatically.

**Result**: No more rate limit errors during high-volume periods.

---

## Performance & Caching

### Problem: Redundant Analysis

When developers push commits to PRs:
- Without deduplication: Same findings flagged again
- With deduplication: Only NEW findings shown

### Solution: Finding Deduplication & Caching

#### How It Works

Each finding gets a stable hash ID based on:
- File path
- Finding type
- Description

```python
# Example
finding_id = hash("src/auth.py::Security::Hardcoded credentials")
# Result: "a7f3d2e1b9c4"
```

Same issue = Same ID = Recognized as duplicate

#### Workflow

1. **First Review**:
   - Find 5 issues
   - Cache IDs: [a7f3, b2e9, c1d6, d4e2, e8a3]
   - Post all 5 in comment

2. **Second Review** (after new commits):
   - Find 4 issues
   - IDs: a7f3, f9b2, b2e9, g3c8
   - Duplicates: a7f3, b2e9 (still present)
   - Comment shows:
     - ✅ FIXED: c1d6, d4e2, e8a3
     - ⚠️ STILL ISSUES: a7f3, b2e9
     - 🆕 NEW: f9b2, g3c8

### Caching Backends

### Option 1: Memory Cache (Default, Development)

```env
CACHE_BACKEND=memory
```

- **Speed**: ⚡ Instant
- **Cost**: $0
- **Persistence**: Lost on restart
- **Best for**: Development, single-server

### Option 2: File Cache (Persistent, Single Server)

```env
CACHE_BACKEND=file
CACHE_DIR=./cache
```

- **Speed**: ⚡ Fast
- **Cost**: $0 (local disk)
- **Persistence**: ✓ Survives restarts
- **Best for**: Single-server production

### Option 3: Redis Cache (Distributed)

```env
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379
```

- **Speed**: ⚡⚡ Very fast
- **Cost**: $$ (Redis service)
- **Persistence**: ✓ Survives restarts
- **Scalability**: ✓ Multi-server
- **Best for**: Distributed deployments

### Performance Impact

| Metric | Without Cache | With Memory | With Redis |
|--------|--------------|-------------|-----------|
| Dedup check | 0 | <1ms | <5ms |
| First review | 20s | 20s | 20s |
| Second review | 20s | 18s | 18s |
| Cost/month | - | - | $5-10 |

### Cost Optimization

**Token savings** (1,000 PRs/month):
- Avoid reanalysis: 10-15% fewer API calls
- Claude: Save ~$2/month
- GPT-4: Save ~$15/month

### Configuration

```env
# Cache settings
CACHE_BACKEND=redis                   # redis, file, or memory
REDIS_URL=redis://localhost:6379      # For Redis
CACHE_TTL_SECONDS=86400               # 24 hours
MAX_CACHE_SIZE_MB=1024                # Max cache size

# Agent settings
MAX_FINDINGS_PER_AGENT=10              # Limit findings
AGENT_TIMEOUT_SECONDS=60               # Agent timeout
```

---

## Deployment

### Local Development Setup

```bash
# 1. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Create .env file
# See SETUP.md for configuration

# 4. Start server
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000
```

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

# Run server
CMD ["python", "-m", "uvicorn", "src.code_reviewer.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and run**:
```bash
docker build -t code-reviewer .
docker run -p 8000:8000 -e GITHUB_TOKEN=$GITHUB_TOKEN code-reviewer
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      GITHUB_WEBHOOK_SECRET: ${GITHUB_WEBHOOK_SECRET}
      CACHE_BACKEND: redis
      REDIS_URL: redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

Start: `docker-compose up -d`

### Cloud Deployment

#### Heroku

```bash
# Create app
heroku create your-app-name

# Set environment variables
heroku config:set GITHUB_TOKEN=ghp_...
heroku config:set GITHUB_WEBHOOK_SECRET=...

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

#### AWS Lambda

Use serverless framework:

```bash
serverless deploy
```

Requires adapter layer for FastAPI. See [serverless-fastapi](https://github.com/jordaneremieff/mangum).

#### Google Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/code-reviewer

# Deploy to Cloud Run
gcloud run deploy code-reviewer \
  --image gcr.io/PROJECT_ID/code-reviewer \
  --set-env-vars GITHUB_TOKEN=$GITHUB_TOKEN \
  --allow-unauthenticated
```

### Pre-Deployment Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Diagnostics pass: `python tests/diagnose.py`
- [ ] Environment variables configured
- [ ] GitHub webhook configured
- [ ] Database/cache backend ready
- [ ] HTTPS certificate installed
- [ ] Firewall rules allow incoming webhooks
- [ ] Logging configured
- [ ] Monitoring set up

---

## Monitoring

### Health Checks

**Endpoint**: `GET /health`

Response:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "github_api": "ok",
    "cache": "ok"
  }
}
```

Monitor with:
```bash
curl http://localhost:8000/health
```

### Logging

**Configure logging** in `.env`:
```env
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/review.log
```

**Recommended production** settings:
```env
LOG_LEVEL=INFO
LOG_FILE=/var/log/code-reviewer/review.log
```

### Key Metrics to Monitor

1. **Review Performance**
   - Analysis time (goal: <30s)
   - API calls per review
   - Cache hit rate

2. **System Health**
   - Server uptime
   - Memory usage
   - CPU usage
   - Disk space

3. **GitHub Integration**
   - Webhook delivery success rate
   - Comment posting success
   - Status check creation success

4. **LLM Usage**
   - API calls per day
   - Token consumption
   - Cost per review
   - Rate limit status

### Example Monitoring Setup

**With ELK Stack**:
```bash
# Application logs → Filebeat → Elasticsearch → Kibana
```

**With DataDog**:
```python
from datadog import initialize, api
options = {'api_key': 'your_api_key', 'app_key': 'your_app_key'}
initialize(**options)
```

**With Prometheus**:
```python
from prometheus_client import Counter, Histogram
review_counter = Counter('reviews_total', 'Total reviews')
review_time = Histogram('review_seconds', 'Review duration')
```

### Alert Examples

Set up alerts for:
- High error rate (>5% failures)
- Slow analysis (>60 seconds)
- High API usage
- Cache failures
- Webhook failures (>10% errors)

---

## Troubleshooting

### Server Issues

**Problem**: Server won't start

```bash
# Check port is available
netstat -ano | findstr :8000

# Try different port
python -m uvicorn src.code_reviewer.main:app --port 8001

# Check logs
export LOG_LEVEL=DEBUG
python -m uvicorn src.code_reviewer.main:app
```

**Problem**: High memory usage

```bash
# Check what's using memory
python -c "import sys; sys.getsizeof(...)"

# Reduce cache size
CACHE_BACKEND=file     # Use file instead of memory
MAX_CACHE_SIZE_MB=500  # Limit cache
```

### Test Failures

**Problem**: Tests timeout

```bash
# Increase timeout
pytest tests/ --timeout=300

# Run tests with less parallelism
pytest tests/ -n 1
```

**Problem**: "Cannot connect to localhost:8000"

```bash
# Start server first
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# Then run tests in another terminal
python tests/examples.py direct --pr-number 15
```

### Performance Issues

**Problem**: Analysis takes too long

```bash
# Profile analysis
import cProfile
cProfile.run('await coordinator.review_pr(state)')

# Check LLM response time
# Set LOG_LEVEL=DEBUG to see timing

# Consider using faster LLM model
# Claude Haiku instead of Opus
```

**Problem**: High API costs

```bash
# Enable caching
CACHE_BACKEND=redis

# Use cheaper LLM model
ANTHROPIC_API_KEY=sk-ant-...  # Use Haiku instead

# Reduce analysis scope
MAX_FINDINGS_PER_AGENT=5  # Limit findings
```

### Webhook Issues

See [INTEGRATION.md#troubleshooting](INTEGRATION.md#troubleshooting) for webhook-specific issues.

---

## Performance Benchmarks

**Expected performance** for typical PR (5 files, ~150 lines):

| Operation | Time |
|-----------|------|
| Fetch PR metadata | <1s |
| Get file diffs | 1-2s |
| Run agents | 10-30s |
| Create status check | <1s |
| Post comment | <1s |
| **Total** | **15-40s** |

**Factors that affect performance**:
- PR size (larger = slower)
- LLM model (Opus > Sonnet > Haiku)
- Network latency
- GitHub API response time
- Agent complexity

---

## Next Steps

1. [Set up integrations](INTEGRATION.md)
2. [Configure monitoring](#monitoring)
3. [Deploy to production](#deployment)
4. [Review architecture](ARCHITECTURE.md)
