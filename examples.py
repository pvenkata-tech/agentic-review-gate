"""
Example: Running a Complete PR Review

This script demonstrates how to use the agentic-review-gate system
to review a pull request using the Blackboard pattern.
"""

import asyncio
from datetime import datetime

from code_reviewer.core.state import ReviewState, PRMetadata, Severity
from code_reviewer.core.coordinator import ReviewCoordinator


# Example PR metadata (would typically come from GitHub API)
EXAMPLE_DIFF = """
diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,10 +1,25 @@
 import hashlib
 import jwt
+import secrets
+from getpass import getpass
 
 class UserAuth:
-    def __init__(self, secret="super_secret_key"):
+    def __init__(self, secret: str):
         self.secret = secret
-        self.users = {}
+        self.users = {}
+        self.admin_pass = "Admin123!"  # Hardcoded password
     
+    def login(self, username: str, password: str) -> bool:
+        # Check credentials
+        if username == "admin":
+            return password == self.admin_pass
+        return False
+    
+    def complex_function(self):
+        if x > 0:
+            if y > 0:
+                if z > 0:
+                    return "nested"
+        return None
"""


async def example_direct_review():
    """Example 1: Direct programmatic review."""
    print("=" * 70)
    print("Example 1: Direct Programmatic Review")
    print("=" * 70)
    
    # Create PR metadata
    pr_metadata = PRMetadata(
        pr_number=123,
        title="Add user authentication system",
        author="alice",
        branch="feature/auth",
        base_branch="main",
        diff_content=EXAMPLE_DIFF,
        files_changed=["src/auth.py"],
        additions=25,
        deletions=5,
        created_at=datetime.utcnow(),
    )
    
    # Create initial review state (the "Blackboard")
    initial_state = ReviewState(pr_metadata=pr_metadata)
    
    print(f"\n📋 PR Information:")
    print(f"  PR #: {pr_metadata.pr_number}")
    print(f"  Title: {pr_metadata.title}")
    print(f"  Author: {pr_metadata.author}")
    print(f"  Files: {pr_metadata.files_changed}")
    
    # Create coordinator
    coordinator = ReviewCoordinator()
    
    print(f"\n🚀 Starting review with multi-agent coordinator...")
    
    # Run the review (orchestrates all phases)
    final_state = await coordinator.review_pr(initial_state)
    
    # Display results
    print(f"\n✅ Review Complete!")
    print(f"\n📊 Statistics:")
    stats = final_state.summary_stats()
    print(f"  Total Findings: {stats['total_findings']}")
    print(f"  Critical: {stats['critical_count']}")
    print(f"  Warnings: {stats['warning_count']}")
    print(f"  Info: {stats['info_count']}")
    print(f"  Is Blocked: {final_state.is_blocked}")
    
    print(f"\n📝 Agent Execution Times:")
    for metadata in final_state.metadata:
        print(f"  {metadata.agent_id}: {metadata.execution_time_ms:.2f}ms ({metadata.status})")
    
    print(f"\n🔍 Detailed Findings:")
    if not final_state.findings:
        print("  (No findings)")
    else:
        for i, finding in enumerate(final_state.findings, 1):
            print(f"\n  {i}. [{finding.severity.upper()}] {finding.finding_type}")
            print(f"     File: {finding.file_path}:{finding.line_number}")
            print(f"     Agent: {finding.agent_id}")
            print(f"     Description: {finding.description}")
            print(f"     Suggestion: {finding.suggestion}")
    
    print(f"\n💬 Final Summary for GitHub:")
    print("-" * 70)
    if final_state.final_summary:
        print(final_state.final_summary)
    else:
        print("(No summary generated)")
    print("-" * 70)


async def example_with_custom_findings():
    """Example 2: Manually add findings to demonstrate synthesis."""
    print("\n" * 2)
    print("=" * 70)
    print("Example 2: Demonstrating Summarizer Synthesis")
    print("=" * 70)
    
    from code_reviewer.agents.summary import SummarizerAgent
    
    # Create PR metadata
    pr_metadata = PRMetadata(
        pr_number=456,
        title="Refactor database models",
        author="bob",
        branch="refactor/models",
        base_branch="main",
        diff_content="... diff content ...",
        files_changed=["src/models/user.py", "src/models/post.py"],
    )
    
    # Create state
    state = ReviewState(pr_metadata=pr_metadata)
    
    # Manually add some findings (simulating what agents would produce)
    state.add_finding(
        state.pr_metadata.__class__(  # Use same object type
            file_path="src/models/user.py",
            line_number=42,
            finding_type="SQL Injection Vulnerability",
            description="Unsafe string concatenation in database query",
            suggestion="Use parameterized queries with placeholders",
            severity=Severity.CRITICAL,
            agent_id="security",
        )
    )
    
    # Note: We need to import AgentFinding properly
    from code_reviewer.core.state import AgentFinding
    
    state.add_finding(
        AgentFinding(
            file_path="src/models/user.py",
            line_number=42,
            finding_type="SQL Injection Vulnerability",
            description="Unsafe string concatenation in database query",
            suggestion="Use parameterized queries with placeholders",
            severity=Severity.CRITICAL,
            agent_id="security",
        )
    )
    
    state.add_finding(
        AgentFinding(
            file_path="src/models/post.py",
            line_number=15,
            finding_type="High Cyclomatic Complexity",
            description="Method has 8 conditional branches",
            suggestion="Extract conditional logic into helper methods",
            severity=Severity.WARNING,
            agent_id="logic",
        )
    )
    
    state.add_finding(
        AgentFinding(
            file_path="src/models/post.py",
            line_number=30,
            finding_type="Unused Variable",
            description="Variable 'temp_data' is assigned but never used",
            suggestion="Remove unused variable",
            severity=Severity.INFO,
            agent_id="logic",
        )
    )
    
    # Set blocking flag if critical issues
    if state.get_critical_findings():
        state.set_blocked(True)
    
    print(f"\n📊 Sample Findings (before synthesis):")
    print(f"  Total: {len(state.findings)}")
    print(f"  Critical: {len(state.get_critical_findings())}")
    
    # Generate synthesis
    summarizer = SummarizerAgent()
    comment = await summarizer.generate_comment(state)
    
    print(f"\n💬 Generated GitHub Comment:")
    print("-" * 70)
    print(comment)
    print("-" * 70)


async def example_workflow_overview():
    """Example 3: Explain the workflow."""
    print("\n" * 2)
    print("=" * 70)
    print("Example 3: The Blackboard Pattern Workflow")
    print("=" * 70)
    
    print("""
The system follows a three-phase workflow:

PHASE A: PARALLEL ANALYSIS
────────────────────────────
    Input: ReviewState with PR metadata and empty findings list
    
    ┌─────────────────────────────────────────────────┐
    │  Logic Agent                                     │
    │  ├─ Analyzes design patterns                    │
    │  ├─ Checks for SOLID violations                 │
    │  ├─ Detects dead code                           │
    │  └─ Returns: List[AgentFinding]                 │
    └────────────┬────────────────────────────────────┘
                 │
                 └──→ ReviewState (Blackboard)
                       ├─ findings.append(LogicAgent findings)
                       └─ metadata.append(LogicAgent execution time)
    
    ┌─────────────────────────────────────────────────┐
    │  Security Guard Agent                           │
    │  ├─ Scans for hardcoded secrets                 │
    │  ├─ Detects PII leaks                           │
    │  ├─ Identifies OWASP vulnerabilities            │
    │  └─ Returns: List[AgentFinding]                 │
    └────────────┬────────────────────────────────────┘
                 │
                 └──→ ReviewState (Blackboard)
                       ├─ findings.append(Security findings)
                       └─ metadata.append(Security execution time)

Both agents run CONCURRENTLY (not sequentially!)
Time saved: ~50% vs. sequential execution

PHASE B: CRITICAL ISSUE EVALUATION
──────────────────────────────────
    if any(f.severity == CRITICAL for f in findings):
        ReviewState.is_blocked = True

PHASE C: SYNTHESIS
──────────────────
    Input: ReviewState with all accumulated findings
    
    Summarizer Agent:
    1. Deduplicates overlapping findings
    2. Organizes by severity and file
    3. Generates professional Markdown
    4. Returns: Single final_summary string
    
    Output: GitHub-ready comment with clear recommendations

KEY ADVANTAGE: No Context Loss
──────────────────────────────
Original approach:
    Logic Agent → Security Agent → Summarizer
    (Only final output visible to Summarizer)
    ❌ Context loss: Summarizer doesn't know WHY Logic flagged something

Blackboard approach:
    Both agents → Shared ReviewState → Summarizer
    (All original findings preserved)
    ✅ Rich context: Summarizer sees all findings with full context
    ✅ Intelligent deduplication: Can merge findings intelligently
    ✅ Better synthesis: Can explain reasoning to developer
""")


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + " AGENTIC REVIEW GATE - EXAMPLES ".center(68) + "║")
    print("║" + " Blackboard Pattern for Multi-Agent PR Review ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run examples
    await example_direct_review()
    await example_with_custom_findings()
    await example_workflow_overview()
    
    print("\n" * 2)
    print("=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Review the source code in src/code_reviewer/")
    print("  2. Implement LLM integration in the agents")
    print("  3. Set up GitHub webhook integration")
    print("  4. Deploy to production!")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
#   D e b u g   t e s t   0 4 / 1 5 / 2 0 2 6   1 2 : 4 2 : 4 7  
 