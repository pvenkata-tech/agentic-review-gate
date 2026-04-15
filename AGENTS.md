# AGENTS.md

## Cursor Cloud specific instructions

### Overview
This is a Python FastAPI application — a multi-agent PR code review system using the Blackboard pattern. No databases or external services are required for local development/testing (agents use Mock LLM clients by default).

### Key commands
- **Install**: `pip install -e ".[dev,llm]"`
- **Tests**: `python3 -m pytest` (16 tests, all pass without external services)
- **Lint**: `python3 -m ruff check src tests`
- **Format check**: `python3 -m black --check src tests`
- **Type check**: `python3 -m mypy src`
- **Dev server**: `python3 -m uvicorn code_reviewer.main:app --reload --host 0.0.0.0 --port 8000`
- **Health check**: `curl http://localhost:8000/health`

### Caveats
- Linting tools (`black`, `ruff`, `mypy`) are installed into user site-packages and may not be on `PATH`. Use `python3 -m black`, `python3 -m ruff`, `python3 -m mypy` instead of bare commands.
- The `.env` file must exist (copy from `.env.example`). The server starts without real API keys — LLM agents fall back to `MockLLMClient` and rule-based analysis.
- The `/review` REST endpoint requires a valid `GITHUB_TOKEN` to fetch PR diffs from GitHub API. For local testing of the full review pipeline without GitHub, invoke `ReviewCoordinator.review_pr()` directly in Python (see README examples).
- The repo has pre-existing `black` formatting and `ruff` lint warnings that are part of the upstream codebase, not introduced by agents.
