# Documentation - Agentic Review Gate

Comprehensive documentation for the agentic code review system.

## Quick Navigation

### Getting Started
- **[README.md](../README.md)** - Project overview and quick start
- **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** - Windows-specific setup instructions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment to production

### Integration & Configuration
- **[GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md)** - GitHub webhook and branch protection setup
- **[LLM_SETUP.md](LLM_SETUP.md)** - LLM provider configuration (Claude, GPT-4)
- **[CACHING_STRATEGY.md](CACHING_STRATEGY.md)** - Caching and performance optimization

### Testing & Troubleshooting
- **[TESTING.md](TESTING.md)** - Testing guide and diagnostics
- **[tests/](../tests/)** - Test suite with examples and diagnostic tools

### Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and patterns
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

## Documentation by Use Case

### "I want to set up the system locally"
1. Start with: [README.md](../README.md)
2. Follow: [WINDOWS_SETUP.md](WINDOWS_SETUP.md) (if on Windows)
3. Next: [GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md) to connect to GitHub
4. Test: [TESTING.md](TESTING.md) to verify installation

### "I want to configure GitHub webhooks"
1. Read: [GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md) - Complete webhook setup
2. Then: [TESTING.md](TESTING.md#webhook-testing) - Test the webhook

### "I want to set up an LLM provider"
1. Read: [LLM_SETUP.md](LLM_SETUP.md) - Provider configuration
2. Choose: Claude (recommended) or GPT-4
3. Test: `python tests/diagnose.py --check token`

### "I want to deploy to production"
1. Read: [DEPLOYMENT.md](DEPLOYMENT.md) - Full deployment guide
2. Reference: [GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md#production-deployment)
3. Monitor: [DEPLOYMENT.md#monitoring](DEPLOYMENT.md#monitoring)

### "I'm getting errors or issues"
1. Run: `python tests/diagnose.py` - Comprehensive diagnostics
2. Read: [TESTING.md#troubleshooting](TESTING.md#troubleshooting)
3. Check: [TESTING.md#debugging](TESTING.md#debugging) - Debug logging setup
4. See: Individual docs for specific topics

## File Descriptions

### ARCHITECTURE.md
**Purpose**: Understand how the system works

**Contents**:
- Multi-agent architecture (Blackboard pattern)
- Agent descriptions and capabilities
- Workflow phases (parallel analysis, critical check, synthesis)
- Design patterns used (Strategy, Blackboard, Dependency Inversion)
- Extension points for custom agents

**When to Read**: You want to understand the system design or add new agents

---

### CONTRIBUTING.md
**Purpose**: Guidelines for contributing to the project

**Contents**:
- Development setup
- Code style and standards
- Pull request process
- Testing requirements
- Documentation guidelines

**When to Read**: You want to contribute code or improve documentation

---

### CACHING_STRATEGY.md
**Purpose**: Optimize performance through caching

**Contents**:
- Cache backends (memory, file, Redis)
- Cache configuration
- Performance impact
- Cache invalidation strategies
- Cost optimization

**When to Read**: You want to improve performance or reduce API costs

---

### DEPLOYMENT.md
**Purpose**: Deploy to production

**Contents**:
- Pre-deployment checklist
- Environment configuration
- Database setup
- Reverse proxy configuration
- HTTPS/SSL setup
- Monitoring and logging
- Scaling and load balancing

**When to Read**: You're deploying to production or a staging environment

---

### GITHUB_INTEGRATION.md
**Purpose**: Set up GitHub webhook and automation

**Contents**:
- Webhook flow and architecture
- Step-by-step webhook setup
- Local testing with ngrok
- GitHub branch protection rules
- Status check enforcement
- Troubleshooting webhook issues
- Production deployment considerations

**When to Read**: You're setting up GitHub integration or webhook automation

---

### LLM_SETUP.md
**Purpose**: Configure AI providers for code analysis

**Contents**:
- Quick start for Claude and GPT-4
- Getting API keys
- Environment configuration
- Provider comparison
- Cost estimation
- Troubleshooting LLM issues
- Advanced configuration
- Security best practices

**When to Read**: You want to enable AI-powered code analysis

---

### TESTING.md
**Purpose**: Test the system thoroughly

**Contents**:
- Unit testing
- Integration testing
- Direct API testing
- Webhook testing
- Diagnostic tools
- Troubleshooting common issues
- Performance metrics
- Testing checklist

**When to Read**: You're testing the system or debugging issues

---

### WINDOWS_SETUP.md
**Purpose**: Windows-specific installation

**Contents**:
- PowerShell setup
- Virtual environment creation
- Dependency installation
- Environment variables
- Running the server

**When to Read**: You're on Windows and setting up the system

---

## Documentation Updates

### Recent Consolidations

The documentation has been reorganized for clarity:

**Consolidated Files**:
- `TESTING.md` ← `WEBHOOK_TESTING.md`, `TESTING.md`
- `GITHUB_INTEGRATION.md` ← `WEBHOOK_CONFIGURATION.md`, `WEBHOOK_INTEGRATION.md`
- `LLM_SETUP.md` ← `LLM_INTEGRATION.md`, `LLM_SETUP.md`

**Benefits**:
- No more duplicate information
- Single source of truth for each topic
- Easier to find and update information
- Better cross-references between docs

## Navigation Tips

### Search Documentation

```bash
# Search for keyword
grep -r "webhook" docs/

# Search test examples
ls tests/
# - examples.py - Running examples
# - diagnose.py - Diagnostics
# - test_core.py - Unit tests
# - test_agents_e2e.py - E2E tests
```

### Related Documents

Each document has "Next Steps" and "See Also" sections to help you navigate.

For example:
- Setup → GitHub Integration → Testing → Deployment

## Contributing to Documentation

### Adding New Documentation

1. Create new file in `docs/` with clear name
2. Add to this README with description
3. Link from related files
4. Run spell check and formatting check

### Updating Existing Documentation

1. Keep changes relevant to the specific document
2. If information should be in multiple places, consider consolidating
3. Update links if moving information
4. Test examples and code snippets

### Documentation Style

- Use Markdown formatting
- Include code examples with language tags
- Use clear headers and sections
- Keep paragraphs concise
- Link to related documentation

## Assets

The `assets/` folder contains:
- Diagrams and architecture images
- Screenshots for setup guides
- Example outputs

## Troubleshooting Documentation

**Can't find information on a topic?**

1. Check the file descriptions above
2. Search: `grep -r "topic" docs/`
3. Check: `tests/examples.py` for interactive examples
4. Run: `python tests/diagnose.py` for system status

**Found an error or outdated information?**

1. Check the file's "Last Updated" date
2. Run the example to verify
3. Submit an issue or PR with the correction
4. See [CONTRIBUTING.md](CONTRIBUTING.md) for process

## Quick Links

| Need | Read |
|------|------|
| Get started | [README.md](../README.md) |
| GitHub setup | [GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md) |
| LLM setup | [LLM_SETUP.md](LLM_SETUP.md) |
| Test system | [TESTING.md](TESTING.md) |
| Deploy | [DEPLOYMENT.md](DEPLOYMENT.md) |
| Understand design | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Optimize | [CACHING_STRATEGY.md](CACHING_STRATEGY.md) |

## Last Updated

Documentation consolidated and reorganized: April 15, 2026

For current status and updates, see the project [README.md](../README.md).
