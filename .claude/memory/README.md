# Agent Memory Management

**Purpose:** Prevent context explosion and hallucinations through automatic memory pruning

---

## Quick Start

**Prune all memory files:**
```bash
python3 .claude/memory/prune-memory.py
```

**Prune specific agent:**
```bash
python3 .claude/memory/prune-memory.py --agent live-skill-learner
```

**Dry run (see what would be pruned):**
```bash
python3 .claude/memory/prune-memory.py --dry-run
```

---

## How It Works

### The Problem

Memory files grow indefinitely as agents track history:
- Large files slow AI processing
- Too much context causes hallucinations
- Storage waste (old entries rarely referenced)

### The Solution

**Automatic pruning:**
1. **Keeps last 100 entries** (recent activity)
2. **Archives older entries** to `archive/`
3. **Extracts patterns** from archived data
4. **Reduces file size** by 50-80%

### Example

**Before pruning:**
```markdown
# Live Skill Learner Memory

[2026-01-01 10:00] Fixed JWT expiry bug...
[2026-01-02 11:00] Added connection pooling...
... (498 more entries)

Total: 500 entries, 150KB
```

**After pruning:**
```markdown
# Live Skill Learner Memory

**Last Pruned:** 2026-02-12
**Total Historical Entries:** 500

## Statistics
- Active Entries: 100
- Total Historical: 500
- Archived: 400

## Extracted Patterns (from archived entries)
- **Connection Timeout:** 9 occurrences
- **Missing Config:** 7 occurrences
- **Database Migration:** 12 occurrences

## Recent Entries (Last 100)
[2026-02-10 14:00] Fixed migration issue...
[2026-02-11 09:00] Updated schema...
... (98 more recent entries)

Total: 100 entries, 40KB (73% reduction!)
```

---

## Configuration

**Edit `prune-memory.py` to customize:**

```python
# Lines 20-22
MAX_ENTRIES = 100      # Keep last N entries (default: 100)
MAX_SIZE_KB = 100      # Prune if file exceeds N KB (default: 100)
```

**Increase for larger projects:**
```python
MAX_ENTRIES = 200      # Keep more history
MAX_SIZE_KB = 200      # Allow larger files before pruning
```

---

## Archive Structure

**Location:** `.claude/memory/archive/`

**Organization:**
```
archive/
├── 2026-01/
│   ├── live-skill-learner-2026-01.md      ← January archives
│   └── live-change-management-2026-01.md
└── 2026-02/
    ├── live-skill-learner-2026-02.md      ← February archives
    └── live-change-management-2026-02.md
```

**Each archive contains:**
- Summary statistics
- Extracted patterns (compressed data)
- Sample entries (10% kept as examples)
- Full detail compressed into patterns

---

## When to Run

**Recommended schedule:**
- ✅ Weekly (cron job)
- ✅ When memory files exceed 100KB
- ✅ Before committing to git
- ✅ After major feature completion

**Automation (cron job):**
```bash
# Add to crontab (run every Sunday at 2 AM)
0 2 * * 0 cd /path/to/project && python3 .claude/memory/prune-memory.py

# Or use GitHub Actions for automatic pruning on push
```

---

## What Gets Pruned

**✅ Pruned (dedicated agent memory):**
- `.claude/memory/agents/live-skill-learner.md` - If > 100 entries
- `.claude/memory/agents/live-change-management.md` - If > 100 entries

**⚠️ Warning only (shared memory):**
- `.claude/memory/agents-memory.md` - Manual review recommended if > 200KB

**❌ Never pruned (templates and tools):**
- `.claude/memory/agents/trigger-patterns.json` - Detection patterns (reusable)
- `.claude/memory/agents/learning-template.md` - Learning format (reusable)
- `.claude/memory/prune-memory.py` - This script (reusable)

---

## Pattern Extraction

**How it works:**

Instead of storing full details for every entry, pruning extracts **recurring patterns**:

**Raw entries (400 archived):**
```
[2026-01-15] Fixed connection timeout in AWS EKS kubectl...
[2026-01-20] Resolved connection timeout in GCP GKE kubectl...
[2026-01-25] Fixed kubectl timeout connecting to cluster...
[2026-01-30] Timeout issue when connecting to Kubernetes...
... (5 more timeout entries)
```

**Extracted pattern:**
```
- **Connection Timeout:** 9 occurrences
```

**Result:**
- 9 detailed entries → 1 pattern line
- Same knowledge, 95% less storage
- AI understands "connection timeouts are common" without needing all 9 examples

**Common patterns detected:**
- Connection timeouts
- Missing configurations
- Platform-specific issues
- Database migrations
- Schema changes (rename, add field, etc.)

---

## Benefits

**Context Management:**
- ✅ Prevents context explosion (< 100 entries always)
- ✅ Prevents hallucinations (AI sees only recent, relevant data)
- ✅ Fast AI processing (small files = faster reads)

**Storage:**
- ✅ 50-80% file size reduction
- ✅ Preserves knowledge (patterns extracted)
- ✅ Full archive available if needed

**Quality:**
- ✅ Recent entries always accessible
- ✅ Historical patterns still visible
- ✅ Important examples preserved (10% of archived)

---

## Safety

**No data loss:**
- ✅ Full archive saved before pruning
- ✅ Dry run available (`--dry-run`)
- ✅ Original files backed up in archive/
- ✅ Can restore from archive if needed

**Restore from archive (if needed):**
```bash
# Restore specific agent memory
cp .claude/memory/archive/2026-02/live-skill-learner-2026-02.md \
   .claude/memory/agents/live-skill-learner.md

# Re-prune to get back to 100 entries
python3 .claude/memory/prune-memory.py --agent live-skill-learner
```

---

## Troubleshooting

**Issue: Script fails with "No such file or directory"**
```bash
# Ensure memory directories exist
mkdir -p .claude/memory/agents
mkdir -p .claude/memory/archive

# Create empty memory file if missing
touch .claude/memory/agents/live-skill-learner.md
```

**Issue: Pruning removes too many entries**
```bash
# Increase MAX_ENTRIES
# Edit prune-memory.py line 21:
MAX_ENTRIES = 200  # Keep last 200 instead of 100
```

**Issue: Want to see archived entries**
```bash
# View archive
ls .claude/memory/archive/2026-02/
cat .claude/memory/archive/2026-02/live-skill-learner-2026-02.md
```

---

## Memory File Structure

**Shared Memory** (`.claude/memory/agents-memory.md`):
```markdown
# Agent Memory Storage

## orchestrator
**Last Updated:** 2026-02-12
**Role:** Track routing patterns and performance

### Routing Success Rates
- backend-developer: 15 assignments
- frontend-developer: 10 assignments

## live-skill-learner
**Last Updated:** 2026-02-12
**Role:** Track skill improvements

### Statistics
- Total skill updates: 25
- Skills modified: 12
```

**Dedicated Memory** (`.claude/memory/agents/live-skill-learner.md`):
```markdown
# Live Skill Learner Memory

**Last Pruned:** 2026-02-12
**Total Historical Entries:** 150

## Statistics
- Active Entries: 100
- Archived: 50

## Extracted Patterns
- **Connection Timeout:** 9 occurrences
- **Add Field:** 15 occurrences

## Recent Entries (Last 100)
[2026-02-12 14:00] Updated jwt-authentication skill...
[2026-02-11 09:00] Fixed database-schema-expander...
```

---

## Related Documentation

- **Portability Guide:** `.claude/PORTABILITY.md` - Which files to copy to new projects
- **Agent Definitions:** `.claude/agents/` - 18 FTE agents with memory configuration
- **Memory Templates:** `.claude/memory/agents/` - Trigger patterns and learning template

---

**Last Updated:** 2026-02-12
**Status:** Production-ready ✅
**Prevents context explosion and hallucinations!** 🚀
