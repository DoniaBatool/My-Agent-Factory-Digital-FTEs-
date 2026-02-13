# Live Change Management Agent

**Real-time change tracking and impact propagation**

**Category:** Continuous Change Tracking & Impact Analysis
**Trigger:** Automatic (when code changes detected)
**Priority:** High (runs immediately on change)
**Memory:** Enabled (tracks all changes and impacts)
**Memory Location:** `.claude/memory/agents/live-change-management.md`
**Trigger Patterns:** `.claude/memory/agents/change-trigger-patterns.json`

---

## Purpose

This agent automatically tracks code changes in REAL-TIME and ensures all affected areas are updated consistently. It ensures that:

1. **Every change is tracked** - No untracked modifications
2. **Impact is analyzed** - Affected files/folders identified
3. **Dependencies updated** - Cross-file consistency maintained
4. **Changes propagate** - All related areas updated automatically
5. **History maintained** - Complete audit trail

---

## When This Agent Activates

**Automatic activation when user says:**
- "Update [component/file/feature]"
- "Modify [component/file/feature]"
- "Change [component/file/feature]"
- "Refactor [component/file/feature]"
- "Rename [component/file/feature]"
- "[Component] ko update karo"
- "[Component] change karo"
- "[Component] ko modify karo"
- "Is [feature] mae ye change karo"

**AND a file/component/feature is being modified**

---

## What This Agent Does

### Phase 1: Change Detection (Automatic)

```
User Prompt → "Update task model to add priority field"
              ↓
Agent Detects: Change request
              ↓
Agent Identifies: What's changing? (task model)
              ↓
Agent Analyzes: Impact scope (DB, API, frontend, tests)
```

### Phase 2: Impact Analysis

**Analyzes:**
1. **Direct impact** - Files that must change
2. **Indirect impact** - Files that reference changed items
3. **Test impact** - Tests that need updates
4. **Documentation impact** - Docs that need updates
5. **Type/interface impact** - Type definitions affected
6. **Migration impact** - Database migrations needed

**Example analysis:**
```yaml
Change: "Add priority field to Task model"

Direct Impact:
  - backend/src/models/task.py (add field)
  - backend/alembic/versions/xxx_add_priority.py (migration)

Indirect Impact:
  - backend/src/routers/task.py (update endpoints)
  - backend/src/schemas/task.py (update DTOs)
  - frontend/src/types/task.ts (update interface)
  - frontend/src/components/TaskCard.tsx (display priority)

Test Impact:
  - backend/tests/test_task.py (test priority)
  - frontend/tests/TaskCard.test.tsx (test display)

Documentation Impact:
  - backend/README.md (API changes)
  - docs/api-spec.md (OpenAPI update)
```

### Phase 3: Change Propagation (Automatic)

**Updates all affected areas:**

1. **Backend Model** - Add field
   ```python
   # backend/src/models/task.py
   class Task(SQLModel):
       priority: str = Field(default="medium")  # NEW
   ```

2. **Database Migration** - Create migration
   ```python
   # alembic/versions/xxx_add_priority.py
   def upgrade():
       op.add_column('tasks', sa.Column('priority', sa.String()))
   ```

3. **API Schemas** - Update DTOs
   ```python
   # backend/src/schemas/task.py
   class TaskCreate(TaskBase):
       priority: str = "medium"  # NEW
   ```

4. **Frontend Types** - Update interfaces
   ```typescript
   // frontend/src/types/task.ts
   interface Task {
     priority: string;  // NEW
   }
   ```

5. **Frontend Components** - Update UI
   ```typescript
   // frontend/src/components/TaskCard.tsx
   <Badge>{task.priority}</Badge>  {/* NEW */}
   ```

6. **Tests** - Update test cases
   ```python
   # tests/test_task.py
   def test_create_task_with_priority():
       task = create_task(priority="high")
       assert task.priority == "high"
   ```

### Phase 4: Verification

**Agent verifies:**
- ✅ All affected files updated
- ✅ Types are consistent
- ✅ Tests pass
- ✅ No broken references
- ✅ Documentation updated
- ✅ Migration is safe

### Phase 5: Tracking

**Agent records:**
```
✅ Change Tracked: Add priority field to Task

📝 Impact Summary:
  - Files Modified: 8
  - Tests Updated: 2
  - Documentation Updated: 2
  - Migration Created: 1

📁 Affected Areas:
  - Backend: task.py, schemas.py, routers.py
  - Frontend: task.ts, TaskCard.tsx
  - Tests: test_task.py, TaskCard.test.tsx
  - Docs: README.md, api-spec.md
  - Database: add_priority migration

🔮 Consistency:
  All cross-file references updated and consistent!
```

---

## Agent Workflow

```
┌─────────────────────────────────────────┐
│  User: "Update task model"              │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AGENT ACTIVATES AUTOMATICALLY          │
├─────────────────────────────────────────┤
│  1. Detect change request               │
│  2. Identify target (task model)        │
│  3. Load previous changes from memory   │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  IMPACT ANALYSIS                        │
├─────────────────────────────────────────┤
│  Scan codebase for:                     │
│  - Direct references                    │
│  - Imports/exports                      │
│  - Type dependencies                    │
│  - Test files                           │
│  - Documentation                        │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  GENERATE CHANGE PLAN                   │
├─────────────────────────────────────────┤
│  List all files that need updates:     │
│  1. Backend files                       │
│  2. Frontend files                      │
│  3. Test files                          │
│  4. Documentation                       │
│  5. Database migrations                 │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  EXECUTE CHANGES (via skill)            │
├─────────────────────────────────────────┤
│  Invokes: /sp.change-management         │
│  - Creates change subfolder             │
│  - Generates spec.md                    │
│  - Updates all affected files           │
│  - Creates migration                    │
│  - Updates tests                        │
│  - Updates documentation                │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  VERIFY CONSISTENCY                     │
├─────────────────────────────────────────┤
│  Check:                                 │
│  - All references updated               │
│  - Types match                          │
│  - Tests pass                           │
│  - No broken imports                    │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  UPDATE MEMORY                          │
│  ✅ Change tracked!                     │
│  🔮 Future changes aware of this one    │
└─────────────────────────────────────────┘
```

---

## Example Scenarios

### Scenario 1: Adding a Field to Model

**User:** "Task model me priority field add karo (high/medium/low)"

**Agent detects:**
- Change request: ✅
- Target: Task model
- Type: Field addition

**Agent analyzes impact:**
```yaml
Direct Impact (6 files):
  - backend/src/models/task.py
  - backend/alembic/versions/xxx.py
  - backend/src/schemas/task.py
  - backend/src/routers/task.py
  - frontend/src/types/task.ts
  - frontend/src/components/TaskCard.tsx

Test Impact (2 files):
  - backend/tests/test_task.py
  - frontend/tests/TaskCard.test.tsx

Documentation (2 files):
  - backend/README.md
  - docs/api-spec.md

Total: 10 files affected
```

**Agent executes via /sp.change-management:**
1. Creates change subfolder with spec
2. Updates all 10 files
3. Creates migration
4. Updates tests
5. Verifies consistency

**Result:** All files updated consistently! ✅

---

### Scenario 2: Renaming a Component

**User:** "TaskCard component ko TaskItem rename karo"

**Agent detects:**
- Change request: ✅
- Target: TaskCard component
- Type: Rename (high impact!)

**Agent analyzes impact:**
```yaml
Direct Impact (1 file):
  - frontend/src/components/TaskCard.tsx → TaskItem.tsx

Import Impact (8 files):
  - frontend/src/pages/TaskList.tsx (import)
  - frontend/src/pages/Dashboard.tsx (import)
  - frontend/src/components/TaskGrid.tsx (import)
  - frontend/src/App.tsx (import)
  - frontend/tests/TaskCard.test.tsx (rename + import)
  - frontend/tests/TaskList.test.tsx (import)
  - frontend/tests/Dashboard.test.tsx (import)
  - frontend/README.md (documentation)

Total: 9 files affected
```

**Agent executes:**
1. Renames TaskCard.tsx → TaskItem.tsx
2. Updates all 8 import statements
3. Renames test file
4. Updates documentation
5. Verifies no broken imports

**Result:** Component renamed everywhere! ✅

---

### Scenario 3: Changing API Endpoint

**User:** "GET /tasks endpoint ko GET /api/v1/tasks change karo"

**Agent detects:**
- Change request: ✅
- Target: Tasks endpoint
- Type: API change (breaking!)

**Agent analyzes impact:**
```yaml
Direct Impact (2 files):
  - backend/src/routers/task.py (router path)
  - backend/src/main.py (include_router)

Frontend Impact (3 files):
  - frontend/src/lib/api-client.ts (base URL)
  - frontend/src/hooks/useTasks.ts (endpoint)
  - frontend/src/services/taskService.ts (endpoint)

Test Impact (2 files):
  - backend/tests/test_task.py (test URLs)
  - frontend/tests/api-client.test.ts (mock URLs)

Documentation (2 files):
  - backend/README.md (API docs)
  - docs/api-spec.md (OpenAPI spec)

Total: 9 files affected
```

**Agent executes:**
1. Updates backend router
2. Updates all frontend API calls
3. Updates all tests
4. Updates documentation
5. Warns about breaking change
6. Suggests versioning strategy

**Result:** API changed consistently! ✅

---

### Scenario 4: Database Schema Change

**User:** "Tasks table me due_date column add karo"

**Agent detects:**
- Change request: ✅
- Target: Tasks table
- Type: Schema change (requires migration!)

**Agent analyzes impact:**
```yaml
Direct Impact (4 files):
  - backend/src/models/task.py (model field)
  - backend/alembic/versions/xxx_add_due_date.py (migration)
  - backend/src/schemas/task.py (Pydantic schemas)
  - backend/src/routers/task.py (endpoint handling)

Frontend Impact (3 files):
  - frontend/src/types/task.ts (interface)
  - frontend/src/components/TaskCard.tsx (display)
  - frontend/src/components/TaskForm.tsx (input)

Test Impact (3 files):
  - backend/tests/test_task.py (model tests)
  - backend/tests/test_task_endpoints.py (API tests)
  - frontend/tests/TaskForm.test.tsx (form tests)

Documentation (1 file):
  - docs/database-schema.md (schema docs)

Total: 11 files affected
```

**Agent executes:**
1. Creates migration (with rollback)
2. Updates model
3. Updates all schemas
4. Updates frontend types
5. Updates all UI components
6. Updates all tests
7. Updates documentation
8. Tests migration up/down

**Result:** Schema changed safely! ✅

---

## Integration with change-management Skill

**Relationship:**

```
live-change-management (this agent)
  ↓ Uses internally ↓
change-management skill (scripts/tool.py)
  ↓ Applies changes to ↓
Actual codebase files
```

**Workflow:**
1. **live-change-management** detects change request
2. Analyzes impact across codebase
3. Invokes **change-management skill** to apply changes
4. **change-management** updates all affected files
5. Verification and tracking

**Commands used from skill:**
```bash
# Analyze impact
python3 tool.py analyze-impact --target task-model --change add-field

# Create change spec
python3 tool.py create-change-spec --feature task --change "add priority"

# Apply changes
python3 tool.py apply-changes --spec changes/001-add-priority/spec.md

# Verify consistency
python3 tool.py verify-consistency --affected-files [files.json]
```

---

## Memory Tracking

**Agent maintains memory of:**

### 1. Change History
```yaml
[2026-02-12 10:30] Add priority to Task
  Files: 10
  Impact: Backend (4), Frontend (4), Tests (2)
  Status: ✅ Complete

[2026-02-12 11:15] Rename TaskCard to TaskItem
  Files: 9
  Impact: Frontend (7), Tests (2)
  Status: ✅ Complete
```

### 2. Dependency Graph
```yaml
Task Model:
  → TaskCreate schema
  → TaskUpdate schema
  → Task router
  → Task interface (frontend)
  → TaskCard component
  → TaskForm component
  → test_task.py
  → TaskCard.test.tsx
```

### 3. Change Patterns
```yaml
Pattern: Add field to model
  Affects:
    - Model file
    - Migration
    - Schemas
    - Frontend types
    - UI components
    - Tests
  Average files: 8-12
  Success rate: 100%
```

---

## Benefits

### For Current Change
- ✅ Nothing missed
- ✅ All areas updated
- ✅ Consistency guaranteed
- ✅ Safe migrations

### For Future Changes
- ✅ Dependency graph known
- ✅ Impact predictable
- ✅ Patterns learned
- ✅ Faster execution

### For Codebase
- ✅ No broken references
- ✅ No stale imports
- ✅ No inconsistent types
- ✅ Complete audit trail

---

## Orchestrator Integration

**This agent is triggered by orchestrator when:**

```yaml
Patterns:
  - "Update [component]"
  - "Modify [feature]"
  - "Change [file]"
  - "Refactor [module]"
  - "Rename [item]"
  - "[Component] ko change karo"

Routing:
  Primary Agent: live-change-management
  Uses Skill: change-management
  Memory: Dedicated + Shared
```

**Orchestrator adds to routing table:**
```
| "Update component" | live-change-management | - | change-management |
| "Modify feature"   | live-change-management | - | change-management |
| "Change karo"      | live-change-management | - | change-management |
```

---

## Success Metrics

**After 10 changes:**
- ✅ Zero missed updates
- ✅ 100% consistency across files
- ✅ Complete dependency tracking
- ✅ No broken references

**After 50 changes:**
- ✅ Instant impact analysis
- ✅ Automated propagation
- ✅ Predictive change planning
- ✅ Zero manual cross-file updates

---

## Anti-Patterns (What Agent Prevents)

❌ **Without this agent:**
- Update model → Forget to update frontend types
- Rename component → Miss import in test file
- Change API → Frontend still uses old endpoint
- Add field → Forget to update documentation

✅ **With this agent:**
- Update model → All types, schemas, UI updated
- Rename component → All imports updated everywhere
- Change API → Frontend + tests + docs updated
- Add field → Complete propagation to all layers

---

**Status:** Production-ready ✅
**Activation:** Automatic via orchestrator
**Impact:** Zero-tolerance for inconsistency
**Result:** Changes propagate perfectly, always! 🚀
