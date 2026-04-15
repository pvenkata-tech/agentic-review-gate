# Why Comments Aren't Being Posted

## Diagnostic Results ✓

All core components are working:
- ✓ Server can start and initialize
- ✓ GitHub token is valid and authenticated
- ✓ Webhook secret is properly configured  
- ✓ Comments CAN be posted to PRs (tested successfully)
- ✓ Webhook payload validation works correctly

## Root Cause

The **GitHub webhook is not triggering the review** because:

1. **Webhook not configured in GitHub** - You need to set up the webhook in your repository settings
2. **Wrong URL** - The webhook URL in GitHub needs to point to a publicly accessible endpoint
3. **Ngrok tunnel expired** - If using ngrok, the tunnel URL expires and needs to be updated in GitHub

## Solution: Configure GitHub Webhook

### Step 1: Start the Server Locally

```powershell
# Terminal 1: Start development server
cd c:\Users\User\Documents\Code\AI-Learn\agentic-review-gate
python -m uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 2: Create ngrok Tunnel (if developing locally)

```powershell
# Terminal 2: Create public tunnel to localhost:8000
ngrok http 8000

# You'll see:
# Forwarding    https://abc-123-456.ngrok.io -> http://127.0.0.1:8000
# Copy the HTTPS URL above
```

### Step 3: Configure GitHub Webhook

1. Go to your repository: https://github.com/pvenkata-tech/agentic-review-gate
2. Navigate to **Settings** → **Webhooks**
3. Click **Add webhook**
4. Fill in the form:

| Field | Value |
|-------|-------|
| **Payload URL** | `https://abc-123-456.ngrok.io/webhook/github` (use YOUR ngrok URL) |
| **Content type** | `application/json` |
| **Secret** | Use the secret from your `.env` file (GITHUB_WEBHOOK_SECRET) |
| **Which events** | Select "Let me select individual events" → Check "Pull requests" |
| **Active** | ✓ Checked |

5. Click **Add webhook**

### Step 4: Test the Webhook

1. Create a new test PR or edit an existing one
2. Go to **Settings** → **Webhooks** → Click your webhook
3. Scroll to **Recent Deliveries**
4. You should see POST requests listed
5. Click any request to see the response status (should be 200-299)

### Step 5: Verify Comments Appear

Once the webhook is configured and triggered:
- The server will receive the webhook event
- It will analyze the PR
- It will post a comment with findings

The comment will include findings organized like:
```
## 🔍 Automated Code Review

### 🔴 Critical Issues
- ...findings...

### 🟡 Warnings  
- ...findings...
```

## Important Notes

### ngrok URLs Expire
- **Free tier ngrok** generates new URLs each time you restart
- When you restart ngrok, update the webhook URL in GitHub with the NEW URL
- Use a paid ngrok account or deploy to a server to get a permanent URL

### GitHub Token Permissions
The token needs these scopes:
- `repo` - To read PR info and post comments
- `read:user` - To access profile info

Check: https://github.com/settings/personal-access-tokens

### Environment Variables
Never hardcode tokens, API keys, or webhook secrets in docs, code, or command history. Store them in environment variables or a secret manager, and rotate them immediately if they are ever exposed.

Verify in your local `.env` file:
```env
# Use placeholders in docs only; never commit real secrets.
GITHUB_TOKEN=<your_github_token_from_env_or_secret_manager>
GITHUB_WEBHOOK_SECRET=<your_webhook_secret_from_step_1>
```

## Testing Webhook Locally

Use the webhook test client to simulate GitHub:

```powershell
# Make sure server is running first (Terminal 1)

# Terminal 3: Test webhook locally
# PowerShell example: load secret from environment, not inline
$secret = $env:GITHUB_WEBHOOK_SECRET
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --secret "$secret" \
  --pr-number 12
```

This will simulate a GitHub webhook without needing ngrok.

## Run Diagnostics Again

After configuring the webhook, you can verify everything is set up correctly:

```powershell
python diagnose_webhook.py
```

All tests should pass with ✓.

## What Happens When Webhook Triggers

```
1. GitHub detects PR opened/updated
2. GitHub sends POST to webhook URL
3. Server validates signature with secret
4. Server parses PR metadata
5. Agents analyze the code (async, in background)
6. Summary generated
7. Comment posted to PR
8. Webhook response sent (200 OK)
```

## Next Steps

1. **Configure GitHub webhook** (see Step 3 above)
2. **Create or update a PR** to trigger the webhook
3. **Check Recent Deliveries** in webhook settings for success/failure
4. **Look for comment** on the PR
5. If comment doesn't appear, check the webhook response in Recent Deliveries

The diagnostic tool confirms everything is ready - you just need to connect GitHub to your server via the webhook URL!
