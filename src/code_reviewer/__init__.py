"""Code Reviewer - Production-grade multi-agent PR review system."""

__version__ = "0.1.0"
__author__ = "Code Reviewer Team"

from .core.state import (
    ReviewState,
    AgentFinding,
    AgentMetadata,
    PRMetadata,
    Severity,
)
from .core.coordinator import ReviewCoordinator

__all__ = [
    "ReviewState",
    "AgentFinding",
    "AgentMetadata",
    "PRMetadata",
    "Severity",
    "ReviewCoordinator",
]
