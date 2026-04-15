# Finding Deduplication & Caching Strategy

## Problem Statement

When a developer submits a PR with issues, the review system flags them. If the developer pushes new commits:

**Without deduplication:**
- Agent flags the SAME issue again
- GitHub comment mentions it again
- Developer sees duplicate notifications → frustration

**With deduplication:**
- System recognizes the issue was already flagged
- Only NEW issues appear in the comment
- Developer only sees actionable changes

## Solution: Finding Deduplication

### How It Works

#### 1. Finding ID Generation

Each finding gets a stable hash ID based on:
- **File path** (`src/auth/login.py`)
- **Finding type** (`SecurityWarning: Hardcoded credentials`)
- **Description** (`Found plaintext password in environment loading`)

```python
# Example
finding_id = hash("src/auth/login.py::SecurityWarning::Found plaintext...")
# Result: "a7f3d2e1b9c4"
```

This is **deterministic**: Same issue in same file always produces same ID.

#### 2. Deduplication Process

**First Review (PR #42):**
```
Phase A: Agents find 5 issues
  ├─ finding_id: "a7f3d2e1b9c4" (hardcoded creds in login.py)
  ├─ finding_id: "b2e9f5d8a1c3" (weak regex pattern)
  ├─ finding_id: "c1d6e9a3f2b7" (missing input validation)
  ├─ finding_id: "d4e2f8b1a9c5" (unused import)
  └─ finding_id: "e8a3f1b7d2c6" (SQL injection risk)

Cache: [a7f3d2e1b9c4, b2e9f5d8a1c3, c1d6e9a3f2b7, d4e2f8b1a9c5, e8a3f1b7d2c6]
GitHub Comment: All 5 issues listed
```

**Second Review (PR #42 - developer pushed new commits):**
```
Phase A: Agents find 4 issues
  ├─ finding_id: "a7f3d2e1b9c4" (SAME: hardcoded creds still there!)
  ├─ finding_id: "f9b2e7c1d3a8" (NEW: Inefficient loop)
  ├─ finding_id: "b2e9f5d8a1c3" (SAME: weak regex still there)
  └─ finding_id: "g3c8f2d9a1b5" (NEW: Missing error handling)

Mark as duplicates:
  ├─ a7f3d2e1b9c4 → is_duplicate = True
  ├─ b2e9f5d8a1c3 → is_duplicate = True

GitHub Comment: 
  - ✅ FIXED: Missing input validation, Unused import, SQL injection risk
  - ⚠️  STILL ISSUES: Hardcoded creds, Weak regex
  - 🆕 NEW: Inefficient loop, Missing error handling
```

### Data Structure

```python
class AgentFinding(BaseModel):
    file_path: str
    line_number: int
    finding_type: str
    description: str
    severity: Severity
    
    # NEW FIELDS FOR DEDUPLICATION
    finding_id: str  # Hash of (file_path, finding_type, description)
    is_duplicate: bool  # True if flagged in previous review
    
    def compute_finding_id(self) -> str:
        """Generate stable hash ID"""
        content = f"{self.file_path}::{self.finding_type}::{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
```

### Workflow

```
1. Review Triggered
   ↓
2. Load Previous Finding IDs from Cache
   ↓
3. Run Agent Analysis (Phase A)
   ├─ Logic Agent finds issues
   └─ Security Agent finds issues
   ↓
4. Compute Finding IDs
   └─ Each finding gets a deterministic hash
   ↓
5. Mark Duplicates (Phase B)
   └─ Compare against previous findings
   ↓
6. Synthesis (Phase C)
   ├─ Summarizer organized findings
   ├─ Highlights new vs. duplicate
   └─ Different tone for "STILL UNFIXED"
   ↓
7. Cache New Finding IDs
   └─ Store in Redis/File for next review
   ↓
8. Post GitHub Comment
   └─ Shows progress (what was fixed, what's still broken)
```

## Cache Backends

### In-Memory Cache (Development)

```python
from code_reviewer.utils.cache import InMemoryCache

cache = InMemoryCache()
cache.set("pr:42:findings", ["a7f3d2e1b9c4", "b2e9f5d8a1c3"], ex=2592000)
previous_ids = cache.get("pr:42:findings")  # ["a7f3d2e1b9c4", "b2e9f5d8a1c3"]
```

**Pros:**
- Zero setup required
- Fast (in-process)

**Cons:**
- Data lost on restart
- Single-server only

**Use case:** Local development, testing

### File Cache (Single-Server Production)

```python
from code_reviewer.utils.cache import FileCache

cache = FileCache(cache_dir=".cache")
cache.set("pr:42:findings", ["a7f3d2e1b9c4", "b2e9f5d8a1c3"], ex=2592000)
previous_ids = cache.get("pr:42:findings")
```

Files stored in `.cache/pr_42_findings.json`:
```json
{
  "value": ["a7f3d2e1b9c4", "b2e9f5d8a1c3"],
  "expiry": "2026-05-15T12:30:45.123456"
}
```

**Pros:**
- Persists across restarts
- Simple to inspect (JSON files)
- No external dependencies

**Cons:**
- Not distributed
- Slower than memory

**Use case:** Small deployments, Heroku

### Redis Cache (Distributed Production)

```python
from code_reviewer.utils.cache import RedisCache

cache = RedisCache(host="localhost", port=6379)
cache.set("pr:42:findings", ["a7f3d2e1b9c4", "b2e9f5d8a1c3"], ex=2592000)
previous_ids = cache.get("pr:42:findings")
```

**Pros:**
- Distributed (across multiple servers)
- Very fast (in-memory store)
- Automatic expiration (TTL)
- Built-in persistence options

**Cons:**
- Requires Redis server
- Network latency
- External dependency

**Use case:** High-scale deployments, AWS, K8s

## Configuration

### Auto-Detection

```python
from code_reviewer.utils.cache import get_cache_backend

# Automatically select based on CACHE_BACKEND env var
cache = get_cache_backend()
```

### Explicit Selection

**Environment Variables:**
```env
# Memory (default)
CACHE_BACKEND=memory

# File-based
CACHE_BACKEND=file
CACHE_DIR=.cache

# Redis
CACHE_BACKEND=redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

**Code:**
```python
from code_reviewer.utils.cache import FileCache, RedisCache
import redis

# File cache
cache = FileCache(cache_dir="/var/cache/reviews")

# Redis with existing client
redis_client = redis.Redis(...)
cache = RedisCache(redis_client=redis_client)
```

## Integration Points

### ReviewCoordinator

```python
from code_reviewer.core.coordinator import ReviewCoordinator
from code_reviewer.utils.cache import get_cache_backend

# Initialize with cache backend
cache_backend = get_cache_backend()
coordinator = ReviewCoordinator(cache_backend=cache_backend)

# Call with previous findings
state = await coordinator.review_pr(
    state,
    previous_finding_ids=["a7f3d2e1b9c4", "b2e9f5d8a1c3"]
)

# Coordinator automatically caches new finding IDs
```

### ReviewState

```python
from code_reviewer.core.state import ReviewState, AgentFinding

state = ReviewState(pr_metadata=metadata)

# After agents add findings...

# Step 1: Compute finding IDs
state.compute_finding_ids()

# Step 2: Mark duplicates
state.mark_duplicates(["a7f3d2e1b9c4", "b2e9f5d8a1c3"])

# Step 3: Get filtered results
new_findings = state.get_new_findings()  # Only new issues
duplicates = state.get_duplicate_findings()  # Issues still unfixed
all_ids = state.get_finding_ids()  # For caching
```

### Main Endpoint

```python
# In src/code_reviewer/main.py

# 1. Load previous findings
cache_key = f"pr:{pr_number}:findings"
previous_ids = cache_backend.get(cache_key)

# 2. Run review with deduplication
state = await coordinator.review_pr(
    initial_state,
    previous_finding_ids=previous_ids
)

# 3. Cache new findings
new_ids = state.get_finding_ids()
cache_backend.set(cache_key, new_ids, ex=86400*30)
```

## Summarizer Enhancement

The SummarizerAgent now distinguishes between new and duplicate findings:

```markdown
## 🤖 Agentic Code Review

### ✅ Fixed (5)
- Unused import in `auth/login.py` ← NO LONGER IN FINDINGS
- Missing input validation in `api/routes.py`
- SQL injection risk in `database/query.py`
- Missing error handling in `utils/http.py`
- Inefficient loop in `services/processor.py`

### ⚠️ Still Issues (2)
These were flagged before but still present:
- **Hardcoded credentials** in `config/auth.py:15`
  - *Previously flagged:* "Found plaintext password"
  - *Still present* → Developer needs to address!
  
- **Weak regex pattern** in `validation/email.py:42`
  - *Previously flagged:* "Regex not RFC-compliant"
  - *Still present* → Consider refactoring

### 🆕 New Issues (2)
- **Low code coverage** in `tests/` (~60% vs recommended 80%)
- **Missing docstring** in `api/handlers.py:105`
```

## Performance Impact

### Finding ID Computation

```
Finding count:  5  findings
Time to compute IDs:  0.5 ms
Overhead:  negligible (<1% of total review time)
```

### Cache Lookup

```
Backend          Lookup Time    Store Time    Expiration
Memory           0.01 ms        0.01 ms       Auto via TTL
File             5-10 ms        5-10 ms       Check on read
Redis            1-5 ms         1-5 ms        Auto via TTL
```

### Recommended Expiration

```python
# 30 days (TTL in seconds)
ex = 86400 * 30

# Why 30 days?
# - Long enough to catch issues across multiple PR iterations
# - Short enough to not cache stale data forever
# - Typical PR lifetime: 1-7 days
```

## Troubleshooting

### "Finding appears as duplicate but is actually new"

**Cause:** Code changed but finding description is identical
**Solution:** Add line number or code snippet to description

```python
# Bad: Generic description
description = "Hardcoded credential"

# Good: Line-specific
description = f"Hardcoded credential on line {line_num}: {code_snippet}"
```

### "Finding marked as new but looks familiar"

**Cause:** Different wording or line number changed
**Solution:** Check file_path + finding_type match

```python
# These generate different IDs:
"src/auth.py::SecurityWarning::Hardcoded password"
"src/auth.py::SecurityWarning::Found plaintext password"

# These generate same ID:
"src/auth.py::SecurityWarning::Hardcoded password"  (line 10)
"src/auth.py::SecurityWarning::Hardcoded password"  (line 15, after refactor)
```

### "Cache not working - findings show as new every time"

**Cause:** 
- Cache backend not configured
- Cache key mismatch
- TTL expired

**Debug:**
```python
# Check backend type
print(type(cache_backend).__name__)

# Check if key exists
exists = cache_backend.exists(f"pr:{pr_number}:findings")

# Check raw value
value = cache_backend.get(f"pr:{pr_number}:findings")
print(f"Previous findings: {value}")
```

## Best Practices

### 1. **Stable Descriptions**

Keep finding descriptions consistent so hashes match:

```python
# ✅ Good
description = f"Hardcoded credential: {credential_type}"

# ❌ Bad (different each time)
description = f"Found hardcoded {credential_type} on {datetime.now()}"
```

### 2. **TTL Management**

Balance retention vs. staleness:

```python
# Short retention (too aggressive)
cache.set(key, value, ex=3600)  # 1 hour
# → May duplicate new issues from fixed code

# Long retention (safe)
cache.set(key, value, ex=2592000)  # 30 days
# → Catches issues across PR iterations
```

### 3. **Error Handling**

Cache failures should not block reviews:

```python
try:
    previous_ids = cache_backend.get(cache_key)
except Exception as e:
    logger.warning(f"Cache read failed: {e}")
    previous_ids = None  # Continue without deduplication
```

### 4. **Monitoring**

Track cache performance:

```python
# Monitor metrics
cache_hits = 0  # Times we found previous findings
cache_misses = 0  # Times cache was empty
cache_errors = 0  # Times cache failed

# In SummarizerAgent
if duplicates:
    logger.info(
        f"Duplicate findings detected",
        duplicate_count=len(duplicates),
        new_count=len(new_findings),
        hit_rate=cache_hits / (cache_hits + cache_misses)
    )
```

## Migration Path

### Phase 1: Basic Deduplication (Now)
- Finding ID computation
- In-memory cache
- Detection of duplicates

### Phase 2: Persistent Storage (Next)
- File or Redis cache
- Multi-server support
- TTL-based cleanup

### Phase 3: Advanced Analytics (Future)
- Finding lifecycle tracking
- Trend analysis ("this issue appears in 30% of PRs")
- Smart recommendations ("you keep writing this type of issue")

## Example: End-to-End Flow

### PR #42: Initial Review

```
Input: First commit
  ├─ src/auth.py:15 - Hardcoded password
  └─ src/api.py:30 - Missing validation

Coordinator:
  1. Agents find 2 issues
  2. Compute IDs: [a7f3d2e1b9c4, b2e9f5d8a1c3]
  3. No previous findings → no duplicates
  4. Synthesizer: "2 issues found"
  5. Cache: store [a7f3d2e1b9c4, b2e9f5d8a1c3]

GitHub Comment:
  🤖 **Code Review**
  - ⚠️ Hardcoded password in src/auth.py:15
  - ⚠️ Missing validation in src/api.py:30
```

### PR #42: Second Review (Developer pushed fix for validation)

```
Input: New commit (removed validation issue, kept password)
  ├─ src/auth.py:15 - Hardcoded password
  └─ (validation issue removed)

Coordinator:
  1. Agents find 1 issue
  2. Compute IDs: [a7f3d2e1b9c4]
  3. Load previous: [a7f3d2e1b9c4, b2e9f5d8a1c3]
  4. Mark duplicates: a7f3d2e1b9c4 = duplicate
  5. Synthesizer: "1 duplicate + 1 fixed"
  6. Cache: update [a7f3d2e1b9c4]

GitHub Comment:
  🤖 **Code Review**
  
  ✅ **Fixed Issues**
  - Missing validation in src/api.py:30
  
  ⚠️ **Still Issues**
  - Hardcoded password in src/auth.py:15
    (Previously flagged but still present)
```

---

**For more details:**
- See [ARCHITECTURE.md](ARCHITECTURE.md) for overall design
- See [examples.py](examples.py) for code examples
- See [README.md](README.md) for user guide
