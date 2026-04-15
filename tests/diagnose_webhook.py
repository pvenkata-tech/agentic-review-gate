#!/usr/bin/env python3
"""
Webhook Diagnostic Tool

This script helps diagnose why comments aren't being posted after webhook triggering.
Run this to test:
1. GitHub API token validity
2. Server configuration
3. Comment posting capability
4. Webhook validation

Usage:
    python diagnose_webhook.py
"""

import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(title: str):
    """Print a section header."""
    print(f"\n{BLUE}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{RESET}\n")


def print_success(msg: str):
    """Print success message."""
    print(f"{GREEN}✓ {msg}{RESET}")


def print_error(msg: str):
    """Print error message."""
    print(f"{RED}✗ {msg}{RESET}")


def print_warning(msg: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {msg}{RESET}")


async def test_github_token():
    """Test if GitHub token is valid and has proper permissions."""
    print_header("Testing GitHub Token")
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print_error("GITHUB_TOKEN not set in .env file")
        return False
    
    print(f"Token: {token[:20]}...")
    
    # Test token validity
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print_success(f"Token is valid for user: {user_data.get('login')}")
                return True
            elif response.status_code == 401:
                print_error("Token is invalid or expired")
                return False
            else:
                print_error(f"GitHub API returned: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Failed to test token: {str(e)}")
            return False


async def test_webhook_secret():
    """Test if webhook secret is configured."""
    print_header("Testing Webhook Secret")
    
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        print_warning("GITHUB_WEBHOOK_SECRET not set (webhooks won't validate)")
        return False
    
    print_success(f"Webhook secret is configured: {secret[:20]}...")
    return True


async def test_comment_posting():
    """Test if we can post a comment to a test PR."""
    print_header("Testing Comment Posting")
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print_error("GITHUB_TOKEN not set - cannot test comment posting")
        return False
    
    # Use a known test repo or prompt user for one
    owner = os.getenv("GITHUB_OWNER", "pvenkata-tech")
    repo = os.getenv("GITHUB_REPO", "agentic-review-gate")
    
    print(f"Repository: {owner}/{repo}")
    print(f"Looking for recent PRs to test comment posting...\n")
    
    # Get list of PRs
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=5",
                headers={"Authorization": f"token {token}"},
                timeout=5
            )
            
            if response.status_code != 200:
                print_error(f"Failed to fetch PRs: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
            prs = response.json()
            if not prs:
                print_warning("No open PRs found for testing")
                print("Create a PR first to test comment posting")
                return False
            
            # Get the first PR
            pr = prs[0]
            pr_number = pr["number"]
            print(f"Found open PR #{pr_number}: {pr['title']}\n")
            
            # Try to post a test comment
            test_comment = "🤖 **Test Comment from Diagnostic Tool**\n\nThis is a test to verify comment posting works."
            
            print(f"Attempting to post test comment to PR #{pr_number}...")
            
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={"body": test_comment},
                timeout=5
            )
            
            if response.status_code == 201:
                comment_data = response.json()
                comment_id = comment_data.get("id")
                print_success(f"Successfully posted test comment (ID: {comment_id})")
                
                # Try to clean up (delete the test comment)
                print(f"\nCleaning up test comment...")
                delete_response = await client.delete(
                    f"https://api.github.com/repos/{owner}/{repo}/issues/comments/{comment_id}",
                    headers={"Authorization": f"token {token}"},
                    timeout=5
                )
                
                if delete_response.status_code == 204:
                    print_success("Cleaned up test comment")
                else:
                    print_warning(f"Could not delete test comment: {delete_response.status_code}")
                
                return True
            else:
                print_error(f"Failed to post comment: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Error testing comment posting: {str(e)}")
            return False


async def test_webhook_validation():
    """Test webhook signature validation logic."""
    print_header("Testing Webhook Validation")
    
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        print_error("GITHUB_WEBHOOK_SECRET not set - cannot validate webhooks")
        return False
    
    try:
        from code_reviewer.utils.webhooks import WebhookHandler
        
        handler = WebhookHandler(secret=secret)
        print_success("WebhookHandler initialized successfully")
        
        # Simulate a proper GitHub webhook payload
        import json
        import hmac
        import hashlib
        
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 99,
                "title": "Test PR",
                "user": {"login": "testuser"},
                "head": {"ref": "feature/test"},
                "base": {"ref": "main"},
            },
            "repository": {
                "owner": {"login": "testorg"},
                "name": "testrepo"
            }
        }
        
        payload_json = json.dumps(payload)
        payload_bytes = payload_json.encode('utf-8')
        
        # Generate valid signature
        signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        print(f"\nGenerated test signature: {signature[:40]}...")
        
        # Test validation
        should_process, parsed_payload, error = handler.process_webhook(
            raw_body=payload_bytes,
            signature_header=signature,
            event_type="pull_request"
        )
        
        if should_process:
            print_success("Webhook signature validation works correctly")
            return True
        else:
            print_error(f"Webhook validation failed: {error}")
            return False
            
    except Exception as e:
        print_error(f"Error testing webhook validation: {str(e)}")
        return False


async def test_server_startup():
    """Test if the FastAPI server can start."""
    print_header("Testing Server Startup")
    
    try:
        # Try to import the main app
        from code_reviewer.main import app
        print_success("FastAPI app imported successfully")
        
        # Check if required environment variables are set
        required_vars = ["GITHUB_TOKEN", "GITHUB_WEBHOOK_SECRET"]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print_warning(f"Missing environment variables: {', '.join(missing)}")
            print("The server will start but may not function properly")
        else:
            print_success("All required environment variables are set")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to import FastAPI app: {str(e)}")
        return False


async def main():
    """Run all diagnostics."""
    print(f"\n{BLUE}Webhook Diagnostic Tool{RESET}")
    print("=" * 60)
    
    results = {}
    
    # Run all tests
    results["Server Startup"] = await test_server_startup()
    results["GitHub Token"] = await test_github_token()
    results["Webhook Secret"] = await test_webhook_secret()
    results["Comment Posting"] = await test_comment_posting()
    results["Webhook Validation"] = await test_webhook_validation()
    
    # Summary
    print_header("Diagnostic Summary")
    
    for test_name, passed in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print(f"{GREEN}All diagnostics passed! ✓{RESET}")
        print("\nNext steps:")
        print("1. Make sure the webhook is configured in GitHub")
        print("   - Go to Settings > Webhooks")
        print("   - Payload URL should be: https://your-ngrok-url/webhook/github")
        print("   - Secret should match GITHUB_WEBHOOK_SECRET")
        print("2. Test by creating a new PR")
        print("3. Check the Recent Deliveries section to see webhook requests")
    else:
        print(f"{RED}Some diagnostics failed ✗{RESET}")
        print("\nFailing tests need to be fixed before webhooks will work")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
