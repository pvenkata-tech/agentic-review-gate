"""
Core interfaces and protocols for dependency inversion.

This module defines abstract interfaces that decouple high-level modules (agents)
from low-level modules (utils). All dependencies flow inward toward these interfaces.

Interfaces:
- DiffProvider: Abstracts diff extraction and parsing
- LLMClient: Abstracts LLM interactions
- GitHubClient: Abstracts GitHub API interactions
- CacheBackend: Abstracts caching operations
- Logger: Abstracts logging
"""

from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DiffInfo:
    """Structured diff information."""
    file_path: str
    status: str  # "ADDED", "DELETED", "MODIFIED", "RENAMED"
    hunks: List[Dict[str, Any]]  # Code hunks with line numbers
    additions: int
    deletions: int


class DiffProvider(Protocol):
    """Abstract interface for diff extraction and parsing."""
    
    def parse_diff(self, diff_content: str) -> List[DiffInfo]:
        """Parse unified diff format into structured data."""
        ...
    
    def get_changed_lines(self, diff_info: DiffInfo) -> List[str]:
        """Extract actual changed lines from diff."""
        ...


class LLMClient(Protocol):
    """Abstract interface for LLM interactions."""
    
    async def analyze(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """Send prompt to LLM and get response."""
        ...
    
    def is_available(self) -> bool:
        """Check if LLM client is ready to use."""
        ...


class GitHubAPIClient(Protocol):
    """Abstract interface for GitHub API interactions."""
    
    async def get_pr_info(self, pr_number: int) -> Dict[str, Any]:
        """Fetch PR metadata."""
        ...
    
    async def get_pr_diff(self, pr_number: int) -> str:
        """Fetch unified diff for PR."""
        ...
    
    async def post_comment(self, pr_number: int, body: str) -> Dict[str, Any]:
        """Post comment on PR."""
        ...


class CacheBackend(Protocol):
    """Abstract interface for caching operations."""
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        ...
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set value in cache with optional expiration."""
        ...
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        ...


class Logger(Protocol):
    """Abstract interface for logging."""
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        ...
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        ...
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        ...
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        ...
