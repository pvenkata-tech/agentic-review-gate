# Testing Guide - Agentic Review Gate

Comprehensive guide for testing the agentic code review system, from unit tests to end-to-end webhook testing.

## Quick Start

```bash
# Run unit tests
pytest tests/ -v

# Test against a specific PR
python tests/examples.py direct --pr-number 15

# Run full diagnostics
python tests/diagnose.py
```

## Table of Contents

1. [Unit Tests](#unit-tests)
2. [Integration Tests](#integration-tests)
3. [Direct API Testing](#direct-api-testing)
4. [Webhook Testing](#webhook-testing)
5. [Diagnostic Tools](#diagnostic-tools)
6. [Troubleshooting](#troubleshooting)

## Unit Tests

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v

# Run with coverage
pytest tests/ --cov=src/code_reviewer --cov-report=html
```

### Test Files

- **test_core.py**: ReviewState, agents, and coordinator unit tests
- **test_agents_e2e.py**: End-to-end agent analysis workflows

### Test Coverage

- Diff parser validation and edge cases
- Agent analysis logic and decision trees
- Cache backend operations
- GitHub client integration
- Webhook signature validation

## Integration Tests

### Prerequisites

1. GitHub token in `.env` (`GITHUB_TOKEN`)
2. Valid GitHub repository access
3. Development server running
4. ngrok tunnel (for webhook testing)

### Running Integration Tests

```bash
pytest tests/test_agents_e2e.py -v
```

## Direct API Testing

### Test Against a Specific PR

```bash
python tests/examples.py direct --pr-number 15
```

This will:
1. Fetch PR metadata from GitHub
2. Extract file diffs
3. Run agents (Logic + Security + Summarizer)
4. Create GitHub status check
5. Post findings comment
6. Return results

### Expected Output

```
✓ Review completed successfully!

Results:
  Total Findings: 3
  Is Blocked: True
  Status Check: Created

Check PR: https://github.com/owner/repo/pull/15
```

## Webhook Testing

### Webhook Architecture

```
GitHub Repository
      ↓
PR opened/updated
      ↓
GitHub sends POST to /webhook/github
      ↓
Server validates signature
      ↓
ReviewCoordinator starts async analysis
      ↓
Agents analyze code
      ↓
Comment posted to PR
      ↓
Status check updated
```

### Step-by-Step Setup

#### 1. Generate Webhook Secret

```python
import secrets
import base64
secret = base64.b64encode(secrets.token_bytes(32)).decode()
print(secret)
```

Add to `.env`:
```env
GITHUB_WEBHOOK_SECRET=<your_secret>
```

#### 2. Start Development Server

```bash
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000
```

#### 3. Create Public URL (for local testing)

```bash
# Using ngrok
ngrok http 8000
# Copy HTTPS URL: https://abc-123-456.ngrok.io
```

#### 4. Configure GitHub Webhook

1. Repository → Settings → Webhooks → Add webhook
2. Fill in:
   - **Payload URL**: `https://your-ngrok-url/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Your GITHUB_WEBHOOK_SECRET
   - **Events**: Select "Pull requests" and "Pushes"
   - **Active**: ✓ Checked
3. Click "Add webhook"

#### 5. Test the Webhook

Create a test PR or push to existing:

```bash
git checkout -b test-feature
echo "# Test" > test.py
git add test.py
git commit -m "test: Add test code"
git push origin test-feature
# Create PR on GitHub
```

Monitor webhook delivery:
1. Settings → Webhooks → your webhook
2. Scroll to "Recent Deliveries"
3. Click any delivery to see request/response
4. Status should be 200-299

### Local Webhook Testing (Without ngrok)

```bash
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --pr-number 15
```

This simulates a GitHub webhook without needing a public URL.

## Diagnostic Tools

### Run All Diagnostics

```bash
python tests/diagnose.py
```

Checks:
- GitHub API authentication ✓
- Server health and connectivity ✓
- PR metadata retrieval ✓
- File diff fetching ✓
- Status check creation ✓
- Recently merged PRs ✓

### Check Specific PR

```bash
python tests/diagnose.py --pr-number 15
```

Additionally checks:
- PR files and patches
- Current status checks on PR
- PR metadata consistency

### Run Specific Diagnostic

```bash
python tests/diagnose.py --check token      # GitHub auth
python tests/diagnose.py --check server     # Server health
python tests/diagnose.py --check pr --pr-number 15  # PR data
python tests/diagnose.py --check status --pr-number 15  # Status checks
python tests/diagnose.py --check merged     # Merged PRs
```

## Troubleshooting

### Webhook Not Triggering

**Symptom**: Status check stuck in "pending" state

**Diagnosis**:
```bash
python tests/diagnose.py
# Check "Server Health" and "GitHub Token" pass
```

**Solutions**:
1. Verify GitHub webhook configuration (Settings → Webhooks)
2. Update webhook URL if using ngrok (new URL on restart)
3. Check webhook "Recent Deliveries" for error responses
4. Verify GITHUB_WEBHOOK_SECRET matches `.env` and GitHub settings

### No Comments Posted

**Symptom**: Review runs but no comment on PR

**Diagnosis**:
```bash
python tests/diagnose.py --pr-number 15
```

**Solutions**:
1. Check server logs for background task errors
2. Verify GitHub token has `repo` scope
3. Ensure PR hasn't been merged
4. Check comment count limit hasn't been exceeded

### Diff Not Parsing

**Symptom**: Agents report "0 files analyzed"

**Diagnosis**:
```bash
python tests/diagnose.py --pr-number 15 --check pr
```

**Solutions**:
1. Verify PR has actual file changes
2. Check if files are too large (>1MB each)
3. Confirm GitHub API returns patch content

### ngrok URL Expired

**Symptom**: Webhook returns 404

**Solution**:
- ngrok free tier generates new URL on restart
- Update GitHub webhook with new URL
- Use paid ngrok account for permanent URL
- Deploy to server for production testing

## Performance Metrics

Expected performance for typical PR:
- Agent analysis: 5-30 seconds
- Status check creation: <1 second
- Comment posting: <1 second
- **Total**: 10-40 seconds

If analysis takes >60 seconds:
1. Check LLM response times (rate limiting?)
2. Check network connectivity to GitHub API
3. Review diff size (>10k lines?)
4. Check agent timeouts in config

## Testing Checklist

### Setup Verification
- [ ] GitHub token in `.env`
- [ ] Server starts without errors
- [ ] Can access http://localhost:8000/docs
- [ ] Can run diagnostics successfully

### Direct API Testing
- [ ] `python tests/examples.py direct --pr-number <N>` works
- [ ] Review completes within 120 seconds
- [ ] Status check created on PR
- [ ] Comment posted with findings

### Webhook Testing
- [ ] Webhook secret configured
- [ ] ngrok tunnel active (if local testing)
- [ ] GitHub webhook configured
- [ ] Webhook shows successful deliveries (200 status)
- [ ] PR comment appears after webhook triggers

### Diagnostic Tests
- [ ] All diagnostics pass: `python tests/diagnose.py`
- [ ] Token, server, API connectivity verified
- [ ] PR metadata retrieval working
- [ ] Status checks and comments functional

## Debugging

### Enable Debug Logging

```bash
# Set in .env or environment
LOG_LEVEL=DEBUG
```

### Key Log Patterns

Successful flow:
```
[github_client] Fetching PR #15
[github_client] Successfully fetched PR diff: 5024 characters
[diff_parser] Extracted 3 files from diff
[logic_agent] Analyzing 3 files
[security_agent] Scanning for security issues
[main] Completed PR review #15
```

Problem indicators:
```
[github_client] PR diff is empty!
[diff_parser] Diff does not start with 'diff --git'
[logic_agent] Received 0 chars (should be > 0)
[agents] Unable to analyze code changes
```

## Next Steps

1. [Configure GitHub Integration](GITHUB_INTEGRATION.md)
2. [Set up LLM Provider](LLM_SETUP.md)
3. [Deploy to Production](DEPLOYMENT.md)
4. [Monitor and Troubleshoot](DEPLOYMENT.md#monitoring)
