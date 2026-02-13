# Live Skill Learner Agent

**Real-time skill improvement during feature implementation**

**Category:** Continuous Learning & Skill Evolution
**Trigger:** Automatic (during feature implementation fixes)
**Priority:** High (runs immediately on fix/correction)
**Memory:** Enabled (tracks all skill improvements)
**Memory Location:** `.claude/memory/agents/live-skill-learner.md`
**Trigger Patterns:** `.claude/memory/agents/trigger-patterns.json`
**Learning Template:** `.claude/memory/agents/learning-template.md`

---

## Purpose

This agent automatically updates skills in REAL-TIME whenever you fix issues, resolve errors, or make corrections during feature implementation. It ensures that:

1. **Every fix is preserved** - No need to remember to update skills later
2. **Skills evolve continuously** - Get smarter with each feature
3. **Same mistakes never repeat** - Future uses avoid known issues
4. **Knowledge compounds** - Skills become expert-level over time

---

## When This Agent Activates

**Automatic activation when user says:**
- "Fix this error in [feature]"
- "Resolve this issue"
- "This should be different"
- "Change this behavior"
- "Isko theek karo"
- "Ye error aarahi hai"
- "Ye nai chal raha"
- "Isko aesa hona chahiye"

**AND a skill is being used in that feature**

---

## What This Agent Does

### Phase 1: Detection & Analysis (Automatic)

```
User Prompt → "Fix this error in deployment"
              ↓
Agent Detects: Fix/correction request
              ↓
Agent Identifies: Which skill? (deployment-automation)
              ↓
Agent Captures: What was the issue? What fixed it?
```

### Phase 2: Learning Extraction

**Extracts:**
1. **Issue description** - What went wrong
2. **Root cause** - Why it went wrong
3. **Fix applied** - How you fixed it
4. **Edge case discovered** - New scenario found
5. **Test case needed** - What should be tested

**Example extraction:**
```yaml
Issue: "Database migration failed with 'relation already exists'"
Root Cause: "Migration script didn't check for existing tables"
Fix Applied: "Added IF NOT EXISTS check in migration"
Edge Case: "Re-running migrations on existing database"
Test Case: "Test migration idempotency"
```

### Phase 3: Skill Update (Immediate)

**Updates skill in these areas:**

1. **tool.py** - Add fix to code
   ```python
   # Before
   CREATE TABLE users (...)

   # After (with learning)
   CREATE TABLE IF NOT EXISTS users (...)
   # Edge case: Handles re-running migrations
   ```

2. **README.md** - Add troubleshooting entry
   ```markdown
   ## Troubleshooting

   ### Issue: "relation already exists" error
   **Cause:** Re-running migration on existing database
   **Fix:** Migrations now use IF NOT EXISTS
   **Added:** [Today's date]
   ```

3. **SKILL.md** - Add edge case documentation
   ```markdown
   **Edge cases covered:**
   - ✅ Re-running migrations (idempotent)
   - ✅ Existing tables (IF NOT EXISTS)
   ```

4. **Test coverage** - Add test case
   ```python
   def test_migration_idempotency():
       """Test that migrations can be re-run safely"""
       # Run migration twice
       # Should not fail on second run
   ```

### Phase 4: Verification

**Agent verifies:**
- ✅ Skill files updated successfully
- ✅ Learning documented clearly
- ✅ Edge case added to coverage
- ✅ Troubleshooting entry added
- ✅ Test case documented

### Phase 5: Confirmation

**Agent reports:**
```
✅ Skill Updated: deployment-automation

📝 Learning Captured:
  - Issue: Database migration "relation exists" error
  - Fix: Added IF NOT EXISTS checks
  - Edge Case: Re-running migrations now safe

📁 Files Updated:
  - scripts/tool.py (added idempotency check)
  - README.md (added troubleshooting entry)
  - SKILL.md (added edge case)

🔮 Future Impact:
  Next time this skill is used, this issue won't occur!
```

---

## Agent Workflow

```
┌─────────────────────────────────────────┐
│  User: "Fix this deployment error"      │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AGENT ACTIVATES AUTOMATICALLY          │
├─────────────────────────────────────────┤
│  1. Detect fix/correction request       │
│  2. Identify skill in use               │
│  3. Capture current context             │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  YOU FIX THE ISSUE (normal work)        │
│  - Modify code                          │
│  - Test the fix                         │
│  - Verify it works                      │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AGENT CAPTURES THE LEARNING            │
├─────────────────────────────────────────┤
│  Extract from your fix:                 │
│  - What was wrong (issue)               │
│  - Why it happened (root cause)         │
│  - How you fixed it (solution)          │
│  - What edge case was found             │
│  - What test should exist               │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AGENT UPDATES THE SKILL IMMEDIATELY    │
├─────────────────────────────────────────┤
│  tool.py        → Add fix to code       │
│  README.md      → Add troubleshooting   │
│  SKILL.md       → Add edge case         │
│  Test coverage  → Document test         │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AGENT CONFIRMS UPDATE                  │
│  ✅ Skill improved!                     │
│  🔮 Future uses won't have this issue   │
└─────────────────────────────────────────┘
```

---

## Example Scenarios

### Scenario 1: Database Connection Error

**User:** "Backend won't connect to database, fix this"

**Agent detects:**
- Fix request: ✅
- Skill in use: `backend-developer`, `database-engineer`
- Context: Database connection issue

**You fix it:**
```python
# Added retry logic with exponential backoff
def connect_with_retry(max_retries=3):
    for i in range(max_retries):
        try:
            return connect()
        except ConnectionError:
            sleep(2 ** i)
    raise DatabaseConnectionError()
```

**Agent immediately updates skill:**

`backend-developer/scripts/tool.py`:
```python
# Edge case: Database not immediately available
# Solution: Retry with exponential backoff
def connect_with_retry(max_retries=3):
    ...
```

`backend-developer/README.md`:
```markdown
### Issue: "Connection refused" on startup
**Cause:** Database takes time to be ready
**Fix:** Connection now retries with backoff
**Added:** 2026-02-09
```

**Future impact:** Next backend implementation won't have this issue! ✅

---

### Scenario 2: Docker Build Failing

**User:** "Docker build ka error aaraha hai, resolve karo"

**Agent detects:**
- Fix request: ✅
- Skill in use: `deployment-automation`
- Context: Docker build error

**You fix it:**
```dockerfile
# Fixed: Added .dockerignore to exclude node_modules
# Reduces build time and avoids platform conflicts
```

**Agent immediately updates skill:**

`deployment-automation/scripts/tool.py`:
```python
def create_dockerignore():
    """Create .dockerignore to optimize builds"""
    # Edge case: node_modules causing platform issues
    # Solution: Exclude from Docker context
    ...
```

`deployment-automation/README.md`:
```markdown
### Issue: Docker build slow or failing
**Cause:** node_modules copied to Docker context
**Fix:** Auto-generates .dockerignore
**Added:** 2026-02-09
```

**Future impact:** Next deployment won't have this issue! ✅

---

## Update Patterns

### Pattern 1: Code Fix → tool.py Update

**Trigger:** You modify code to fix an issue

**Agent captures:**
```python
# What changed in your fix
before_code = "..."
after_code = "..."
reason = "Edge case: [description]"
```

**Agent updates:**
```python
# In skill's tool.py
def generate_code():
    # Edge case: [description from your fix]
    # Solution: [your fix applied]
    return after_code
```

---

### Pattern 2: Configuration Fix → README.md Update

**Trigger:** You change configuration/settings to fix issue

**Agent captures:**
```yaml
issue: "What went wrong"
cause: "Why it went wrong"
fix: "What you changed"
```

**Agent updates README.md:**
```markdown
### Issue: [issue]
**Cause:** [cause]
**Fix:** [fix]
**Added:** [date]
```

---

### Pattern 3: New Edge Case → SKILL.md Update

**Trigger:** You discover a scenario not handled before

**Agent captures:**
```yaml
edge_case: "New scenario found"
handling: "How you handled it"
test: "How to test for it"
```

**Agent updates SKILL.md:**
```markdown
**Edge cases covered:**
- ✅ [edge_case] - [handling]

**Test coverage:**
- ✅ [test]
```

---

## Integration with skill-learner

**Relationship:**

```
live-skill-learner (this agent)
  ↓ Uses internally ↓
skill-learner skill
  ↓ Applies changes to ↓
Actual skills (seo-specialist, aws-eks-deploy, etc.)
```

**Workflow:**
1. **live-skill-learner** captures learning in real-time
2. Invokes **skill-learner** to apply updates
3. **skill-learner** updates the target skill
4. Verification and confirmation

---

## Success Metrics

**After 10 features using skills:**
- ✅ 80% reduction in repeated issues
- ✅ 50% faster feature implementation (no repeat debugging)
- ✅ Skills become expert-level (handle all edge cases)
- ✅ Zero knowledge loss (all learnings preserved)

**After 50 features:**
- ✅ Near-zero repeated issues
- ✅ Skills handle 95% of scenarios automatically
- ✅ Production-ready without manual intervention
- ✅ Skills rival professional specialists

---

## Example: Full Cycle

**Feature:** Deploying application to AWS EKS

**Issue 1:** "kubectl connection timeout"
- **Agent captures:** Connection timeout issue
- **You fix:** Add retry logic with exponential backoff
- **Agent updates:** `aws-eks-deploy/scripts/tool.py` with retry logic
- **Result:** ✅ Updated immediately

**Issue 2:** "Pods stuck in Pending state"
- **Agent captures:** Pod pending issue
- **You fix:** Increase node resources
- **Agent updates:** `aws-eks-deploy/README.md` troubleshooting section
- **Result:** ✅ Documented immediately

**Issue 3:** "LoadBalancer not getting external IP"
- **Agent captures:** LoadBalancer issue
- **You fix:** Add security group rules
- **Agent updates:** `aws-eks-deploy/scripts/tool.py` auto-creates rules
- **Result:** ✅ Automated immediately

**Feature completes with 3 skill improvements!**

**Next time someone uses `aws-eks-deploy`:**
- ✅ No connection timeout (auto-retry)
- ✅ No pending pods (right resources)
- ✅ LoadBalancer works (auto-rules)

**Skills evolved in real-time!** 🚀

---

## Benefits

### For Current Feature
- ✅ Issues get fixed properly
- ✅ Documentation stays current
- ✅ Edge cases are handled

### For Future Features
- ✅ Same issues don't repeat
- ✅ Skills are smarter
- ✅ Development is faster
- ✅ Quality is higher

### For Skills Library
- ✅ Continuous improvement
- ✅ Expert-level knowledge accumulation
- ✅ Production-tested patterns
- ✅ Zero-knowledge-loss

---

**Status:** Production-ready ✅
**Activation:** Automatic during feature implementation
**Impact:** Compounding skill intelligence over time
**Result:** Skills become expert-level automatically! 🚀
