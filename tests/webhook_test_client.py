#!/usr/bin/env python3
"""
GitHub Webhook Test Client

Simulates GitHub webhook delivery for local testing.
Useful for testing the webhook handler without a real GitHub push.

Usage:
    python webhook_test_client.py --help
    python webhook_test_client.py --url http://localhost:8000/webhook/github \\
      --secret my_secret --pr-number 42
"""

import asyncio
import argparse
import json
import hmac
import hashlib
from typing import Dict, Any
from datetime import datetime


def create_github_payload(
    pr_number: int = 42,
    action: str = "opened",
    title: str = "Test PR",
    author: str = "testuser",
    owner: str = "testorg",
    repo: str = "testrepo",
    branch: str = "feature/test",
    base_branch: str = "main",
    additions: int = 10,
    deletions: int = 5,
    changed_files: int = 3,
) -> Dict[str, Any]:
    """
    Create a realistic GitHub webhook payload.
    
    Args:
        pr_number: PR number
        action: PR action (opened, synchronize, reopened, closed)
        title: PR title
        author: Author username
        owner: Repository owner
        repo: Repository name
        branch: Feature branch name
        base_branch: Target branch name
        additions: Lines added
        deletions: Lines deleted
        changed_files: Number of files changed
        
    Returns:
        GitHub webhook payload dict
    """
    return {
        "action": action,
        "pull_request": {
            "id": pr_number * 1000,
            "number": pr_number,
            "title": title,
            "user": {
                "login": author,
                "id": 1,
                "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                "gravatar_id": "",
                "url": f"https://api.github.com/users/{author}",
            },
            "body": f"Description for PR #{pr_number}",
            "created_at": datetime.now().isoformat() + "Z",
            "updated_at": datetime.now().isoformat() + "Z",
            "head": {
                "label": f"{owner}:{branch}",
                "ref": branch,
                "sha": "abc123def456789",
                "user": {
                    "login": author,
                },
                "repo": {
                    "name": repo,
                    "owner": {
                        "login": owner,
                    },
                },
            },
            "base": {
                "label": f"{owner}:{base_branch}",
                "ref": base_branch,
                "sha": "def456abc789123",
                "user": {
                    "login": owner,
                },
                "repo": {
                    "name": repo,
                    "owner": {
                        "login": owner,
                    },
                },
            },
            "additions": additions,
            "deletions": deletions,
            "changed_files": changed_files,
            "state": "open",
            "locked": False,
            "draft": False,
            "mergeable": True,
            "merged": False,
            "commits": 1,
            "comments": 0,
        },
        "repository": {
            "id": 1234567,
            "name": repo,
            "full_name": f"{owner}/{repo}",
            "private": False,
            "owner": {
                "login": owner,
                "id": 1,
            },
            "html_url": f"https://github.com/{owner}/{repo}",
            "description": "Test repository",
        },
        "sender": {
            "login": author,
            "id": 1,
        },
    }


def calculate_signature(payload: bytes, secret: str) -> str:
    """
    Calculate GitHub webhook signature.
    
    Args:
        payload: JSON payload as bytes
        secret: Webhook secret
        
    Returns:
        Signature string in format: sha256=<hex>
    """
    signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


async def send_webhook(
    url: str,
    payload: Dict[str, Any],
    secret: str,
    event_type: str = "pull_request",
    verbose: bool = False,
) -> bool:
    """
    Send webhook to server.
    
    Args:
        url: Webhook endpoint URL
        payload: Webhook payload dict
        secret: Webhook secret for HMAC
        event_type: GitHub event type
        verbose: Print detailed output
        
    Returns:
        True if successful (2xx status), False otherwise
    """
    try:
        import httpx
    except ImportError:
        print("Error: httpx not installed. Install with: pip install httpx")
        return False
    
    # Serialize payload to JSON
    payload_json = json.dumps(payload, indent=2)
    payload_bytes = payload_json.encode()
    
    # Calculate signature
    signature = calculate_signature(payload_bytes, secret)
    
    # Prepare headers
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": event_type,
        "X-Hub-Signature-256": signature,
        "User-Agent": "GitHub-Hookshot/webhook-test",
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Webhook Test Client")
        print(f"{'='*60}")
        print(f"\nURL: {url}")
        print(f"Event: {event_type}")
        print(f"Signature: {signature}")
        print(f"\nHeaders:")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        print(f"\nPayload Preview:")
        print(f"  PR #{payload['pull_request']['number']}: {payload['pull_request']['title']}")
        print(f"  Author: {payload['pull_request']['user']['login']}")
        print(f"  Action: {payload['action']}")
        print(f"\n{'='*60}")
    
    try:
        # Send POST request
        async with httpx.AsyncClient() as client:
            print(f"\n➜ Sending webhook to {url}...")
            response = await client.post(url, headers=headers, content=payload_bytes)
            
            if verbose:
                print(f"\nResponse Status: {response.status_code}")
                print(f"Response Headers:")
                for key, value in response.headers.items():
                    print(f"  {key}: {value}")
                if response.text:
                    print(f"Response Body:")
                    print(f"  {response.text}")
            
            if 200 <= response.status_code < 300:
                print(f"✓ Webhook delivered successfully ({response.status_code})")
                return True
            else:
                print(f"✗ Webhook delivery failed ({response.status_code})")
                return False
    
    except Exception as e:
        print(f"✗ Error sending webhook: {str(e)}")
        print(f"  Make sure the server is running at {url}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Send a GitHub webhook event to test the receiver"
    )
    
    # Required arguments
    parser.add_argument(
        "--url",
        required=True,
        help="Webhook endpoint URL (e.g., http://localhost:8000/webhook/github)",
    )
    parser.add_argument(
        "--secret",
        required=True,
        help="Webhook secret (must match server's GITHUB_WEBHOOK_SECRET)",
    )
    
    # Payload customization
    parser.add_argument(
        "--pr-number",
        type=int,
        default=42,
        help="Pull request number (default: 42)",
    )
    parser.add_argument(
        "--action",
        choices=["opened", "synchronize", "reopened", "closed"],
        default="opened",
        help="PR action (default: opened)",
    )
    parser.add_argument(
        "--title",
        default="Add webhook testing capability",
        help="PR title",
    )
    parser.add_argument(
        "--author",
        default="testuser",
        help="PR author username",
    )
    parser.add_argument(
        "--owner",
        default="testorg",
        help="Repository owner",
    )
    parser.add_argument(
        "--repo",
        default="testrepo",
        help="Repository name",
    )
    parser.add_argument(
        "--additions",
        type=int,
        default=10,
        help="Lines added",
    )
    parser.add_argument(
        "--deletions",
        type=int,
        default=5,
        help="Lines deleted",
    )
    parser.add_argument(
        "--changed-files",
        type=int,
        default=3,
        help="Number of files changed",
    )
    
    # Options
    parser.add_argument(
        "--event",
        default="pull_request",
        help="GitHub event type (default: pull_request)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Send webhook N times",
    )
    
    args = parser.parse_args()
    
    # Send webhook(s)
    for i in range(args.count):
        payload = create_github_payload(
            pr_number=args.pr_number + i,
            action=args.action,
            title=args.title,
            author=args.author,
            owner=args.owner,
            repo=args.repo,
            additions=args.additions,
            deletions=args.deletions,
            changed_files=args.changed_files,
        )
        
        success = await send_webhook(
            url=args.url,
            payload=payload,
            secret=args.secret,
            event_type=args.event,
            verbose=args.verbose or i == 0,  # Verbose for first request
        )
        
        if not success:
            exit(1)
        
        if args.count > 1 and i < args.count - 1:
            print(f"\nWaiting before next webhook...")
            await asyncio.sleep(1)
    
    print(f"\n✓ All {args.count} webhook(s) sent successfully!")


if __name__ == "__main__":
    asyncio.run(main())
#   T e s t   d e b u g   l o g g i n g   -   2 0 2 6 - 0 4 - 1 5   1 2 : 4 5 : 0 5  
 