# GitHub Webhook Integration Guide

## Overview

This guide explains how to set up and test GitHub webhook integration with the agentic-review-gate system.

## Webhook Flow

```
GitHub Repository
      │
      ├─→ PR opened / commits pushed
      │
      ├─→ GitHub sends POST to /webhook/github
      │
      ├─→ Signature validated with GITHUB_WEBHOOK_SECRET
      │
      ├─→ Payload parsed and analyzed
      │
      ├─→ ReviewCoordinator runs analysis in background
      │
      └─→ Comment posted to PR with findings
```

## Setup Steps

### Step 1: Generate Webhook Secret

The webhook secret is used to verify that requests come from GitHub.

**Option A: Using Python**

```python
import secrets
import base64

# Generate a random secret
secret = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"GITHUB_WEBHOOK_SECRET={secret}")
```

**Option B: Using PowerShell**

```powershell
$secret = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
Write-Host "GITHUB_WEBHOOK_SECRET=$secret"
```

**Option C: Using OpenSSL** (if installed)

```bash
openssl rand -base64 32
```

Save this secret! You'll need it for both GitHub and your environment variables.

### Step 2: Set Environment Variable

Add the secret to your `.env` file or system environment variables:

```env
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_WEBHOOK_SECRET=your_generated_secret
```

### Step 3: Configure GitHub Webhook

1. Go to your repository → **Settings** → **Webhooks**
2. Click **"Add webhook"** button
3. Fill in the webhook form:

| Field | Value |
|-------|-------|
| **Payload URL** | `https://your-domain.com/webhook/github` |
| **Content type** | `application/json` |
| **Secret** | Paste your secret from Step 1 |
| **Which events would you like to trigger this webhook?** | Select "Let me select individual events" |

4. **Select Events** (check these boxes):
   - ✅ Pull requests
   - Optionally: Pull request reviews, Pull request review comments

5. Make sure **"Active"** is checked
6. Click **"Add webhook"**

### Step 4: Test the Webhook

GitHub provides a "Recent Deliveries" tab where you can:
1. See all webhook deliveries
2. View the payload sent
3. See the response status
4. Resend a delivery for testing

## Local Testing

For development, you'll need to expose your local server to the internet.

### Option 1: ngrok (Recommended for Development)

ngrok creates a secure tunnel to your localhost.

**Setup:**

```powershell
# Download from https://ngrok.com/download
# Extract and add to PATH

# Create ngrok config file at %APPDATA%\ngrok\ngrok.yml
# Add:
#   authtoken: your_ngrok_auth_token

# Run ngrok
ngrok http 8000

# You'll see output like:
# Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

**Use this URL in GitHub webhook:**
- Payload URL: `https://abc123.ngrok.io/webhook/github`
- Secret: Your generated secret

### Option 2: Cloudflare Tunnel

```bash
# Install Cloudflare Tunnel
# Then run:
cloudflared tunnel --url http://localhost:8000

# Use the provided URL for your webhook
```

### Option 3: Manual Testing with curl

Test without a real PR:

**PowerShell:**

```powershell
$payload = @{
    action = "opened"
    pull_request = @{
        number = 1
        title = "Test PR"
        head = @{
            ref = "feature/test"
            sha = "abc123"
        }
        base = @{
            ref = "main"
        }
        user = @{
            login = "test-user"
        }
        diff_url = "https://api.github.com/repos/owner/repo/pulls/1.diff"
    }
    repository = @{
        name = "test-repo"
        full_name = "owner/test-repo"
        owner = @{
            login = "owner"
        }
    }
} | ConvertTo-Json

# Generate signature
$secret = "your_webhook_secret"
$bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
$hmac = New-Object System.Security.Cryptography.HMACSHA256
$hmac.Key = [System.Text.Encoding]::UTF8.GetBytes($secret)
$signature = "sha256=" + ($hmac.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") } | Join-String)

# Send request
$headers = @{
    "X-Hub-Signature-256" = $signature
    "X-GitHub-Event" = "pull_request"
    "Content-Type" = "application/json"
}

Invoke-WebRequest -Uri "http://localhost:8000/webhook/github" `
    -Method POST `
    -Headers $headers `
    -Body $payload
```

**Bash/curl:**

```bash
SECRET="your_webhook_secret"
PAYLOAD='{"action":"opened","pull_request":{"number":1,...}}'

SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" -r | cut -d' ' -f1)"

curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -d "$PAYLOAD"
```

## Webhook Event Types

The system responds to these pull request events:

| Event | Trigger | Behavior |
|-------|---------|----------|
| `opened` | PR created | Full analysis run |
| `synchronize` | New commits pushed | Full analysis run |
| `reopened` | PR reopened | Full analysis run |
| `closed` | PR closed | Ignored (webhook sent but not processed) |
| `labeled` | Label added | Ignored |
| `unlabeled` | Label removed | Ignored |

## Security Best Practices

### 1. Use HTTPS

Always use HTTPS for your webhook URL in production:

```
❌ http://example.com/webhook/github
✅ https://example.com/webhook/github
```

### 2. Validate Signatures

The system validates `X-Hub-Signature-256` header:

```python
# In verify_github_webhook_signature()
if not verify_github_webhook_signature(raw_body, signature, secret):
    raise HTTPException(status_code=403, detail="Invalid signature")
```

### 3. Rotate Secrets

Change your webhook secret periodically:

```
GitHub Settings → Webhooks → Your Webhook → Edit → Update Secret
```

### 4. Limit Permissions

Your GitHub token should have minimal required permissions:

```
✅ repo:status (access commit status)
✅ read:repo_hook (read webhook config)
❌ admin:repo_hook (DON'T grant if not needed)
❌ public_repo (avoid exposing all repos)
```

### 5. Monitor Deliveries

Check GitHub webhook delivery history regularly:

1. Go to repository → Settings → Webhooks
2. Click your webhook → "Recent Deliveries"
3. Look for failed deliveries (status != 200)
4. Check response body for error messages

## Debugging Webhook Issues

### Check Webhook Logs

In GitHub webhook delivery history:

```json
{
  "id": 123456789,
  "guid": "abc-123-def",
  "url": "https://api.github.com/repos/owner/repo/hooks/123456789/deliveries/abc-123",
  "status": "completed",
  "conclusion": "success",
  "action": "opened",
  "attempt": 1,
  "created_at": "2024-04-15T12:00:00Z",
  "updated_at": "2024-04-15T12:00:01Z",
  "request": {
    "headers": {...},
    "payload": {...}
  },
  "response": {
    "status": 200,
    "headers": {...},
    "body": "{\"status\": \"accepted\", ...}"
  }
}
```

### Check Application Logs

Enable debug logging:

```env
LOG_LEVEL=DEBUG
```

Look for messages like:
```
GitHub webhook received for PR #123
Webhook signature verification successful
Starting review analysis in background
```

### Common Issues

**Issue: 404 Not Found**
- Check webhook URL spelling
- Verify server is running on correct port
- Check if route is registered in FastAPI

**Issue: 403 Forbidden (Signature Verification Failed)**
- Verify secret matches between GitHub and `.env`
- Check that raw body is being used (not parsed JSON)
- Ensure constant-time comparison is used

**Issue: Timeout (Request takes >30 seconds)**
- GitHub webhooks have a 30-second timeout
- Use background tasks for long-running operations
- Verify operations are async

**Issue: 500 Internal Server Error**
- Check application logs for stack trace
- Verify GITHUB_TOKEN is valid
- Check that all environment variables are set

## Advanced Configuration

### Retries

GitHub automatically retries failed deliveries:

- **Immediate retry**: If response status ≠ 200
- **Delayed retries**: Up to 3 days later (exponential backoff)
- **Manual retry**: Through "Recent Deliveries" UI

### Rate Limiting

GitHub has rate limits:

- **Webhooks**: No hard limit, but must respond quickly
- **API calls**: 5,000 requests/hour per token

Monitor usage:

```python
import requests
response = requests.head("https://api.github.com/rate_limit")
remaining = response.headers.get("X-RateLimit-Remaining")
```

### Multiple Webhooks

You can have multiple webhook URLs:

- One for testing (development URL)
- One for staging
- One for production

Each with its own secret!

## Testing Checklist

- [ ] Webhook URL is publicly accessible
- [ ] Secret is set in both GitHub and environment
- [ ] Signature validation is enabled
- [ ] POST /webhook/github returns 202 Accepted
- [ ] Background task starts review
- [ ] Comments posted to PR after analysis
- [ ] Review coordinator handles errors gracefully
- [ ] Logs show all webhook events
- [ ] Rate limiting doesn't cause issues
- [ ] Multiple PRs can be processed in parallel

## Production Deployment

For production:

1. **Use HTTPS**: Enable SSL/TLS
2. **Enable signature validation**: Don't skip in production!
3. **Monitor deliveries**: Set up alerting for failures
4. **Scale horizontally**: Multiple instances behind load balancer
5. **Add caching**: Store review results in Redis
6. **Implement retry logic**: Handle transient failures
7. **Set up Dead Letter Queue**: For failed reviews
8. **Monitor rate limits**: Implement backoff strategy

## Webhook Payload Reference

Full structure of `pull_request` webhook:

```json
{
  "action": "opened|synchronize|reopened",
  "pull_request": {
    "id": 123456,
    "number": 42,
    "title": "Fix bug in authentication",
    "user": {
      "login": "github-username"
    },
    "head": {
      "ref": "feature/fix-auth",
      "sha": "abc123def456..."
    },
    "base": {
      "ref": "main",
      "sha": "xyz789..."
    },
    "diff_url": "https://github.com/owner/repo/pull/42.diff",
    "patch_url": "https://github.com/owner/repo/pull/42.patch"
  },
  "repository": {
    "name": "repo-name",
    "full_name": "owner/repo-name",
    "owner": {
      "login": "owner"
    }
  }
}
```

---

For more help, see:
- [GitHub Webhook Documentation](https://docs.github.com/webhooks-and-events)
- [GitHub REST API](https://docs.github.com/rest)
- [ngrok Documentation](https://ngrok.com/docs)
