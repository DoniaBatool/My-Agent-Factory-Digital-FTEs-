---
name: database-schema-expander
description: Automated database schema evolution with Alembic migrations and SQLModel
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



# Skill: Database Schema Expander

## Purpose

Add tables/columns safely to an existing schema while keeping the app running, with zero-downtime migrations.

## When to Use

- Adding new tables to existing database
- Adding columns to existing tables (nullable or with defaults)
- Creating self-referential relationships (parent/child hierarchies)
- Adding indexes for query performance
- Implementing partial indexes for conditional uniqueness
- Modifying schema for new features (recurring tasks, tags, priorities)

## Prerequisites

- Alembic installed and configured
- SQLModel models defined
- Database connection pooling configured
- Understanding of backward compatibility requirements

## Usage

```bash
# Invoke this skill for schema changes
/sp.database-schema-expander "Add recurring tasks fields to tasks table"
```

## Implementation Steps

### Phase 1: Design Schema Changes

1. **Define new columns/tables** with SQLModel
   - Use appropriate types (String, Integer, DateTime, Boolean)
   - Mark nullable columns explicitly (`Optional[str] = Field(default=None)`)
   - Define relationships (`Relationship(back_populates="...")`)

2. **Design relationships**
   - Foreign keys with proper `ondelete` behavior (CASCADE, SET NULL, RESTRICT)
   - Self-referential FKs for parent/child hierarchies
   - Many-to-many via junction tables

3. **Plan indexes**
   - Standard indexes on frequently queried columns
   - Composite indexes for multi-column queries
   - Partial indexes for conditional uniqueness
   - Unique constraints for preventing duplicates

### Phase 2: Create Migration (Backward Compatible)

1. **Generate migration**
   ```bash
   alembic revision --autogenerate -m "Add recurring fields to tasks"
   ```

2. **Add columns as nullable initially**
   ```python
   op.add_column('tasks',
       sa.Column('is_recurring', sa.Boolean(),
                 nullable=False, server_default='false'))
   ```

3. **Add foreign key constraints**
   ```python
   op.create_foreign_key(
       'fk_tasks_parent_task_id',
       'tasks', 'tasks',
       ['parent_task_id'], ['id'],
       ondelete='CASCADE'
   )
   ```

4. **Add indexes (use CREATE INDEX CONCURRENTLY in production)**
   ```python
   # Standard index
   op.create_index('ix_tasks_parent_task_id', 'tasks', ['parent_task_id'])

   # Partial index (conditional)
   op.execute("""
       CREATE INDEX ix_tasks_user_recurring
       ON tasks (user_id, is_recurring)
       WHERE is_recurring = TRUE
   """)

   # Unique partial index (idempotency)
   op.execute("""
       CREATE UNIQUE INDEX ix_tasks_parent_due_unique
       ON tasks (parent_task_id, due_date)
       WHERE parent_task_id IS NOT NULL AND completed = FALSE
   """)
   ```

5. **Test downgrade path**
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```

### Phase 3: Backfill (if needed)

1. **Write backfill script** for existing data
2. **Run in controlled batches** (1000 rows at a time)
3. **Validate counts** match expectations
4. **Monitor performance** during backfill

### Phase 4: Tighten Constraints

1. **After backfill completes**, add NOT NULL constraints
2. **Remove deprecated columns** in separate migration
3. **Update application code** to use new schema

## Key Patterns

### Pattern 1: Self-Referential Foreign Keys

**Use Case:** Parent/child relationships (recurring task → occurrences)

**SQLModel:**
```python
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_task_id: Optional[int] = Field(default=None, foreign_key="tasks.id")

    # Relationships
    parent_task: Optional["Task"] = Relationship(
        back_populates="child_occurrences",
        sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    child_occurrences: List["Task"] = Relationship(back_populates="parent_task")
```

**Migration:**
```python
op.add_column('tasks', sa.Column('parent_task_id', sa.Integer(), nullable=True))
op.create_foreign_key(
    'fk_tasks_parent_task_id',
    'tasks', 'tasks',
    ['parent_task_id'], ['id'],
    ondelete='CASCADE'  # Delete children when parent deleted
)
op.create_index('ix_tasks_parent_task_id', 'tasks', ['parent_task_id'])
```

### Pattern 2: Partial Indexes (Conditional)

**Use Case:** Index only subset of rows (performance optimization)

**Example:** Index only recurring tasks
```python
op.execute("""
    CREATE INDEX ix_tasks_user_recurring
    ON tasks (user_id, is_recurring)
    WHERE is_recurring = TRUE
""")
```

**Benefits:**
- Smaller index size (only recurring tasks)
- Faster queries filtering by `is_recurring = TRUE`
- Lower maintenance cost

### Pattern 3: Unique Partial Indexes (Idempotency)

**Use Case:** Prevent duplicates with conditional uniqueness

**Example:** Prevent duplicate next occurrences
```python
op.execute("""
    CREATE UNIQUE INDEX ix_tasks_parent_due_unique
    ON tasks (parent_task_id, due_date)
    WHERE parent_task_id IS NOT NULL AND completed = FALSE
""")
```

**Benefits:**
- Database-level idempotency enforcement
- Prevents race conditions (concurrent requests)
- Clear error message (IntegrityError)

**Application Code:**
```python
try:
    session.add(next_occurrence)
    session.commit()
except IntegrityError:
    session.rollback()
    logger.warning("Next occurrence already exists (idempotency)")
    # Return existing occurrence instead of creating duplicate
```

### Pattern 4: Date Columns with Time Zones

**Use Case:** Storing due dates, recurrence end dates

**SQLModel:**
```python
due_date: Optional[datetime] = Field(default=None)
recurrence_end_date: Optional[datetime] = Field(default=None)
```

**Migration:**
```python
op.add_column('tasks', sa.Column('due_date', sa.DateTime(), nullable=True))
```

**Edge Cases:**
- Month-end dates (Jan 31 → Feb 28/29) - Handle with `dateutil.relativedelta`
- Leap years (Feb 29) - Automatically handled by relativedelta
- Timezone conversions - Store UTC, convert on display

## Common Pitfalls

### Pitfall 1: Long-Running Migrations Block Writes

**Problem:** Adding NOT NULL constraint without default locks table

**Solution:**
```python
# BAD: Locks table during backfill
op.add_column('tasks', sa.Column('new_field', sa.String(), nullable=False))

# GOOD: Add as nullable, backfill, then tighten
op.add_column('tasks', sa.Column('new_field', sa.String(), nullable=True))
# (backfill in separate script)
# (then in future migration: ALTER COLUMN SET NOT NULL)
```

### Pitfall 2: Missing Cascade Deletes Cause Orphans

**Problem:** Deleting parent task leaves child occurrences

**Solution:**
```python
op.create_foreign_key(
    'fk_tasks_parent_task_id',
    'tasks', 'tasks',
    ['parent_task_id'], ['id'],
    ondelete='CASCADE'  # Auto-delete children
)
```

### Pitfall 3: Indexes Not Used in Queries

**Problem:** Created index on (user_id, is_recurring) but query filters (is_recurring, user_id)

**Solution:** Index column order matters. Put most selective column first or match query order.

### Pitfall 4: Unique Constraints Too Strict

**Problem:** Unique constraint on (parent_task_id, due_date) blocks legitimate use cases

**Solution:** Use partial indexes with WHERE clause
```python
# Only enforce uniqueness for incomplete tasks
WHERE parent_task_id IS NOT NULL AND completed = FALSE
```

## Testing Strategy

### Unit Tests (Migration Validation)

```python
def test_migration_upgrade_and_downgrade():
    """Test migration applies and rolls back cleanly."""
    # Run upgrade
    alembic upgrade head
    # Verify columns exist
    assert column_exists('tasks', 'is_recurring')
    # Run downgrade
    alembic downgrade -1
    # Verify columns removed
    assert not column_exists('tasks', 'is_recurring')
```

### Integration Tests (Schema Validation)

```python
def test_self_referential_relationship():
    """Test parent/child relationship works."""
    parent = Task(title="Parent", is_recurring=True)
    session.add(parent)
    session.commit()

    child = Task(title="Child", parent_task_id=parent.id)
    session.add(child)
    session.commit()

    # Verify relationship
    assert parent.child_occurrences[0].id == child.id
    assert child.parent_task.id == parent.id
```

### Edge Case Tests

```python
def test_cascade_delete():
    """Test deleting parent deletes children."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    child = Task(title="Child", parent_task_id=parent.id)
    session.add(child)
    session.commit()

    session.delete(parent)
    session.commit()

    # Verify child deleted
    assert session.get(Task, child.id) is None
```

```python
def test_unique_partial_index_idempotency():
    """Test partial unique index prevents duplicates."""
    parent = Task(title="Parent")
    session.add(parent)
    session.commit()

    due = datetime(2026, 2, 10, 10, 0)
    occ1 = Task(title="Occ1", parent_task_id=parent.id, due_date=due, completed=False)
    session.add(occ1)
    session.commit()

    # Try to create duplicate
    occ2 = Task(title="Occ2", parent_task_id=parent.id, due_date=due, completed=False)
    session.add(occ2)

    with pytest.raises(IntegrityError):
        session.commit()
```

## Examples

See `examples/` directory for:
- `example-1-recurring-tasks.md`: Self-referential FK + partial indexes (Phase V)
- `example-2-tags.md`: Many-to-many relationship with junction table

## Related Skills

- `/sp.database-engineer` - Database optimization and query tuning
- `/sp.mcp-tool-builder` - Tools that use new schema fields
- `/sp.transaction-management` - Atomic operations with new schema
- `/sp.user-isolation` - Ensure new tables enforce user_id filtering
- `/sp.edge-case-tester` - Test schema edge cases

## Success Criteria

- [ ] Migration applies cleanly (upgrade + downgrade tested)
- [ ] No long-running locks (columns added as nullable with defaults)
- [ ] Indexes created for all foreign keys
- [ ] Partial indexes used where appropriate (conditional uniqueness)
- [ ] Cascade delete configured for parent/child relationships
- [ ] SQLModel relationships defined (back_populates)
- [ ] Edge cases tested (orphans, duplicates, cascade deletes)
- [ ] Backward compatibility maintained (code handles old + new schema)
- [ ] Production deployment plan documented