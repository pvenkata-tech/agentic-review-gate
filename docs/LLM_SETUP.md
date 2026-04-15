# LLM Setup and Usage Guide

Complete guide to setting up and using Large Language Models with the Code Reviewer.

## Quick Start

### 1. Using Claude (Recommended)

```bash
# Install
pip install anthropic

# Set API key
export ANTHROPIC_API_KEY="sk-ant-your-key"

# Start server
python -m uvicorn src.code_reviewer.main:app --port 8000
```

### 2. Using GPT-4

```bash
# Install
pip install openai

# Set API key
export OPENAI_API_KEY="sk-your-key"

# Start server
python -m uvicorn src.code_reviewer.main:app --port 8000
```

### 3. Using Mock (Development)

```bash
# No installation needed, no API key required
python -m uvicorn src.code_reviewer.main:app --port 8000
```

---

## Detailed Configuration

### Getting API Keys

#### Claude (Anthropic)

1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create new API key
5. Copy key (format: `sk-ant-...`)

**Free Tier**: Limited tokens, then paid as you go

#### GPT-4 (OpenAI)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Create new secret key
4. Copy key (format: `sk-...`)

**Free Tier**: $5 credit, then paid as you go

### Environment Setup

#### Option A: Environment Variables

**Linux/macOS**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

**Windows PowerShell**:
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:OPENAI_API_KEY = "sk-..."
```

#### Option B: .env File

Create `.env` in project root:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=my_secret_123
```

Then load in Python:
```python
from dotenv import load_dotenv
load_dotenv()
```

#### Option C: Direct in Code

```python
from code_reviewer.llm import ClaudeClient

client = ClaudeClient(api_key="sk-ant-...")
agent = LogicAgent(llm_client=client)
```

---

## Provider Comparison

| Aspect | Claude | GPT-4 | Mock |
|--------|--------|-------|------|
| **Cost** | $$ | $$$ | $0 |
| **Code Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **Security** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| **Speed** | Fast | Medium | Instant |
| **Context** | 200k tokens | 8k-128k tokens | Limited |
| **API Setup** | Easy | Easy | None |
| **Recommended** | ✅ Yes | Alternative | Dev only |

---

## Running Tests

### Unit Tests

```bash
# Test LLM clients
pytest tests/test_core.py::TestLLMIntegration -v

# Test webhook validation
pytest tests/test_core.py::TestWebhookValidation -v

# Test agents with LLM
pytest tests/test_core.py::TestLLMIntegration::test_logic_agent_with_llm -v
```

### Webhook Testing

```bash
# Test with mock LLM (no API keys needed)
python tests/webhook_test_client.py \
  --url http://localhost:8000/webhook/github \
  --secret my_webhook_secret \
  --pr-number 42 \
  --verbose

# Or with real repository
# 1. Set up ngrok tunnel: ngrok http 8000
# 2. Add webhook to GitHub: https://<ngrok-url>/webhook/github
# 3. Create PR to trigger webhook
```

---

## Cost Analysis

### Token Usage per PR

**Typical PR** (5 files, 100 additions/deletions):
- Logic agent: ~2,000 tokens
- Security agent: ~2,000 tokens
- **Total: ~4,000 tokens per PR**

**Large PR** (20 files, 500 additions/deletions):
- Logic agent: ~4,000 tokens
- Security agent: ~4,000 tokens
- **Total: ~8,000 tokens per PR**

### Monthly Cost

Assuming 50 PRs/day, 20 days/month (1000 PRs/month):

| Provider | Model | Cost |
|----------|-------|------|
| Claude | Sonnet | ~$2.40/month |
| Claude | Opus | ~$19.20/month |
| GPT-4 | Turbo | ~$4.00/month |
| GPT-4 | 4 | ~$12.00/month |

---

## Troubleshooting

### "No module named 'anthropic'"

```bash
pip install anthropic>=0.7.0
```

### "API key invalid" (401)

1. Check key is correct: `echo $ANTHROPIC_API_KEY`
2. Verify key is not expired
3. Check API key permissions
4. Try re-creating the key

### "Rate limit exceeded" (429)

1. Wait a minute before retrying
2. Reduce request frequency
3. Use cheaper model (Haiku vs Opus)
4. Implement request batching

### "LLM analysis failed"

The system automatically falls back to rule-based analysis:

```python
# This happens automatically
try:
    findings = await agent._analyze_with_llm(state, diff)
except Exception as e:
    findings = await agent._analyze_with_rules(state, diff)
```

---

## Advanced Configuration

### Custom LLM Provider

```python
from code_reviewer.llm import LLMClient, LLMResponse

class MyCustomLLM(LLMClient):
    async def call(self, system_prompt, user_prompt, **kwargs):
        # Your implementation
        response = await my_llm_api.generate(
            system=system_prompt,
            user=user_prompt,
            **kwargs
        )
        return LLMResponse(
            content=response.text,
            model="my-model",
        )

# Use with agents
agent = LogicAgent(llm_client=MyCustomLLM())
```

### Temperature Tuning

For deterministic analysis (security, logic):
```python
# Low temperature = more consistent, less creative
await llm_client.call(..., temperature=0.2)
```

For exploratory analysis:
```python
# High temperature = more varied, more creative
await llm_client.call(..., temperature=0.7)
```

### Model Selection

#### Claude Options

```python
from code_reviewer.llm import ClaudeClient

# Most capable (slower, more expensive)
opus = ClaudeClient(model="claude-3-opus-20240229")

# Best balance (recommended)
sonnet = ClaudeClient(model="claude-3-sonnet-20240229")

# Fastest (cheapest)
haiku = ClaudeClient(model="claude-3-haiku-20240307")
```

#### GPT-4 Options

```python
from code_reviewer.llm import GPT4Client

# Most capable
gpt4 = GPT4Client(model="gpt-4")

# Good balance (recommended)
turbo = GPT4Client(model="gpt-4-turbo")

# Faster, cheaper
mini = GPT4Client(model="gpt-4-turbo-preview")
```

---

## Production Deployment

### Environment Variables (Required)

```bash
# At least one API key
export ANTHROPIC_API_KEY="sk-ant-..."    # OR
export OPENAI_API_KEY="sk-..."

# GitHub integration
export GITHUB_TOKEN="ghp_..."
export GITHUB_WEBHOOK_SECRET="your_secret"

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

