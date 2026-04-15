# Contributing to Agentic Code Reviewer

## Pull Request Guidelines

### PR Size & Scope

**Follow the Single Responsibility Principle at the PR level:**

Each PR should address ONE concern. Avoid large PRs that mix multiple independent changes.

**Recommended PR breakdown:**

1. **Infrastructure PRs** (Testing, Configuration)
   - Files: `tests/`, `TESTING.md`, `pytest.ini`, `.github/workflows/`
   - Example title: `test: Add webhook integration tests`

2. **Core Feature PRs** (Agent Logic, Coordinator)
   - Files: `agents/`, `core/coordinator.py`, `core/interfaces.py`
   - Example title: `feat: Implement security analysis agent with pattern matching`

3. **Utility PRs** (GitHub Client, Diff Parser, Cache)
   - Files: `utils/`, `core/interfaces.py`
   - Example title: `fix: Improve GitHub API diff retrieval with proper headers`

4. **Architecture PRs** (Interfaces, Patterns, Refactoring)
   - Files: `core/interfaces.py`, dependency injection changes
   - Example title: `arch: Add dependency inversion interfaces for testability`

**Benefits:**
- ✅ Easier to review thoroughly
- ✅ Reduces risk of introducing bugs
- ✅ Clearer git history for bisecting issues
- ✅ Simpler to revert if needed
- ✅ Enables parallel review and merging

### PR Title Format

Use the format: `[type]: [scope] - [description]`

Examples:
```
fix: GitHub API diff retrieval - handle empty responses gracefully
feat: Logic agent - add SOLID principle violation detection
test: Webhook integration - add PR comment validation tests
arch: Dependency inversion - introduce abstraction interfaces
docs: Contributing guide - clarify PR structure expectations
refactor: Agent base - extract common logging patterns
perf: Diff parser - optimize hunk iteration performance
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `test`: Test additions/improvements
- `arch`: Architectural changes
- `refactor`: Code restructuring
- `perf`: Performance improvements
- `docs`: Documentation
- `ci`: CI/CD configuration

## Architecture Principles

### Dependency Inversion

High-level modules should NOT depend on low-level implementation details.

**Bad:**
```python
class LogicAgent:
    def __init__(self):
        self.github = GitHubClient()  # Concrete dependency
        self.llm = get_llm_client()    # Function dependency
```

**Good:**
```python
from core.interfaces import GitHubAPIClient, LLMClient

class LogicAgent:
    def __init__(self, github: GitHubAPIClient, llm: LLMClient):
        self.github = github
        self.llm = llm
```

### Strategy Pattern for Agents

Agents should use consistent interface for different analysis strategies.

**All agents must implement:**
```python
from typing import List
from core.state import ReviewState
from base import AgentFinding

class AnalysisAgent:
    async def analyze(self, state: ReviewState) -> List[AgentFinding]:
        """Analyze PR and return findings."""
        ...
```

### Observer/Event Pattern for Webhooks

Webhook handling should be decoupled from review execution.

**Current pattern:**
```
WebhookHandler → ReviewRequest → BackgroundTask → ReviewCoordinator
```

Maintains separation of concerns:
- WebhookHandler: Validates and parses GitHub events
- ReviewRequest: Data transfer object
- BackgroundTask: Async execution management  
- ReviewCoordinator: Orchestrates agent analysis

## Code Organization

### Module Responsibilities

```
src/code_reviewer/
├── agents/           # Analysis agents (Strategy pattern)
│   ├── base.py       # Base agent interface
│   ├── logic.py      # Code quality analysis
│   └── security.py   # Security vulnerability detection
├── core/             # Core abstractions and coordination
│   ├── interfaces.py # Dependency inversion protocols
│   ├── coordinator.py # Agent orchestration
│   └── state.py      # Shared state model
├── llm/              # LLM provider implementations
│   └── client.py     # Claude/OpenAI clients
├── prompts/          # Agent prompts and templates
│   └── __init__.py   # Prompt definitions
└── utils/            # Utilities (GitHub, diff parsing, logging)
    ├── github_client.py
    ├── diff_parser.py
    ├── cache.py
    ├── logger.py
    └── webhooks.py
```

### When to Extract Into New Module

Move code when:
- ✅ It has a single, clear responsibility
- ✅ It could be tested independently
- ✅ It might be reused elsewhere
- ✅ It has multiple classes/functions (>300 LOC)

Don't extract prematurely:
- ❌ Avoid micro-modules for single functions
- ❌ Don't split code that's always used together
- ❌ Wait until you see the pattern (rule of three)

## Testing Strategy

### Unit Tests
- Test individual agents with mocked dependencies
- Test diff parser edge cases
- Test cache operations

### Integration Tests
- End-to-end webhook processing
- GitHub API interactions (with token)
- Agent analysis with real diffs

### Webhook Tests
- Manual testing with ngrok tunnel
- Verify comment posting
- Monitor performance with large PRs

See [TESTING.md](TESTING.md) for detailed testing procedures.

## Code Review Checklist

When reviewing PRs, verify:

- [ ] Single Responsibility Principle: Does PR address one concern?
- [ ] Architecture: Are high-level modules free of low-level dependencies?
- [ ] Testing: Are critical changes covered by tests?
- [ ] Documentation: Is PR title clear and specific?
- [ ] Logging: Are important operations logged for debugging?
- [ ] Error Handling: Are error cases handled gracefully?

## Commit Message Guidelines

Write clear, descriptive commit messages:

```
[type]: [scope] - [description]

[Extended explanation if needed]

Related issues: #123, #456
```

Examples:
```
fix: GitHub client - use correct Accept header for diff retrieval

The v3.diff format was deprecated. Updated to use modern GitHub API
header format (application/vnd.github.diff) which returns diffs 
consistently across API versions.

Fixes: Diff content showing as empty in PR reviews
```

## Performance Considerations

### Agent Execution Time
- Target: < 30 seconds per PR analysis
- Profile with: `time_execution()` decorator in logger
- Optimize before: > 60 seconds per PR

### GitHub API Rate Limits  
- Get PR info: 1 call
- Get PR diff: 1 call
- Post comment: 1 call
- Total: 3 calls per PR (safe within 5000/hour limit)

### Memory Usage
- Diff content: Usually < 1MB
- Cache: In-memory by default (suitable for small deployments)
- Consider Redis for production (> 100 PRs/day)

## Release Checklist

Before releasing a new version:

- [ ] All tests passing
- [ ] CHANGELOG updated
- [ ] Version bumped (pyproject.toml)
- [ ] README accurate
- [ ] Security issues addressed
- [ ] Performance benchmarks reviewed
