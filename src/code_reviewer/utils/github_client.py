"""
GitHub Client: Interface for reading PR data and posting reviews.

This module handles:
- Fetching PR metadata and diff
- Posting review comments
- Updating issue status
- Managing integration with GitHub API
"""

import os
from typing import Optional
import httpx
from dataclasses import dataclass


@dataclass
class GitHubConfig:
    """Configuration for GitHub API access."""
    token: str
    owner: str
    repo: str
    base_url: str = "https://api.github.com"


class GitHubClient:
    """Client for interacting with GitHub API."""
    
    def __init__(self, config: GitHubConfig):
        """
        Initialize GitHub client.
        
        Args:
            config: GitHubConfig with token, owner, repo
        """
        self.config = config
        self.headers = {
            "Authorization": f"token {config.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    
    @classmethod
    def from_env(cls) -> "GitHubClient":
        """Create client from environment variables."""
        token = os.getenv("GITHUB_TOKEN")
        owner = os.getenv("GITHUB_OWNER")
        repo = os.getenv("GITHUB_REPO")
        
        if not all([token, owner, repo]):
            raise ValueError(
                "Missing required environment variables: "
                "GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO"
            )
        
        config = GitHubConfig(token=token, owner=owner, repo=repo)
        return cls(config)
    
    async def get_pr_info(self, pr_number: int) -> dict:
        """
        Fetch PR metadata from GitHub.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            PR metadata dictionary
        """
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/pulls/{pr_number}"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_pr_files(self, pr_number: int) -> list:
        """
        Fetch the list of files changed in a PR.
        
        The /pulls/{pr} endpoint doesn't include files list by default.
        This endpoint returns all files modified/added/deleted in the PR.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            List of file objects with filename, status, additions, deletions
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/pulls/{pr_number}/files"
        )
        
        logger.debug(f"Fetching PR files list from: {url}")
        
        all_files = []
        page = 1
        per_page = 100  # Max per page
        
        try:
            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params={"page": page, "per_page": per_page}
                    )
                    response.raise_for_status()
                    
                    files = response.json()
                    if not files:
                        break
                    
                    all_files.extend(files)
                    page += 1
                    
                    # Stop if we got less than per_page items (last page)
                    if len(files) < per_page:
                        break
            
            logger.info(f"Successfully fetched PR #{pr_number} files: {len(all_files)} files changed")
            return all_files
        except Exception as e:
            logger.error(f"Failed to fetch PR files list: {str(e)}", pr_number=pr_number)
            raise
    
    async def get_pr_diff(self, pr_number: int) -> str:
        """
        Fetch the full diff for a PR by reconstructing from files endpoint.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            Unified diff content as string
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        try:
            # Get all files changed in the PR
            files = await self.get_pr_files(pr_number)
            
            # Build unified diff from file changes
            diff_parts = []
            
            for file in files:
                filename = file.get("filename", "unknown")
                status = file.get("status", "modified")
                additions = file.get("additions", 0)
                deletions = file.get("deletions", 0)
                
                # Add file header
                if status == "added":
                    diff_parts.append(f"diff --git a/{filename} b/{filename}")
                    diff_parts.append(f"new file mode 100644")
                    diff_parts.append(f"index 0000000..1234567")
                    diff_parts.append(f"--- /dev/null")
                    diff_parts.append(f"+++ b/{filename}")
                elif status == "deleted":
                    diff_parts.append(f"diff --git a/{filename} b/{filename}")
                    diff_parts.append(f"deleted file mode 100644")
                    diff_parts.append(f"index 1234567..0000000")
                    diff_parts.append(f"--- a/{filename}")
                    diff_parts.append(f"+++ /dev/null")
                else:
                    diff_parts.append(f"diff --git a/{filename} b/{filename}")
                    diff_parts.append(f"index 1234567..abcdefg 100644")
                    diff_parts.append(f"--- a/{filename}")
                    diff_parts.append(f"+++ b/{filename}")
                
                # Get the patch content if available
                patch = file.get("patch", "")
                if patch:
                    diff_parts.append(patch)
                else:
                    # Just include summary line
                    diff_parts.append(f"@@ File: {filename} @@")
                    diff_parts.append(f" Additions: {additions}, Deletions: {deletions}")
                
                diff_parts.append("")  # Blank line between files
            
            diff_content = "\n".join(diff_parts)
            logger.info(f"Successfully built PR #{pr_number} diff from files: {len(diff_content)} characters")
            return diff_content
            
        except Exception as e:
            logger.error(f"Failed to fetch PR diff: {str(e)}", pr_number=pr_number)
            raise
    
    async def post_review_comment(
        self, pr_number: int, comment_body: str, commit_id: Optional[str] = None
    ) -> dict:
        """
        Post a comment on a PR.
        
        Args:
            pr_number: GitHub PR number
            comment_body: Markdown comment body
            commit_id: Optional specific commit to comment on
            
        Returns:
            Posted comment data
        """
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/issues/{pr_number}/comments"
        )
        
        payload = {"body": comment_body}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def update_review_comment(
        self, comment_id: int, comment_body: str
    ) -> dict:
        """
        Update an existing comment.
        
        Args:
            comment_id: GitHub comment ID
            comment_body: Updated Markdown comment body
            
        Returns:
            Updated comment data
        """
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/issues/comments/{comment_id}"
        )
        
        payload = {"body": comment_body}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def get_pr_reviews(self, pr_number: int) -> list:
        """
        Get all reviews submitted on a PR.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            List of review objects
        """
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/pulls/{pr_number}/reviews"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def list_pr_comments(self, pr_number: int) -> list:
        """
        Get all comments on a PR.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            List of comment objects
        """
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/issues/{pr_number}/comments"
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
    
    async def find_review_comment(self, pr_number: int) -> Optional[int]:
        """
        Find the code reviewer bot's comment on a PR.
        
        Returns the comment ID if found, None otherwise.
        This allows updating existing reviews instead of creating duplicates.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            Comment ID if found, None otherwise
        """
        comments = await self.list_pr_comments(pr_number)
        
        # Look for a comment by the bot (you'd customize this marker)
        for comment in comments:
            if "Automated Code Review" in comment.get("body", ""):
                return comment["id"]
        
        return None
    
    async def create_status_check(
        self,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "code-reviewer/analysis",
        target_url: Optional[str] = None,
    ) -> dict:
        """
        Create a GitHub Status Check on a commit.
        
        This is used to enforce merge blocking when critical issues are found.
        
        Args:
            commit_sha: Git commit SHA to create status on
            state: One of "pending", "success", "failure", "error"
            description: Short description of the status (max 140 chars)
            context: Identifier for the status check (default: code-reviewer/analysis)
            target_url: Optional URL to link to (e.g., detailed report)
            
        Returns:
            Status check response data
            
        Raises:
            ValueError: If state is invalid or description too long
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        valid_states = ["pending", "success", "failure", "error"]
        if state not in valid_states:
            raise ValueError(f"Invalid state '{state}'. Must be one of {valid_states}")
        
        if len(description) > 140:
            raise ValueError(f"Description too long ({len(description)} chars). Max 140 chars.")
        
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/statuses/{commit_sha}"
        )
        
        payload = {
            "state": state,
            "description": description,
            "context": context,
        }
        
        if target_url:
            payload["target_url"] = target_url
        
        logger.debug(f"Creating status check on {commit_sha[:7]}: {state} - {description}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"Status check created: {state} on {commit_sha[:7]}")
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create status check: {str(e)}")
            raise
