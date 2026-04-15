# Tests Directory - Consolidated Test Suite

This directory contains the consolidated test suite for agentic-review-gate.

## File Organization

### Core Test Files

**test_core.py** - Unit tests for core system components
- ReviewState (Blackboard) tests
- Agent implementation tests
- Coordinator workflow tests
- Webhook validation tests
- LLM integration tests

```bash
pytest tests/test_core.py -v
```

**test_agents_e2e.py** - End-to-end agent testing
- Full multi-agent workflow
- Parallel agent execution
- Finding deduplication
- Comment generation
- Status check creation

```bash
pytest tests/test_agents_e2e.py -v
```

### Testing Tools

**test_utils.py** - Shared utilities for all tests
- ANSI color helpers (print_success, print_error, etc.)
- GitHub configuration helpers
- Environment variable loading

Used by other test scripts for consistent output and configuration.

**examples.py** - Interactive examples and integration tests
- Direct PR review testing
- Webhook trigger demonstration
- Findings explanation
- Multi-phase workflow overview

```bash
# Run all examples
python tests/examples.py

# Test direct review of a PR
python tests/examples.py direct --pr-number 15

# Show specific example
python tests/examples.py webhook    # Webhook flow
python tests/examples.py findings   # Finding structure
python tests/examples.py workflow   # Multi-phase architecture
```

**diagnose.py** - Comprehensive diagnostic tool
- GitHub API authentication verification
- Server health checks
- PR metadata and file retrieval testing
- Status check validation
- Webhook delivery verification

```bash
# Run all diagnostics
python tests/diagnose.py

# Check specific PR
python tests/diagnose.py --pr-number 15

# Run specific check
python tests/diagnose.py --check token
python tests/diagnose.py --check server
python tests/diagnose.py --check pr --pr-number 15
python tests/diagnose.py --check status --pr-number 15
python tests/diagnose.py --check merged
```

## Running Tests

### Run All Unit Tests

```bash
pytest tests/ -v
```

### Run Specific Test Class

```bash
pytest tests/test_core.py::TestReviewState -v
pytest tests/test_core.py::TestAgents -v
pytest tests/test_core.py::TestLLMIntegration -v
```

### Run with Coverage

```bash
pytest tests/ --cov=src/code_reviewer --cov-report=html
```

### Run Tests Matching Pattern

```bash
pytest tests/ -k "webhook" -v
pytest tests/ -k "agent" -v
```

## Integration Testing Workflow

### Step 1: Unit Tests

```bash
pytest tests/test_core.py -v
```

### Step 2: Run Diagnostics

```bash
python tests/diagnose.py
```

All checks should pass with ✓.

### Step 3: Direct PR Review Test

```bash
python tests/examples.py direct --pr-number 15
```

Should complete in 10-40 seconds with findings reported.

### Step 4: End-to-End Test

```bash
pytest tests/test_agents_e2e.py -v
```

Tests full agent coordination workflow.

### Step 5: Webhook Testing (if configured)

```bash
# Local webhook simulation (no public URL needed)
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --pr-number 15
```

## Configuration

All tests use `.env` for configuration:

```env
GITHUB_TOKEN=ghp_xxxx              # Required
GITHUB_WEBHOOK_SECRET=your_secret  # For webhook tests
ANTHROPIC_API_KEY=sk-ant-xxxx      # For LLM tests (optional)
LOG_LEVEL=INFO                      # Debug logging: DEBUG
```

## Expected Test Results

### Successful Test Suite Run

```
tests/test_core.py::TestReviewState::test_create_state PASSED
tests/test_core.py::TestReviewState::test_add_finding PASSED
tests/test_core.py::TestAgents::test_logic_agent PASSED
tests/test_core.py::TestAgents::test_security_agent PASSED
tests/test_agents_e2e.py::test_full_workflow PASSED

========================== 5 passed in 2.34s ==========================
```

### Successful Diagnostics Run

```
✓ GitHub Token ............................................. ✓ PASS
✓ Server Health ............................................ ✓ PASS
✓ Recently Merged PRs ...................................... ✓ PASS

============================================================
All diagnostics passed!
```

### Successful Direct Review Test

```
✓ Review completed successfully!

Results:
  Total Findings: 2
  Is Blocked: True
  Status Check: Created

Check PR: https://github.com/owner/repo/pull/15
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'code_reviewer'"

Add project to Python path:
```bash
# From project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/
```

Or run with module import:
```bash
python -m pytest tests/
```

### "GITHUB_TOKEN not set"

```bash
# Load environment from .env
export $(cat .env | xargs)
pytest tests/
```

Or set directly:
```bash
export GITHUB_TOKEN=ghp_xxxx
pytest tests/
```

### "Cannot connect to http://localhost:8000"

Start the development server first:
```bash
# Terminal 1
python -m uvicorn src.code_reviewer.main:app --host 127.0.0.1 --port 8000

# Terminal 2 - run tests
python tests/examples.py direct --pr-number 15
```

### Tests Timeout

Increase timeout:
```bash
# Run with longer timeout
pytest tests/ --timeout=300 -v
```

Or set in pytest.ini:
```ini
[pytest]
timeout = 300
```

## Adding New Tests

Create test in appropriate file:

```python
# tests/test_core.py or tests/test_agents_e2e.py

import pytest
from code_reviewer.core.state import ReviewState

@pytest.mark.asyncio
async def test_my_feature():
    """Test description."""
    # Setup
    state = ReviewState(...)
    
    # Execute
    result = await function(state)
    
    # Assert
    assert result.expected == True
```

Run your new test:
```bash
pytest tests/test_core.py::test_my_feature -v
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ -v
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Next Steps

- [Testing Guide](../docs/TESTING.md) - Comprehensive testing documentation
- [Diagnostics](diagnose.py) - Troubleshoot your setup
- [Examples](examples.py) - See the system in action
