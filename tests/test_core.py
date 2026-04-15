"""
Unit tests for the Code Reviewer system.

Test structure:
- test_state.py: ReviewState and data model tests
- test_agents.py: Agent implementation tests
- test_coordinator.py: Coordinator workflow tests
- test_integration.py: End-to-end integration tests
"""

import pytest
import asyncio
from datetime import datetime

from code_reviewer.core.state import (
    ReviewState,
    AgentFinding,
    PRMetadata,
    Severity,
)
from code_reviewer.agents.base import BaseAgent
from code_reviewer.agents.logic import LogicAgent
from code_reviewer.agents.security import SecurityGuardAgent
from code_reviewer.agents.summary import SummarizerAgent


class TestReviewState:
    """Test ReviewState (the Blackboard)."""
    
    def test_create_state(self):
        """Test creating a ReviewState."""
        pr_metadata = PRMetadata(
            pr_number=1,
            title="Test PR",
            author="test_author",
            branch="test_branch",
            diff_content="...",
        )
        
        state = ReviewState(pr_metadata=pr_metadata)
        
        assert state.pr_metadata.pr_number == 1
        assert len(state.findings) == 0
        assert state.is_blocked is False
        assert state.final_summary is None
    
    def test_add_finding(self):
        """Test adding findings to the blackboard."""
        pr_metadata = PRMetadata(
            pr_number=2,
            title="Test",
            author="user",
            branch="main",
            diff_content="...",
        )
        state = ReviewState(pr_metadata=pr_metadata)
        
        finding = AgentFinding(
            file_path="test.py",
            line_number=10,
            finding_type="Test Issue",
            description="Test description",
            suggestion="Test suggestion",
            severity=Severity.WARNING,
            agent_id="test_agent",
        )
        
        state.add_finding(finding)
        
        assert len(state.findings) == 1
        assert state.findings[0].finding_type == "Test Issue"
    
    def test_get_critical_findings(self):
        """Test filtering critical findings."""
        pr_metadata = PRMetadata(
            pr_number=3,
            title="Test",
            author="user",
            branch="main",
            diff_content="...",
        )
        state = ReviewState(pr_metadata=pr_metadata)
        
        # Add mixed severity findings
        for severity in [Severity.CRITICAL, Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
            state.add_finding(
                AgentFinding(
                    file_path="test.py",
                    finding_type="Test",
                    description="Test",
                    suggestion="Test",
                    severity=severity,
                    agent_id="test",
                )
            )
        
        critical = state.get_critical_findings()
        assert len(critical) == 2
    
    def test_summary_stats(self):
        """Test getting summary statistics."""
        pr_metadata = PRMetadata(
            pr_number=4,
            title="Test",
            author="user",
            branch="main",
            diff_content="...",
        )
        state = ReviewState(pr_metadata=pr_metadata)
        
        state.add_finding(
            AgentFinding(
                file_path="file1.py",
                finding_type="Issue 1",
                description="Test",
                suggestion="Test",
                severity=Severity.CRITICAL,
                agent_id="test",
            )
        )
        state.add_finding(
            AgentFinding(
                file_path="file1.py",
                finding_type="Issue 2",
                description="Test",
                suggestion="Test",
                severity=Severity.WARNING,
                agent_id="test",
            )
        )
        state.add_finding(
            AgentFinding(
                file_path="file2.py",
                finding_type="Issue 3",
                description="Test",
                suggestion="Test",
                severity=Severity.INFO,
                agent_id="test",
            )
        )
        
        stats = state.summary_stats()
        
        assert stats["total_findings"] == 3
        assert stats["critical_count"] == 1
        assert stats["warning_count"] == 1
        assert stats["info_count"] == 1
        assert stats["files_affected"] == 2


class TestAgents:
    """Test agent implementations."""
    
    @pytest.mark.asyncio
    async def test_base_agent_create_finding(self):
        """Test BaseAgent helper method."""
        
        class TestAgent(BaseAgent):
            async def analyze(self, state):
                return []
        
        agent = TestAgent("test")
        finding = agent._create_finding(
            file_path="test.py",
            finding_type="Test",
            description="Test description",
            suggestion="Test suggestion",
            severity=Severity.WARNING,
            line_number=5,
        )
        
        assert finding.file_path == "test.py"
        assert finding.agent_id == "test"
        assert finding.severity == Severity.WARNING
        assert finding.line_number == 5
    
    @pytest.mark.asyncio
    async def test_logic_agent_analyze(self):
        """Test LogicAgent analysis."""
        pr_metadata = PRMetadata(
            pr_number=5,
            title="Test",
            author="user",
            branch="main",
            diff_content="...",
            files_changed=["test.py"],
        )
        state = ReviewState(pr_metadata=pr_metadata)
        
        agent = LogicAgent()
        findings = await agent.analyze(state)
        
        # Should return a list (even if empty in this test)
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_security_agent_analyze(self):
        """Test SecurityGuardAgent analysis."""
        pr_metadata = PRMetadata(
            pr_number=6,
            title="Test",
            author="user",
            branch="main",
            diff_content="...",
            files_changed=["config.py"],
        )
        state = ReviewState(pr_metadata=pr_metadata)
        
        agent = SecurityGuardAgent()
        findings = await agent.analyze(state)
        
        assert isinstance(findings, list)
    
    @pytest.mark.asyncio
    async def test_summarizer_deduplication(self):
        """Test Summarizer's deduplication logic."""
        summarizer = SummarizerAgent()
        
        # Create duplicate findings (same file, line, type)
        findings = [
            AgentFinding(
                file_path="test.py",
                line_number=10,
                finding_type="Duplicate",
                description="Found by agent 1",
                suggestion="Fix it",
                severity=Severity.WARNING,
                agent_id="logic",
            ),
            AgentFinding(
                file_path="test.py",
                line_number=10,
                finding_type="Duplicate",
                description="Found by agent 2",
                suggestion="Fix it",
                severity=Severity.WARNING,
                agent_id="security",
            ),
        ]
        
        deduplicated = summarizer._deduplicate_findings(findings)
        
        # Should keep only one
        assert len(deduplicated) == 1


class TestIntegration:
    """Integration tests."""
    
    @pytest.mark.asyncio
    async def test_basic_review_flow(self):
        """Test basic review flow."""
        from code_reviewer.core.coordinator import ReviewCoordinator
        
        pr_metadata = PRMetadata(
            pr_number=100,
            title="Integration Test",
            author="test_user",
            branch="test_branch",
            diff_content="...",
            files_changed=["test.py"],
        )
        
        state = ReviewState(pr_metadata=pr_metadata)
        coordinator = ReviewCoordinator()
        
        # Run review
        final_state = await coordinator.review_pr(state)
        
        # Verify state was updated
        assert final_state.pr_metadata.pr_number == 100
        assert len(final_state.metadata) > 0  # Should have execution metadata
        assert final_state.final_summary is not None  # Should have summary


# For running tests with pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
