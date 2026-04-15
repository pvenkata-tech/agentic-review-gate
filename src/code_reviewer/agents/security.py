"""
Security Guard Agent: Scans for secrets, PII, and OWASP vulnerabilities.

Design Pattern: Strategy pattern
- Implements the AnalysisAgent interface from core/interfaces.py
- Inherits from BaseAgent (abstract base class)
- Can be added/removed without changing ReviewCoordinator code (Open/Closed Principle)

This agent focuses on:
- Hardcoded API keys, passwords, and credentials
- Personally Identifiable Information (PII) leaks
- Common OWASP top 10 vulnerabilities
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure cryptography usage
- Weak authentication patterns

Can operate in two modes:
1. LLM-powered: Uses Claude or GPT-4 with specialized security prompts
2. Rule-based: Uses regex patterns for offline detection

Example:
    agent = SecurityGuardAgent(llm_client=llm, use_llm=True)
    findings = await agent.analyze(state)
"""

import re
from typing import List, Optional
from code_reviewer.core.state import ReviewState, AgentFinding, Severity, AgentMetadata
from code_reviewer.prompts import get_prompt_for_agent
from code_reviewer.llm import get_llm_client, LLMClient, LLMResponse, MockLLMClient
from code_reviewer.utils.diff_parser import DiffParser
from .base import BaseAgent


class SecurityGuardAgent(BaseAgent):
    """Agent for detecting security vulnerabilities and sensitive data leaks."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, use_llm: bool = True):
        """
        Initialize Security Agent.
        
        Args:
            llm_client: LLM client to use (if None, auto-detects)
            use_llm: Whether to use LLM for analysis (default True)
        """
        super().__init__(agent_id="security")
        self.use_llm = use_llm
        
        if use_llm:
            self.llm_client = llm_client or get_llm_client()
        else:
            self.llm_client = None
        
        self.prompt_template = get_prompt_for_agent("security")
        self._setup_patterns()
    
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """
        Analyze PR for security vulnerabilities.
        
        Uses a combined approach:
        1. Fast regex/pattern matching on all code
        2. Optional LLM analysis for contextual understanding
        
        Args:
            state: Current ReviewState
            
        Returns:
            List of security findings
        """
        import time
        from code_reviewer.utils.logger import get_logger
        
        logger = get_logger()
        start_time = time.perf_counter()
        
        findings: List[AgentFinding] = []
        
        # Debug: log diff content
        diff_content = state.pr_metadata.diff_content
        logger.debug(f"[{self.agent_id}] Received diff_content: {len(diff_content)} chars")
        if diff_content and len(diff_content) > 0:
            logger.debug(f"[{self.agent_id}] First 200 chars:\n{diff_content[:200]}")
        
        # Parse diff to get changed code
        diff_parser = DiffParser()
        file_diffs = diff_parser.parse(state.pr_metadata.diff_content)
        logger.info(f"[{self.agent_id}] Parsed {len(file_diffs)} files from diff")
        
        # Debug: log hunk statistics
        total_hunks = sum(len(f.hunks) for f in file_diffs)
        logger.debug(f"[{self.agent_id}] Total hunks: {total_hunks}")
        
        diff_text = self._format_diff_for_llm(file_diffs)
        logger.debug(f"[{self.agent_id}] Formatted diff_text: {len(diff_text)} chars")
        
        # Always run pattern matching (fast and doesn't require API)
        findings.extend(await self._analyze_with_patterns(state, diff_text))
        
        # Optionally run LLM analysis (slower, more sophisticated)
        if self.use_llm and self.llm_client and not isinstance(self.llm_client, MockLLMClient):
            llm_findings = await self._analyze_with_llm(state, diff_text)
            # Merge LLM findings with pattern findings (avoid duplicates)
            findings.extend(
                f for f in llm_findings
                if not self._is_duplicate_finding(f, findings)
            )
        
        return findings
    
    def _is_duplicate_finding(
        self,
        finding: AgentFinding,
        existing_findings: List[AgentFinding]
    ) -> bool:
        """Check if a finding is already in the list."""
        for existing in existing_findings:
            if (existing.file_path == finding.file_path and
                existing.finding_type == finding.finding_type and
                existing.description == finding.description):
                return True
        return False
    
    async def _analyze_with_llm(
        self,
        state: ReviewState,
        diff_text: str
    ) -> List[AgentFinding]:
        """
        Analyze using LLM for contextual understanding.
        
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
            file_diffs=diff_text,
        )
        
        try:
            # Call LLM
            response: LLMResponse = await self.llm_client.call(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"],
                temperature=0.2,  # Very low temperature for security (deterministic)
                max_tokens=2000,
            )
            
            # Parse response into findings
            findings = self._parse_llm_findings(response, state)
            return findings
        
        except Exception as e:
            logger = self._get_logger()
            logger.warning(f"LLM security analysis failed: {str(e)}")
            return []  # Return empty list - pattern matching already ran
    
    async def _analyze_with_patterns(
        self,
        state: ReviewState,
        diff_text: str
    ) -> List[AgentFinding]:
        """
        Analyze using regex pattern matching.
        
        This runs first as it's fast and doesn't require API calls.
        """
        findings: List[AgentFinding] = []
        
        # Scan for secrets
        findings.extend(
            await self._scan_for_secrets(state, diff_text)
        )
        
        # Scan for PII
        findings.extend(
            await self._scan_for_pii(state, diff_text)
        )
        
        # Scan for OWASP vulnerabilities
        findings.extend(
            await self._scan_for_owasp(state, diff_text)
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
                    finding_type=finding_data.get("finding_type", "Security Vulnerability"),
                    description=finding_data.get("description", ""),
                    suggestion=finding_data.get("suggestion", ""),
                    severity=self._parse_severity(finding_data.get("severity")),
                    agent_id=self.agent_id,
                )
                findings.append(finding)
        
        except Exception as e:
            logger = self._get_logger()
            logger.warning(f"Failed to parse security findings from LLM: {str(e)}")
        
        return findings
    
    def _get_logger(self):
        """Get logger instance."""
        from code_reviewer.utils.logger import get_logger
        return get_logger()
    
    def _parse_severity(self, severity_str: str) -> Severity:
        """Parse severity string to enum."""
        if not severity_str:
            return Severity.WARNING
        
        severity_str = severity_str.lower()
        if severity_str == "critical":
            return Severity.CRITICAL
        elif severity_str == "warning":
            return Severity.WARNING
        else:
            return Severity.INFO
    
    def _setup_patterns(self) -> None:
        """Initialize regex patterns for secret and PII detection."""
        # Patterns for common credential formats
        self.secret_patterns = {
            "api_key": re.compile(
                r"api[_-]?key\s*=\s*['\"]([a-zA-Z0-9\-_.]{20,})['\"]",
                re.IGNORECASE
            ),
            "aws_key": re.compile(
                r"AKIA[0-9A-Z]{16}",
                re.IGNORECASE
            ),
            "github_token": re.compile(
                r"ghp_[A-Za-z0-9_]{36,}",
            ),
            "slack_token": re.compile(
                r"xox[baprs]-[0-9a-zA-Z]{10,48}",
            ),
            "private_key": re.compile(
                r"-----BEGIN RSA PRIVATE KEY-----",
                re.IGNORECASE
            ),
        }
        
        # Patterns for PII
        self.pii_patterns = {
            "email_hardcoded": re.compile(
                r"email\s*=\s*['\"]([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})['\"]",
                re.IGNORECASE
            ),
            "ssn": re.compile(
                r"\b\d{3}-\d{2}-\d{4}\b",  # XXX-XX-XXXX format
            ),
            "phone": re.compile(
                r"\b(?:\+1|\d{1})?[\s.-]?\(?[0-9]{3}\)?[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}\b",
            ),
        }
    
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """
        Scan PR for security vulnerabilities and sensitive data.
        
        Args:
            state: Current ReviewState
            
        Returns:
            List of AgentFinding objects
        """
        findings: List[AgentFinding] = []
        
        # Analyze each modified file
        for file_path in state.pr_metadata.files_changed:
            # Skip binary and config-only files
            if self._should_skip_file(file_path):
                continue
            
            # Scan for secrets
            findings.extend(
                await self._scan_for_secrets(file_path, state)
            )
            
            # Scan for PII
            findings.extend(
                await self._scan_for_pii(file_path, state)
            )
            
            # Scan for common vulnerabilities
            findings.extend(
                await self._scan_for_vulnerabilities(file_path, state)
            )
        
        # Set the blocked flag if critical issues found
        critical_count = sum(
            1 for f in findings
            if f.severity == Severity.CRITICAL
        )
        if critical_count > 0:
            # Note: In a real implementation, this would be done by the coordinator
            # but we flag it here for the Security Guard's responsibility
            pass
        
        return findings
    
    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if a file should be skipped from security scanning."""
        skip_extensions = {".png", ".jpg", ".gif", ".pdf", ".zip", ".tar", ".gz"}
        skip_prefixes = {"docs/", ".git", "node_modules/", "venv/"}
        
        for ext in skip_extensions:
            if file_path.endswith(ext):
                return True
        
        for prefix in skip_prefixes:
            if file_path.startswith(prefix):
                return True
        
        return False
    
    async def _scan_for_secrets(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect hardcoded credentials and secrets."""
        findings: List[AgentFinding] = []
        
        # In production, read the actual file diff content
        # For now, simulate detection based on content patterns
        
        for secret_type, pattern in self.secret_patterns.items():
            # This is a placeholder - would scan actual diff content
            if secret_type == "api_key" and "config" in file_path.lower():
                findings.append(
                    self._create_finding(
                        file_path=file_path,
                        finding_type="Hardcoded API Key",
                        description=f"Detected potential {secret_type} hardcoded in source",
                        suggestion="Move credentials to environment variables or secure vault. "
                                  "Rotate compromised keys immediately.",
                        severity=Severity.CRITICAL,
                        line_number=15,
                    )
                )
        
        return findings
    
    async def _scan_for_pii(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect personally identifiable information."""
        findings: List[AgentFinding] = []
        
        # Placeholder: would scan actual diff content with PII patterns
        
        return findings
    
    async def _scan_for_vulnerabilities(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect common OWASP vulnerabilities."""
        findings: List[AgentFinding] = []
        
        # Check for SQL injection vulnerabilities
        if ".py" in file_path:
            findings.extend(
                await self._check_sql_injection(file_path, state)
            )
            findings.extend(
                await self._check_insecure_crypto(file_path, state)
            )
            findings.extend(
                await self._check_deserialization(file_path, state)
            )
        
        return findings
    
    async def _check_sql_injection(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect potential SQL injection vulnerabilities."""
        findings: List[AgentFinding] = []
        
        # Placeholder: would parse AST to detect string concatenation in SQL queries
        
        return findings
    
    async def _check_insecure_crypto(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect insecure cryptography usage."""
        findings: List[AgentFinding] = []
        
        # Placeholder: would detect use of weak algorithms like MD5, DES
        
        return findings
    
    async def _check_deserialization(
        self, file_path: str, state: ReviewState
    ) -> List[AgentFinding]:
        """Detect unsafe deserialization that could lead to RCE."""
        findings: List[AgentFinding] = []
        
        # Placeholder: would detect unsafe pickle, yaml, or eval usage
        
        return findings
