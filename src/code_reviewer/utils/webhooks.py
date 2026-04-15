"""
GitHub Webhook Handler: Manages incoming PR webhook events with signature validation.

This module provides:
- Webhook payload parsing and validation
- X-Hub-Signature-256 verification (HMAC-SHA256)
- PR event filtering and processing
- Payload extraction and normalization
"""

import hmac
import hashlib
import json
from typing import Dict, Optional, Tuple
from enum import Enum


class GitHubEventType(str, Enum):
    """GitHub webhook event types."""
    PULL_REQUEST = "pull_request"
    PUSH = "push"
    PULL_REQUEST_REVIEW = "pull_request_review"


class PRAction(str, Enum):
    """Pull request webhook action types."""
    OPENED = "opened"
    SYNCHRONIZE = "synchronize"  # New commits pushed
    REOPENED = "reopened"
    CLOSED = "closed"
    LABELED = "labeled"
    UNLABELED = "unlabeled"


class WebhookValidationError(Exception):
    """Raised when webhook validation fails."""
    pass


class WebhookPayloadError(Exception):
    """Raised when webhook payload is malformed."""
    pass


class GitHubWebhookValidator:
    """Validates incoming GitHub webhooks."""
    
    @staticmethod
    def verify_signature(
        payload: bytes,
        signature_header: str,
        secret: str
    ) -> bool:
        """
        Verify GitHub webhook X-Hub-Signature-256 header.
        
        GitHub sends: X-Hub-Signature-256: sha256=<hash>
        We calculate HMAC-SHA256 of payload and compare.
        
        Args:
            payload: Raw request body bytes
            signature_header: X-Hub-Signature-256 header value
            secret: GitHub webhook secret
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            WebhookValidationError: If signature format is invalid
        """
        if not signature_header:
            raise WebhookValidationError("X-Hub-Signature-256 header missing")
        
        if not signature_header.startswith("sha256="):
            raise WebhookValidationError(
                f"Invalid signature format: expected 'sha256=...', got '{signature_header[:20]}...'"
            )
        
        try:
            # Extract the hash from header
            expected_signature = signature_header.split("=", 1)[1]
            
            # Calculate HMAC-SHA256
            calculated_hash = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(calculated_hash, expected_signature)
        
        except Exception as e:
            raise WebhookValidationError(f"Signature verification failed: {str(e)}") from e
    
    @staticmethod
    def is_review_trigger_event(payload: Dict) -> bool:
        """
        Check if this webhook event should trigger a review.
        
        Only PR open/synchronize/reopen events trigger reviews.
        
        Args:
            payload: Parsed webhook payload
            
        Returns:
            True if this should trigger a review
        """
        if payload.get("action") not in [
            PRAction.OPENED.value,
            PRAction.SYNCHRONIZE.value,
            PRAction.REOPENED.value,
        ]:
            return False
        
        # Must be a pull_request event
        return payload.get("pull_request") is not None


class GitHubWebhookPayload:
    """Normalized GitHub webhook payload."""
    
    def __init__(self, payload: Dict):
        """Initialize with raw payload."""
        self.raw = payload
        self._validate()
    
    def _validate(self) -> None:
        """Validate payload has required fields."""
        if not self.raw.get("pull_request"):
            raise WebhookPayloadError("Missing pull_request object")
        
        if not self.raw.get("repository"):
            raise WebhookPayloadError("Missing repository object")
    
    @property
    def pr_number(self) -> int:
        """PR number."""
        return self.raw["pull_request"]["number"]
    
    @property
    def action(self) -> str:
        """PR action (opened, synchronize, reopened, etc)."""
        return self.raw.get("action", "unknown")
    
    @property
    def owner(self) -> str:
        """Repository owner (organization or user)."""
        return self.raw["repository"]["owner"]["login"]
    
    @property
    def repo(self) -> str:
        """Repository name."""
        return self.raw["repository"]["name"]
    
    @property
    def full_repo(self) -> str:
        """Full repository name (owner/repo)."""
        return f"{self.owner}/{self.repo}"
    
    @property
    def title(self) -> str:
        """PR title."""
        return self.raw["pull_request"].get("title", "")
    
    @property
    def author(self) -> str:
        """PR author GitHub username."""
        return self.raw["pull_request"]["user"]["login"]
    
    @property
    def head_ref(self) -> str:
        """Source branch (feature branch)."""
        return self.raw["pull_request"]["head"]["ref"]
    
    @property
    def head_sha(self) -> str:
        """Current commit SHA of source branch."""
        return self.raw["pull_request"]["head"]["sha"]
    
    @property
    def base_ref(self) -> str:
        """Target branch (main, develop, etc)."""
        return self.raw["pull_request"]["base"]["ref"]
    
    @property
    def additions(self) -> int:
        """Total lines added."""
        return self.raw["pull_request"].get("additions", 0)
    
    @property
    def deletions(self) -> int:
        """Total lines deleted."""
        return self.raw["pull_request"].get("deletions", 0)
    
    @property
    def changed_files(self) -> int:
        """Number of files changed."""
        return self.raw["pull_request"].get("changed_files", 0)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary suitable for ReviewRequest."""
        return {
            "pr_number": self.pr_number,
            "owner": self.owner,
            "repo": self.repo,
            "title": self.title,
            "author": self.author,
            "branch": self.head_ref,
            "base_branch": self.base_ref,
            "action": self.action,
            "head_sha": self.head_sha,
        }


class WebhookHandler:
    """Orchestrates webhook validation and processing."""
    
    def __init__(self, secret: str = ""):
        """
        Initialize handler.
        
        Args:
            secret: GitHub webhook secret (optional for development)
        """
        self.secret = secret
        self.validator = GitHubWebhookValidator()
    
    def process_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        event_type: str
    ) -> Tuple[bool, Optional[GitHubWebhookPayload], Optional[str]]:
        """
        Process incoming webhook with full validation.
        
        Args:
            raw_body: Raw request body
            signature_header: X-Hub-Signature-256 header value
            event_type: X-GitHub-Event header value
            
        Returns:
            Tuple of (should_process, payload, error_message)
            - should_process: True if this webhook should trigger a review
            - payload: Parsed payload if valid, None otherwise
            - error_message: Error description if validation failed
        """
        # Step 1: Validate signature
        if self.secret:
            try:
                if not self.validator.verify_signature(raw_body, signature_header, self.secret):
                    return False, None, "Webhook signature validation failed (invalid signature)"
            except Exception as e:
                return False, None, f"Webhook signature validation failed: {str(e)}"
        else:
            # No secret configured - warn but allow (dev mode)
            return False, None, "Warning: webhook secret not configured, signature validation skipped"
        
        # Step 2: Check event type
        if event_type != GitHubEventType.PULL_REQUEST:
            return False, None, f"Event type '{event_type}' not supported (need pull_request)"
        
        # Step 3: Parse payload
        try:
            payload_dict = json.loads(raw_body.decode())
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON payload: {str(e)}"
        
        # Step 4: Validate payload structure
        try:
            payload = GitHubWebhookPayload(payload_dict)
        except WebhookPayloadError as e:
            return False, None, f"Invalid webhook payload: {str(e)}"
        
        # Step 5: Check if this is a triggering event
        if not self.validator.is_review_trigger_event(payload_dict):
            action = payload_dict.get("action", "unknown")
            return False, payload, f"PR action '{action}' does not trigger review"
        
        # All checks passed
        return True, payload, None
    
    def get_error_response(self, error_message: str, status_code: int = 400) -> Dict:
        """Get standardized error response."""
        return {
            "status": "error",
            "message": error_message,
            "code": status_code,
        }
    
    def get_ignored_response(self, error_message: str) -> Dict:
        """Get standardized 'ignored' response."""
        return {
            "status": "ignored",
            "reason": error_message,
        }
    
    def get_accepted_response(self, payload: GitHubWebhookPayload) -> Dict:
        """Get standardized 'accepted' response."""
        return {
            "status": "accepted",
            "pr_number": payload.pr_number,
            "repo": payload.full_repo,
            "action": payload.action,
            "files_changed": payload.changed_files,
        }
