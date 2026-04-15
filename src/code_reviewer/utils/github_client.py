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
import re


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
    
    def _should_include_file(self, filename: str) -> bool:
        """
        Determine if a file should be included in analysis.
        
        Filters out non-code files to reduce token usage and noise:
        - Lockfiles (package-lock.json, poetry.lock, Gemfile.lock, yarn.lock)
        - Minified/generated files (*.min.js, *.min.css, dist/*, build/*)
        - Binary/media files (handled separately, but filter here for safety)
        
        Args:
            filename: File path to check
            
        Returns:
            True if file should be analyzed, False to skip
        """
        # Lockfiles that shouldn't be analyzed
        lockfiles = {
            'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'poetry.lock', 'pipfile.lock', 'gemfile.lock',
            'composer.lock', 'mix.lock'
        }
        
        # Patterns to skip
        skip_patterns = [
            '.min.js', '.min.css',  # Minified
            'dist/', 'build/', '.next/', '.venv/', 'node_modules/',  # Generated/deps
            '.git', '.github/', '.vscode/',  # Config/meta
        ]
        
        # Check lockfiles
        basename = filename.split('/')[-1].lower()
        if basename in lockfiles:
            return False
        
        # Check patterns
        for pattern in skip_patterns:
            if pattern in filename.lower():
                return False
        
        return True
    
    async def get_pr_diff(self, pr_number: int, token_budget: int = 100000) -> str:
        """
        Fetch the full diff for a PR with intelligent token budgeting.
        
        The files endpoint includes a 'patch' field with unified diff for each file.
        Filters out non-code files (lockfiles, minified, auto-generated) to reduce
        token usage and noise sent to LLMs.
        
        Token Budgeting:
        - Prioritizes .py, .js, .ts files (highest value for analysis)
        - Includes medium-priority files (.java, .go, .rs, .cs)
        - Skips low-priority files (.md, .json, .yaml) if budget exceeded
        - Redacts secrets before returning
        
        Args:
            pr_number: GitHub PR number
            token_budget: Maximum tokens to include (default 100k ≈ 400k chars)
            
        Returns:
            Unified diff content as string (redacted, filtered, budget-aware)
        """
        from code_reviewer.utils.logger import get_logger
        logger = get_logger()
        
        try:
            # Get all files changed in the PR
            files = await self.get_pr_files(pr_number)
            
            # Prioritize files by importance for analysis
            sorted_files = self._prioritize_files(files)
            
            # Build unified diff with token budgeting
            diff_parts = []
            skipped_files = []
            included_files = []
            token_count = 0
            budget_exceeded = False
            
            for file in sorted_files:
                filename = file.get("filename", "unknown")
                patch = file.get("patch", "")
                
                # Filter out non-code files
                if not self._should_include_file(filename):
                    skipped_files.append({"name": filename, "reason": "filtered"})
                    continue
                
                # Estimate tokens for this file
                file_tokens = self._estimate_tokens(patch)
                
                # Token budgeting: skip low-priority files if budget exceeded
                if budget_exceeded:
                    priority = self._get_file_priority_category(filename)
                    if priority != 'high':
                        skipped_files.append({"name": filename, "reason": "token_budget"})
                        continue
                
                # Add file to diff
                if patch:
                    diff_parts.append(patch)
                    diff_parts.append("")  # Blank line between files
                    included_files.append(filename)
                    token_count += file_tokens
                    
                    # Check if we've exceeded budget
                    if token_count > token_budget:
                        budget_exceeded = True
                        logger.warning(
                            f"Token budget exceeded for PR #{pr_number}",
                            token_count=token_count,
                            budget=token_budget,
                            files_included=len(included_files),
                            files_skipped_due_to_budget=len([s for s in skipped_files if s.get('reason') == 'token_budget'])
                        )
            
            diff_content = "\n".join(diff_parts)
            
            # Apply secret redaction (critical for security)
            diff_content = self._redact_secrets(diff_content)
            
            logger.info(
                f"Built PR #{pr_number} diff with token budgeting",
                total_files=len(files),
                included_files=len(included_files),
                skipped_files=len(skipped_files),
                token_count=token_count,
                token_budget=token_budget,
                diff_size=len(diff_content),
                budget_exceeded=budget_exceeded
            )
            
            if skipped_files:
                filtered_count = len([s for s in skipped_files if s.get('reason') == 'filtered'])
                budget_count = len([s for s in skipped_files if s.get('reason') == 'token_budget'])
                if filtered_count > 0:
                    logger.debug(f"Skipped {filtered_count} non-code files for PR #{pr_number}")
                if budget_count > 0:
                    logger.debug(f"Skipped {budget_count} low-priority files due to token budget for PR #{pr_number}")
            
            if not diff_content or diff_content.strip() == "":
                logger.warning(f"PR #{pr_number} has no code changes to analyze")
            
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
        Find the code reviewer bot's comment on a PR (for idempotent updates).
        
        Returns the comment ID if found, None otherwise.
        This allows updating existing reviews instead of creating duplicates,
        keeping the PR conversation clean when developers push follow-up commits.
        
        Looks for markers:
        - "Automated Code Review" (primary marker)
        - "code-reviewer/analysis" (fallback for robustness)
        - Comment from bot user (if available)
        
        Args:
            pr_number: GitHub PR number
            
        Returns:
            Comment ID if found, None otherwise
        """
        try:
            comments = await self.list_pr_comments(pr_number)
            
            # Markers that identify our bot's comments
            bot_markers = [
                "Automated Code Review",
                "code-reviewer/analysis",
                "## Code Review Analysis",
                "## Review Results"
            ]
            
            for comment in comments:
                body = comment.get("body", "")
                user = comment.get("user", {}).get("login", "")
                
                # Check if any bot marker is in the comment
                for marker in bot_markers:
                    if marker in body:
                        from code_reviewer.utils.logger import get_logger
                        get_logger().debug(
                            f"Found existing bot comment for PR #{pr_number}",
                            comment_id=comment["id"],
                            marker=marker
                        )
                        return comment["id"]
            
            return None
        except Exception as e:
            from code_reviewer.utils.logger import get_logger
            get_logger().error(f"Error finding review comment: {str(e)}")
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
