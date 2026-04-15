"""
Summarizer Agent: Synthesizes findings into a professional GitHub comment.

This agent's role is NOT to find bugs, but to:
- Deduplicate findings from other agents
- Organize by severity and type
- Generate professional, peer-level tone
- Create actionable GitHub-flavored Markdown output
- Provide executive summary and detailed breakdown
"""

from typing import List, Dict, Set
from code_reviewer.core.state import ReviewState, AgentFinding, Severity
from .base import BaseAgent


class SummarizerAgent(BaseAgent):
    """Agent for synthesizing findings into a cohesive review comment."""
    
    def __init__(self):
        super().__init__(agent_id="summarizer")
    
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """
        The Summarizer doesn't generate new findings; it synthesizes existing ones.
        
        This agent's execute() method is overridden to call generate_comment()
        instead, which directly modifies the state with the final summary.
        
        Args:
            state: Current ReviewState with all findings
            
        Returns:
            Empty list (Summarizer doesn't add findings, it generates summary)
        """
        return []
    
    async def generate_comment(self, state: ReviewState) -> str:
        """
        Generate a professional GitHub-flavored Markdown comment.
        
        This is the core responsibility of the Summarizer. It:
        1. Deduplicates findings
        2. Organizes by severity and file
        3. Generates professional tone
        4. Adds context and recommendations
        
        Args:
            state: ReviewState with accumulated findings
            
        Returns:
            Markdown-formatted comment ready to post to GitHub
        """
        # Step 1: Deduplicate findings
        deduplicated = self._deduplicate_findings(state.findings)
        
        # Step 2: Organize findings
        organized = self._organize_findings(deduplicated)
        
        # Step 3: Generate comment
        comment = self._build_comment(state, organized)
        
        return comment
    
    def _deduplicate_findings(self, findings: List[AgentFinding]) -> List[AgentFinding]:
        """
        Remove duplicate findings from multiple agents.
        
        If Logic and Security both flag the same line/file/type, keep only one
        with additional context noting both agents' perspectives.
        
        Args:
            findings: List of all findings from all agents
            
        Returns:
            Deduplicated list
        """
        # Use a set to track unique findings by key
        seen: Set[str] = set()
        deduplicated: List[AgentFinding] = []
        
        for finding in findings:
            # Create a unique key (file + line + type)
            key = f"{finding.file_path}:{finding.line_number}:{finding.finding_type}"
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)
        
        return deduplicated
    
    def _organize_findings(
        self, findings: List[AgentFinding]
    ) -> Dict[str, Dict[str, List[AgentFinding]]]:
        """
        Organize findings by severity, then by file.
        
        Returns a nested structure for easy template rendering.
        
        Args:
            findings: Deduplicated findings list
            
        Returns:
            Dict[severity][file_path] = [findings]
        """
        organized: Dict[str, Dict[str, List[AgentFinding]]] = {
            Severity.CRITICAL: {},
            Severity.WARNING: {},
            Severity.INFO: {},
        }
        
        for finding in findings:
            severity_key = finding.severity.value
            if severity_key not in organized:
                organized[severity_key] = {}
            
            if finding.file_path not in organized[severity_key]:
                organized[severity_key][finding.file_path] = []
            
            organized[severity_key][finding.file_path].append(finding)
        
        return organized
    
    def _build_comment(
        self,
        state: ReviewState,
        organized: Dict[str, Dict[str, List[AgentFinding]]],
    ) -> str:
        """
        Build the final Markdown comment.
        
        Structure:
        1. Header with summary stats
        2. Blocking verdict (if applicable)
        3. Critical issues (if any)
        4. Warnings
        5. Info-level feedback
        6. Overall recommendation
        
        Args:
            state: ReviewState with metadata
            organized: Organized findings by severity/file
            
        Returns:
            Markdown-formatted comment
        """
        lines: List[str] = []
        
        # Add header
        lines.append("## 🔍 Automated Code Review")
        lines.append("")
        
        # Add stats
        stats = state.summary_stats()
        lines.append(f"**Review Summary:** {stats['total_findings']} issues found")
        lines.append(f"- 🔴 {stats['critical_count']} Critical")
        lines.append(f"- 🟡 {stats['warning_count']} Warning")
        lines.append(f"- 🔵 {stats['info_count']} Info")
        lines.append("")
        
        # Add blocking verdict
        if state.is_blocked:
            lines.append("## ⛔ Blocking Issues")
            lines.append(
                "This PR has **critical security or structural issues** that must be "
                "resolved before merging. Please address the items marked 🔴 below."
            )
            lines.append("")
        
        # Add findings by severity
        for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
            severity_key = severity.value
            if not organized.get(severity_key):
                continue
            
            lines.append(self._section_for_severity(severity, organized[severity_key]))
        
        # Add recommendation
        lines.append(self._build_recommendation(state))
        
        return "\n".join(lines)
    
    def _section_for_severity(
        self, severity: Severity, findings_by_file: Dict[str, List[AgentFinding]]
    ) -> str:
        """Generate a section for a severity level with senior-level tone."""
        if severity == Severity.CRITICAL:
            header = "### 🔴 Critical Issues"
        elif severity == Severity.WARNING:
            header = "### 🟡 Warnings"
        else:
            header = "### 🔵 Info"
        
        lines = [header, ""]
        
        for file_path in sorted(findings_by_file.keys()):
            findings = findings_by_file[file_path]
            lines.append(f"**{file_path}**")
            lines.append("")
            
            for finding in findings:
                # Senior-level finding presentation
                lines.append(f"- **{finding.finding_type}**")
                if finding.line_number:
                    lines.append(f"  *Line {finding.line_number}*")
                
                # Present as architectural/design guidance, not just errors
                lines.append(f"  {finding.description}")
                
                # Suggestion as actionable improvement with context
                suggestion = finding.suggestion
                # Enhance suggestions with architectural framing
                if "should" in suggestion.lower() or "recommend" in suggestion.lower():
                    lines.append(f"  > **Suggestion:** {suggestion}")
                else:
                    lines.append(f"  > {suggestion}")
                lines.append("")
        
        return "\n".join(lines)
    
    def _build_recommendation(self, state: ReviewState) -> str:
        """Generate final recommendation text with senior architectural context."""
        lines = ["---", ""]
        
        if state.is_blocked:
            lines.append(
                "**Recommendation:** ❌ **Do Not Merge**\n\n"
                "This PR contains critical issues that require resolution before merging. "
                "The flagged items represent significant risks to system stability, security, or maintainability. "
                "Please address all 🔴 critical items, then request re-review."
            )
        else:
            stats = state.summary_stats()
            if stats["total_findings"] == 0:
                lines.append(
                    "**Recommendation:** ✅ **Approved**\n\n"
                    "No issues found. The code is architecturally sound and ready to merge."
                )
            else:
                lines.append(
                    "**Recommendation:** ⚠️ **Conditional Approval**\n\n"
                    "This PR can be merged after addressing the warnings and info items above. "
                    "Consider these suggestions as opportunities to improve code quality, maintainability, and resilience."
                )
        
        lines.append("")
        lines.append(
            "*This review was generated by an automated multi-agent system using architectural analysis. "
            "Please use your domain expertise when evaluating suggestions—automated feedback is a tool, not a verdict.*"
        )
        
        return "\n".join(lines)
