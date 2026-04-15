# Code Reviewer - Testing Guide

## Overview

This document describes how to test the agentic code review system with proper setup, execution, and validation procedures.

## Testing Scenarios

### 1. Unit Tests

**Directory**: `tests/`

Run unit tests for core components:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_core.py -v

# Run with coverage
pytest tests/ --cov=src/code_reviewer
```

**Test Coverage**:
- Diff parser validation and edge cases
- Agent analysis logic and decision trees
- Cache backend operations
- GitHub client integration

### 2. Integration Tests

**Setup Required**:
1. GitHub token in `.env` (`GITHUB_TOKEN`)
2. ngrok tunnel running on port 8000
3. GitHub webhook configured to point to ngrok URL

**Test Steps**:
```bash
# Start dev server
./dev-server.ps1

# In another terminal, start ngrok
ngrok http 8000

# Create a test PR
git checkout -b test-feature
echo "test code" > test.py
git add test.py
git commit -m "feat: Test feature"
git push origin test-feature

# Create PR on GitHub and monitor bot response
```

### 3. Webhook Testing

**Prerequisites**:
- GitHub webhook configured in repo settings
- Dev server running on localhost:8000
- ngrok tunnel active pointing to webhook endpoint

**Webhook Test Flow**:

1. **Create Test PR**
   - Push branch: `git push origin test-branch`
   - Create PR on GitHub
   - Observe GitHub webhook event in logs

2. **Monitor Webhook Processing**
   - Check dev server logs for: `"GitHub webhook accepted for PR review"`
   - Verify diff retrieval: `"PR diff received: X characters"`
   - Confirm parsing: `"DiffParser: Extracted X files"`
   - Check agent analysis: `"Agent analysis complete"`

3. **Validate Code Review Comment**
   - Bot should post comment with findings
   - Comment should contain:
     - Code quality issues (from logic agent)
     - Security concerns (from security agent)
     - Summary of findings

**Debug Webhook Issues**:

```bash
# Check webhook configuration
# Go to: https://github.com/[owner]/[repo]/settings/hooks
# Verify: webhook URL, secret, and event types

# View webhook deliveries
# GitHub UI: Settings > Webhooks > Recent Deliveries
# Check Response section for error messages

# Monitor logs for common issues
# - "Webhook signature validation failed" → Check GITHUB_WEBHOOK_SECRET
# - "PR diff is empty!" → GitHub API returned no content
# - "DiffParser: Extracted 0 files" → Diff format not recognized
```

### 4. Diff Extraction Testing

**Purpose**: Verify that code diffs are correctly extracted and parsed

**Test Cases**:

1. **Simple File Changes**
   - Add a Python file with actual code
   - Verify bot identifies code quality issues
   - Confirm diff shows in analysis logs

2. **Multiple Files**
   - Modify 3+ files in single commit
   - Verify all files are parsed and analyzed
   - Check hunk extraction is correct

3. **Edge Cases**
   - Binary files (should be skipped)
   - Whitespace-only changes (should be noted)
   - Large diffs (>10MB - may be truncated)
   - Renamed files (should parse correctly)

**Validation Checklist**:
- [ ] Diff received by GitHub API
- [ ] Diff parsed into FileDiff objects
- [ ] Hunks extracted correctly
- [ ] Agents receive formatted diff_text
- [ ] LLM analysis includes code snippets
- [ ] GitHub comment shows actual findings

## Debugging Guide

### Enable Debug Logging

Set environment variable:
```bash
export LOG_LEVEL=DEBUG
# or in .env
LOG_LEVEL=DEBUG
```

### Key Log Messages to Watch

```
# Successful flow
[github_client] Fetching PR diff from: https://api.github.com/...
[github_client] Successfully fetched PR diff: 5024 characters
[diff_parser] Processing 42 lines from diff
[diff_parser] Extracted 3 files from diff
[logic_agent] Parsed 3 files from diff
[security_agent] Formatted diff_text: 2048 chars
[main] Completed PR review #7

# Problem indicators
[github_client] PR diff is empty!
[diff_parser] Diff does not start with 'diff --git'
[logic_agent] Received diff_content: 0 chars (should be > 0)
[agents] Unable to analyze code changes
```

### Troubleshooting Steps

**Problem**: Webhook not received
1. Verify ngrok is running: `ngrok http 8000`
2. Check GitHub webhook settings for URL and secret
3. Review webhook delivery logs on GitHub
4. Ensure firewall allows incoming connections

**Problem**: Diff is empty
1. Check GitHub token has repo access
2. Verify Accept header in GitHub client
3. Review GitHub API response in logs
4. Test manually: `curl -H "Authorization: token $TOKEN" https://api.github.com/.../pulls/1 -H "Accept: application/vnd.github.diff"`

**Problem**: Agents not analyzing
1. Verify diff_content is non-empty in logs
2. Check if LLM_LOGIC/LLM_SECURITY are enabled
3. Review LLM client initialization
4. Check for API rate limiting errors

## Agent Architecture

### Design Patterns

The system uses multiple design patterns for extensibility and maintainability:

**1. Strategy Pattern (Agents)**
- Each agent implements the `AnalysisAgent` interface from `core/interfaces.py`
- Different analysis strategies: `LogicAgent`, `SecurityGuardAgent`
- New agents can be added without modifying existing code (Open/Closed Principle)

**2. Blackboard Pattern (State)**
- `ReviewState` acts as a shared blackboard
- Agents deposit findings without direct inter-agent communication
- `ReviewCoordinator` synthesizes findings at the end
- Reduces coupling and allows parallel agent execution

**3. Dependency Inversion Principle**
- High-level modules depend on abstractions (`core/interfaces.py`)
- Low-level modules (`utils/`) implement the abstractions
- Makes system testable with mock implementations

### Agent Implementation

All agents follow this structure:

1. **Inherit from `BaseAgent`** (ABC - Abstract Base Class)
   ```python
   from agents.base import BaseAgent
   from core.state import ReviewState, AgentFinding
   
   class LogicAgent(BaseAgent):
       async def analyze(self, state: ReviewState) -> List[AgentFinding]:
           # Analysis implementation
           return findings
   ```

2. **Follow the interface contract**
   - Accept `ReviewState` parameter (blackboard snapshot)
   - Return `List[AgentFinding]` with metadata
   - Don't modify state directly
   - Include execution timing and metrics

3. **Use consistent severity levels**
   ```python
   from core.state import Severity
   
   finding = AgentFinding(
       agent_id="logic",
       category="Design Pattern Violation",
       message="Single Responsibility Principle violated",
       severity=Severity.WARNING,  # CRITICAL, WARNING, INFO
       file_path="src/module.py",
       line_number=42
   )
   ```

### Adding New Agents

To extend with a new agent (e.g., `PerformanceAgent`):

1. Create `src/code_reviewer/agents/performance.py`
2. Inherit from `BaseAgent`
3. Implement `analyze()` method
4. Register in `ReviewCoordinator`

```python
# agents/performance.py
class PerformanceAgent(BaseAgent):
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        findings = []
        # Analyze for performance antipatterns
        return findings

# core/coordinator.py - add to agents list
agents = [
    LogicAgent(llm),
    SecurityGuardAgent(llm),
    PerformanceAgent(),  # New agent
]
```

### Testing Agents in Isolation

**Unit Test Template**:
```python
import pytest
from core.state import ReviewState, Severity
from agents.logic import LogicAgent

@pytest.mark.asyncio
async def test_logic_agent_detects_solid_violation():
    # Use rule-based mode (no LLM) for deterministic testing
    agent = LogicAgent(use_llm=False)
    state = ReviewState(
        pr_number=1,
        title="Test PR",
        diff_text="def violating_class():\n    # Too many responsibilities",
    )
    
    findings = await agent.analyze(state)
    
    assert len(findings) > 0
    assert any(f.severity == Severity.WARNING for f in findings)
```

## Performance Testing

**Large PR Handling**:
- Test with 50+ file changes
- Verify diff doesn't exceed token limits
- Monitor agent execution time
- Check comment posting doesn't timeout

**Concurrent Webhooks**:
- Multiple PRs triggering simultaneously
- Verify background tasks don't interfere
- Check cache doesn't cause race conditions
