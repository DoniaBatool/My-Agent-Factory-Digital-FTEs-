---
name: edge-case-tester
description: Comprehensive edge case testing framework covering 57+ scenarios for bulletproof code
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



# Skill: Edge Case Tester

## Purpose

Find and prevent failures by systematically testing edge cases beyond "happy path" to ensure robustness.

## When to Use

- After implementing a new feature
- Before releasing to production
- When bugs are reported (expand test coverage)
- For recurring patterns (date arithmetic, idempotency, relationships)
- When validating natural language input parsing
- For database constraints and relationships

## Prerequisites

- Feature implementation complete
- Test framework configured (pytest for backend)
- Database migrations applied
- Understanding of feature requirements

## Usage

```bash
# Invoke this skill for edge case testing
/sp.edge-case-tester "Test recurring tasks edge cases (month-end, leap years, duplicates)"
```

## Implementation Steps

### Phase 1: Build Edge-Case Matrix

1. **Identify all inputs and constraints**
   - Required vs optional parameters
   - Data types and ranges
   - Natural language vs structured input
   - Database constraints (unique, foreign key, not null)

2. **List boundary values**
   - Min/max values (0, 1, 365, MAX_INT)
   - Empty strings, null, undefined
   - Extremes (very long strings, far future dates)

3. **List "weird but valid" values**
   - Unicode/emoji in text fields
   - Month-end dates (Jan 31, Feb 29)
   - Leap years
   - Concurrent operations
   - Duplicate operations (idempotency)

4. **Create edge case matrix**
   ```markdown
   | Category | Edge Case | Expected Behavior | Test Status |
   |----------|-----------|-------------------|-------------|
   | Date Arithmetic | Jan 31 + 1 month | Feb 28/29 | ✅ |
   | Date Arithmetic | Feb 29 + 1 year (non-leap) | Feb 28 | ✅ |
   | Idempotency | Duplicate occurrence | IntegrityError handled | ✅ |
   | Concurrency | Complete task twice | Second returns existing | ❌ |
   ```

### Phase 2: Execute Tests

1. **Manual probes** (exploratory testing)
   - Try edge cases through UI/API
   - Document unexpected behaviors
   - Capture error messages

2. **Automated tests** (regression prevention)
   - Unit tests for validation logic
   - Integration tests for database operations
   - E2E tests for user workflows

3. **Load testing** (concurrency)
   - Simulate concurrent requests
   - Test race conditions
   - Verify database constraints hold

### Phase 3: Report and Fix

1. **Document findings**
   - Repro steps (exact inputs, sequence)
   - Expected vs actual behavior
   - Error messages and stack traces

2. **Categorize severity**
   - Critical: Data loss, security breach
   - High: Feature broken, user blocked
   - Medium: Edge case fails, workaround exists
   - Low: Cosmetic, rare scenario

3. **Suggest fixes**
   - Validation improvements
   - Error handling
   - Database constraints
   - User-facing error messages

## Test Dimensions (Comprehensive Checklist)

### Dimension 1: Input Shape
- [ ] Empty strings (`""`)
- [ ] Whitespace only (`"   "`)
- [ ] Very long strings (>1000 chars)
- [ ] Unicode/emoji in text fields
- [ ] Invalid types (string when int expected)
- [ ] Null/None values
- [ ] Missing required fields

### Dimension 2: Ambiguity
- [ ] Partial matches (fuzzy search)
- [ ] Multiple matches (non-unique identifiers)
- [ ] Case sensitivity ("Daily" vs "daily")
- [ ] Synonyms ("high" vs "urgent" vs "important")
- [ ] Missing identifiers (no task_id provided)

### Dimension 3: Time & Dates
- [ ] Past dates (yesterday)
- [ ] Far future dates (>10 years)
- [ ] Month-end dates (Jan 31, Feb 29)
- [ ] Leap years (Feb 29 in leap vs non-leap year)
- [ ] Timezone issues (UTC vs local time)
- [ ] DST transitions (spring forward, fall back)
- [ ] Natural language ambiguity ("next Friday" on Friday)
- [ ] Invalid date strings ("Feb 30", "13:99")

### Dimension 4: Concurrency & Race Conditions
- [ ] Double-submit (click button twice rapidly)
- [ ] Simultaneous updates (two users edit same task)
- [ ] Retry logic (network timeout, user retries)
- [ ] Idempotency (duplicate operations should be safe)
- [ ] Database locks (concurrent writes to same row)

### Dimension 5: Security
- [ ] Cross-user access (user_id mismatch)
- [ ] SQL injection strings (`'; DROP TABLE users; --`)
- [ ] XSS attempts (`<script>alert('xss')</script>`)
- [ ] Authorization bypass (missing user_id check)
- [ ] Horizontal privilege escalation (access other user's data)

### Dimension 6: Resilience
- [ ] Tool failures (external API down)
- [ ] Database timeouts (slow query)
- [ ] Network failures (connection lost)
- [ ] Partial outages (read replica down)
- [ ] Malformed responses (invalid JSON)
- [ ] Missing dependencies (library not installed)

### 🆕 Dimension 7: Date Arithmetic (Phase V)
- [ ] Month-end edge cases (Jan 31 → Feb 28/29)
- [ ] Leap year handling (Feb 29 + 1 year)
- [ ] Year-end rollovers (Dec 31 + 1 day)
- [ ] Custom intervals (every 3 days, every 2 weeks)
- [ ] Recurrence end dates (stop creating occurrences)
- [ ] Missing due dates (default to current time)

### 🆕 Dimension 8: Recurring Patterns (Phase V)
- [ ] Invalid patterns ("every tuesday", "sometimes")
- [ ] Zero interval ("every 0 days")
- [ ] Huge intervals ("every 1000 months")
- [ ] Negative intervals ("every -5 days")
- [ ] Pattern typos ("daly" instead of "daily")
- [ ] Case variations ("DAILY" vs "daily" vs "Daily")

### 🆕 Dimension 9: Idempotency (Phase V)
- [ ] Duplicate next occurrences (same parent, same due_date)
- [ ] Concurrent completion (two requests complete same recurring task)
- [ ] Retry after partial failure (network timeout)
- [ ] Unique constraint violations (IntegrityError)
- [ ] Graceful degradation (return existing instead of error)

### 🆕 Dimension 10: Self-Referential Relationships (Phase V)
- [ ] Orphan records (parent deleted, children remain)
- [ ] Cascade delete (parent deleted, children auto-deleted)
- [ ] Circular references (task A → task B → task A)
- [ ] Deep hierarchies (10+ levels)
- [ ] Missing parent (parent_task_id points to non-existent task)
- [ ] Cross-user references (parent belongs to user A, child to user B)

## Key Patterns

### Pattern 1: Month-End Date Arithmetic

**Problem:** Adding months to dates near month-end
```python
# Jan 31 + 1 month = Feb 31 (INVALID)
# Expected: Feb 28 or Feb 29 (leap year)
```

**Solution:** Use `dateutil.relativedelta`
```python
from dateutil.relativedelta import relativedelta

# Automatically handles month-end
next_date = datetime(2026, 1, 31) + relativedelta(months=1)
# Result: datetime(2026, 2, 28)  ✅
```

**Tests:**
```python
def test_month_end_january_to_february():
    """Test Jan 31 + 1 month = Feb 28/29."""
    jan_31 = datetime(2026, 1, 31, 10, 0)
    feb_date = jan_31 + relativedelta(months=1)
    assert feb_date == datetime(2026, 2, 28, 10, 0)

def test_month_end_leap_year():
    """Test Jan 31 + 1 month in leap year = Feb 29."""
    jan_31_leap = datetime(2024, 1, 31, 10, 0)  # 2024 is leap year
    feb_date = jan_31_leap + relativedelta(months=1)
    assert feb_date == datetime(2024, 2, 29, 10, 0)

def test_month_end_march_to_february():
    """Test Mar 31 + 11 months = Feb 28/29 (next year)."""
    mar_31 = datetime(2026, 3, 31, 10, 0)
    feb_date = mar_31 + relativedelta(months=11)
    assert feb_date == datetime(2027, 2, 28, 10, 0)
```

### Pattern 2: Leap Year Handling

**Problem:** Feb 29 + 1 year in non-leap year
```python
# Feb 29, 2024 + 1 year = Feb 29, 2025 (INVALID - not leap year)
# Expected: Feb 28, 2025
```

**Solution:** `relativedelta` automatically adjusts
```python
leap_date = datetime(2024, 2, 29, 10, 0)  # 2024 is leap year
next_year = leap_date + relativedelta(years=1)
# Result: datetime(2025, 2, 28, 10, 0)  ✅
```

**Tests:**
```python
def test_leap_year_to_non_leap_year():
    """Test Feb 29 (leap) + 1 year = Feb 28 (non-leap)."""
    feb_29_2024 = datetime(2024, 2, 29, 10, 0)
    feb_2025 = feb_29_2024 + relativedelta(years=1)
    assert feb_2025 == datetime(2025, 2, 28, 10, 0)

def test_leap_year_to_leap_year():
    """Test Feb 29 (leap) + 4 years = Feb 29 (leap)."""
    feb_29_2024 = datetime(2024, 2, 29, 10, 0)
    feb_2028 = feb_29_2024 + relativedelta(years=4)
    assert feb_2028 == datetime(2028, 2, 29, 10, 0)

def test_non_leap_year_century():
    """Test century year (2100 is NOT leap year)."""
    # Most century years are not leap years (except divisible by 400)
    # 2000 was leap, 2100/2200/2300 are not, 2400 will be
    feb_29_2096 = datetime(2096, 2, 29, 10, 0)  # 2096 is leap
    feb_2100 = feb_29_2096 + relativedelta(years=4)
    assert feb_2100 == datetime(2100, 2, 28, 10, 0)  # 2100 not leap
```

### Pattern 3: Idempotency with Unique Partial Indexes

**Problem:** Concurrent requests create duplicate occurrences

**Solution:** Database-level idempotency with unique constraint
```sql
CREATE UNIQUE INDEX ix_tasks_parent_due_unique
ON tasks (parent_task_id, due_date)
WHERE parent_task_id IS NOT NULL AND completed = FALSE
```

**Application Code:**
```python
from sqlalchemy.exc import IntegrityError

def create_next_occurrence(session, parent_task, next_due):
    """Create next occurrence with idempotency."""
    next_occ = Task(
        parent_task_id=parent_task.id,
        due_date=next_due,
        completed=False
    )

    try:
        session.add(next_occ)
        session.commit()
        return next_occ
    except IntegrityError:
        # Duplicate already exists (idempotency)
        session.rollback()
        logger.warning("Next occurrence already exists")
        # Return existing occurrence
        existing = session.query(Task).filter(
            Task.parent_task_id == parent_task.id,
            Task.due_date == next_due,
            Task.completed == False
        ).first()
        return existing
```

**Tests:**
```python
def test_idempotency_duplicate_occurrence():
    """Test duplicate occurrence raises IntegrityError."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    due = datetime(2026, 2, 10, 10, 0)

    # Create first occurrence
    occ1 = Task(parent_task_id=parent.id, due_date=due, completed=False)
    session.add(occ1)
    session.commit()

    # Try to create duplicate
    occ2 = Task(parent_task_id=parent.id, due_date=due, completed=False)
    session.add(occ2)

    with pytest.raises(IntegrityError):
        session.commit()


def test_idempotency_graceful_handling():
    """Test graceful handling of duplicate occurrences."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    due = datetime(2026, 2, 10, 10, 0)

    # Create first occurrence
    result1 = create_next_occurrence(session, parent, due)
    assert result1 is not None

    # Try to create duplicate (should return existing)
    result2 = create_next_occurrence(session, parent, due)
    assert result2.id == result1.id  # Same occurrence


def test_idempotency_allows_different_due_dates():
    """Test different due dates are allowed."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    # Create occurrence for Feb 10
    occ1 = Task(parent_task_id=parent.id,
                due_date=datetime(2026, 2, 10), completed=False)
    session.add(occ1)
    session.commit()

    # Create occurrence for Feb 17 (should succeed)
    occ2 = Task(parent_task_id=parent.id,
                due_date=datetime(2026, 2, 17), completed=False)
    session.add(occ2)
    session.commit()  # No IntegrityError

    assert occ1.id != occ2.id
```

### Pattern 4: Self-Referential Relationship Edge Cases

**Problem:** Orphan records when parent deleted

**Solution:** Cascade delete in foreign key constraint
```python
op.create_foreign_key(
    'fk_tasks_parent_task_id',
    'tasks', 'tasks',
    ['parent_task_id'], ['id'],
    ondelete='CASCADE'  # Auto-delete children
)
```

**Tests:**
```python
def test_cascade_delete_children():
    """Test deleting parent deletes all children."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    # Create 3 child occurrences
    children = [
        Task(title=f"Child{i}", parent_task_id=parent.id)
        for i in range(3)
    ]
    session.add_all(children)
    session.commit()

    child_ids = [c.id for c in children]

    # Delete parent
    session.delete(parent)
    session.commit()

    # Verify children deleted
    for child_id in child_ids:
        assert session.get(Task, child_id) is None


def test_self_referential_relationship():
    """Test parent/child relationship works."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    child = Task(title="Child", parent_task_id=parent.id)
    session.add(child)
    session.commit()

    # Test forward relationship
    assert parent.child_occurrences[0].id == child.id

    # Test backward relationship
    assert child.parent_task.id == parent.id


def test_circular_reference_prevention():
    """Test circular references are prevented."""
    # Create task A
    task_a = Task(title="Task A")
    session.add(task_a)
    session.commit()

    # Try to make task A its own parent (should fail)
    task_a.parent_task_id = task_a.id
    session.add(task_a)

    # This should fail validation or FK constraint
    # (depends on implementation - check constraint or app-level validation)
    with pytest.raises((IntegrityError, ValueError)):
        session.commit()
```

## Common Pitfalls

### Pitfall 1: Not Testing Month-End Edge Cases

**Problem:** Code works for most dates but breaks on Jan 31, Feb 29, etc.

**Solution:** Always test month-end dates
```python
test_dates = [
    datetime(2026, 1, 31),  # Jan 31
    datetime(2026, 3, 31),  # Mar 31
    datetime(2026, 5, 31),  # May 31
    datetime(2024, 2, 29),  # Feb 29 (leap year)
]

for date in test_dates:
    next_date = date + relativedelta(months=1)
    # Verify no ValueError raised
```

### Pitfall 2: Assuming Idempotency Without Tests

**Problem:** Assuming operations are idempotent without testing

**Solution:** Test duplicate operations explicitly
```python
def test_create_task_idempotent():
    """Test creating same task twice."""
    params = {"title": "Test", "user_id": "123"}

    # First call
    result1 = create_task(**params)

    # Second call (should be idempotent)
    result2 = create_task(**params)

    # Should return same task or handle gracefully
    assert result1["task_id"] == result2["task_id"]
```

### Pitfall 3: Not Testing Cascade Deletes

**Problem:** Deleting parent leaves orphan children

**Solution:** Test cascade delete behavior
```python
def test_delete_parent_orphans_children():
    """Verify cascade delete works."""
    parent = create_task("Parent")
    child = create_task("Child", parent_task_id=parent.id)

    delete_task(parent.id)

    # Verify child is also deleted (not orphaned)
    with pytest.raises(ValueError, match="not found"):
        get_task(child.id)
```

### Pitfall 4: Not Testing Concurrent Operations

**Problem:** Race conditions not caught until production

**Solution:** Test concurrent operations
```python
import concurrent.futures

def test_concurrent_completion():
    """Test completing same task concurrently."""
    task = create_task("Test", is_recurring=True)

    # Complete task from 2 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(complete_task, task.id)
        future2 = executor.submit(complete_task, task.id)

        result1 = future1.result()
        result2 = future2.result()

    # Both should succeed (idempotency)
    # Only one next occurrence should be created
    next_occurrences = get_next_occurrences(task.id)
    assert len(next_occurrences) == 1
```

## Testing Strategy

### Unit Tests (Validation Logic)

Test validation functions independently:
```python
def test_validate_pattern_valid():
    assert _validate_pattern("daily") is None
    assert _validate_pattern("weekly") is None
    assert _validate_pattern("every 3 days") is None

def test_validate_pattern_invalid():
    with pytest.raises(ValueError):
        _validate_pattern("every tuesday")

def test_validate_pattern_zero_interval():
    with pytest.raises(ValueError, match="must be positive"):
        _validate_pattern("every 0 days")
```

### Integration Tests (Database Operations)

Test with real database:
```python
def test_recurring_task_month_end(db_session):
    """Integration test: month-end recurring task."""
    task = Task(
        title="Monthly report",
        is_recurring=True,
        recurrence_pattern="monthly",
        due_date=datetime(2026, 1, 31, 10, 0)
    )
    db_session.add(task)
    db_session.commit()

    # Complete task (should create next occurrence)
    complete_task(db_session, task.id)

    # Verify next occurrence created with correct date (Feb 28)
    next_occ = db_session.query(Task).filter(
        Task.parent_task_id == task.id
    ).first()

    assert next_occ is not None
    assert next_occ.due_date == datetime(2026, 2, 28, 10, 0)
```

### E2E Tests (User Workflows)

Test through API/UI:
```python
def test_e2e_recurring_task_leap_year(client, auth_headers):
    """E2E test: Create recurring task on Feb 29."""
    # Create task on leap year
    response = client.post("/tasks", headers=auth_headers, json={
        "title": "Leap year task",
        "is_recurring": True,
        "recurrence_pattern": "yearly",
        "due_date": "2024-02-29T10:00:00Z"
    })

    task_id = response.json()["id"]

    # Complete task
    client.post(f"/tasks/{task_id}/complete", headers=auth_headers)

    # Verify next occurrence created for Feb 28, 2025
    response = client.get(f"/tasks?parent_task_id={task_id}", headers=auth_headers)
    next_occ = response.json()[0]

    assert next_occ["due_date"] == "2025-02-28T10:00:00Z"
```

## Examples

See `examples/` directory for:
- `example-1-recurring-tasks-edge-cases.md`: Comprehensive recurring tasks edge case matrix (Phase V)
- `example-2-date-arithmetic.md`: Month-end and leap year test scenarios

## Related Skills

- `/sp.database-schema-expander` - Test database constraints and relationships
- `/sp.mcp-tool-builder` - Test MCP tool edge cases
- `/sp.qa-engineer` - Comprehensive QA strategy
- `/sp.backend-developer` - Implement fixes for edge cases found
- `/sp.robust-ai-assistant` - Already has date parsing edge cases documented

## Success Criteria

- [ ] Edge case matrix created for feature
- [ ] All date arithmetic edge cases tested (month-end, leap year)
- [ ] Idempotency tested (duplicate operations)
- [ ] Self-referential relationships tested (cascade delete, orphans)
- [ ] Concurrent operations tested (race conditions)
- [ ] Security edge cases tested (cross-user access)
- [ ] Natural language parsing edge cases tested (invalid input)
- [ ] All critical bugs have regression tests
- [ ] Tests run in CI/CD pipeline
- [ ] Edge cases documented for future reference