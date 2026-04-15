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
        Fetch the full diff for a PR.
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            Unified diff content as string
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        # Use the .diff endpoint which directly returns unified diff format
        url = (
            f"{self.config.base_url}/repos/{self.config.owner}/"
            f"{self.config.repo}/pulls/{pr_number}.diff"
        )
        
        logger.debug(f"Fetching PR diff from: {url}")
        
        # Standard headers for GitHub API
        diff_headers = {
            "Authorization": f"token {self.config.token}",
            "User-Agent": "agentic-code-reviewer",
            "Accept": "application/vnd.github.v3.raw",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=diff_headers)
                response.raise_for_status()
                
                diff_content = response.text
                logger.info(f"Successfully fetched PR #{pr_number} diff: {len(diff_content)} characters")
                
                if not diff_content or len(diff_content.strip()) == 0:
                    logger.warning(f"PR #{pr_number} diff is empty! Status: {response.status_code}")
                    logger.debug(f"Response headers: {dict(response.headers)}")
                else:
                    # Log first part of diff to understand format
                    first_lines = "\n".join(diff_content.split("\n")[:10])
                    logger.debug(f"First 10 lines of diff:\n{first_lines}")
                
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
