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
    
    async def get_pr_diff(self, pr_number: int) -> str:
        """
        Fetch the full diff for a PR.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            Unified diff content as string
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/pulls/{pr_number}"
        )
        
        logger.debug(f"Fetching PR diff from: {url}")
        logger.debug(f"Using Accept header: application/vnd.github.v3.diff")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={**self.headers, "Accept": "application/vnd.github.v3.diff"},
            )
            response.raise_for_status()
            
            diff_content = response.text
            logger.debug(f"Received diff: {len(diff_content)} characters")
            if diff_content:
                logger.debug(f"First 300 chars:\n{diff_content[:300]}")
            else:
                logger.warning("PR diff is empty!")
            
            return diff_content
    
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
