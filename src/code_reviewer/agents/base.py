"""
Abstract base class for all agents in the review system.

Each agent implements a stateless analyze method that receives a ReviewState
snapshot and returns findings to be merged back into the blackboard.
"""

from abc import ABC, abstractmethod
from typing import List
import time
from datetime import datetime

from code_reviewer.core.state import ReviewState, AgentFinding, AgentMetadata, Severity


class BaseAgent(ABC):
    """
    Abstract base class for all PR review agents.
    
    The Blackboard pattern ensures loose coupling: agents don't communicate directly
    but instead deposit findings on the shared ReviewState. This prevents "message
    pass-through" fatigue and allows the final Summarizer to deduplicate and
    synthesize without loss of context.
    """
    
    def __init__(self, agent_id: str):
        """
        Initialize the agent.
        
        Args:
            agent_id: Unique identifier for this agent (e.g., "logic", "security", "summarizer")
        """
        self.agent_id = agent_id
    
    @abstractmethod
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """
        Perform specialized analysis on the PR.
        
        This is the core method implemented by each specialized agent. It receives
        a snapshot of the current ReviewState and returns a list of findings.
        The agent does NOT modify the state directly; instead, the coordinator
        merges findings back.
        
        Args:
            state: Current ReviewState (blackboard snapshot)
            
        Returns:
            List of AgentFinding objects discovered during analysis
        """
        pass
    
    async def execute(self, state: ReviewState) -> tuple[List[AgentFinding], AgentMetadata]:
        """
        Execute the agent with timing and error handling.
        
        This wrapper method:
        1. Calls the agent's analyze() method
        2. Records execution metadata (time, token usage)
        3. Handles exceptions gracefully
        
        Args:
            state: Current ReviewState
            
        Returns:
            Tuple of (findings list, execution metadata)
        """
        start_time = time.perf_counter()
        findings: List[AgentFinding] = []
        error_message: str | None = None
        status = "success"
        
        try:
            findings = await self.analyze(state)
        except Exception as e:
            status = "error"
            error_message = str(e)
            # Log the error but don't crash the entire review
            print(f"Agent {self.agent_id} failed: {error_message}")
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        metadata = AgentMetadata(
            agent_id=self.agent_id,
            execution_time_ms=elapsed_ms,
            token_usage=self._get_token_usage(),
            status=status,
            error_message=error_message,
            timestamp=datetime.utcnow(),
        )
        
        return findings, metadata
    
    def _get_token_usage(self) -> dict[str, int]:
        """
        Return token usage for this execution.
        
        Override in LLM-based agents to return actual token counts.
        Default returns empty dict.
        
        Returns:
            Dictionary with 'input_tokens' and 'output_tokens' keys
        """
        return {}
    
    def _create_finding(
        self,
        file_path: str,
        finding_type: str,
        description: str,
        suggestion: str,
        severity: Severity,
        line_number: int | None = None,
    ) -> AgentFinding:
        """
        Helper to create a finding with this agent's ID pre-filled.
        
        Args:
            file_path: Relative path to the file
            finding_type: Category of finding
            description: Human-readable description
            suggestion: Actionable suggestion
            severity: Severity level
            line_number: Optional line number (1-indexed)
            
        Returns:
            AgentFinding instance ready to be added to blackboard
        """
        return AgentFinding(
            file_path=file_path,
            line_number=line_number,
            finding_type=finding_type,
            description=description,
            suggestion=suggestion,
            severity=severity,
            agent_id=self.agent_id,
        )
