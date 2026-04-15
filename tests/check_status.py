#!/usr/bin/env python3
"""
Check if status checks were created on a PR.

Usage:
    python check_status.py --pr-number 15
"""

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


async def check_status_checks(pr_number: int, owner: str = "pvenkata-tech", repo: str = "agentic-review-gate"):
    """Check status checks on a PR commit."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print(f"{RED}✗ GITHUB_TOKEN not set{RESET}")
        return False
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    
    print(f"\n{BLUE}Checking status checks for PR #{pr_number}{RESET}")
    
    # Get PR info to get commit SHA
    async with httpx.AsyncClient() as client:
        # Get PR info
        pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = await client.get(pr_url, headers=headers)
        pr_response.raise_for_status()
        pr_info = pr_response.json()
        
        commit_sha = pr_info["head"]["sha"]
        print(f"Commit SHA: {commit_sha[:7]}")
        
        # Get status checks for this commit
        status_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}/status"
        status_response = await client.get(status_url, headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        print(f"\nOverall state: {status_data['state']}")
        print(f"Total statuses: {len(status_data['statuses'])}\n")
        
        if not status_data['statuses']:
            print(f"{YELLOW}⚠ No status checks found on this commit yet{RESET}")
            print(f"  This might mean:")
            print(f"  1. Status checks haven't been created yet")
            print(f"  2. Give the server a few seconds and check again")
            print(f"  3. Check server logs for errors")
            return False
        
        found_code_reviewer = False
        for status in status_data['statuses']:
            context = status['context']
            state = status['state']
            description = status['description']
            
            if 'code-reviewer' in context:
                found_code_reviewer = True
                color = GREEN if state == 'failure' else RED
                print(f"{color}✓ {context}: {state}{RESET}")
                print(f"  Description: {description}")
            else:
                print(f"  {context}: {state}")
                print(f"    {description}")
        
        if found_code_reviewer:
            print(f"\n{GREEN}✓ Code reviewer status check found!{RESET}")
            print(f"\nTo enforce merge blocking:")
            print(f"1. Go to: https://github.com/{owner}/{repo}/settings/rules")
            print(f"2. Click 'New ruleset'")
            print(f"3. Set enforcement to 'Active'")
            print(f"4. Add target: main branch")
            print(f"5. Add rule: 'Require status checks to pass'")
            print(f"6. Search for and select: 'code-reviewer/analysis'")
            print(f"7. Click 'Create'")
            return True
        else:
            print(f"\n{YELLOW}⚠ Code reviewer status check not found{RESET}")
            return False


if __name__ == "__main__":
    import asyncio
    
    parser = argparse.ArgumentParser(description="Check status checks on a PR")
    parser.add_argument("--pr-number", type=int, default=15, help="PR number to check")
    args = parser.parse_args()
    
    success = asyncio.run(check_status_checks(args.pr_number))
    
    if not success:
        print(f"\n{YELLOW}Next steps:{RESET}")
        print(f"1. Make sure the server is running and healthy")
        print(f"2. Run the review test again: python tests/test_review_direct.py --pr-number {args.pr_number}")
        print(f"3. Wait 5 seconds")
        print(f"4. Run this script again\n")
