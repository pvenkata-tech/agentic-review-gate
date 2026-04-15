# Integration Guide - GitHub and LLM Setup

Complete guide for integrating external services: GitHub webhooks, branch protection, and LLM providers.

## Table of Contents

1. [GitHub Webhook Integration](#github-webhook-integration)
2. [GitHub Branch Protection](#github-branch-protection)
3. [LLM Provider Setup](#llm-provider-setup)
4. [Status Checks](#status-checks)
5. [Testing Integrations](#testing-integrations)
6. [Troubleshooting](#troubleshooting)

---

## GitHub Webhook Integration

### Overview

Webhooks allow GitHub to automatically trigger code reviews when PRs are opened or updated.

**Flow**:
```
GitHub PR Event → POST to /webhook/github → Signature validation
    ↓
Load PR metadata and diff → Run agents in background
    ↓
Post comment with findings → Create status check
```

### Step 1: Generate Webhook Secret

```python
import secrets
import base64
secret = base64.b64encode(secrets.token_bytes(32)).decode()
print(secret)
```

Save this value for use in Step 2 and GitHub configuration.

### Step 2: Update Environment Variables

Add to `.env`:
```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
```

### Step 3: Start Server

```bash
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000
```

### Step 4: Expose Server to Internet

For local development, you need public access.

#### Option A: ngrok (Recommended for Development)

```bash
# Download from https://ngrok.com/download

ngrok http 8000
# Output: Forwarding https://abc-123.ngrok.io -> http://127.0.0.1:8000

# Copy the HTTPS URL: https://abc-123.ngrok.io
```

#### Option B: Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:8000
```

#### Option C: Production Deployment

Use your production domain with HTTPS (see [OPERATIONS.md#deployment](OPERATIONS.md#deployment))

### Step 5: Configure GitHub Webhook

1. Go to repository → **Settings** → **Webhooks** → **Add webhook**
2. Fill in:

| Field | Value |
|-------|-------|
| Payload URL | `https://your-ngrok-url/webhook/github` |
| Content type | `application/json` |
| Secret | Your GITHUB_WEBHOOK_SECRET |
| Events | Select "Pull requests" |
| Active | ✓ Checked |

3. Click **"Add webhook"**

### Step 6: Test Webhook

1. Create test PR: `git checkout -b test && git push origin test` then create PR on GitHub
2. Monitor webhook: Settings → Webhooks → Recent Deliveries
3. Verify 200-299 status code
4. Check PR for comment and status check

---

## GitHub Branch Protection

### Setup Branch Protection Rules

Branch protection rules enforce code review before merging.

1. Go to repository → **Settings** → **Branches** → **Add rule**
2. Branch name pattern: `main` (or your protected branch)
3. Check these options:

**Require pull request before merging**:
- ✓ Require pull request reviews before merging
- ✓ Dismiss stale pull request approvals when new commits are pushed

**Require status checks to pass before merging**:
- ✓ Require branches to be up to date before merging
- ✓ Select: `code-reviewer/analysis`

4. Click **"Create"**

### Result

With these rules:
- ✅ **No critical issues** → Status = `success` → PR can merge
- ❌ **Critical issues found** → Status = `failure` → PR BLOCKED

### GitHub Token Scopes

Your GitHub token needs:
- ✓ `repo` - Read PRs, post comments, create status checks
- ✓ `read:user` - Access user profile information

Check token scopes at: https://github.com/settings/personal-access-tokens

### Token Security

**Best Practices**:
1. Never commit tokens - keep in `.env` (added to `.gitignore`)
2. Use environment variables in CI/CD pipelines
3. Rotate tokens if ever exposed
4. Use fine-grained tokens instead of classic tokens
5. Regenerate if compromised

---

## LLM Provider Setup

### Overview

LLMs enable semantic code analysis. The system supports:
- **Claude 3** (Anthropic) - Recommended
- **GPT-4** (OpenAI) - Alternative
- **Mock Mode** (No LLM) - Development only

### Option 1: Claude (Recommended)

**Why Claude?**
- Excellent code understanding
- $3 per 1M input tokens (cost-effective)
- 200k context window (handles large diffs)
- Best reasoning for design patterns

#### Setup

1. Get API key:
   - Go to https://console.anthropic.com/
   - Create account if needed
   - Generate API key in settings
   - Copy key (format: `sk-ant-...`)

2. Add to `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

3. Verify:
```bash
python -c "import anthropic; print('✓ Claude ready')"
```

### Option 2: GPT-4 (Alternative)

**Why GPT-4?**
- Strong semantic understanding
- Available through OpenAI
- Good for code review

#### Setup

1. Get API key:
   - Go to https://platform.openai.com/api-keys
   - Create account if needed
   - Generate API key
   - Copy key (format: `sk-...`)

2. Add to `.env`:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxx
```

3. Verify:
```bash
python -c "import openai; print('✓ GPT-4 ready')"
```

### Option 3: Mock Mode (Development)

No API key required, no costs:

```bash
# Just don't set ANTHROPIC_API_KEY or OPENAI_API_KEY
# System uses built-in rule-based analysis
python -m uvicorn src.code_reviewer.main:app
```

### Provider Comparison

| Feature | Claude | GPT-4 | Mock |
|---------|--------|-------|------|
| Cost | $$ | $$$ | Free |
| Code Analysis | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Speed | Fast | Medium | Instant |
| Context | 200k tokens | 128k tokens | Limited |
| Setup | 2 minutes | 2 minutes | None |

### Cost Estimation

**Typical PR** (5 files, ~150 lines changed):
- Input tokens: ~2,500
- Output tokens: ~500
- **Claude cost**: ~$0.015 per PR
- **GPT-4 cost**: ~$0.10 per PR

**Monthly** (1,000 PRs):
- **Claude**: ~$15-20/month
- **GPT-4**: ~$100-150/month

### API Rate Limits

**Claude**:
- 5 requests per minute (free)
- Higher with paid plan

**GPT-4**:
- Based on organization tier
- 3,500 requests per minute (standard)

### Verify LLM Configuration

```bash
# Test Claude
python -c "from anthropic import Anthropic; c = Anthropic(); print('✓ Claude available')"

# Test GPT-4
python -c "from openai import OpenAI; c = OpenAI(); print('✓ GPT-4 available')"

# Test system
python tests/diagnose.py --check token
```

---

## Status Checks

### How Status Checks Work

Status checks are GitHub's mechanism to enforce quality gates.

**Status Check Details**:
- **Context**: `code-reviewer/analysis`
- **States**:
  - `pending` - Analysis in progress
  - `success` - No critical issues (can merge)
  - `failure` - Critical issues found (merge blocked)

### Viewing Status Checks

On PR page, status appears below description:
```
✓ code-reviewer/analysis — success
All checks have passed

🟢 All checks passed
```

Or if issues found:
```
✗ code-reviewer/analysis — failure
❌ Changes Requested - 2 critical findings

🔴 Some checks were not successful
```

### Enforcing with Branch Protection

When branch protection is enabled with status check requirement:
- ✅ PR with `success` status → **CAN MERGE** ✓
- ❌ PR with `failure` status → **CANNOT MERGE** ✗

---

## Testing Integrations

### Quick Integration Test

```bash
# Test direct review (no webhook needed)
python tests/examples.py direct --pr-number 15

# Should complete in 10-40 seconds with findings
```

### Webhook Testing (Local)

```bash
# Simulate webhook without ngrok
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --pr-number 15
```

### Real PR Testing

1. Create test PR:
```bash
git checkout -b test-feature
echo "# test" > test.py
git add test.py
git commit -m "test: Add test file"
git push origin test-feature
# Create PR on GitHub
```

2. Monitor webhook delivery:
   - Settings → Webhooks → Recent Deliveries
   - Click delivery to view response

3. Verify on PR:
   - Status check present and passing/failing
   - Comment with findings posted
   - Merge button shows status

### Run Diagnostics

```bash
python tests/diagnose.py             # All checks
python tests/diagnose.py --pr-number 15  # Specific PR
python tests/diagnose.py --check token   # Token only
```

---

## Troubleshooting

### Webhook Not Triggering

**Problem**: No webhook deliveries in Recent Deliveries

**Solutions**:
1. Verify webhook is enabled (Settings → Webhooks)
2. Check webhook is "Active" (not disabled)
3. Verify Payload URL is correct and public
4. Verify event includes "Pull requests"
5. Check firewall allows incoming webhooks

### Webhook Error Responses

**404 Not Found**: Wrong webhook URL
- Verify ngrok URL or server address
- Update webhook URL in GitHub settings

**Timeout**: Server not responding
- Verify server is running
- Check network connectivity
- Increase timeout if analysis takes >30 seconds

**400 Bad Request**: Signature validation failed
- Verify GITHUB_WEBHOOK_SECRET matches in `.env` and GitHub
- Check secret hasn't been accidentally modified

**500 Internal Server Error**: Server error during processing
- Check server logs for detailed error message
- Verify PR metadata is accessible
- Check GitHub token has required permissions

### Status Check Not Appearing

**Problem**: PR shows no status check

**Solutions**:
1. Check server received webhook (view logs)
2. Verify analysis completed (check timestamps)
3. Ensure GitHub token has `repo` scope
4. Verify commit SHA is correct

### LLM Not Being Used

**Problem**: Review runs but analysis seems basic

**Solutions**:
1. Check API key is set: `echo $ANTHROPIC_API_KEY`
2. Verify key format (Claude: `sk-ant-`, OpenAI: `sk-`)
3. Check logs for LLM errors
4. Verify API key hasn't expired
5. Test key directly:
```python
from anthropic import Anthropic
c = Anthropic(api_key="your-key")
c.messages.create(model="claude-3-opus-20240229", messages=[{"role": "user", "content": "test"}])
```

### ngrok URL Expired

**Problem**: Webhooks fail after restarting ngrok

**Solution**:
1. Run ngrok again: `ngrok http 8000`
2. Copy new HTTPS URL
3. Update webhook in GitHub:
   - Settings → Webhooks → Edit
   - Paste new Payload URL
   - Save
4. Test with new PR

**Permanent Solution**: Use paid ngrok plan or deploy to server with permanent domain

### API Rate Limiting

**Problem**: "Rate limit exceeded" errors

**Solutions**:
1. Wait 1-2 minutes before retrying
2. Space out PR creations to avoid hitting limits
3. Use cheaper/faster LLM model
4. Upgrade GitHub token to higher rate limit tier

---

## Next Steps

1. [Run tests to verify setup](OPERATIONS.md#testing)
2. [Deploy to production](OPERATIONS.md#deployment)
3. [Monitor webhook deliveries](OPERATIONS.md#monitoring)
4. [Understand architecture](ARCHITECTURE.md)
