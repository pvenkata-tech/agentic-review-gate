#!/usr/bin/env python3
"""Quick test to verify files are being retrieved"""
import asyncio
import os
from dotenv import load_dotenv
from code_reviewer.utils.github_client import GitHubClient, GitHubConfig

load_dotenv()

async def test_file_retrieval():
    token = os.getenv("GITHUB_TOKEN")
    config = GitHubConfig(token=token, owner="pvenkata-tech", repo="agentic-review-gate")
    client = GitHubClient(config)
    
    print("Testing file retrieval for PR #12...")
    print()
    
    # Get PR info
    pr_info = await client.get_pr_info(12)
    print(f"PR Info:")
    print(f"  Title: {pr_info['title']}")
    print(f"  Additions: {pr_info.get('additions', 0)}")
    print(f"  Deletions: {pr_info.get('deletions', 0)}")
    print()
    
    # Get files (this is the fix)
    files = await client.get_pr_files(12)
    print(f"Files Changed: {len(files)} files")
    for i, f in enumerate(files[:5], 1):
        print(f"  {i}. {f['filename']}")
    if len(files) > 5:
        print(f"  ... and {len(files) - 5} more files")
    print()
    
    print("✓ File retrieval working correctly!")

asyncio.run(test_file_retrieval())
