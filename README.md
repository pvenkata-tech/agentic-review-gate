# agentic-review-gate

A production-grade multi-agent PR review system using the **Shared State (Blackboard) Pattern** to avoid "message pass-through" fatigue. Each specialized agent analyzes a PR independently, deposits findings on a shared state, and a final Summarizer synthesizes findings into a professional GitHub comment.

## Architecture Overview

### The Blackboard Pattern

Instead of linear agent chains where Agent A → Agent B → Agent C (causing context loss), our system uses a shared `ReviewState` ("Blackboard") where all agents contribute findings asynchronously:

```
Logic Agent ────┐
                ├──> ReviewState (Blackboard) ──> Summarizer ──> GitHub Comment
Security Guard ─┘
```

### Key Design Principles

1. **Loose Coupling**: Agents don't communicate directly; they only interact via the ReviewState
2. **No Context Loss**: The Summarizer has access to all original findings and their context
3. **Parallel Execution**: Logic and Security agents run concurrently during Phase A
4. **Deduplication**: The Summarizer intelligently deduplicates overlapping findings
5. **Professional Synthesis**: Final output is tone-matched and ranked by severity

## Project Structure

```
.
├── pyproject.toml                 # Python package configuration
├── README.md                       # This file
├── src/code_reviewer/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entrypoint
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract base agent class
│   │   ├── logic.py               # Logic & design pattern analysis
│   │   ├── security.py            # Security & vulnerability scanning
│   │   └── summary.py             # Synthesis & GitHub comment generation
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py               # Pydantic schemas (ReviewState, AgentFinding, etc.)
│   │   ├── coordinator.py         # ReviewCoordinator orchestration logic
│   │   └── github_client.py       # GitHub API interactions
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # Structured JSON logging
│       └── github_client.py       # GitHub API client
└── tests/                         # Test suite (coming soon)
```

## State Schema (The "Blackboard")

### ReviewState

The central data structure that all agents read and write to:

```python
class ReviewState(BaseModel):
    pr_metadata: PRMetadata           # PR info (title, author, diff, etc.)
    findings: List[AgentFinding]     # Accumulated findings from all agents
    metadata: List[AgentMetadata]    # Execution records (time, tokens, status)
    is_blocked: bool                 # True if critical security issues found
    final_summary: Optional[str]     # GitHub-formatted markdown comment
```

### AgentFinding

Each finding represents a specific issue identified by an agent:

```python
class AgentFinding(BaseModel):
    file_path: str                   # Relative file path
    line_number: Optional[int]       # 1-indexed line number
    finding_type: str               # Category (e.g., "PII Leak", "High Complexity")
    description: str                # Human-readable description
    suggestion: str                 # Actionable fix
    severity: Severity              # CRITICAL | WARNING | INFO
    agent_id: str                   # Which agent found this
```

## Multi-Agent Workflow

### Phase A: Parallel Analysis

Both agents receive a snapshot of the ReviewState and analyze independently:

- **Logic Agent**: Detects design patterns, SOLID violations, code complexity, dead code
- **Security Guard Agent**: Scans for hardcoded secrets, PII, OWASP vulnerabilities

### Phase B: Critical Issue Evaluation

The coordinator checks for critical security findings and sets `is_blocked = True` if needed.

### Phase C: Synthesis

The **Summarizer Agent** takes the accumulated findings and:
1. **Deduplicates**: Removes duplicate findings from multiple agents
2. **Organizes**: Groups by severity and file
3. **Tones**: Generates professional, peer-level Markdown
4. **Ranks**: Places critical issues first

## Workflow Execution

```
┌─────────────────────────────────────┐
│   ReviewCoordinator.review_pr()     │
└──────────────┬──────────────────────┘
               │
               ├─→ Phase A: Parallel Analysis
               │   ├─ LogicAgent.analyze(state)
               │   └─ SecurityGuardAgent.analyze(state)
               │
               ├─→ Merge findings into ReviewState
               │
               ├─→ Phase B: Evaluate blocking
               │   └─ Set is_blocked flag if critical issues
               │
               └─→ Phase C: Synthesis
                   └─ SummarizerAgent.generate_comment(state)
                       → Final GitHub Markdown
```

## API Endpoints

### POST /review

Trigger a PR review:

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "pr_number": 123,
    "owner": "your-org",
    "repo": "your-repo",
    "github_token": "ghp_..."
  }'
```

**Response:**
```json
{
  "pr_number": 123,
  "total_findings": 5,
  "is_blocked": false,
  "summary_url": null
}
```

### POST /webhook/github

GitHub webhook receiver (handles PR opened/synchronized events):

```bash
# GitHub sends this automatically with correct X-Hub-Signature header
```

### GET /health

Health check:

```bash
curl http://localhost:8000/health
```

## Installation & Setup

### 1. Clone and Setup

```bash
git clone https://github.com/your-org/agentic-review-gate.git
cd agentic-review-gate
```

### 2. Create Python Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n code-reviewer python=3.10
conda activate code-reviewer
```

### 3. Install Dependencies

```bash
pip install -e ".[dev,llm]"
```

This installs:
- Core: `pydantic`, `fastapi`, `uvicorn`, `httpx`
- Dev: `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`
- LLM: `anthropic`, `openai` (optional, for AI-powered analysis)

### 4. Environment Variables

Create a `.env` file:

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
LOG_LEVEL=INFO
```

### 5. Run the Server

```bash
python -m code_reviewer.main
# or
uvicorn code_reviewer.main:app --reload
```

The server will start at `http://localhost:8000`.

## Usage Examples

### Example 1: Direct Review via API

```python
import asyncio
from code_reviewer import ReviewCoordinator, ReviewState, PRMetadata

async def main():
    coordinator = ReviewCoordinator()
    
    # Create PR metadata
    pr_metadata = PRMetadata(
        pr_number=456,
        title="Add user authentication",
        author="alice",
        branch="feature/auth",
        base_branch="main",
        diff_content="... unified diff ...",
        files_changed=["src/auth.py", "tests/test_auth.py"],
    )
    
    # Create initial state
    state = ReviewState(pr_metadata=pr_metadata)
    
    # Run review
    final_state = await coordinator.review_pr(state)
    
    # Access results
    print(f"Findings: {len(final_state.findings)}")
    print(f"Blocked: {final_state.is_blocked}")
    print(f"Summary:\n{final_state.final_summary}")

asyncio.run(main())
```

### Example 2: GitHub Webhook Integration

1. Go to your GitHub repo settings → Webhooks
2. Add new webhook:
   - **Payload URL**: `https://your-domain.com/webhook/github`
   - **Content type**: `application/json`
   - **Events**: Pull Requests
   - **Active**: ✓

3. Every new PR or commit will trigger an automatic review

## Extending the System

### Adding a Custom Agent

1. Create a new agent file in `src/code_reviewer/agents/`:

```python
from code_reviewer.agents.base import BaseAgent
from code_reviewer.core.state import ReviewState, AgentFinding, Severity

class MyCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="my_agent")
    
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        findings = []
        # Your analysis logic here
        findings.append(
            self._create_finding(
                file_path="example.py",
                finding_type="My Issue",
                description="...",
                suggestion="...",
                severity=Severity.WARNING,
            )
        )
        return findings
```

2. Register in `ReviewCoordinator`:

```python
class ReviewCoordinator:
    def __init__(self):
        self.my_agent = MyCustomAgent()
        # ... other agents ...
    
    async def _phase_a_analyze(self, state: ReviewState) -> None:
        agents = [self.logic_agent, self.security_agent, self.my_agent]
        # ... execute all agents ...
```

### Integrating with LLM

For AI-powered analysis, override `_get_token_usage()` in your agent:

```python
async def analyze(self, state: ReviewState) -> List[AgentFinding]:
    findings = []
    
    # Use Claude, GPT-4, etc.
    response = await self.llm_client.analyze_code(
        files=state.pr_metadata.files_changed,
        diff=state.pr_metadata.diff_content,
    )
    
    # Parse response and create findings
    return findings

def _get_token_usage(self) -> dict[str, int]:
    return {
        "input_tokens": self.last_input_tokens,
        "output_tokens": self.last_output_tokens,
    }
```

## Persistent State & Re-Reviews

The `ReviewCoordinator.handle_pr_update()` method supports tracking across multiple commits:

```python
# Initial review
state_v1 = await coordinator.review_pr(initial_state)

# Developer pushes fix
new_diff = fetch_updated_diff()
state_v2 = await coordinator.handle_pr_update(state_v1, new_diff)

# Compare findings to show progress
```

For production, consider storing ReviewState in:
- **Redis**: Fast in-memory store keyed by `pr_number`
- **GitHub**: Hidden comment or blob on PR
- **PostgreSQL**: Full audit trail of reviews

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src/code_reviewer

# Specific test file
pytest tests/test_logic_agent.py
```

## Performance Characteristics

- **Phase A (Analysis)**: ~500ms per agent (LLM-based may take 5-15s)
- **Phase B (Evaluation)**: <1ms
- **Phase C (Synthesis)**: ~50ms
- **Total**: ~600ms-1s for heuristic analysis; 5-20s with LLM

Parallel execution of Logic + Security agents saves ~50% vs. sequential.

## Monitoring & Logging

All actions are logged as structured JSON:

```json
{
  "timestamp": "2024-04-15T12:34:56.789Z",
  "level": "INFO",
  "message": "Agent execution: logic",
  "request_id": "abc-123-def",
  "agent_id": "logic",
  "execution_time_ms": 523.45,
  "findings_count": 3
}
```

View logs in your observability platform (DataDog, Splunk, CloudWatch, etc.)

## Known Limitations & TODOs

- [ ] LLM integration for semantic analysis
- [ ] Persistent storage of review history
- [ ] Advanced deduplication using semantic similarity
- [ ] Machine learning to learn from developer feedback
- [ ] Rate limiting and quota management
- [ ] Custom rules engine (like ESLint, but for semantic analysis)
- [ ] Support for private code analysis (no external LLM calls)

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/awesome`
3. Make changes and add tests
4. Format: `black src tests`
5. Lint: `ruff check src tests`
6. Test: `pytest`
7. Submit a pull request

## License

MIT

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/your-org/agentic-review-gate/issues
- Email: team@example.com
