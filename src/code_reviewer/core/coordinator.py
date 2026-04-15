"""
Review Coordinator: Orchestrates the multi-agent workflow using the Blackboard pattern.

The coordinator manages:
1. Phase A: Parallel analysis by specialized agents
2. Phase B: Merging findings back to the shared state
3. Phase C: Synthesis by the Summarizer agent
4. Final: Generate GitHub comment and handle blocking

Uses asyncio.gather() for fan-out parallelization and proper exception handling.
"""

import asyncio
import time
from typing import List, Tuple, Optional
from datetime import datetime

from code_reviewer.core.state import ReviewState, Severity, AgentFinding, AgentMetadata
from code_reviewer.agents.base import BaseAgent
from code_reviewer.agents.logic import LogicAgent
from code_reviewer.agents.security import SecurityGuardAgent
from code_reviewer.agents.summary import SummarizerAgent
from code_reviewer.utils.logger import get_logger

logger = get_logger()


class ReviewCoordinator:
    """
    Orchestrates the multi-agent PR review workflow.
    
    This coordinator implements the Analyze-Synthesize-Report flow:
    
    Phase A (Parallel): Logic and Security agents analyze independently
    Phase B (Merge): Findings are merged into the shared ReviewState
    Phase C (Synthesis): Summarizer synthesizes findings into a GitHub comment
    
    The coordinator also supports finding deduplication by tracking finding IDs
    across review cycles, preventing redundant notifications of the same issues.
    """
    
    def __init__(self, cache_backend=None):
        """Initialize the coordinator with all agents.
        
        Args:
            cache_backend: Optional cache backend for storing previous finding_ids
                          (e.g., Redis client for persistent state)
        """
        self.logic_agent = LogicAgent()
        self.security_agent = SecurityGuardAgent()
        self.summarizer_agent = SummarizerAgent()
        self.cache_backend = cache_backend  # For future Redis integration
    
    async def review_pr(self, state: ReviewState, previous_finding_ids=None) -> ReviewState:
        """
        Execute a complete PR review workflow.
        
        Args:
            state: Initial ReviewState with PR metadata
            previous_finding_ids: Optional list of finding_ids from previous reviews
                                 (for deduplication)
            
        Returns:
            Completed ReviewState with findings and final summary
        """
        start_time = time.perf_counter()
        
        # Phase A: Parallel analysis
        print(f"[Coordinator] Starting Phase A: Parallel Analysis")
        await self._phase_a_analyze(state)
        
        # Compute finding IDs for deduplication
        state.compute_finding_ids()
        
        # Mark duplicates if we have previous findings
        if previous_finding_ids:
            state.mark_duplicates(previous_finding_ids)
            duplicates = state.get_duplicate_findings()
            new_findings = state.get_new_findings()
            print(
                f"[Coordinator] Finding deduplication: "
                f"{len(new_findings)} new, {len(duplicates)} duplicates"
            )
        
        # Phase B: Check for critical issues
        print(f"[Coordinator] Starting Phase B: Critical Issue Evaluation")
        await self._phase_b_evaluate(state)
        
        # Phase C: Synthesis
        print(f"[Coordinator] Starting Phase C: Synthesis and Summary")
        await self._phase_c_synthesize(state)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        print(f"[Coordinator] Review completed in {elapsed:.2f}ms")
        
        # Cache the finding IDs for next review (if cache_backend configured)
        if self.cache_backend:
            try:
                finding_ids = state.get_finding_ids()
                cache_key = f"pr:{state.pr_metadata.pr_number}:findings"
                self.cache_backend.set(cache_key, finding_ids, ex=86400*30)  # 30 days
                print(f"[Coordinator] Cached {len(finding_ids)} finding IDs")
            except Exception as e:
                print(f"[Coordinator] Warning: Failed to cache finding IDs: {e}")
        
        return state
    
    async def _phase_a_analyze(self, state: ReviewState) -> None:
        """
        Phase A: Run Logic and Security agents in parallel using asyncio.gather().
        
        This is the core asyncio orchestration pattern:
        - Creates tasks for each agent
        - Executes them concurrently
        - Gathers results and merges into shared state
        - Handles exceptions gracefully
        
        Args:
            state: ReviewState to be analyzed
            
        Raises:
            Exception: Re-raises if all agents fail (unlikely but possible)
        """
        agents = [self.logic_agent, self.security_agent]
        
        logger.info(
            f"[Phase A] Starting parallel analysis",
            agent_count=len(agents),
            pr_number=state.pr_metadata.pr_number
        )
        
        # Create tasks for concurrent execution
        tasks = []
        for agent in agents:
            task = self._execute_agent_safe(agent, state)
            tasks.append(task)
        
        # Execute all agents concurrently and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results with error handling
        successful_agents = 0
        failed_agents = []
        
        for i, result in enumerate(results):
            agent_id = agents[i].agent_id
            
            # Check if this result is an exception
            if isinstance(result, Exception):
                logger.error(
                    f"Agent {agent_id} failed",
                    agent_id=agent_id,
                    error=str(result),
                    pr_number=state.pr_metadata.pr_number
                )
                failed_agents.append((agent_id, str(result)))
                continue
            
            # Unpack successful result
            findings, metadata = result
            successful_agents += 1
            
            # Add all findings to the blackboard
            for finding in findings:
                state.add_finding(finding)
                logger.debug(
                    f"Finding added",
                    agent_id=agent_id,
                    finding_type=finding.finding_type,
                    file_path=finding.file_path,
                    severity=finding.severity
                )
            
            # Record execution metadata
            state.add_metadata(metadata)
            
            logger.info(
                f"Agent analysis complete",
                agent_id=agent_id,
                findings_count=len(findings),
                execution_time_ms=metadata.execution_time_ms,
                pr_number=state.pr_metadata.pr_number
            )
        
        # Summary logging
        logger.info(
            f"[Phase A] Analysis complete",
            successful_agents=successful_agents,
            failed_agents=len(failed_agents),
            total_findings=len(state.findings),
            pr_number=state.pr_metadata.pr_number
        )
        
        if failed_agents and successful_agents == 0:
            # All agents failed - this is a critical error
            errors = "; ".join([f"{aid}: {err}" for aid, err in failed_agents])
            raise RuntimeError(f"Phase A failed: All agents failed. {errors}")
        
        if failed_agents:
            # Some agents failed but at least one succeeded
            logger.warning(
                f"Partial agent failure in Phase A",
                failed_agents=[aid for aid, _ in failed_agents],
                pr_number=state.pr_metadata.pr_number
            )
    
    async def _execute_agent_safe(
        self, agent: BaseAgent, state: ReviewState
    ) -> Tuple[List[AgentFinding], AgentMetadata]:
        """
        Safely execute an agent with exception handling and timeout.
        
        Args:
            agent: Agent to execute
            state: ReviewState to analyze
            
        Returns:
            Tuple of (findings, metadata)
            
        Raises:
            Exception: If agent execution fails or times out
        """
        try:
            # Execute agent with 60-second timeout
            findings, metadata = await asyncio.wait_for(
                agent.execute(state),
                timeout=60.0
            )
            return findings, metadata
        except asyncio.TimeoutError as e:
            logger.error(
                f"Agent execution timeout",
                agent_id=agent.agent_id,
                timeout_seconds=60,
                pr_number=state.pr_metadata.pr_number
            )
            raise TimeoutError(f"Agent {agent.agent_id} timed out after 60 seconds") from e
        except Exception as e:
            logger.error(
                f"Agent execution error",
                agent_id=agent.agent_id,
                error_type=type(e).__name__,
                error_message=str(e),
                pr_number=state.pr_metadata.pr_number
            )
            raise
    
    async def _phase_b_evaluate(self, state: ReviewState) -> None:
        """
        Phase B: Evaluate findings and set blocking flags.
        
        Determines if critical issues should block the PR:
        - If critical findings exist, set is_blocked = True
        - This flag is used by Summarizer to set appropriate tone
        - Security vulnerabilities almost always block
        
        Args:
            state: ReviewState with findings from Phase A
        """
        critical_findings = state.get_critical_findings()
        
        logger.info(
            f"[Phase B] Evaluating findings",
            total_findings=len(state.findings),
            critical_count=len(critical_findings),
            pr_number=state.pr_metadata.pr_number
        )
        
        if critical_findings:
            logger.warning(
                f"Critical issues detected - blocking PR",
                critical_count=len(critical_findings),
                pr_number=state.pr_metadata.pr_number
            )
            
            for finding in critical_findings:
                logger.warning(
                    f"Critical finding: {finding.finding_type}",
                    file_path=finding.file_path,
                    agent_id=finding.agent_id,
                    pr_number=state.pr_metadata.pr_number
                )
            
            state.set_blocked(True)
        else:
            logger.info(
                f"[Phase B] No critical issues - PR can proceed",
                pr_number=state.pr_metadata.pr_number
            )
    
    async def _phase_c_synthesize(self, state: ReviewState) -> None:
        """
        Phase C: Synthesize findings into professional summary.
        
        The Summarizer agent:
        - Takes all findings from the blackboard
        - Organizes them by severity and category
        - Generates professional GitHub-flavored Markdown
        - Highlights progress if there are duplicate findings
        
        Args:
            state: ReviewState with all findings accumulated
        """
        logger.info(
            f"[Phase C] Starting synthesis",
            total_findings=len(state.findings),
            new_findings=len(state.get_new_findings()),
            duplicate_findings=len(state.get_duplicate_findings()),
            pr_number=state.pr_metadata.pr_number
        )
        
        try:
            # Generate the final comment
            comment = await self.summarizer_agent.generate_comment(state)
            
            # Store it in the state
            state.set_summary(comment)
            
            logger.info(
                f"[Phase C] Synthesis complete",
                comment_length=len(comment),
                is_blocked=state.is_blocked,
                pr_number=state.pr_metadata.pr_number
            )
        except Exception as e:
            logger.error(
                f"Synthesis failed",
                error_type=type(e).__name__,
                error_message=str(e),
                pr_number=state.pr_metadata.pr_number
            )
            
            # Fallback: generate basic comment from findings
            state.set_summary(self._generate_fallback_summary(state))
            logger.info(
                f"Using fallback summary due to synthesis error",
                pr_number=state.pr_metadata.pr_number
            )
    
    def _generate_fallback_summary(self, state: ReviewState) -> str:
        """
        Generate a basic summary when synthesis fails.
        
        This is a fallback to ensure we always have some output.
        """
        findings = state.findings
        critical = state.get_critical_findings()
        
        summary = f"""🤖 **Agentic Code Review**

**Status**: {'🚫 Changes Requested' if state.is_blocked else '✅ Approved'}

**Summary**: Found {len(findings)} issue(s) across {len(set(f.file_path for f in findings))} file(s).

**Critical Issues**: {len(critical)}

"""
        
        if findings:
            summary += "**Findings**:\n"
            for f in findings:
                summary += f"\n- **{f.finding_type}** ({f.severity}): {f.description}\n"
        
        return summary
    
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
