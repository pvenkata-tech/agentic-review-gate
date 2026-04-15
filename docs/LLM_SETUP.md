# LLM Setup and Integration Guide

Complete guide to setting up and integrating Large Language Models for enhanced code analysis.

## Quick Start

### Option 1: Using Claude (Recommended)

Claude 3 Opus provides the best reasoning for code analysis.

```bash
# 1. Get API key from https://console.anthropic.com/

# 2. Set environment variable
export ANTHROPIC_API_KEY=<your_anthropic_api_key>

# 3. Install dependencies
pip install anthropic>=0.7.0

# 4. Start server (LLM will be used automatically)
python -m uvicorn src.code_reviewer.main:app --port 8000
```

### Option 2: Using GPT-4

OpenAI's GPT-4 also works well for code review.

```bash
# 1. Get API key from https://platform.openai.com/api-keys

# 2. Set environment variable
export OPENAI_API_KEY=<your_openai_api_key>

# 3. Install dependencies
pip install openai>=1.0.0

# 4. Start server
python -m uvicorn src.code_reviewer.main:app --port 8000
```

### Option 3: Mock Mode (Development)

For testing without API costs:

```bash
# No API key needed, no installation required
python -m uvicorn src.code_reviewer.main:app --port 8000
```

## Getting API Keys

### Anthropic (Claude)

1. Go to https://console.anthropic.com/
2. Sign up for free account
3. Create API key in account settings
4. Copy key (format: `sk-ant-...`)
5. Add to `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-xxxx
```

**Pricing**: Pay-as-you-go (~$3 per 1M input tokens)

### OpenAI (GPT-4)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create new API key
4. Copy key (format: `sk-...`)
5. Add to `.env`:
```env
OPENAI_API_KEY=sk-xxxx
```

**Pricing**: $0.03 per 1K input tokens (GPT-4)

## Environment Configuration

### Option A: .env File (Recommended)

Create `.env` in project root:

```env
# Choose ONE LLM provider
ANTHROPIC_API_KEY=sk-ant-xxxx    # For Claude
# OPENAI_API_KEY=sk-xxxx          # For GPT-4 (commented out)

# GitHub configuration
GITHUB_TOKEN=ghp_xxxx
GITHUB_WEBHOOK_SECRET=your_secret_here

# Other settings
LOG_LEVEL=INFO
```

### Option B: Environment Variables

**Linux/macOS**:
```bash
export ANTHROPIC_API_KEY=sk-ant-xxxx
export OPENAI_API_KEY=sk-xxxx
export GITHUB_TOKEN=ghp_xxxx
```

**Windows PowerShell**:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-xxxx"
$env:OPENAI_API_KEY = "sk-xxxx"
$env:GITHUB_TOKEN = "ghp_xxxx"
```

### Option C: Configuration File

```python
from code_reviewer.llm import ClaudeClient

client = ClaudeClient(api_key="sk-ant-xxxx")
agent = LogicAgent(llm_client=client)
```

## Provider Comparison

| Aspect | Claude | GPT-4 | Mock |
|--------|--------|-------|------|
| **Cost** | $$ | $$$ | Free |
| **Code Analysis** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Speed** | Fast | Medium | Instant |
| **Context Window** | 200k tokens | 128k tokens | Limited |
| **Recommended** | ✅ Yes | Alternative | Dev only |

## How It Works

When LLM is configured, the agents use semantic analysis:

```
PR Code
   ↓
PR Metadata (title, author, branch)
   ↓
Diff Content (actual code changes)
   ↓
                    ┌─→ Logic Agent ─→ Claude API
   Coordinator  ─→ ┤
                    └─→ Security Agent ─→ Claude API
   ↓
Results aggregated and deduplicated
   ↓
GitHub comment + status check
```

Without LLM, agents use rule-based analysis (pattern matching, regex).

## Cost Estimation

### Per PR Analysis

Typical PR (5 files, ~150 lines changed):
- **Input tokens**: ~2,500 (diff + context)
- **Output tokens**: ~500 (findings)
- **Claude cost**: ~$0.015 per PR
- **GPT-4 cost**: ~$0.10 per PR

### Monthly Budget

Assuming 50 PRs/day, 20 working days:
- **1,000 PRs/month with Claude**: ~$15-20/month
- **1,000 PRs/month with GPT-4**: ~$100-150/month

## Troubleshooting

### "No module named 'anthropic'"

```bash
pip install anthropic>=0.7.0
pip install openai>=1.0.0  # if using OpenAI
```

### "API key invalid" (401)

1. Verify key format (Claude: `sk-ant-`, OpenAI: `sk-`)
2. Check key hasn't expired
3. Verify token permissions on provider dashboard
4. Re-create key if needed

### "Rate limit exceeded" (429)

1. Wait 1-2 minutes before retrying
2. Reduce concurrent requests
3. Use less expensive model (Claude Haiku vs Opus)
4. Implement exponential backoff retry logic

### Agents falling back to rule-based mode

The system automatically uses rule-based analysis if LLM fails:

```python
try:
    findings = await agent._analyze_with_llm(state)
except LLMError:
    findings = await agent._analyze_with_rules(state)  # Fallback
```

Check server logs to see which mode is being used:
```
[logic_agent] Using LLM-based analysis (Claude)
# or
[logic_agent] LLM unavailable, using rule-based analysis
```

## Advanced Configuration

### Using Claude

```python
from anthropic import Anthropic

client = Anthropic(api_key="sk-ant-xxxx")

# Recommended for code review
model = "claude-3-opus-20240229"  # Most capable
# model = "claude-3-sonnet-20240229"  # Balanced
# model = "claude-3-haiku-20240307"  # Fastest, cheapest
```

### Using OpenAI

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxxx")

# Recommended for code review
model = "gpt-4-turbo"  # Best balance
# model = "gpt-4"  # Most capable
# model = "gpt-3.5-turbo"  # Cheapest
```

### Temperature Tuning

For deterministic analysis (security, logic):
```python
response = client.messages.create(
    ...,
    temperature=0.2,  # Low = consistent
)
```

For exploratory analysis:
```python
response = client.messages.create(
    ...,
    temperature=0.7,  # High = varied
)
```

## Performance Tuning

### Timeout Configuration

```python
# In .env
AGENT_TIMEOUT_SECONDS=60  # Max wait for LLM response
LLM_RETRY_ATTEMPTS=3      # Retry failed LLM calls
```

### Token Limits

```python
# Maximum tokens to send in analysis
MAX_DIFF_TOKENS=4000

# Maximum response tokens from LLM
MAX_COMPLETION_TOKENS=500
```

### Caching

Use built-in caching to reduce API calls:

```python
# In .env
CACHE_BACKEND=redis  # or "file" or "memory"
```

The same PR diff gets cached, so re-running analysis is free.

## Security Best Practices

### API Key Management

1. **Never commit keys**:
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use environment variables**:
   ```python
   import os
   api_key = os.getenv("ANTHROPIC_API_KEY")
   # Never do: api_key = "sk-ant-xxxx"
   ```

3. **Rotate keys regularly**:
   - OpenAI: https://platform.openai.com/api-keys
   - Anthropic: https://console.anthropic.com/account/keys

4. **Use fine-grained tokens** (OpenAI):
   - Create tokens with minimal required permissions
   - Use separate tokens for different environments

### Data Privacy

- Diff content is sent to LLM for analysis
- Consider data sensitivity for proprietary code
- Anthropic and OpenAI have data retention policies
- Check provider terms for your use case

## Testing

### Run Unit Tests

```bash
# All LLM tests
pytest tests/test_core.py::TestLLMIntegration -v

# Test specific agent
pytest tests/test_core.py -k "logic_agent" -v
```

### Test Against Real PR

```bash
# Using direct endpoint
python tests/examples.py direct --pr-number 15

# With diagnostics
python tests/diagnose.py --pr-number 15
```

## Next Steps

1. [Configure GitHub Integration](GITHUB_INTEGRATION.md)
2. [Run tests](TESTING.md)
3. [Deploy to production](DEPLOYMENT.md)
4. [Monitor usage and costs](DEPLOYMENT.md#monitoring)
mini = GPT4Client(model="gpt-4-turbo-preview")
```

---

## Production Deployment

### Environment Variables (Required)

```bash
# At least one API key
export ANTHROPIC_API_KEY=<your_anthropic_api_key>    # OR
export OPENAI_API_KEY=<your_openai_api_key>

# GitHub integration
export GITHUB_TOKEN=<your_github_token>
export GITHUB_WEBHOOK_SECRET=<your_webhook_secret>

# Optional
export LOG_LEVEL="INFO"
export CACHE_BACKEND="redis"
export REDIS_URL="redis://localhost:6379"
```

### Performance Optimization

1. **Enable Caching**: Reduce repeated analyses
```python
from code_reviewer.utils.cache import RedisCache
cache = RedisCache()
coordinator = ReviewCoordinator(cache_backend=cache)
```

2. **Parallel Processing**: Use asyncio (built-in)

3. **Rate Limiting**: Implement with API provider

4. **Monitoring**: Track costs and usage

---

## Next Steps

1. ✅ Choose provider (Claude recommended)
2. ✅ Get API key
3. ✅ Set environment variable
4. ✅ Run tests
5. ✅ Test with webhook
6. ✅ Deploy to production
7. ✅ Monitor costs

See [WEBHOOK_TESTING.md](WEBHOOK_TESTING.md) for webhook integration guide.

