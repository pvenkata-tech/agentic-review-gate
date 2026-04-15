# LLM Integration Guide

This guide explains how to integrate Large Language Models (Claude, GPT-4, etc.) into the agentic-review-gate system for enhanced code analysis.

## Overview

By default, the agents use heuristic-based analysis (pattern matching, static rules). For more sophisticated analysis, you can integrate LLMs that understand code semantics and can reason about design patterns, security implications, and code quality.

## Architecture

```
PR Diff
   │
   ├─→ Logic Agent
   │   ├─ (Local heuristics)
   │   └─ (LLM for semantic analysis) ←── Claude/GPT-4
   │
   ├─→ Security Guard Agent
   │   ├─ (Regex patterns)
   │   └─ (LLM for vulnerability reasoning) ←── Claude/GPT-4
   │
   └─→ Summarizer
       └─ (Generate professional output)
```

## Implementation Examples

### Option 1: Using Anthropic's Claude

#### Step 1: Install Claude SDK

```bash
pip install anthropic>=0.7.0
```

#### Step 2: Create an LLM-based Agent

```python
# src/code_reviewer/agents/logic_llm.py

import asyncio
from anthropic import Anthropic
from code_reviewer.agents.base import BaseAgent
from code_reviewer.core.state import ReviewState, AgentFinding, Severity


class LLMLogicAgent(BaseAgent):
    """Logic agent powered by Claude."""
    
    def __init__(self, api_key: str = None):
        super().__init__(agent_id="logic_llm")
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-opus-20240229"
        self.last_input_tokens = 0
        self.last_output_tokens = 0
    
    async def analyze(self, state: ReviewState) -> list[AgentFinding]:
        """Use Claude to analyze code logic."""
        findings = []
        
        # Prepare the prompt
        diff = state.pr_metadata.diff_content
        files = state.pr_metadata.files_changed
        
        prompt = f"""Analyze this code pull request for logical and design issues.

FILES CHANGED:
{', '.join(files)}

DIFF:
{diff[:4000]}  # Truncate for token limits

Please identify:
1. Design pattern violations
2. SOLID principle violations (Single Responsibility, Open/Closed, etc.)
3. Code complexity issues
4. Dead code or unused variables
5. Architectural concerns

For each issue, provide:
- File path and line number (if visible in diff)
- Clear description
- Actionable suggestion

Format as JSON array:
[
  {{
    "file": "path/to/file.py",
    "line": 42,
    "type": "Description of issue",
    "suggestion": "How to fix it"
  }}
]

Return ONLY valid JSON, no other text."""
        
        try:
            # Call Claude API
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                )
            )
            
            # Track token usage
            self.last_input_tokens = response.usage.input_tokens
            self.last_output_tokens = response.usage.output_tokens
            
            # Parse response
            response_text = response.content[0].text
            
            # Extract JSON from response
            import json
            import re
            
            # Find JSON array in response
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                issues = json.loads(match.group())
                
                for issue in issues:
                    findings.append(
                        self._create_finding(
                            file_path=issue.get("file", "unknown"),
                            finding_type=issue.get("type", "Code Issue"),
                            description=issue.get("type", ""),
                            suggestion=issue.get("suggestion", ""),
                            severity=Severity.WARNING,
                            line_number=issue.get("line"),
                        )
                    )
        
        except Exception as e:
            print(f"Claude API error: {str(e)}")
            # Graceful fallback to heuristics
        
        return findings
    
    def _get_token_usage(self) -> dict[str, int]:
        return {
            "input_tokens": self.last_input_tokens,
            "output_tokens": self.last_output_tokens,
        }
```

#### Step 3: Use in Coordinator

```python
# src/code_reviewer/core/coordinator.py

from code_reviewer.agents.logic_llm import LLMLogicAgent

class ReviewCoordinator:
    def __init__(self, use_llm: bool = True):
        if use_llm:
            self.logic_agent = LLMLogicAgent(api_key=os.getenv("ANTHROPIC_API_KEY"))
        else:
            self.logic_agent = LogicAgent()  # Fallback to heuristics
        
        # ... other agents ...
```

### Option 2: Using OpenAI's GPT-4

```python
# src/code_reviewer/agents/security_llm.py

import asyncio
from openai import AsyncOpenAI
from code_reviewer.agents.base import BaseAgent
from code_reviewer.core.state import ReviewState, AgentFinding, Severity


class LLMSecurityAgent(BaseAgent):
    """Security agent powered by GPT-4."""
    
    def __init__(self, api_key: str = None):
        super().__init__(agent_id="security_llm")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4"
        self.last_input_tokens = 0
        self.last_output_tokens = 0
    
    async def analyze(self, state: ReviewState) -> list[AgentFinding]:
        """Use GPT-4 to analyze security issues."""
        findings = []
        
        diff = state.pr_metadata.diff_content
        
        prompt = f"""Analyze this code for security vulnerabilities.

DIFF:
{diff[:6000]}

Identify:
1. Hardcoded secrets or credentials
2. PII (Personally Identifiable Information) exposure
3. SQL injection vulnerabilities
4. XSS vulnerabilities
5. Insecure cryptography
6. Authentication/authorization issues
7. Data exposure risks

Return JSON array with findings."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security expert analyzing code for vulnerabilities.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=2048,
            )
            
            # Track usage
            self.last_input_tokens = response.usage.prompt_tokens
            self.last_output_tokens = response.usage.completion_tokens
            
            # Parse and convert to findings
            response_text = response.choices[0].message.content
            
            # ... parse JSON and create findings ...
        
        except Exception as e:
            print(f"GPT-4 API error: {str(e)}")
        
        return findings
```

### Option 3: Hybrid Approach (Local + LLM)

Combine heuristics with LLM for best results:

```python
class HybridLogicAgent(BaseAgent):
    """Combines heuristic and LLM analysis."""
    
    def __init__(self):
        super().__init__(agent_id="logic_hybrid")
        self.client = Anthropic()
    
    async def analyze(self, state: ReviewState) -> list[AgentFinding]:
        findings = []
        
        # Step 1: Run local heuristics (fast)
        heuristic_findings = await self._heuristic_analysis(state)
        findings.extend(heuristic_findings)
        
        # Step 2: Run LLM on specific patterns (focused)
        if any(self._needs_llm_analysis(f) for f in heuristic_findings):
            llm_findings = await self._llm_analysis(state)
            findings.extend(llm_findings)
        
        return findings
    
    def _needs_llm_analysis(self, finding: AgentFinding) -> bool:
        """Determine if a finding needs deeper LLM analysis."""
        # Only deep-dive on complex findings
        return finding.severity in [Severity.WARNING, Severity.CRITICAL]
```

## Prompt Engineering Best Practices

### 1. Context Window Management

LLMs have limited token budgets. For large PRs:

```python
def truncate_diff(diff: str, max_tokens: int = 8000) -> str:
    """Truncate diff to fit within token budget."""
    lines = diff.split('\n')
    current_tokens = 0
    truncated_lines = []
    
    for line in lines:
        line_tokens = len(line.split()) + 1
        if current_tokens + line_tokens > max_tokens:
            truncated_lines.append("... (truncated)")
            break
        truncated_lines.append(line)
        current_tokens += line_tokens
    
    return '\n'.join(truncated_lines)
```

### 2. Temperature & Sampling

```python
# For analysis (consistency)
response = client.messages.create(
    model="claude-3-opus-20240229",
    temperature=0.2,  # Low = consistent, deterministic
    max_tokens=2048,
    messages=[...],
)

# For creative suggestions (diversity)
response = client.messages.create(
    model="claude-3-opus-20240229",
    temperature=0.7,  # Higher = more creative
    max_tokens=1024,
    messages=[...],
)
```

### 3. Chain-of-Thought Prompting

For complex analysis:

```python
prompt = """Analyze this code step-by-step:

1. First, identify what the code is trying to do.
2. Then, check for common security vulnerabilities.
3. Finally, suggest improvements.

Diff:
...

Provide your analysis in JSON format."""
```

### 4. Few-Shot Examples

```python
prompt = """You are a code reviewer. Analyze code and return findings in this format:

EXAMPLE:
Code: config_value = "<example_config_placeholder>"
Finding: {"type": "Hardcoded Secret", "suggestion": "Move to environment variable"}

Now analyze this code:
{diff}

Return findings as JSON array."""
```

## Cost Optimization

### 1. Caching Responses

```python
import hashlib
import json
from datetime import datetime, timedelta

class LLMCache:
    def __init__(self, ttl_hours: int = 24):
        self.cache = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def get_cache_key(self, diff: str, agent_id: str) -> str:
        content = f"{diff}:{agent_id}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, diff: str, agent_id: str) -> Optional[list]:
        key = self.get_cache_key(diff, agent_id)
        if key in self.cache:
            findings, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return findings
        return None
    
    def set(self, diff: str, agent_id: str, findings: list) -> None:
        key = self.get_cache_key(diff, agent_id)
        self.cache[key] = (findings, datetime.now())
```

Use it in agents:

```python
async def analyze(self, state: ReviewState) -> list[AgentFinding]:
    cache_key = hashlib.md5(
        state.pr_metadata.diff_content.encode()
    ).hexdigest()
    
    # Check cache
    cached = await self.cache.get(state.pr_metadata.diff_content, self.agent_id)
    if cached:
        return cached
    
    # Call LLM
    findings = await self._call_llm(state)
    
    # Store in cache
    await self.cache.set(state.pr_metadata.diff_content, self.agent_id, findings)
    
    return findings
```

### 2. Token Budget Management

```python
class TokenBudget:
    def __init__(self, monthly_budget: int = 1_000_000):
        self.monthly_budget = monthly_budget
        self.tokens_used = 0
    
    def can_afford(self, tokens: int) -> bool:
        return self.tokens_used + tokens <= self.monthly_budget
    
    def charge(self, tokens: int) -> None:
        self.tokens_used += tokens
    
    def remaining(self) -> int:
        return self.monthly_budget - self.tokens_used

# In coordinator
budget = TokenBudget(monthly_budget=1_000_000)

async def _phase_a_analyze(self, state: ReviewState):
    for agent in [self.logic_agent, self.security_agent]:
        if hasattr(agent, 'estimate_tokens'):
            est_tokens = agent.estimate_tokens(state)
            if not budget.can_afford(est_tokens):
                print(f"Token budget exceeded. Using heuristics only.")
                continue
        
        findings, metadata = await agent.execute(state)
        if metadata.token_usage:
            budget.charge(
                metadata.token_usage.get('input_tokens', 0) +
                metadata.token_usage.get('output_tokens', 0)
            )
        state.add_finding(findings)
        state.add_metadata(metadata)
```

## Environment Setup

### 1. Create `.env` file

```env
# Anthropic
ANTHROPIC_API_KEY=<your_anthropic_api_key>

# OpenAI
OPENAI_API_KEY=<your_openai_api_key>

# Other
GITHUB_TOKEN=<your_github_token>
LOG_LEVEL=INFO

# Feature flags
USE_LLM_LOGIC=true
USE_LLM_SECURITY=true
HYBRID_MODE=true
```

### 2. Load in coordinator

```python
# src/code_reviewer/core/coordinator.py

import os
from dotenv import load_dotenv

load_dotenv()

class ReviewCoordinator:
    def __init__(self):
        use_llm = os.getenv("USE_LLM_LOGIC", "true").lower() == "true"
        
        if use_llm:
            self.logic_agent = LLMLogicAgent()
        else:
            self.logic_agent = LogicAgent()
        
        # ... other agents ...
```

## Testing LLM Integration

```python
import pytest

@pytest.mark.asyncio
async def test_llm_agent_analysis():
    """Test LLM agent produces valid findings."""
    agent = LLMLogicAgent()
    
    pr_metadata = PRMetadata(
        pr_number=1,
        title="Test",
        author="test",
        branch="test",
        diff_content="""
+def get_user(username):
+    query = "SELECT * FROM users WHERE name = '" + username + "'"
+    return db.execute(query)
""",
        files_changed=["app.py"],
    )
    
    state = ReviewState(pr_metadata=pr_metadata)
    findings = await agent.analyze(state)
    
    # Verify findings structure
    assert isinstance(findings, list)
    if findings:
        for finding in findings:
            assert finding.file_path
            assert finding.finding_type
            assert finding.suggestion
```

## Monitoring LLM Costs

Track API usage:

```python
# src/code_reviewer/utils/cost_tracker.py

class CostTracker:
    # Pricing (USD per 1M tokens)
    CLAUDE_INPUT = 3.00
    CLAUDE_OUTPUT = 15.00
    GPT4_INPUT = 3.00
    GPT4_OUTPUT = 6.00
    
    def calculate_cost(self, agent_id: str, input_tokens: int, output_tokens: int) -> float:
        if "claude" in agent_id:
            return (input_tokens * self.CLAUDE_INPUT + output_tokens * self.CLAUDE_OUTPUT) / 1_000_000
        elif "gpt" in agent_id:
            return (input_tokens * self.GPT4_INPUT + output_tokens * self.GPT4_OUTPUT) / 1_000_000
        return 0.0

# Use in coordinator
cost_tracker = CostTracker()

for metadata in final_state.metadata:
    if metadata.token_usage:
        cost = cost_tracker.calculate_cost(
            metadata.agent_id,
            metadata.token_usage.get('input_tokens', 0),
            metadata.token_usage.get('output_tokens', 0),
        )
        print(f"Agent {metadata.agent_id}: ${cost:.4f}")
```

## Comparison: Heuristics vs. LLM

| Aspect | Heuristics | LLM |
|--------|-----------|-----|
| Speed | Fast (< 1s) | Slow (3-10s) |
| Cost | Free | $0.01-$0.10 per PR |
| Accuracy | 70-80% | 85-95% |
| Coverage | Limited patterns | Semantic understanding |
| False Positives | Medium | Low |
| Explainability | High | Medium |
| Customization | Hard | Easy |

## Recommendation

**Hybrid approach** for production:
1. Use heuristics for basic security (secrets, patterns)
2. Use LLM for complex analysis (design, logic)
3. Cache results for identical diffs
4. Set token budgets to control costs
5. Monitor costs and adjust accordingly

This gives you 90%+ accuracy at reasonable cost.
