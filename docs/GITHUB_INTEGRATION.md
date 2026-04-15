# GitHub Integration Guide

Complete guide for integrating the agentic code review system with GitHub.

## Table of Contents

1. [Webhook Setup](#webhook-setup)
2. [GitHub Configuration](#github-configuration)
3. [Branch Protection Rules](#branch-protection-rules)
4. [Status Checks](#status-checks)
5. [Testing Webhooks](#testing-webhooks)
6. [Troubleshooting](#troubleshooting)

## Webhook Setup

### Overview

The webhook allows GitHub to automatically trigger code reviews when PRs are opened or updated.

**Flow**:
```
GitHub PR Event
      ↓
POST to /webhook/github endpoint
      ↓
Signature validation (GITHUB_WEBHOOK_SECRET)
      ↓
Payload parsed
      ↓
ReviewCoordinator analysis (background)
      ↓
Comment posted with findings
      ↓
Status check updated
```

### Step 1: Generate Webhook Secret

```python
import secrets
import base64
secret = base64.b64encode(secrets.token_bytes(32)).decode()
print(secret)
```

Or in PowerShell:
```powershell
$secret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host $secret
```

### Step 2: Set Environment Variables

Add to `.env`:
```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
```

### Step 3: Start Development Server

```bash
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000
```

### Step 4: Expose Local Server (Development)

For local testing, you need to expose your localhost to the internet.

#### Option A: ngrok (Recommended)

```bash
# Install ngrok from https://ngrok.com/download
# Configure authentication

ngrok http 8000
# Copy the HTTPS forwarding URL: https://abc-123.ngrok.io
```

#### Option B: Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
# Use the provided URL
```

#### Option C: Deploy to Server

Use your production domain for automatic public access.

### Step 5: Configure GitHub Webhook

1. Go to repository → **Settings** → **Webhooks**
2. Click **"Add webhook"**
3. Fill in:

| Field | Value |
|-------|-------|
| Payload URL | `https://your-url/webhook/github` |
| Content type | `application/json` |
| Secret | Your GITHUB_WEBHOOK_SECRET |
| Events | Select "Pull requests" (and optionally "Pushes") |
| Active | ✓ Checked |

4. Click **"Add webhook"**

### Step 6: Test the Webhook

1. Create a test PR or push to a branch with an open PR
2. Go to Settings → Webhooks → Your webhook
3. Scroll to "Recent Deliveries"
4. Click any delivery to see:
   - Request payload
   - Response status (should be 200-299)
   - Response body

## GitHub Configuration

### Required Permissions

Your GitHub token needs these scopes:
- `repo` - Read PRs, post comments, create status checks
- `read:user` - Access profile information

Check permissions:
1. Go to [GitHub Settings → Personal access tokens](https://github.com/settings/personal-access-tokens)
2. Select your token
3. Verify required scopes are present

### API Rate Limits

GitHub API has rate limits:
- **Authenticated requests**: 5,000 per hour
- **Per-PR analysis**: ~3-5 requests (metadata, files, diff, comments)

For batch testing, space out PR creations to avoid hitting limits.

### Token Security

**Never commit tokens**:
- Keep tokens in `.env` (added to `.gitignore`)
- Use environment variables in CI/CD
- Rotate tokens if ever exposed
- Use fine-grained tokens (recommended) instead of classic tokens

## Branch Protection Rules

Branch protection rules enforce your review criteria.

### Setup Branch Protection

1. Go to repository → **Settings** → **Branches**
2. Click **"Add rule"**
3. Branch name pattern: `main` (or your protected branch)
4. Check these options:

- [ ] **Require a pull request before merging**
  - Dismisses stale pull request approvals when new commits are pushed
- [ ] **Require status checks to pass before merging**
  - Select: `code-reviewer/analysis`
  - This blocks merging if our review status is "failure"
- [ ] **Include administrators** (optional)
  - Applies rules to repository administrators too

### Result

With these rules:
- ✅ When agentic review finds NO critical issues: Status = **success** → PR can be merged
- ❌ When agentic review finds CRITICAL issues: Status = **failure** → PR BLOCKED from merging

## Status Checks

The system creates GitHub status checks to enforce merge policies.

### Status Check Details

- **Context**: `code-reviewer/analysis`
- **States**:
  - `pending` - Analysis in progress
  - `success` - No critical issues found (can merge)
  - `failure` - Critical issues found (merge blocked)
- **Description**: Shows findings count and recommendation

### Example Status Check

```
🔴 code-reviewer/analysis - Expected
❌ Changes Requested - 2 critical findings

[Details] [Re-run]
```

## Testing Webhooks

### Local Testing (No Public Server)

Use the webhook test client to simulate GitHub:

```bash
# Make sure server is running first
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# In another terminal, test the webhook
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --pr-number 15
```

### Test Against Real PR

1. Create and push a test branch:
```bash
git checkout -b test-feature
echo "# Test" > test.py
git add test.py
git commit -m "test: Add test file"
git push origin test-feature
```

2. Create PR on GitHub

3. Monitor webhook delivery:
   - Settings → Webhooks → Recent Deliveries
   - Should see 200-299 status codes

4. Check PR for:
   - Status check `code-reviewer/analysis` present
   - Comment with findings posted
   - Merge button shows status (if branch protected)

### Monitor Logs

```bash
# Check server output for webhook processing
# Should see messages like:

# [webhook] Received GitHub webhook for PR #15
# [coordinator] Starting review analysis
# [logic_agent] Found 2 design issues
# [security_agent] Found 1 security issue
# [summarizer] Generated final summary
# [github_client] Posted comment to PR #15
# [github_client] Created status check: failure
```

## Troubleshooting

### Webhook Not Triggering

**Symptom**: No webhook deliveries in "Recent Deliveries"

**Solutions**:
1. Verify webhook is configured (Settings → Webhooks)
2. Check webhook is "Active" (not disabled after errors)
3. Verify Payload URL is correct and accessible
4. Check server is running and accessible
5. Verify event type includes "Pull requests"

### Webhook Returns Error

**Check webhook delivery response**:
1. Settings → Webhooks → Recent Deliveries
2. Click a delivery
3. View "Response" tab

Common errors:
- `404 Not Found` - Wrong Payload URL
- `Timeout` - Server not running or slow response
- `400 Bad Request` - Signature validation failed (check secret)
- `500 Internal Server Error` - Server error (check logs)

### Status Check Not Appearing

**Symptom**: PR shows no status checks

**Solutions**:
1. Verify server received webhook (check logs)
2. Confirm analysis completed (check log timestamps)
3. Verify GitHub token has sufficient permissions
4. Check commit SHA is correct

### PR Comment Not Posted

**Symptom**: Review ran but no comment on PR

**Solutions**:
1. Check server logs for comment posting errors
2. Verify GitHub token has `repo` scope
3. Ensure PR hasn't been merged (can't comment on merged PRs)
4. Check comment rate limits haven't been exceeded

### ngrok URL Expired

**Symptom**: Webhooks fail after restarting ngrok

**Solution**:
1. ngrok free tier generates new URL on each restart
2. Get new URL: `ngrok http 8000` and copy HTTPS URL
3. Update GitHub webhook with new URL:
   - Settings → Webhooks → Edit webhook
   - Paste new Payload URL
   - Click "Update webhook"
4. Create new test PR to verify

Alternatives:
- Use paid ngrok plan for permanent URL
- Deploy to server with permanent domain
- Use GitHub Actions instead of webhook for automation

## Production Deployment

### Requirements

1. **Public domain**: GitHub must reach your server
2. **HTTPS**: GitHub webhooks require HTTPS
3. **Persistent server**: Webhooks must be processed reliably
4. **Database**: Store review history
5. **Monitoring**: Track webhook deliveries and failures

### Recommended Setup

- Use managed hosting (AWS, GCP, Azure, Heroku)
- Set up HTTPS with auto-renewal (Let's Encrypt)
- Configure load balancing for high availability
- Use database for persistent storage
- Set up alerting for webhook failures
- Monitor API rate limits

### Example: Deployment Configuration

```env
# Production environment
GITHUB_TOKEN=<secure_production_token>
GITHUB_WEBHOOK_SECRET=<strong_secret_32chars>
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for full production setup guide.

## Next Steps

1. [Test your setup](TESTING.md#webhook-testing)
2. [Configure LLM provider](LLM_SETUP.md)
3. [Deploy to production](DEPLOYMENT.md)
4. [Monitor and maintain](DEPLOYMENT.md#monitoring)
