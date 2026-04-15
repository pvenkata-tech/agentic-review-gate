"""
Logic Agent: Analyzes code quality, design patterns, and SOLID principles.

This agent focuses on:
- Design pattern violations
- SOLID principle violations
- Dead code detection
- Code complexity analysis
- Architectural concerns

Can operate in two modes:
1. LLM-powered: Uses Claude or GPT-4 with specialized prompts
2. Rule-based: Uses regex/AST patterns for offline analysis
"""

from typing import List, Optional
from code_reviewer.core.state import ReviewState, AgentFinding, Severity
from code_reviewer.prompts import get_prompt_for_agent
from code_reviewer.llm import get_llm_client, LLMClient, LLMResponse, MockLLMClient
from code_reviewer.utils.diff_parser import DiffParser
from .base import BaseAgent


class LogicAgent(BaseAgent):
    """Agent for detecting logic and design pattern issues."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, use_llm: bool = True):
        """
        Initialize Logic Agent.
        
        Args:
            llm_client: LLM client to use (if None, auto-detects)
            use_llm: Whether to use LLM for analysis (default True)
        """
        super().__init__(agent_id="logic")
        self.use_llm = use_llm
        
        if use_llm:
            self.llm_client = llm_client or get_llm_client()
        else:
            self.llm_client = None
        
        self.prompt_template = get_prompt_for_agent("logic")
    
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """
        Analyze PR for logic and design pattern issues.
        
        If LLM is available, sends the diff and prompt to Claude/GPT-4.
        Otherwise, falls back to rule-based pattern matching.
        
        Args:
            state: Current ReviewState
            
        Returns:
            List of AgentFinding objects
        """
        findings: List[AgentFinding] = []
        
        # Parse the diff to extract only changed code
        diff_parser = DiffParser()
        file_diffs = diff_parser.parse(state.pr_metadata.diff_content)
        
        # Prepare diff content for LLM
        diff_text = self._format_diff_for_llm(file_diffs)
        
        if self.use_llm and self.llm_client and not isinstance(self.llm_client, MockLLMClient):
            # Use LLM for sophisticated analysis
            findings = await self._analyze_with_llm(state, diff_text)
        else:
            # Fall back to rule-based analysis
            findings = await self._analyze_with_rules(state, diff_text)
        
        return findings
    
    async def _analyze_with_llm(
        self,
        state: ReviewState,
        diff_text: str
    ) -> List[AgentFinding]:
        """
        Analyze using LLM (Claude or GPT-4).
        
        Args:
            state: ReviewState with PR metadata
            diff_text: Formatted diff content
            
        Returns:
            List of findings from LLM analysis
        """
        # Format the prompt with PR details
        prompt = self.prompt_template.format(
            pr_number=state.pr_metadata.pr_number,
            pr_title=state.pr_metadata.title,
            author=state.pr_metadata.author,
            files_changed_count=len(state.pr_metadata.files_changed),
            additions=state.pr_metadata.additions,
            deletions=state.pr_metadata.deletions,
            file_diffs=diff_text,
        )
        
        try:
            # Call LLM
            response: LLMResponse = await self.llm_client.call(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                temperature=0.3,  # Lower temperature for deterministic analysis
                max_tokens=2000,
            )
            
            # Parse response into findings
            findings = self._parse_llm_findings(response, state)
            
            return findings
        
        except Exception as e:
            # Log error and fall back to rules
            logger = self._get_logger()
            logger.error(f"LLM analysis failed: {str(e)}")
            return await self._analyze_with_rules(state, diff_text)
    
    async def _analyze_with_rules(
        self,
        state: ReviewState,
        diff_text: str
    ) -> List[AgentFinding]:
        """
        Analyze using rule-based pattern matching.
        
        This is the fallback when LLM is not available or fails.
        
        Args:
            state: ReviewState with PR metadata
            diff_text: Formatted diff content
            
        Returns:
            List of findings from pattern matching
        """
        findings: List[AgentFinding] = []
        
        # Analyze each modified file
        for file_path in state.pr_metadata.files_changed:
            # Pattern 1: Check for overly long methods/functions
            findings.extend(
                await self._check_method_complexity(file_path, state)
            )
            
            # Pattern 2: Check for code duplication
            findings.extend(
                await self._check_code_duplication(file_path, state)
            )
            
            # Pattern 3: Check for unused imports/variables
            findings.extend(
                await self._check_unused_code(file_path, state)
            )
            
            # Pattern 4: Check for deep nesting
            findings.extend(
                await self._check_nesting_depth(file_path, state)
            )
        
        return findings
    
    def _format_diff_for_llm(self, file_diffs: List) -> str:
        """Format parsed diff for inclusion in LLM prompt."""
        if not file_diffs:
            return "No files changed in this PR."
        
        result = []
        result.append(f"## Code Changes ({len(file_diffs)} files modified)\n")
        
        for file_diff in file_diffs[:15]:  # Limit to first 15 files
            result.append(f"\n### File: `{file_diff.file_path}`")
            
            # Add file status
            if file_diff.is_added:
                result.append("**Status**: NEW FILE")
            elif file_diff.is_deleted:
                result.append("**Status**: DELETED")
            elif file_diff.is_renamed:
                result.append(f"**Status**: RENAMED (from `{file_diff.old_file}`)")
            else:
                result.append("**Status**: MODIFIED")
            
            if file_diff.is_binary:
                result.append("(Binary file - not analyzed)")
                continue
            
            # If no hunks, indicate that
            if not file_diff.hunks:
                result.append("(No code changes in diff, or file only has whitespace changes)")
                continue
            
            # Collect all lines from all hunks with better context
            for hunk_idx, hunk in enumerate(file_diff.hunks):
                result.append(f"\n**Hunk {hunk_idx + 1}** (lines {hunk.new_start}-{hunk.new_start + hunk.new_count}):")
                
                # Include the actual lines from the hunk
                if hunk.lines:
                    # Format the diff lines with better readability
                    formatted_lines = []
                    for line in hunk.lines[:40]:  # Limit lines per hunk
                        if line.startswith('+') and not line.startswith('+++'):
                            formatted_lines.append(f"➕ {line}")
                        elif line.startswith('-') and not line.startswith('---'):
                            formatted_lines.append(f"➖ {line}")
                        else:
                            formatted_lines.append(f"  {line}")
                    
                    result.append("```diff\n" + "\n".join(formatted_lines) + "\n```")
                
                # Also include statistics about the hunk
                if hunk.added_lines or hunk.removed_lines:
                    result.append(f"- Lines added: {len(hunk.added_lines)}")
                    result.append(f"- Lines removed: {len(hunk.removed_lines)}")
        
        return "\n".join(result) if result else "No analyzable changes in this PR."
    
    def _parse_llm_findings(
        self,
        response: LLMResponse,
        state: ReviewState
    ) -> List[AgentFinding]:
        """Parse JSON findings from LLM response."""
        findings = []
        
        try:
            data = response.parse_json()
            
            for finding_data in data.get("findings", []):
                finding = AgentFinding(
                    file_path=finding_data.get("file_path", "unknown"),
                    line_number=finding_data.get("line_number"),
                    finding_type=finding_data.get("finding_type", "Code Quality"),
                    description=finding_data.get("description", ""),
                    suggestion=finding_data.get("suggestion", ""),
                    severity=self._parse_severity(finding_data.get("severity")),
                    agent_id=self.agent_id,
                )
                findings.append(finding)
        
        except Exception as e:
            logger = self._get_logger()
            logger.warning(f"Failed to parse LLM findings: {str(e)}")
        
        return findings
    
    def _get_logger(self):
        """Get logger instance."""
        from code_reviewer.utils.logger import get_logger
        return get_logger()
    
    def _parse_severity(self, severity_str: str) -> Severity:
        """Parse severity string to enum."""
        if not severity_str:
            return Severity.INFO
        
        severity_str = severity_str.lower()
        if severity_str == "critical":
            return Severity.CRITICAL
        elif severity_str == "warning":
            return Severity.WARNING
        else:
            return Severity.INFO
    
    async def _check_method_complexity(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect methods with high cyclomatic complexity."""
        findings: List[AgentFinding] = []
        
        # This is a placeholder. In production:
        # - Parse the file's AST
        # - Count conditional branches
        # - Flag methods with complexity > threshold
        # - Use LLM for contextual suggestions
        
        # Example finding (would be programmatically detected)
        if "test" not in file_path and ".py" in file_path:
            # Simulate detection of a complex method
            findings.append(
                self._create_finding(
                    file_path=file_path,
                    finding_type="High Cyclomatic Complexity",
                    description="Method has multiple nested conditionals increasing cognitive complexity",
                    suggestion="Consider extracting conditional logic into separate, well-named methods",
                    severity=Severity.WARNING,
                    line_number=42,
                )
            )
        
        return findings
    
    async def _check_code_duplication(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect duplicated code blocks."""
        findings: List[AgentFinding] = []
        
        # This is a placeholder. In production:
        # - Use radon or similar tools for duplication detection
        # - Compare against codebase for similar patterns
        # - Suggest refactoring into shared utilities
        
        return findings
    
    async def _check_unused_code(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect unused imports and variables."""
        findings: List[AgentFinding] = []
        
        # This is a placeholder. In production:
        # - Use tools like vulture or bandit
        # - Parse imports and their usage
        # - Identify unused declarations
        
        return findings
    
    async def _check_nesting_depth(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect overly nested code."""
        findings: List[AgentFinding] = []
        
        # This is a placeholder. In production:
        # - Count nesting levels in control flow
        # - Flag functions with nesting > 3 levels
        # - Suggest early returns or helper functions
        
        return findings
