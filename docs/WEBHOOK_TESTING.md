# GitHub Webhook Testing Guide

This guide covers how to test the GitHub webhook integration with real webhooks.

## Table of Contents

1. [Local Testing with Ngrok](#local-testing-with-ngrok)
2. [Testing with GitHub Repository Webhook](#testing-with-github-repository-webhook)
3. [Webhook Testing Examples](#webhook-testing-examples)
4. [Troubleshooting](#troubleshooting)

---

## Local Testing with Ngrok

Ngrok allows your local development server to receive webhooks from GitHub without deployment.

### Prerequisites

- Ngrok account (free at https://ngrok.com)
- Local development server running on port 8000
- GitHub repository with webhook permissions

### Step 1: Download and Install Ngrok

```bash
# macOS with Homebrew
brew install ngrok

# Linux
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.zip
unzip ngrok-v3-stable-linux-amd64.zip
sudo mv ngrok /usr/local/bin

# Windows (via PowerShell)
choco install ngrok  # if using Chocolatey
# Or download from https://ngrok.com/download
```

### Step 2: Start Development Server

```bash
# Terminal 1: Start the review service
cd agentic-review-gate

# Configure environment (use placeholders only in docs)
export GITHUB_WEBHOOK_SECRET=<your_webhook_secret_from_env_or_secret_manager>
export GITHUB_TOKEN=<your_github_token_from_env_or_secret_manager>

# Start server
python -m uvicorn src.code_reviewer.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 3: Create Ngrok Tunnel

```bash
# Terminal 2: Create tunnel
ngrok http 8000

# Output will show:
# Forwarding    https://1234-56-78-90-12.ngrok.io -> http://localhost:8000
# Copy the HTTPS URL for next step
```

### Step 4: Configure GitHub Webhook

1. Go to your test repository on GitHub
2. Settings → Webhooks → Add webhook
3. Configure:
   - **Payload URL**: `https://1234-56-78-90-12.ngrok.io/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: value from `GITHUB_WEBHOOK_SECRET` (do not paste real secrets in docs)
   - **Events**: Select "Pull requests"
   - **Active**: ✓ (checked)

4. Click "Add webhook"

### Step 5: Test with Real PR

Create a test pull request in the repository:

```bash
# In your test repo
git checkout -b test/webhook-test
echo "# Test" >> README.md
git add README.md
git commit -m "test: webhook testing"
git push origin test/webhook-test

# Then open PR on GitHub web interface
```

Monitor the development server logs:

```
2024-01-15 10:23:45 - github.webhook - INFO - Webhook received from GitHub
2024-01-15 10:23:45 - github.webhook - INFO - Event: pull_request, Action: opened
2024-01-15 10:23:46 - coordinator - INFO - Starting Phase A: Analyze with agents
...
```

---

## Testing with GitHub Repository Webhook

### Using GitHub's Webhook Test Feature

After adding the webhook:

1. Go to Settings → Webhooks → Select webhook
2. Scroll down to "Recent Deliveries"
3. Click on the "Redeliver" button for any delivery
4. Or manually trigger by creating a PR

### Monitoring Webhook Deliveries

In the webhook settings:

1. Click "Recent Deliveries"
2. View:
   - Request/response payloads
   - Status codes (200 = success)
   - Response headers
3. Useful for debugging:
   - Signature validation failures
   - Payload parsing errors
   - Server errors

---

## Webhook Testing Examples

### Example 1: Simple PR Opened Event

```json
{
  "action": "opened",
  "pull_request": {
    "number": 42,
    "title": "Add webhook testing docs",
    "user": {
      "login": "developer"
    },
    "head": {
      "ref": "feature/webhook-docs",
      "sha": "abc123def456"
    },
    "base": {
      "ref": "main"
    },
    "additions": 50,
    "deletions": 5,
    "changed_files": 2
  },
  "repository": {
    "name": "agentic-review-gate",
    "owner": {
      "login": "your-org"
    }
  }
}
```

**Expected behavior**:
- Server receives webhook
- Validates HMAC signature
- Queues PR for review
- Runs async agents in parallel (Phase A)
- Evaluates critical findings (Phase B)
- Generates GitHub comment (Phase C)
- Posts comment to PR

### Example 2: Security Finding Test

Create a PR that intentionally includes a security issue:

```bash
# In test repository
git checkout -b test/security-issue
cat > test_secrets.py << 'EOF'
# This will trigger security findings
API_KEY = EXAMPLE_API_KEY_PLACEHOLDER
DATABASE_PASSWORD = EXAMPLE_DATABASE_PASSWORD_PLACEHOLDER


def login(user, pass):
    # SQL injection vulnerable query
    query = f"SELECT * FROM users WHERE id={user}"
    return query
EOF
git add test_secrets.py
git commit -m "test: intentional security issues"
git push origin test/security-issue
# Open PR on GitHub
```

**Expected behavior**:
- SecurityGuardAgent detects hardcoded credentials
- Flags as CRITICAL severity
- PR becomes blocked
- GitHub comment includes security findings

### Example 3: Code Quality Finding Test

```bash
git checkout -b test/code-quality
cat > test_quality.py << 'EOF'
def complex_function(a, b, c, d, e, f, g, h):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return a + b + c + d + e
    return 0

# Duplicated code
def copy_paste_1():
    result = []
    for i in range(100):
        result.append(i * 2)
    return result

def copy_paste_2():
    result = []
    for i in range(100):
        result.append(i * 2)
    return result
EOF
git add test_quality.py
git commit -m "test: code quality issues"
git push origin test/code-quality
# Open PR
```

**Expected behavior**:
- LogicAgent detects:
  - Deep nesting (>5 levels)
  - Code duplication
  - Cyclomatic complexity
- Files WARNING level findings

---

## Testing with Webhook Simulation

### Using cURL to Simulate Webhook

```bash
#!/bin/bash

# Set variables
WEBHOOK_URL="http://localhost:8000/webhook/github"
SECRET=${GITHUB_WEBHOOK_SECRET}
PAYLOAD='{"action":"opened","pull_request":{"number":42},"repository":{"name":"test"}}'

# Calculate HMAC signature
SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)"

# Send webhook request
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -H "X-GitHub-Event: pull_request" \
  -d "$PAYLOAD"
```

### Using Python Script (Recommended)

See `tests/webhook_test_client.py` for a complete webhook simulation script.

```bash
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --secret "$GITHUB_WEBHOOK_SECRET" \
  --event pull_request \
  --action opened \
  --pr-number 42
```

---

## Testing LLM Integration

### Using Mock LLM (Development)

By default, the system uses `MockLLMClient` when no API keys are configured:

```bash
# Development: Uses mock LLM
python -m uvicorn src.code_reviewer.main:app --port 8000

# Logs show:
# INFO: Using LLM provider: mock
```

### Testing with Real LLM

#### Option 1: Claude (Anthropic)

```bash
# Install anthropic package
pip install anthropic

# Set API key
export ANTHROPIC_API_KEY=<your_anthropic_api_key>

# Start server - will auto-detect and use Claude
python -m uvicorn src.code_reviewer.main:app --port 8000

# Logs show:
# INFO: Using LLM provider: claude
```

#### Option 2: GPT-4 (OpenAI)

```bash
# Install openai package
pip install openai

# Set API key
export OPENAI_API_KEY=<your_openai_api_key>

# Start server - will auto-detect and use GPT-4
python -m uvicorn src.code_reviewer.main:app --port 8000

# Logs show:
# INFO: Using LLM provider: gpt4
```

### Testing LLM Fallback

Test that the system gracefully handles LLM failures:

1. Start with valid LLM credentials
2. Change API key to invalid: `export ANTHROPIC_API_KEY=<invalid_api_key_for_testing>`
3. Send webhook
4. Observe:
   - LLM call fails with 401 Unauthorized
   - Agent falls back to rule-based analysis
   - PR review still completes
   - Logs show fallback used

---

## Troubleshooting

### Webhook Not Being Received

**Problem**: No logs showing webhook received

**Solutions**:
1. Verify ngrok tunnel is active: `ngrok http 8000`
2. Check webhook URL in GitHub (should be the ngrok URL)
3. Verify payload URL format: `https://xxxxx.ngrok.io/webhook/github`
4. Check GitHub's webhook delivery logs (Recent Deliveries section)

### Signature Validation Failure

**Problem**: `403 Forbidden - Signature verification failed`

**Solutions**:
1. Verify secret matches in both places:
   - GitHub webhook settings
   - Server environment: `GITHUB_WEBHOOK_SECRET`
2. Ensure secret doesn't have extra spaces
3. Check ngrok request body isn't modified
4. Verify X-Hub-Signature-256 header present

### Server Not Processing Webhook

**Problem**: Webhook received (200 OK) but no review posted

**Solutions**:
1. Check server logs for errors: `tail -f logs/code-review.log`
2. Verify GITHUB_TOKEN is valid
3. Check if PR is in a fork (webhooks may not work)
4. Look for agent timeout errors (60s per agent)
5. Verify agents directory exists and imports work

### LLM Integration Issues

**Problem**: Agent returning empty findings

**Solutions**:
1. Verify LLM API key is valid: Try calling directly
2. Check API rate limits
3. Ensure prompt formatting is correct
4. Review LLM response logs
5. Fall back to mock: `export ANTHROPIC_API_KEY=""`

### ngrok Issues

**Problem**: "command not found: ngrok"

**Solutions**:
1. Reinstall ngrok
2. Add to PATH: `export PATH="/usr/local/bin:$PATH"`
3. Or use docker alternative:
   ```bash
   docker run -it -e NGROK_AUTHTOKEN=token ngrok/ngrok:latest \
     http host.docker.internal:8000
   ```

---

## Performance Testing

### Load Testing with Multiple PRs

```bash
#!/bin/bash
# Open multiple PRs to test concurrent processing

for i in {1..5}; do
  git checkout -b test/pr-$i
  echo "PR $i" >> test.txt
  git add test.txt
  git commit -m "PR $i"
  git push origin test/pr-$i
  # Create PR via GitHub web or API
done
```

Monitor:
- CPU usage
- Memory usage
- Response times
- Agent execution times

### Metrics to Track

1. **Webhook Latency**: Time from webhook received to comment posted
2. **Agent Execution**: Time per agent (target: <20s each)
3. **Throughput**: PRs processed per minute
4. **Error Rate**: Failed reviews / total reviews

---

## Next Steps

1. Run unit tests: `pytest tests/test_core.py -v`
2. Test webhook signature validation: `pytest tests/test_core.py::TestWebhookValidation -v`
3. Test LLM integration: `pytest tests/test_core.py::TestLLMIntegration -v`
4. Deploy to staging environment
5. Monitor real GitHub webhooks in production

