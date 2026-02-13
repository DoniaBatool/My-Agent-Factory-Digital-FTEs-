# Agent & Skill Portability Guide

**Created:** 2026-02-12
**Purpose:** Explains which components are project-specific vs reusable, and how to use them in other projects

---

## Quick Answer

**✅ REUSABLE (Generic - can be used in ANY project):**
- `.claude/agents/` - All 18 FTE agents (orchestrator, backend-developer, etc.)
- `.claude/skills/` - All 61 expert-level skills (jwt-authentication, database-schema-expander, etc.)
- `.specify/` - Entire SpecKit Plus framework (spec, plan, tasks workflows)

**❌ PROJECT-SPECIFIC (Contains your todo_phase5 project data):**
- `.claude/memory/` - All memory files (agents-memory.md, dedicated agent memory)
- `specs/` - Your feature specifications
- `history/` - Your PHRs and ADRs

---

## Detailed Breakdown

### 1. Agents (`.claude/agents/`) - 100% REUSABLE ✅

**What they are:**
- Generic role-based AI agents (backend-developer, frontend-developer, etc.)
- Contain reusable workflows, routing patterns, and automation rules
- NO project-specific data - only role definitions

**Examples:**
```
.claude/agents/
├── orchestrator.md              ← Routes requests to other agents
├── backend-developer.md          ← FastAPI automation workflows
├── frontend-developer.md         ← Next.js automation workflows
├── live-skill-learner.md         ← Real-time skill improvement
├── live-change-management.md     ← Real-time change propagation
└── ... (13 more agents)
```

**Portability:**
- Copy entire `.claude/agents/` folder to new project → Works immediately! ✅
- No configuration needed
- Agents adapt to new project structure automatically

**Use case:**
```bash
# Start new project
mkdir my-new-project && cd my-new-project

# Copy agents (reusable!)
cp -r /path/to/todo_phase5/.claude/agents .claude/

# Agents now work in my-new-project! ✅
# orchestrator will route requests
# backend-developer will scaffold FastAPI code
# frontend-developer will create Next.js components
```

---

### 2. Skills (`.claude/skills/`) - 100% REUSABLE ✅

**What they are:**
- Generic implementation patterns (authentication, database, testing, deployment)
- Contain reusable code templates, automation scripts (tool.py), and best practices
- NO project-specific data - only implementation knowledge

**Examples:**
```
.claude/skills/
├── jwt-authentication/          ← Works for ANY FastAPI project
│   ├── SKILL.md
│   ├── README.md
│   └── scripts/tool.py          ← Generates JWT auth code
├── database-schema-expander/    ← Works for ANY SQLModel project
│   └── scripts/tool.py          ← Generates migrations
├── chatbot-endpoint/            ← Works for ANY AI chatbot
│   └── scripts/tool.py          ← Generates chat endpoint
└── ... (58 more skills)
```

**Portability:**
- Copy entire `.claude/skills/` folder to new project → Works immediately! ✅
- Skills generate code based on NEW project structure
- No configuration needed

**Use case:**
```bash
# New e-commerce project
mkdir ecommerce-api && cd ecommerce-api

# Copy skills (reusable!)
cp -r /path/to/todo_phase5/.claude/skills .claude/

# Use skills in new project ✅
python3 .claude/skills/jwt-authentication/scripts/tool.py setup
# → Generates JWT auth for ecommerce-api

python3 .claude/skills/database-schema-expander/scripts/tool.py create-migration --name add_products_table
# → Creates migration for ecommerce products table
```

---

### 3. SpecKit Plus (`.specify/`) - 100% REUSABLE ✅

**What it is:**
- Complete spec-driven development framework
- Provides `/sp.specify`, `/sp.plan`, `/sp.tasks`, `/sp.implement` workflows
- Templates for spec.md, plan.md, tasks.md, ADRs, PHRs

**Portability:**
- Copy entire `.specify/` folder to new project → Works immediately! ✅
- Contains generic templates and workflows
- Constitution file is project-specific but easily customizable

**Use case:**
```bash
# New mobile app project
mkdir mobile-app && cd mobile-app

# Copy SpecKit Plus (reusable!)
cp -r /path/to/todo_phase5/.specify .specify/

# Customize constitution for mobile app
# Edit .specify/memory/constitution.md with mobile-specific rules

# Use SDD workflows ✅
/sp.specify "User authentication with Google Sign-In"
/sp.plan specs/001-google-auth/
/sp.tasks specs/001-google-auth/
/sp.implement specs/001-google-auth/
```

---

### 4. Memory (`.claude/memory/`) - ❌ PROJECT-SPECIFIC

**What it is:**
- Agent execution history from YOUR todo_phase5 project
- Tracks skills used, issues fixed, changes made IN THIS PROJECT
- Contains project-specific learnings and patterns

**Why NOT portable:**
- References files from todo_phase5 (backend/src/..., frontend/...)
- Contains learnings specific to todo features (recurring tasks, reminders)
- Tracks YOUR project's architecture decisions

**Examples:**
```
.claude/memory/
├── agents-memory.md                    ← todo_phase5 agent stats
├── agents/
│   ├── live-skill-learner.md           ← todo_phase5 skill updates
│   ├── live-change-management.md       ← todo_phase5 code changes
│   ├── trigger-patterns.json           ← Generic (reusable!)
│   └── learning-template.md            ← Generic (reusable!)
└── prune-memory.py                     ← Generic (reusable!)
```

**What to do in new project:**
1. **DON'T copy** `.claude/memory/` folder (contains project-specific data)
2. **DO copy** memory system files:
   ```bash
   # Auto-pruning module (IMPORTANT!)
   cp .claude/memory/auto_prune.py new-project/.claude/memory/

   # Templates (reusable)
   cp .claude/memory/agents/trigger-patterns.json new-project/.claude/memory/agents/
   cp .claude/memory/agents/learning-template.md new-project/.claude/memory/agents/

   # Manual pruning script (backup option)
   cp .claude/memory/prune-memory.py new-project/.claude/memory/
   ```
3. **Memory files auto-create** - NO need to create manually! ✅
   ```bash
   # ❌ DON'T DO THIS (unnecessary):
   # touch new-project/.claude/memory/agents-memory.md
   # touch new-project/.claude/memory/agents/live-skill-learner.md

   # ✅ DO THIS (nothing!):
   # Files auto-create when agents first use them
   # auto_prune.py automatically creates files if they don't exist
   ```

---

### 5. Specs (`specs/`) - ❌ PROJECT-SPECIFIC

**What it is:**
- Feature specifications for todo_phase5
- Contains spec.md, plan.md, tasks.md for recurring tasks, reminders, priorities, tags

**Why NOT portable:**
- Specific to todo application features
- References todo_phase5 architecture

**What to do:**
- **DON'T copy** to new project
- **DO use** `.specify/` framework to create NEW specs for new project features

---

### 6. History (`history/`) - ❌ PROJECT-SPECIFIC

**What it is:**
- Prompt History Records (PHRs) from todo_phase5 development
- Architectural Decision Records (ADRs) for todo_phase5
- Project journal and learnings

**Why NOT portable:**
- Documents YOUR project's development journey
- Contains decisions specific to todo_phase5

**What to do:**
- **DON'T copy** to new project
- **DO create** fresh `history/` folder in new project for its own PHRs/ADRs

---

## Memory Management & Context Prevention

### The Problem

**Memory growth → Context explosion → Hallucinations → Storage issues**

When agents track history, memory files grow indefinitely:
```
.claude/memory/agents/live-skill-learner.md
├── Entry 1: Fixed JWT expiry bug (Jan 1)
├── Entry 2: Added connection pooling (Jan 2)
├── ...
├── Entry 500: Fixed migration issue (Feb 12)  ← 500 entries!
└── Entry 501: Updated schema (Feb 12)
```

**Impact:**
- Large files slow down AI processing
- Too much context causes hallucinations (AI mixes old/new info)
- Storage waste (old entries rarely referenced)

### The Solution: Automatic Pruning

**Script:** `.claude/memory/prune-memory.py`

**What it does:**
1. **Keeps last 100 entries** (recent activity)
2. **Archives older entries** to `.claude/memory/archive/`
3. **Extracts patterns** from archived data (compression)
4. **Reduces file size** by 50-80%

**How it works:**

```python
# Before pruning: 500 entries, 150KB
[2026-01-01 10:00] Fixed JWT expiry bug in backend/src/auth/jwt.py
[2026-01-02 11:00] Added connection pooling (15 connections)
... (498 more entries)

# After pruning: 100 recent + pattern summary, 40KB
## Statistics
- Active Entries: 100
- Total Historical: 500
- Archived: 400

## Extracted Patterns (from archived entries)
- **Connection Timeout:** 9 occurrences
- **Missing Config:** 7 occurrences
- **Database Migration:** 12 occurrences
- **Add Field:** 15 occurrences

## Recent Entries (Last 100)
[2026-02-10 14:00] Fixed migration issue...
[2026-02-11 09:00] Updated schema...
... (98 more recent entries)
```

**Compression technique:**
- Instead of storing 400 detailed entries
- Store pattern summary: "Connection Timeout: 9 occurrences"
- Keep 10% of archived entries as examples
- Result: Same knowledge, 75% less storage

### Usage

**Automatic pruning (recommended):**
```bash
# Prune all memory files when they exceed 100 entries
python3 .claude/memory/prune-memory.py

# Output:
# 🔍 Memory Pruning - Starting...
#
# ✓ live-skill-learner.md: Archived 150 entries
#   Kept: 100 recent entries
#   Saved: 85.4 KB
#   Archive: .claude/memory/archive/2026-02/live-skill-learner-2026-02.md
#
# ✓ live-change-management.md: 45 entries (within limit)
#
# ✓ agents-memory.md: 12.3 KB (within limit)
#
# 📊 Pruning Summary:
#   Files checked: 3
#   Files pruned: 1
#   Entries archived: 150
#   Space saved: 85.4 KB
#
# ✅ Pruning complete!
```

**Prune specific agent:**
```bash
python3 .claude/memory/prune-memory.py --agent live-skill-learner
```

**Dry run (see what would be pruned):**
```bash
python3 .claude/memory/prune-memory.py --dry-run
```

**When to run:**
- Weekly (cron job recommended)
- When memory files exceed 100KB
- Before committing to git (keep memory small)
- After major feature completion (clean up history)

**Archive structure:**
```
.claude/memory/archive/
├── 2026-01/
│   ├── live-skill-learner-2026-01.md     ← January archives
│   └── live-change-management-2026-01.md
└── 2026-02/
    ├── live-skill-learner-2026-02.md     ← February archives
    └── live-change-management-2026-02.md
```

**Benefits:**
- ✅ Prevents context explosion (< 100 entries always)
- ✅ Prevents hallucinations (AI sees only recent, relevant data)
- ✅ Saves storage (50-80% reduction)
- ✅ Preserves knowledge (patterns extracted, examples kept)
- ✅ Fast AI processing (small files = faster reads)

---

## Portability Checklist

When starting a new project and want to reuse todo_phase5 components:

### ✅ COPY THESE (Generic & Reusable):

- [ ] `.claude/agents/` - All 18 FTE agents
- [ ] `.claude/skills/` - All 61 expert-level skills
- [ ] `.specify/` - SpecKit Plus framework
- [ ] `.claude/memory/auto_prune.py` - Auto-pruning module (IMPORTANT!)
- [ ] `.claude/memory/agents/trigger-patterns.json` - Detection patterns
- [ ] `.claude/memory/agents/learning-template.md` - Learning format
- [ ] `.claude/memory/prune-memory.py` - Manual pruning script (backup)

### ❌ DON'T COPY THESE (Project-Specific):

- [ ] `.claude/memory/agents-memory.md` - todo_phase5 agent stats
- [ ] `.claude/memory/agents/live-skill-learner.md` - todo_phase5 skill updates
- [ ] `.claude/memory/agents/live-change-management.md` - todo_phase5 changes
- [ ] `.claude/memory/archive/` - todo_phase5 archived entries
- [ ] `specs/` - todo_phase5 feature specifications
- [ ] `history/` - todo_phase5 PHRs and ADRs

### ✏️ AUTO-CREATES (No manual creation needed!):

- [ ] `.claude/memory/agents-memory.md` - Auto-creates when agents use auto_prune.py
- [ ] `.claude/memory/agents/live-skill-learner.md` - Auto-creates when agent first writes
- [ ] `.claude/memory/agents/live-change-management.md` - Auto-creates when agent first writes
- [ ] `.claude/memory/archive/` - Auto-creates when first pruning happens
- [ ] `specs/` - Create as needed using `/sp.specify`
- [ ] `history/prompts/` - Create as needed when creating PHRs

### ⚙️ CUSTOMIZE (Optional):

- [ ] `.specify/memory/constitution.md` - Update with new project principles
- [ ] `.claude/agents/orchestrator.md` - Verify routing patterns match new project

---

## Example: Porting to New Project

### Scenario: E-Commerce API (FastAPI + Next.js)

**Step 1: Copy reusable components**
```bash
# New project setup
mkdir ecommerce-api && cd ecommerce-api
git init

# Copy agents (18 FTE agents)
cp -r /path/to/todo_phase5/.claude/agents .claude/

# Copy skills (61 expert-level skills)
cp -r /path/to/todo_phase5/.claude/skills .claude/

# Copy SpecKit Plus framework
cp -r /path/to/todo_phase5/.specify .specify/

# Copy memory system
mkdir -p .claude/memory/agents

# Auto-pruning module (IMPORTANT!)
cp /path/to/todo_phase5/.claude/memory/auto_prune.py .claude/memory/

# Templates and tools
cp /path/to/todo_phase5/.claude/memory/agents/trigger-patterns.json .claude/memory/agents/
cp /path/to/todo_phase5/.claude/memory/agents/learning-template.md .claude/memory/agents/
cp /path/to/todo_phase5/.claude/memory/prune-memory.py .claude/memory/
```

**Step 2: Memory files auto-create - NO manual work needed!**
```bash
# ✅ NEW WAY (automatic):
# Memory files auto-create when agents first use them via auto_prune.py
# No need to create:
#   - agents-memory.md
#   - live-skill-learner.md
#   - live-change-management.md
#   - archive/ folder
# All auto-create automatically! ✅

# Create history directories (if needed)
mkdir -p history/prompts/{constitution,general}
mkdir -p history/decisions

# Create specs directory (if needed)
mkdir -p specs
```

**Step 3: Customize constitution**
```bash
# Edit constitution for e-commerce project
nano .specify/memory/constitution.md

# Update with e-commerce-specific principles:
# - Payment security standards (PCI DSS)
# - Product catalog architecture
# - Order processing workflows
# - Inventory management patterns
```

**Step 4: Start using in new project!**
```bash
# Create first feature using SDD
/sp.specify "User authentication with email/password and Google OAuth"
# → Creates specs/001-auth/spec.md

/sp.plan specs/001-auth/
# → Creates plan.md, data-model.md, contracts/

/sp.tasks specs/001-auth/
# → Creates tasks.md

# Use skills immediately! ✅
python3 .claude/skills/jwt-authentication/scripts/tool.py setup
# → Generates JWT auth for e-commerce API

python3 .claude/skills/database-schema-expander/scripts/tool.py create-migration --name add_users_table
# → Creates migration for users table

# Skills generate code specific to e-commerce API, not todo_phase5! ✅
```

---

## Memory Portability: Templates Only

While memory files themselves are project-specific, the **templates** and **tools** are generic:

### ✅ Portable Memory Components:

**1. Trigger Patterns** (`.claude/memory/agents/trigger-patterns.json`)
- Generic fix/change detection patterns
- Works for ANY project
- No customization needed

**2. Learning Template** (`.claude/memory/agents/learning-template.md`)
- Structured format for capturing learnings
- Generic format works for ANY project
- No customization needed

**3. Auto-Pruning Module** (`.claude/memory/auto_prune.py`) **← NEW!**
- Automatic background pruning (like Claude's context compaction)
- Works on ANY memory file structure
- No customization needed
- Files auto-create when first used

**4. Manual Pruning Script** (`.claude/memory/prune-memory.py`)
- Generic memory management tool (backup option)
- Works on ANY memory file structure
- No customization needed

**5. Archive Structure**
- `.claude/memory/archive/YYYY-MM/` pattern is generic
- Works for ANY project
- Auto-creates when needed (no manual creation required)

### How to Use in New Project:

```bash
# Copy templates and tools (generic)
mkdir -p new-project/.claude/memory/agents

# Auto-pruning module (IMPORTANT!)
cp todo_phase5/.claude/memory/auto_prune.py new-project/.claude/memory/

# Templates (reusable)
cp todo_phase5/.claude/memory/agents/trigger-patterns.json new-project/.claude/memory/agents/
cp todo_phase5/.claude/memory/agents/learning-template.md new-project/.claude/memory/agents/

# Manual pruning script (backup)
cp todo_phase5/.claude/memory/prune-memory.py new-project/.claude/memory/

# Memory files auto-create - NO need to create manually! ✅
# ❌ DON'T DO THIS (unnecessary):
# touch new-project/.claude/memory/agents-memory.md
# touch new-project/.claude/memory/agents/live-skill-learner.md

# ✅ DO THIS (nothing!):
# Files auto-create when agents first use them via auto_prune.py

# Archive folder also auto-creates when first pruning happens
# No manual creation needed!
```

---

## Why This Design?

**Agents & Skills = Knowledge Libraries** 📚
- Contain generic patterns, workflows, and automation
- Like programming libraries (React, FastAPI) - reusable across projects
- No project-specific data embedded

**Memory = Project Journal** 📔
- Tracks what happened IN THIS PROJECT
- Like git history - specific to this codebase
- Should NOT be copied to new projects

**SpecKit = Development Framework** 🛠️
- Provides workflows for creating specs, plans, tasks
- Like a build tool (webpack, gradle) - reusable across projects
- Constitution customizable per project

---

## FAQ

**Q: Can I use backend-developer agent in a Django project?**
A: Yes! Agent contains generic backend patterns. Some skills (FastAPI-specific) won't apply, but agent routing and workflows are generic.

**Q: Will jwt-authentication skill work in Express.js?**
A: Partially. The skill contains FastAPI-specific code templates, but the SKILL.md documentation (JWT concepts, best practices) is generic. You can read patterns and implement in Express.

**Q: Should I copy memory files to new project?**
A: NO! Memory contains todo_phase5 history. Copy only tools (auto_prune.py, prune-memory.py) and templates (trigger-patterns.json, learning-template.md). Memory files auto-create when agents first use them - no need to create manually!

**Q: Do I need to create memory files manually?**
A: NO! `auto_prune.py` automatically creates memory files when agents first use them. Just copy the auto_prune.py module and let agents create files as needed.

**Q: How do I know if memory is growing too large?**
A: With `auto_prune.py`, memory automatically stays ≤ 100 entries (like Claude's context compaction). No manual checking needed! For manual verification: `python3 .claude/memory/prune-memory.py --dry-run`.

**Q: Will pruning lose important data?**
A: No! Pruning:
- Keeps last 100 entries (recent activity)
- Extracts patterns from archived entries (compression)
- Stores 10% of archived entries as examples
- Full archive saved in `.claude/memory/archive/`

**Q: Can I customize pruning thresholds?**
A: Yes! Edit `.claude/memory/prune-memory.py`:
```python
# Configuration (lines 20-22)
MAX_ENTRIES = 100      # Change to 200 for larger projects
MAX_SIZE_KB = 100      # Change to 200 for larger files
```

**Q: Should I commit memory files to git?**
A: Optional:
- ✅ Commit: If team needs shared agent memory
- ❌ Don't commit: If memory is personal or project is solo
- Recommendation: Add `.claude/memory/agents/*.md` to `.gitignore`, keep templates and prune-memory.py committed

---

## Summary

**🎯 Key Takeaway:**

```
AGENTS + SKILLS + SPECKIT = Generic libraries (reusable) ✅
MEMORY + SPECS + HISTORY = Project journal (NOT reusable) ❌
```

**To use in new project:**
1. Copy agents, skills, SpecKit ✅
2. Copy memory system (auto_prune.py, templates, tools) ✅
3. Memory files auto-create - NO manual creation needed! ✅
4. Customize constitution (optional) ✏️
5. Start building! 🚀

**Memory management:**
- **Automatic:** `auto_prune.py` automatically compacts memory (like Claude's context compaction)
- **Manual (backup):** Run `prune-memory.py` weekly if not using auto-pruning
- Keeps last 100 entries, archives older ones
- Extracts patterns for compression
- Prevents hallucinations and storage issues
- Zero user intervention with auto-pruning! ✅

---

**Last Updated:** 2026-02-12 (Updated: Added auto_prune.py, memory files auto-create)
**Status:** Production-ready ✅
**Agents & skills are portable! Memory auto-creates! Zero manual work!** 🚀

## 🆕 Recent Updates (2026-02-12)

**Auto-Pruning System Added:**
- ✅ Added `auto_prune.py` - Automatic memory compaction (like Claude!)
- ✅ Memory files now **auto-create** when agents first use them
- ✅ Archive folders **auto-create** when first pruning happens
- ✅ **NO manual file creation needed** - everything automatic!

**Updated Sections:**
- Memory portability guide (added auto_prune.py)
- Portability checklist (auto-create instead of manual touch)
- Example walkthrough (removed manual file creation)
- FAQ (added auto-create questions)

**Key Change:**
```bash
# ❌ OLD: Manual file creation
touch .claude/memory/agents-memory.md
touch .claude/memory/agents/live-skill-learner.md

# ✅ NEW: Auto-creates (no manual work!)
# Files create automatically when agents use auto_prune.py
```
