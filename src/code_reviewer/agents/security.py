"""
Security Guard Agent: Scans for secrets, PII, and OWASP vulnerabilities.

This agent focuses on:
- Hardcoded API keys and credentials
- Personally Identifiable Information (PII) leaks
- Common OWASP top 10 vulnerabilities
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure cryptography usage
"""

import re
from typing import List
from code_reviewer.core.state import ReviewState, AgentFinding, Severity
from .base import BaseAgent


class SecurityGuardAgent(BaseAgent):
    """Agent for detecting security vulnerabilities and sensitive data leaks."""
    
    def __init__(self):
        super().__init__(agent_id="security")
        self._setup_patterns()
    
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
