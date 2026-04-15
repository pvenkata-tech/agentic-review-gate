#!/usr/bin/env python3
"""
Unified diagnostic tool for the agentic code review system.

This tool performs comprehensive diagnostics to help troubleshoot issues:
- GitHub API connectivity and authentication
- Server health and webhook configuration
- PR metadata retrieval
- Diff fetching and parsing
- Status check creation
- Comment posting

Usage:
    python diagnose.py
    python diagnose.py --pr-number 15        # Check specific PR
    python diagnose.py --check status        # Run only status checks
"""

import asyncio
import httpx
import os
import argparse
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from test_utils import (
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    get_github_token,
    get_github_config,
    GREEN,
    RED,
    YELLOW,
    BLUE,
    RESET,
)

load_dotenv()


async def check_github_token() -> bool:
    """Verify GitHub token is valid."""
    print_header("GitHub Token Verification")
    try:
        token = get_github_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {token}"},
            )
            if response.status_code == 200:
                user = response.json()
                print_success(f"Valid GitHub token for user: {user['login']}")
                return True
            else:
                print_error(f"Invalid token (status: {response.status_code})")
                return False
    except Exception as e:
        print_error(f"GitHub token check failed: {e}")
        return False


async def check_server_health() -> bool:
    """Check if server is running."""
    print_header("Server Health Check")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/docs", timeout=5.0)
            if response.status_code == 200:
                print_success("Server is running on http://localhost:8000")
                return True
            else:
                print_warning(f"Server returned status {response.status_code}")
                return False
    except httpx.ConnectError:
        print_error("Cannot connect to http://localhost:8000")
        print_info("Start server with: python -m uvicorn src.code_reviewer.main:app")
        return False
    except Exception as e:
        print_error(f"Server health check failed: {e}")
        return False


async def check_pr_metadata(pr_number: int) -> bool:
    """Check if we can fetch PR metadata."""
    print_header(f"PR #{pr_number} Metadata")
    try:
        config = get_github_config()
        async with httpx.AsyncClient() as client:
            url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/pulls/{pr_number}"
            response = await client.get(
                url,
                headers={"Authorization": f"token {config['token']}"},
            )
            if response.status_code == 200:
                pr = response.json()
                print_success(f"Retrieved PR #{pr_number}")
                print(f"  Title: {pr['title']}")
                print(f"  Author: {pr['user']['login']}")
                print(f"  Files: {pr['changed_files']}")
                print(f"  Additions: {pr['additions']}")
                print(f"  Deletions: {pr['deletions']}")
                return True
            else:
                print_error(f"Cannot fetch PR (status: {response.status_code})")
                return False
    except Exception as e:
        print_error(f"PR metadata check failed: {e}")
        return False


async def check_pr_files(pr_number: int) -> bool:
    """Check if we can fetch PR files."""
    print_header(f"PR #{pr_number} Files")
    try:
        config = get_github_config()
        async with httpx.AsyncClient() as client:
            url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/pulls/{pr_number}/files"
            response = await client.get(
                url,
                headers={"Authorization": f"token {config['token']}"},
                params={"per_page": 100},
            )
            if response.status_code == 200:
                files = response.json()
                print_success(f"Retrieved {len(files)} files from PR")
                
                # Check if patches are present
                files_with_patch = sum(1 for f in files if 'patch' in f)
                print(f"  Files with patch content: {files_with_patch}/{len(files)}")
                
                if files_with_patch > 0:
                    # Show sample patch
                    sample = next((f for f in files if 'patch' in f), None)
                    if sample:
                        patch_preview = sample['patch'][:100].replace('\n', ' ')
                        print(f"  Sample patch: {patch_preview}...")
                        return True
                else:
                    print_warning("No files have patch content")
                    return False
            else:
                print_error(f"Cannot fetch files (status: {response.status_code})")
                return False
    except Exception as e:
        print_error(f"Files check failed: {e}")
        return False


async def check_status_checks(pr_number: int) -> bool:
    """Check status checks for a PR."""
    print_header(f"PR #{pr_number} Status Checks")
    try:
        config = get_github_config()
        
        # Get commit SHA first
        async with httpx.AsyncClient() as client:
            pr_url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/pulls/{pr_number}"
            pr_response = await client.get(
                pr_url,
                headers={"Authorization": f"token {config['token']}"},
            )
            if pr_response.status_code != 200:
                print_error(f"Cannot fetch PR (status: {pr_response.status_code})")
                return False
            
            commit_sha = pr_response.json()['head']['sha']
            
            # Get status checks
            status_url = f"https://api.github.com/repos/{config['owner']}/{config['repo']}/commits/{commit_sha}/status"
            status_response = await client.get(
                status_url,
                headers={"Authorization": f"token {config['token']}"},
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                statuses = status_data.get('statuses', [])
                
                if not statuses:
                    print_warning("No status checks found")
                    return True
                
                print_success(f"Found {len(statuses)} status checks")
                for status in statuses:
                    state_icon = "✓" if status['state'] == 'success' else "✗" if status['state'] == 'failure' else "⏳"
                    print(f"  {state_icon} {status['context']}: {status['state']}")
                    if status['description']:
                        print(f"     {status['description']}")
                
                return True
            else:
                print_error(f"Cannot fetch status checks (status: {status_response.status_code})")
                return False
    except Exception as e:
        print_error(f"Status check failed: {e}")
        return False


async def check_merged_prs() -> bool:
    """Check for recently merged PRs."""
    print_header("Recently Merged PRs (Last 30 Days)")
    try:
        config = get_github_config()
        last_30_days = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
        
        async with httpx.AsyncClient() as client:
            url = "https://api.github.com/search/issues"
            params = {
                "q": f"is:pr is:merged merged:>{last_30_days} repo:{config['owner']}/{config['repo']}",
                "sort": "updated",
                "order": "desc",
                "per_page": 30,
            }
            response = await client.get(
                url,
                headers={"Authorization": f"token {config['token']}"},
                params=params,
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data['total_count']
                
                if count == 0:
                    print_info("No merged PRs in the last 30 days")
                    return True
                
                print_success(f"Found {count} merged PRs")
                for pr in data['items'][:5]:
                    print(f"  PR #{pr['number']}: {pr['title']}")
                    print(f"    Status: ✓ Merged by {pr['user']['login']}")
                    print(f"    Updated: {pr['updated_at']}")
                
                if count > 5:
                    print(f"  ... and {count - 5} more")
                
                return True
            else:
                print_error(f"Cannot fetch merged PRs (status: {response.status_code})")
                return False
    except Exception as e:
        print_error(f"Merged PRs check failed: {e}")
        return False


async def run_all_diagnostics(pr_number: int | None = None) -> None:
    """Run all diagnostic checks."""
    print(f"\n{BLUE}{'='*60}")
    print("Agentic Review Gate - Diagnostic Tool")
    print(f"{'='*60}{RESET}\n")
    
    results = {}
    
    # Basic checks
    results["GitHub Token"] = await check_github_token()
    results["Server Health"] = await check_server_health()
    
    # PR-specific checks
    if pr_number:
        results[f"PR #{pr_number} Metadata"] = await check_pr_metadata(pr_number)
        results[f"PR #{pr_number} Files"] = await check_pr_files(pr_number)
        results[f"PR #{pr_number} Status"] = await check_status_checks(pr_number)
    
    # Global checks
    results["Merged PRs"] = await check_merged_prs()
    
    # Summary
    print_header("Diagnostic Summary")
    for check_name, passed in results.items():
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"{check_name:.<50} {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    
    if all_passed:
        print_success("All diagnostics passed!")
        if not pr_number:
            print_info("Run with --pr-number to check a specific PR")
    else:
        print_error("Some diagnostics failed. See above for details.")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Diagnostic tool for agentic code review system"
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        help="Check specific PR (optional)"
    )
    parser.add_argument(
        "--check",
        choices=["token", "server", "pr", "status", "merged"],
        help="Run specific check (optional)"
    )
    
    args = parser.parse_args()
    
    if args.check:
        if args.check == "token":
            await check_github_token()
        elif args.check == "server":
            await check_server_health()
        elif args.check == "pr" and args.pr_number:
            await check_pr_metadata(args.pr_number)
            await check_pr_files(args.pr_number)
        elif args.check == "status" and args.pr_number:
            await check_status_checks(args.pr_number)
        elif args.check == "merged":
            await check_merged_prs()
    else:
        await run_all_diagnostics(args.pr_number)


if __name__ == "__main__":
    asyncio.run(main())
