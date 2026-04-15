"""
Review Coordinator: Orchestrates the multi-agent workflow using the Blackboard pattern.

The coordinator manages:
1. Phase A: Parallel analysis by specialized agents
2. Phase B: Merging findings back to the shared state
3. Phase C: Synthesis by the Summarizer agent
4. Final: Generate GitHub comment and handle blocking
"""

import asyncio
import time
from typing import List
from datetime import datetime

from code_reviewer.core.state import ReviewState, Severity
from code_reviewer.agents.base import BaseAgent
from code_reviewer.agents.logic import LogicAgent
from code_reviewer.agents.security import SecurityGuardAgent
from code_reviewer.agents.summary import SummarizerAgent


class ReviewCoordinator:
    """
    Orchestrates the multi-agent PR review workflow.
    
    This coordinator implements the Analyze-Synthesize-Report flow:
    
    Phase A (Parallel): Logic and Security agents analyze independently
    Phase B (Merge): Findings are merged into the shared ReviewState
    Phase C (Synthesis): Summarizer synthesizes findings into a GitHub comment
    """
    
    def __init__(self):
        """Initialize the coordinator with all agents."""
        self.logic_agent = LogicAgent()
        self.security_agent = SecurityGuardAgent()
        self.summarizer_agent = SummarizerAgent()
    
    async def review_pr(self, state: ReviewState) -> ReviewState:
        """
        Execute a complete PR review workflow.
        
        Args:
            state: Initial ReviewState with PR metadata
            
        Returns:
            Completed ReviewState with findings and final summary
        """
        start_time = time.perf_counter()
        
        # Phase A: Parallel analysis
        print(f"[Coordinator] Starting Phase A: Parallel Analysis")
        await self._phase_a_analyze(state)
        
        # Phase B: Check for critical issues
        print(f"[Coordinator] Starting Phase B: Critical Issue Evaluation")
        await self._phase_b_evaluate(state)
        
        # Phase C: Synthesis
        print(f"[Coordinator] Starting Phase C: Synthesis and Summary")
        await self._phase_c_synthesize(state)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        print(f"[Coordinator] Review completed in {elapsed:.2f}ms")
        
        return state
    
    async def _phase_a_analyze(self, state: ReviewState) -> None:
        """
        Phase A: Run Logic and Security agents in parallel.
        
        Both agents receive the same state snapshot and deposit findings
        on the blackboard without knowing about each other.
        
        Args:
            state: ReviewState to be analyzed
        """
        # Create a list of agents to run in parallel
        agents = [self.logic_agent, self.security_agent]
        
        # Execute all agents concurrently
        results = await asyncio.gather(
            *[agent.execute(state) for agent in agents]
        )
        
        # Merge results back into state
        for findings, metadata in results:
            # Add all findings
            for finding in findings:
                state.add_finding(finding)
                print(
                    f"  [{metadata.agent_id}] Found: {finding.finding_type} "
                    f"in {finding.file_path}"
                )
            
            # Record execution metadata
            state.add_metadata(metadata)
    
    async def _phase_b_evaluate(self, state: ReviewState) -> None:
        """
        Phase B: Evaluate if critical issues should block the PR.
        
        If any critical findings exist, set is_blocked = True.
        This flag will be used by the Summarizer to set tone.
        
        Args:
            state: ReviewState with findings
        """
        critical_findings = state.get_critical_findings()
        
        if critical_findings:
            print(
                f"[Coordinator] {len(critical_findings)} critical issue(s) detected. "
                f"Setting is_blocked = True"
            )
            state.set_blocked(True)
        else:
            print("[Coordinator] No critical issues. PR can proceed.")
    
    async def _phase_c_synthesize(self, state: ReviewState) -> None:
        """
        Phase C: Generate final summary using the Summarizer agent.
        
        The Summarizer doesn't analyze; it synthesizes findings into a
        professional GitHub-flavored Markdown comment.
        
        Args:
            state: ReviewState with all findings accumulated
        """
        # Generate the final comment
        comment = await self.summarizer_agent.generate_comment(state)
        
        # Store it in the state
        state.set_summary(comment)
        
        print(f"[Coordinator] Summary generated ({len(comment)} characters)")
    
    async def handle_pr_update(
        self, state: ReviewState, new_diff: str
    ) -> ReviewState:
        """
        Handle a PR update (new commit pushed).
        
        This method supports re-review after developer changes:
        1. Update the PR diff in metadata
        2. Clear previous findings
        3. Run full review again
        4. Compare with previous findings to show progress
        
        Args:
            state: Previous ReviewState (with old findings)
            new_diff: Updated diff content
            
        Returns:
            Updated ReviewState with new findings
        """
        # Update PR metadata with new diff
        state.pr_metadata.diff_content = new_diff
        state.pr_metadata.updated_at = datetime.utcnow()
        
        # Create fresh state for analysis (don't clear findings, append)
        # This allows tracking of previously-flagged issues
        new_state = ReviewState(
            pr_metadata=state.pr_metadata,
            findings=[],  # Fresh findings
            metadata=[],
        )
        
        # Re-run review
        await self.review_pr(new_state)
        
        return new_state
    
    def get_review_stats(self, state: ReviewState) -> dict:
        """Get summary statistics about the review."""
        return state.summary_stats()
