"""
State schema module defining the Blackboard pattern for PR review coordination.

The ReviewState acts as the single source of truth, with each agent contributing
specialized findings without direct inter-agent communication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib


class Severity(str, Enum):
    """Finding severity levels for prioritization."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AgentFinding(BaseModel):
    """Represents a single finding from an agent's analysis.
    
    This is the fundamental unit of work passed through the blackboard.
    Each finding has a finding_id for deduplication across review cycles.
    """
    file_path: str = Field(..., description="Relative path to the file being reviewed")
    line_number: Optional[int] = Field(None, description="Line number (1-indexed) of the finding")
    finding_type: str = Field(..., description="Category of finding (e.g., 'Pattern Match', 'PII Leak')")
    description: str = Field(..., description="Human-readable description of the finding")
    suggestion: str = Field(..., description="Actionable suggestion to resolve the finding")
    severity: Severity = Field(..., description="Severity level: info, warning, or critical")
    agent_id: str = Field(..., description="ID of the agent that generated this finding")
    finding_id: Optional[str] = Field(None, description="Hash-based ID for deduplication (computed from file_path + finding_type + description)")
    is_duplicate: bool = Field(default=False, description="True if this finding was flagged in a previous review")
    
    class Config:
        use_enum_values = False
    
    def compute_finding_id(self) -> str:
        """Compute a stable hash ID for deduplication.
        
        The ID is based on file path, finding type, and description to allow
        detection of duplicate findings across review cycles.
        
        Returns:
            Hash string (first 12 chars of SHA256)
        """
        content = f"{self.file_path}::{self.finding_type}::{self.description}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:12]


class AgentMetadata(BaseModel):
    """Metadata about an agent's execution within the review cycle."""
    agent_id: str = Field(..., description="Unique identifier for the agent")
    execution_time_ms: float = Field(..., description="Time taken to execute in milliseconds")
    token_usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Token counts (input, output, etc.) if using LLM-based agents"
    )
    status: str = Field(default="success", description="Execution status: success, error, etc.")
    error_message: Optional[str] = Field(None, description="Error details if status is not success")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = False


class PRMetadata(BaseModel):
    """Metadata about the PR being reviewed."""
    pr_number: int = Field(..., description="GitHub PR number")
    title: str = Field(..., description="PR title")
    author: str = Field(..., description="PR author GitHub username")
    branch: str = Field(..., description="Target branch name")
    base_branch: str = Field(default="main", description="Base branch being merged into")
    diff_content: str = Field(..., description="Full diff content of the PR")
    files_changed: List[str] = Field(default_factory=list, description="List of modified file paths")
    additions: int = Field(default=0, description="Total lines added")
    deletions: int = Field(default=0, description="Total lines deleted")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = False


class ReviewState(BaseModel):
    """
    The Blackboard: Single source of truth for PR review state.
    
    Each agent reads the current ReviewState, performs analysis, and contributes
    findings without direct coupling to other agents. The coordinator merges
    findings and manages the workflow.
    """
    # Immutable input data
    pr_metadata: PRMetadata = Field(..., description="Information about the PR being reviewed")
    
    # Mutable accumulated state
    findings: List[AgentFinding] = Field(
        default_factory=list,
        description="All findings from all agents accumulated on the blackboard"
    )
    
    # Execution metadata
    metadata: List[AgentMetadata] = Field(
        default_factory=list,
        description="Execution records for each agent"
    )
    
    # Control flags
    is_blocked: bool = Field(
        default=False,
        description="True if Security Guard found critical issues blocking merge"
    )
    
    # Final output
    final_summary: Optional[str] = Field(
        None,
        description="GitHub-flavored Markdown comment generated by Summarizer"
    )
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = False
    
    def add_finding(self, finding: AgentFinding) -> None:
        """Append a finding to the blackboard."""
        self.findings.append(finding)
        self.updated_at = datetime.utcnow()
    
    def add_metadata(self, metadata: AgentMetadata) -> None:
        """Record an agent's execution metadata."""
        self.metadata.append(metadata)
        self.updated_at = datetime.utcnow()
    
    def set_blocked(self, blocked: bool = True) -> None:
        """Set the blocked flag (typically by Security Guard)."""
        self.is_blocked = blocked
        self.updated_at = datetime.utcnow()
    
    def set_summary(self, summary: str) -> None:
        """Set the final summary (typically by Summarizer)."""
        self.final_summary = summary
        self.updated_at = datetime.utcnow()
    
    def get_critical_findings(self) -> List[AgentFinding]:
        """Filter findings by critical severity."""
        return [f for f in self.findings if f.severity == Severity.CRITICAL]
    
    def get_findings_by_agent(self, agent_id: str) -> List[AgentFinding]:
        """Filter findings by agent ID."""
        return [f for f in self.findings if f.agent_id == agent_id]
    
    def get_findings_by_file(self, file_path: str) -> List[AgentFinding]:
        """Filter findings by file path."""
        return [f for f in self.findings if f.file_path == file_path]
    
    def summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics about the review."""
        return {
            "total_findings": len(self.findings),
            "critical_count": len(self.get_critical_findings()),
            "warning_count": sum(1 for f in self.findings if f.severity == Severity.WARNING),
            "info_count": sum(1 for f in self.findings if f.severity == Severity.INFO),
            "files_affected": len(set(f.file_path for f in self.findings)),
            "is_blocked": self.is_blocked,
        }
    
    def compute_finding_ids(self) -> None:
        """Compute finding_id for all findings (call before deduplication).
        
        This must be called after agents add findings but before deduplication.
        """
        for finding in self.findings:
            if not finding.finding_id:
                finding.finding_id = finding.compute_finding_id()
    
    def mark_duplicates(self, previous_finding_ids: List[str]) -> None:
        """Mark findings that were flagged in previous reviews.
        
        Args:
            previous_finding_ids: List of finding_ids from previous review cycles
        """
        for finding in self.findings:
            if finding.finding_id and finding.finding_id in previous_finding_ids:
                finding.is_duplicate = True
    
    def get_new_findings(self) -> List[AgentFinding]:
        """Get only new findings (not marked as duplicates)."""
        return [f for f in self.findings if not f.is_duplicate]
    
    def get_duplicate_findings(self) -> List[AgentFinding]:
        """Get findings that were flagged in previous reviews."""
        return [f for f in self.findings if f.is_duplicate]
    
    def get_finding_ids(self) -> List[str]:
        """Get all finding IDs for storage/caching in persistent state."""
        return [f.finding_id for f in self.findings if f.finding_id]
