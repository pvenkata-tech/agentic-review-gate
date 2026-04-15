#!/usr/bin/env python3
"""
Direct Review Test: Test the review endpoint without waiting for webhooks.

This script calls the /review endpoint directly to verify agents are working.
It tests the entire flow: fetching PR, running agents, and posting comments.

Usage:
    python test_review_direct.py --pr-number 12
"""

import asyncio
import httpx
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(title: str):
    print(f"\n{BLUE}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{RESET}\n")


async def test_review_endpoint(pr_number: int, owner: str = "pvenkata-tech", repo: str = "agentic-review-gate"):
    """Test the /review endpoint directly."""
    print_header(f"Testing Review Endpoint for PR #{pr_number}")
    
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(f"{RED}✗ GITHUB_TOKEN not set{RESET}")
        return False
    
    # Create review request
    payload = {
        "pr_number": pr_number,
        "owner": owner,
        "repo": repo,
        "github_token": token,
    }
    
    print(f"Review Request:")
    print(f"  PR: #{pr_number}")
    print(f"  Repository: {owner}/{repo}")
    print(f"  Token: {token[:20]}...")
    print()
    
    # Call the endpoint
    async with httpx.AsyncClient() as client:
        try:
            print(f"{YELLOW}Calling /review endpoint...{RESET}")
            response = await client.post(
                "http://localhost:8000/review",
                json=payload,
                timeout=120  # Allow up to 2 minutes for agent analysis
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n{GREEN}✓ Review completed successfully!{RESET}\n")
                print(f"Results:")
                print(f"  PR Number: {result['pr_number']}")
                print(f"  Total Findings: {result['total_findings']}")
                print(f"  Is Blocked: {result['is_blocked']}")
                
                # Check if comment was posted
                if result['total_findings'] > 0:
                    print(f"\n{GREEN}Agents found {result['total_findings']} issues!{RESET}")
                    print(f"A comment should have been posted to the PR.")
                    print(f"\nNow check PR #{pr_number} for the comment:")
                    print(f"  https://github.com/{owner}/{repo}/pull/{pr_number}")
                else:
                    print(f"\n{YELLOW}⚠ No findings detected by agents{RESET}")
                
                return True
            else:
                print(f"\n{RED}✗ Review failed{RESET}")
                print(f"Response: {response.text}")
                return False
                
        except httpx.ConnectError:
            print(f"{RED}✗ Cannot connect to http://localhost:8000{RESET}")
            print(f"\nMake sure the server is running:")
            print(f"  python -m uvicorn src.code_reviewer.main:app --reload --host 127.0.0.1 --port 8000")
            return False
        except asyncio.TimeoutError:
            print(f"{YELLOW}⚠ Request timed out after 120 seconds{RESET}")
            print(f"The agents are still analyzing. Check the server logs.")
            return False
        except Exception as e:
            print(f"{RED}✗ Error: {str(e)}{RESET}")
            return False


async def main():
    parser = argparse.ArgumentParser(
        description="Test the review endpoint directly"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        default=12,
        help="GitHub PR number (default: 12)"
    )
    parser.add_argument(
        "--owner",
        default="pvenkata-tech",
        help="GitHub repo owner (default: pvenkata-tech)"
    )
    parser.add_argument(
        "--repo",
        default="agentic-review-gate",
        help="GitHub repo name (default: agentic-review-gate)"
    )
    
    args = parser.parse_args()
    
    print(f"{BLUE}Direct Review Test Tool{RESET}")
    print("=" * 60)
    
    # Test the endpoint
    success = await test_review_endpoint(args.pr_number, args.owner, args.repo)
    
    print("\n" + "=" * 60)
    if success:
        print(f"{GREEN}Test passed! ✓{RESET}")
        print("\nNext steps:")
        print("1. Wait a few seconds for the background comment posting to complete")
        print("2. Refresh the PR page")
        print("3. Look for the '🤖 **Automated Code Review**' comment")
        print("4. If still not visible, check server logs for errors")
    else:
        print(f"{RED}Test failed ✗{RESET}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
