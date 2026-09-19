# Example 1: Recurring Tasks Schema (Phase V)

## Context

Phase V feature: Add recurring tasks support to existing tasks table. Requirements:
- Set tasks as recurring with patterns (daily, weekly, monthly, custom)
- Auto-create next occurrence when recurring task completed
- Track parent/child relationship between original task and occurrences
- Support recurrence end dates
- Prevent duplicate occurrences (idempotency)

## Schema Design

### New Columns on `tasks` Table

```python
class Task(SQLModel, table=True):
    # ... existing fields ...

    # Phase V: Recurring Tasks Fields
    is_recurring: bool = Field(
        default=False,
        index=True,
        description="Whether this task repeats"
    )
    recurrence_pattern: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Pattern like 'daily', 'weekly', 'every 3 days'"
    )
    recurrence_end_date: Optional[datetime] = Field(
        default=None,
        description="When to stop creating occurrences (null = infinite)"
    )
    parent_task_id: Optional[int] = Field(
        default=None,
        foreign_key="tasks.id",
        description="ID of parent recurring task (null for originals)"
    )

    # Relationships
    parent_task: Optional["Task"] = Relationship(
        back_populates="child_occurrences",
        sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    child_occurrences: List["Task"] = Relationship(
        back_populates="parent_task"
    )
```

## Migration (Alembic)

**File:** `alembic/versions/czrecan0aykx_add_recurring_fields_to_tasks.py`

```python
def upgrade() -> None:
    """Add recurring task fields and indexes."""

    # 1. Add columns (nullable initially for backward compatibility)
    op.add_column('tasks',
        sa.Column('is_recurring', sa.Boolean(),
                  nullable=False, server_default='false'))

    op.add_column('tasks',
        sa.Column('recurrence_pattern', sa.String(length=50), nullable=True))

    op.add_column('tasks',
        sa.Column('recurrence_end_date', sa.DateTime(), nullable=True))

    op.add_column('tasks',
        sa.Column('parent_task_id', sa.Integer(), nullable=True))

    # 2. Add foreign key constraint (self-referential with cascade delete)
    op.create_foreign_key(
        'fk_tasks_parent_task_id',
        'tasks', 'tasks',
        ['parent_task_id'], ['id'],
        ondelete='CASCADE'  # Delete children when parent deleted
    )

    # 3. Add partial index for filtering recurring tasks (performance)
    #    Only indexes rows where is_recurring = TRUE
    op.execute("""
        CREATE INDEX ix_tasks_user_recurring
        ON tasks (user_id, is_recurring)
        WHERE is_recurring = TRUE
    """)

    # 4. Add standard index on parent_task_id (for joins)
    op.create_index('ix_tasks_parent_task_id', 'tasks', ['parent_task_id'])

    # 5. Add unique partial index (idempotency - prevent duplicate occurrences)
    #    Ensures only ONE incomplete occurrence per parent task per due date
    op.execute("""
        CREATE UNIQUE INDEX ix_tasks_parent_due_unique
        ON tasks (parent_task_id, due_date)
        WHERE parent_task_id IS NOT NULL AND completed = FALSE
    """)


def downgrade() -> None:
    """Remove recurring task fields and indexes."""
    # Drop indexes first
    op.drop_index('ix_tasks_parent_due_unique', table_name='tasks')
    op.drop_index('ix_tasks_parent_task_id', table_name='tasks')
    op.drop_index('ix_tasks_user_recurring', table_name='tasks')

    # Drop foreign key constraint
    op.drop_constraint('fk_tasks_parent_task_id', 'tasks', type_='foreignkey')

    # Drop columns
    op.drop_column('tasks', 'parent_task_id')
    op.drop_column('tasks', 'recurrence_end_date')
    op.drop_column('tasks', 'recurrence_pattern')
    op.drop_column('tasks', 'is_recurring')
```

## Key Patterns Used

### 1. Self-Referential Foreign Key

**Purpose:** Track parent/child hierarchy (original recurring task → occurrences)

**Pattern:**
- `parent_task_id` → `tasks.id`
- `ondelete='CASCADE'` → Auto-delete children when parent deleted
- SQLModel relationship with `remote_side="Task.id"`

**Example Usage:**
```python
# Create parent recurring task
parent = Task(
    title="Buy milk",
    is_recurring=True,
    recurrence_pattern="weekly",
    due_date=datetime(2026, 2, 10, 9, 0)
)
session.add(parent)
session.commit()

# Create next occurrence (child)
next_occurrence = Task(
    title="Buy milk",  # Same title
    parent_task_id=parent.id,  # Link to parent
    due_date=datetime(2026, 2, 17, 9, 0),  # +1 week
    completed=False
)
session.add(next_occurrence)
session.commit()

# Query relationship
assert parent.child_occurrences[0].id == next_occurrence.id
assert next_occurrence.parent_task.id == parent.id
```

### 2. Partial Index (Performance Optimization)

**Purpose:** Index only recurring tasks (small subset) for fast filtering

**Pattern:**
```sql
CREATE INDEX ix_tasks_user_recurring
ON tasks (user_id, is_recurring)
WHERE is_recurring = TRUE
```

**Benefits:**
- Index size: Only ~5% of tasks (if 5% are recurring)
- Query speed: Fast filtering `WHERE is_recurring = TRUE`
- Maintenance: Cheaper updates (only updates index if is_recurring changes)

**Query Example:**
```python
# This query uses the partial index
recurring_tasks = session.exec(
    select(Task)
    .where(Task.user_id == user_id)
    .where(Task.is_recurring == True)
).all()
```

### 3. Unique Partial Index (Idempotency)

**Purpose:** Prevent duplicate next occurrences (race condition protection)

**Pattern:**
```sql
CREATE UNIQUE INDEX ix_tasks_parent_due_unique
ON tasks (parent_task_id, due_date)
WHERE parent_task_id IS NOT NULL AND completed = FALSE
```

**Constraint:** Only ONE incomplete occurrence per parent per due_date

**Application Code:**
```python
from sqlalchemy.exc import IntegrityError

def create_next_occurrence(parent_task: Task, next_due: datetime) -> Task:
    """Create next occurrence with idempotency."""
    next_occ = Task(
        user_id=parent_task.user_id,
        title=parent_task.title,
        parent_task_id=parent_task.id,
        due_date=next_due,
        completed=False
    )

    try:
        session.add(next_occ)
        session.commit()
        return next_occ
    except IntegrityError as e:
        # Duplicate occurrence already exists (idempotency)
        session.rollback()
        logger.warning(f"Next occurrence already exists: {e}")

        # Return existing occurrence
        existing = session.exec(
            select(Task)
            .where(Task.parent_task_id == parent_task.id)
            .where(Task.due_date == next_due)
            .where(Task.completed == False)
        ).first()
        return existing
```

## Edge Cases Handled

### 1. Month-End Dates

**Problem:** Jan 31 + 1 month = Feb 31 (invalid)

**Solution:** Use `dateutil.relativedelta` (automatically handles month-end)
```python
from dateutil.relativedelta import relativedelta

# Jan 31 + 1 month = Feb 28/29 (correct)
next_due = datetime(2026, 1, 31) + relativedelta(months=1)
# Result: 2026-02-28 (or Feb 29 in leap year)
```

### 2. Leap Years

**Problem:** Feb 29, 2024 + 1 year = Feb 29, 2025 (invalid - not leap year)

**Solution:** `relativedelta` automatically adjusts to Feb 28
```python
next_due = datetime(2024, 2, 29) + relativedelta(years=1)
# Result: 2025-02-28 (correct)
```

### 3. Concurrent Requests (Race Condition)

**Problem:** Two API requests complete same recurring task simultaneously → create 2 duplicates

**Solution:** Unique partial index raises IntegrityError (database-level protection)
```python
# Request 1 and Request 2 both try to create next occurrence
# Database enforces: UNIQUE (parent_task_id, due_date) WHERE completed = FALSE
# One succeeds, other gets IntegrityError
# Application handles error gracefully (return existing occurrence)
```

### 4. Cascade Deletes (Orphan Prevention)

**Problem:** User deletes recurring task → child occurrences become orphans

**Solution:** `ondelete='CASCADE'` automatically deletes children
```python
# User deletes parent recurring task
session.delete(parent_task)
session.commit()

# All child occurrences with parent_task_id = parent_task.id
# are automatically deleted by PostgreSQL
```

## Testing

```python
import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.exc import IntegrityError

def test_self_referential_relationship(db_session):
    """Test parent/child relationship."""
    parent = Task(title="Parent", is_recurring=True)
    db_session.add(parent)
    db_session.commit()

    child = Task(title="Child", parent_task_id=parent.id)
    db_session.add(child)
    db_session.commit()

    assert parent.child_occurrences[0].id == child.id
    assert child.parent_task.id == parent.id


def test_cascade_delete(db_session):
    """Test cascade delete removes children."""
    parent = Task(title="Parent")
    db_session.add(parent)
    db_session.commit()

    child = Task(title="Child", parent_task_id=parent.id)
    db_session.add(child)
    db_session.commit()

    db_session.delete(parent)
    db_session.commit()

    # Child should be deleted
    assert db_session.get(Task, child.id) is None


def test_unique_partial_index_prevents_duplicates(db_session):
    """Test idempotency constraint."""
    parent = Task(title="Parent")
    db_session.add(parent)
    db_session.commit()

    due = datetime(2026, 2, 10, 10, 0)

    occ1 = Task(
        title="Occ1",
        parent_task_id=parent.id,
        due_date=due,
        completed=False
    )
    db_session.add(occ1)
    db_session.commit()

    # Try to create duplicate occurrence (same parent, same due_date, incomplete)
    occ2 = Task(
        title="Occ2",
        parent_task_id=parent.id,
        due_date=due,
        completed=False
    )
    db_session.add(occ2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_month_end_date_arithmetic(db_session):
    """Test month-end edge case."""
    parent = Task(
        title="Monthly task",
        is_recurring=True,
        recurrence_pattern="monthly",
        due_date=datetime(2026, 1, 31, 10, 0)
    )
    db_session.add(parent)
    db_session.commit()

    # Calculate next due date (should be Feb 28, not Feb 31)
    next_due = parent.due_date + relativedelta(months=1)
    assert next_due == datetime(2026, 2, 28, 10, 0)


def test_leap_year_handling(db_session):
    """Test leap year edge case."""
    # 2024 is a leap year
    parent = Task(
        title="Yearly task",
        is_recurring=True,
        recurrence_pattern="yearly",
        due_date=datetime(2024, 2, 29, 10, 0)
    )
    db_session.add(parent)
    db_session.commit()

    # 2025 is NOT a leap year
    next_due = parent.due_date + relativedelta(years=1)
    assert next_due == datetime(2025, 2, 28, 10, 0)  # Adjusted to Feb 28
```

## Lessons Learned

1. **Self-referential FKs need `remote_side`** in SQLModel relationships
2. **Partial indexes** are powerful for optimizing queries on subsets of data
3. **Unique partial indexes** provide database-level idempotency (better than application-level)
4. **CASCADE deletes** prevent orphan records (crucial for hierarchies)
5. **`relativedelta`** handles month-end and leap year edge cases automatically
6. **IntegrityError handling** is essential when using unique constraints for idempotency

## Related Files

- **Migration:** `backend/alembic/versions/czrecan0aykx_add_recurring_fields_to_tasks.py`
- **Model:** `backend/src/models.py` (Task class)
- **Service:** `backend/src/services/recurrence_engine.py` (date arithmetic)
- **Tests:** `backend/tests/integration/test_recurring_tasks.py`
