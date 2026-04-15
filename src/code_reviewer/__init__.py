"""
Code Reviewer - Production-grade multi-agent PR review system.

Architecture:
- Blackboard Pattern: Central ReviewState for shared state
- Async Orchestration: Parallel agent execution with asyncio
- Multi-phase Review: Analyze → Evaluate → Synthesize
- LLM Integration: Claude, GPT-4, or mock providers
- GitHub Webhook Support: Real-time PR review triggering
"""

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
from .prompts import get_prompt_for_agent, get_all_prompts, AgentPersona
from .llm import (
    get_llm_client,
    LLMClient,
    LLMResponse,
    LLMProvider,
    ClaudeClient,
    GPT4Client,
    MockLLMClient,
)

__all__ = [
    # Core state
    "ReviewState",
    "AgentFinding",
    "AgentMetadata",
    "PRMetadata",
    "Severity",
    # Orchestration
    "ReviewCoordinator",
    # Prompts
    "get_prompt_for_agent",
    "get_all_prompts",
    "AgentPersona",
    # LLM
    "get_llm_client",
    "LLMClient",
    "LLMResponse",
    "LLMProvider",
    "ClaudeClient",
    "GPT4Client",
    "MockLLMClient",
]

