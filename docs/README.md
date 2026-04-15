# Documentation Guide

Quick reference for navigating documentation for agentic-review-gate.

## 📚 Core Documentation

### 1. **[SETUP.md](SETUP.md)** - Getting Started
**Installation, Configuration, and Verification**

Start here to:
- ✅ Install Python dependencies
- ✅ Set up virtual environment
- ✅ Configure environment variables
- ✅ Set up GitHub authentication
- ✅ Configure LLM (Claude, GPT-4, or mock)
- ✅ Verify everything works

**Read time**: 10-15 minutes | **For**: Everyone (first-time setup)

---

### 2. **[INTEGRATION.md](INTEGRATION.md)** - External Services
**GitHub Webhooks, Branch Protection, and LLM Providers**

Learn about:
- 🔗 GitHub webhook setup and configuration
- 🔐 Webhook secret generation and validation
- 🌐 Exposing local server (ngrok)
- 📋 Branch protection rules
- 🤖 LLM provider setup (Claude, GPT-4)
- ✔️ Status checks and PR blocking

**Read time**: 15-20 minutes | **For**: Setting up webhooks and integrations

---

### 3. **[OPERATIONS.md](OPERATIONS.md)** - Deployment and Monitoring
**Testing, Deployment, Performance, and Troubleshooting**

Covers:
- 🧪 Running unit and integration tests
- 📦 Deploying to Docker, Kubernetes, and cloud platforms
- ⚡ Performance optimization and caching
- 📊 Monitoring and observability
- 🔧 Troubleshooting common issues

**Read time**: 20-30 minutes | **For**: Deployment, testing, and ops

---

### 4. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System Design
**Architecture, Design Patterns, and Contributing**

Understand:
- 🏗️ Blackboard pattern for multi-agent coordination
- 🧩 Agent interface and extensibility
- 🔀 Workflow phases (analysis, evaluation, synthesis)
- 💡 Design principles and patterns
- 📝 Contributing guidelines and code organization
- ⚙️ Performance characteristics and scalability

**Read time**: 25-40 minutes | **For**: Understanding system design and contributing

---

## Quick Navigation

### I want to...

**🚀 Get started quickly**
1. Read [SETUP.md](SETUP.md)
2. Run `python tests/diagnose.py`
3. Test with `python tests/examples.py direct --pr-number 15`

**🔗 Set up webhooks**
1. Read [SETUP.md](SETUP.md) for environment setup
2. Follow [INTEGRATION.md#github-webhook-integration](INTEGRATION.md#github-webhook-integration)
3. Configure ngrok or production server

**🚀 Deploy to production**
1. Review [SETUP.md](SETUP.md) for configuration
2. Read [OPERATIONS.md#deployment](OPERATIONS.md#deployment)
3. Follow Docker or Kubernetes instructions

**🧪 Run tests**
1. Read [OPERATIONS.md#testing](OPERATIONS.md#testing)
2. Run `pytest tests/ -v`
3. For diagnostics: `python tests/diagnose.py`

**🤖 Understand the system**
1. Start with [ARCHITECTURE.md#overview](ARCHITECTURE.md#overview)
2. Review [ARCHITECTURE.md#the-blackboard-pattern-solution](ARCHITECTURE.md#the-blackboard-pattern-solution)
3. See [ARCHITECTURE.md#agent-interface](ARCHITECTURE.md#agent-interface)

**👨‍💻 Contribute code**
1. Read [ARCHITECTURE.md#contributing-guidelines](ARCHITECTURE.md#contributing-guidelines)
2. Follow [ARCHITECTURE.md#code-organization](ARCHITECTURE.md#code-organization)
3. Review [ARCHITECTURE.md#design-principles](ARCHITECTURE.md#design-principles)

**⚙️ Troubleshoot issues**
1. Run `python tests/diagnose.py`
2. Check [INTEGRATION.md#troubleshooting](INTEGRATION.md#troubleshooting)
3. See [OPERATIONS.md#troubleshooting](OPERATIONS.md#troubleshooting)

**📊 Monitor and optimize**
1. Review [OPERATIONS.md#monitoring](OPERATIONS.md#monitoring)
2. Check [OPERATIONS.md#performance--caching](OPERATIONS.md#performance--caching)
3. Follow [OPERATIONS.md#performance-benchmarks](OPERATIONS.md#performance-benchmarks)
---

## Documentation Structure

```
docs/
├── README.md                 ← You are here
├── SETUP.md                  ← Installation and configuration
├── INTEGRATION.md            ← GitHub & LLM integrations
├── OPERATIONS.md             ← Testing, deployment, monitoring
├── ARCHITECTURE.md           ← System design and contributing
└── assets/                   ← Images and diagrams
```

---

## Key Concepts

### Blackboard Pattern

The system uses a **Blackboard Pattern** (shared state) for multi-agent coordination:
- All agents read from and write to `ReviewState`
- Agents run in parallel for 50% faster analysis
- Summarizer intelligently deduplicates findings

See [ARCHITECTURE.md#the-blackboard-pattern-solution](ARCHITECTURE.md#the-blackboard-pattern-solution)

### Three-Phase Workflow

1. **Phase A**: Logic and Security agents analyze PR independently
2. **Phase B**: Check if any critical issues warrant blocking
3. **Phase C**: Summarizer synthesizes findings into a comment

See [ARCHITECTURE.md#workflow-phases](ARCHITECTURE.md#workflow-phases)

### Integration Points

- **GitHub**: Webhooks for automatic PR review triggers
- **LLM**: Claude or GPT-4 for semantic code analysis
- **Cache**: Redis or file-based for finding deduplication

---

## Testing

### Quick Test

```bash
# Start server
python -m uvicorn src.code_reviewer.main:app &

# Test direct review endpoint
python tests/examples.py direct --pr-number 15

# Run diagnostics
python tests/diagnose.py
```

### Full Test Suite

```bash
pytest tests/ -v
```

See [OPERATIONS.md#testing](OPERATIONS.md#testing) for detailed testing procedures.

---

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/your-org/agentic-review-gate/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/your-org/agentic-review-gate/discussions)
- 📖 **Documentation**: See docs above
- 🤝 **Contributing**: See [ARCHITECTURE.md#contributing-guidelines](ARCHITECTURE.md#contributing-guidelines)

---

## Document Consolidation

This documentation was consolidated from 9+ files into 4 comprehensive guides:

- **SETUP.md**: Merged Windows setup + LLM setup
- **INTEGRATION.md**: Merged webhook docs + LLM provider setup
- **OPERATIONS.md**: Merged testing + deployment + performance/caching docs
- **ARCHITECTURE.md**: Merged system design + contributing guidelines

This 4-file structure eliminates duplication while maintaining comprehensive coverage.

---

**Last Updated**: 2024 | **Version**: 1.0

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
