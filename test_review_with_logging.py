#!/usr/bin/env python
"""
Test the review system and verify comment posting works.

This script will:
1. Test a PR review end-to-end
2. Show detailed logs of what's happening
3. Help diagnose why comments might not be posting

Usage:
    python test_review_with_logging.py <pr_number>

Example:
    python test_review_with_logging.py 18
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Set up logging BEFORE importing our modules
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from code_reviewer.core.state import ReviewState, PRMetadata
from code_reviewer.core.coordinator import ReviewCoordinator
from code_reviewer.utils.github_client import GitHubClient, GitHubConfig
from code_reviewer.utils.cache import get_cache_backend
from code_reviewer.utils.logger import get_logger

logger = get_logger()


async def test_review(pr_number: int):
    """Test review for a specific PR."""
    print(f"\n{'='*60}")
    print(f"Testing Review for PR #{pr_number}")
    print(f"{'='*60}\n")
    
    # Get credentials
    github_token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER")
    repo = os.getenv("GITHUB_REPO")
    
    if not all([github_token, owner, repo]):
        print("❌ Missing GitHub credentials. Check .env file.")
        print(f"   GITHUB_TOKEN: {'✓' if github_token else '❌'}")
        print(f"   GITHUB_OWNER: {'✓' if owner else '❌'}")
        print(f"   GITHUB_REPO: {'✓' if repo else '❌'}")
        return
    
    print(f"✅ GitHub config loaded:")
    print(f"   Owner: {owner}")
    print(f"   Repo: {repo}")
    print(f"   Token: {'***' + github_token[-4:]}\n")
    
    # Initialize GitHub client
    github_config = GitHubConfig(token=github_token, owner=owner, repo=repo)
    github_client = GitHubClient(github_config)
    
    try:
        # Step 1: Fetch PR info
        print(f"📌 Step 1: Fetching PR #{pr_number} info...")
        pr_info = await github_client.get_pr_info(pr_number)
        print(f"✅ PR Title: {pr_info['title']}")
        print(f"   Author: {pr_info['user']['login']}")
        print(f"   Files changed: {pr_info.get('changed_files', 'unknown')}\n")
        
        # Step 2: Fetch diff
        print(f"📌 Step 2: Fetching PR diff...")
        pr_diff = await github_client.get_pr_diff(pr_number)
        diff_size = len(pr_diff)
        print(f"✅ Diff fetched: {diff_size} bytes\n")
        
        # Step 3: Fetch file list
        print(f"📌 Step 3: Fetching file list...")
        pr_files = await github_client.get_pr_files(pr_number)
        print(f"✅ Files in PR: {len(pr_files)}\n")
        
        # Step 4: Create review state
        print(f"📌 Step 4: Creating review state...")
        pr_metadata = PRMetadata(
            pr_number=pr_number,
            title=pr_info["title"],
            author=pr_info["user"]["login"],
            branch=pr_info["head"]["ref"],
            base_branch=pr_info["base"]["ref"],
            diff_content=pr_diff,
            files_changed=[f["filename"] for f in pr_files],
            additions=pr_info.get("additions", 0),
            deletions=pr_info.get("deletions", 0),
        )
        initial_state = ReviewState(pr_metadata=pr_metadata)
        print(f"✅ ReviewState created\n")
        
        # Step 5: Run review
        print(f"📌 Step 5: Running review coordinator...")
        cache_backend = get_cache_backend()
        coordinator = ReviewCoordinator(cache_backend=cache_backend)
        
        review_state = await coordinator.review_pr(initial_state)
        
        stats = review_state.summary_stats()
        print(f"✅ Review complete!")
        print(f"   Total findings: {stats['total_findings']}")
        print(f"   Critical: {stats['critical_count']}")
        print(f"   Warnings: {stats['warning_count']}")
        print(f"   Info: {stats['info_count']}")
        print(f"   Is blocked: {review_state.is_blocked}\n")
        
        # Step 6: Check final summary
        print(f"📌 Step 6: Checking final summary...")
        if review_state.final_summary:
            print(f"✅ Final summary generated ({len(review_state.final_summary)} chars)")
            print(f"\n{'='*60}")
            print("COMMENT PREVIEW:")
            print(f"{'='*60}")
            print(review_state.final_summary)
            print(f"{'='*60}\n")
        else:
            print(f"❌ Final summary is EMPTY!\n")
            print(f"   This is why no comment is being posted.\n")
            print(f"   Check:")
            print(f"   1. Are agents running? (USE_LLM_LOGIC, USE_LLM_SECURITY env vars)")
            print(f"   2. Is ANTHROPIC_API_KEY set?")
            print(f"   3. Are there any findings? ({stats['total_findings']} found)\n")
        
        # Step 7: Check existing comments
        print(f"📌 Step 7: Checking for existing bot comments...")
        existing_comment_id = await github_client.find_review_comment(pr_number)
        if existing_comment_id:
            print(f"✅ Found existing comment (ID: {existing_comment_id})")
            print(f"   This would be UPDATED (not recreated)\n")
        else:
            print(f"ℹ️  No existing bot comment found (new comment would be created)\n")
        
        # Step 8: Simulate comment posting
        if review_state.final_summary:
            print(f"📌 Step 8: Testing comment posting (DRY RUN)...")
            try:
                if existing_comment_id:
                    print(f"   Would UPDATE comment {existing_comment_id}")
                    # Uncomment to actually post:
                    # result = await github_client.update_review_comment(existing_comment_id, review_state.final_summary)
                    # print(f"✅ Comment updated")
                else:
                    print(f"   Would POST new comment")
                    # Uncomment to actually post:
                    # result = await github_client.post_review_comment(pr_number, review_state.final_summary)
                    # print(f"✅ Comment posted (ID: {result.get('id')})")
                print(f"\n   To actually post, uncomment the lines in this script\n")
            except Exception as e:
                print(f"❌ Error posting comment: {e}\n")
        
        print(f"{'='*60}")
        print(f"✅ Test complete!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_review_with_logging.py <pr_number>")
        print("Example: python test_review_with_logging.py 18")
        sys.exit(1)
    
    try:
        pr_number = int(sys.argv[1])
    except ValueError:
        print(f"Error: PR number must be an integer, got '{sys.argv[1]}'")
        sys.exit(1)
    
    asyncio.run(test_review(pr_number))
