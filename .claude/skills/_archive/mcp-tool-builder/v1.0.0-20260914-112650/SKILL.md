---
name: mcp-tool-builder
description: Build Model Context Protocol tools for AI agent integration with OpenAI Agents SDK
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



# Skill: MCP Tool Builder

## Purpose

Build MCP (Model Context Protocol) tools that are deterministic, safe, validated, and easy for AI agents to call correctly.

## When to Use

- Creating new MCP tools for AI agent
- Adding natural language input parsing to tools
- Implementing idempotent operations with database constraints
- Building tools that validate complex inputs (dates, patterns, enums)
- Extending existing tools with new parameters
- Creating helper functions for complex tool logic

## Prerequisites

- MCP SDK installed
- OpenAI Agents SDK configured
- Pydantic models defined
- Database session management configured
- Understanding of user isolation patterns

## Usage

```bash
# Invoke this skill for MCP tool creation
/sp.mcp-tool-builder "Create set_recurring MCP tool with natural language date parsing"
```

## Implementation Steps

### Phase 1: Design Tool Contract

1. **Define tool purpose** (verb-first, specific)
   - Good: `set_recurring`, `add_tag`, `search_tasks`
   - Bad: `task_helper`, `update`, `do_something`

2. **Design Pydantic input schema**
   ```python
   class SetRecurringParams(BaseModel):
       user_id: str = Field(..., description="User ID for isolation")
       task_id: int = Field(..., description="Task to make recurring")
       pattern: str = Field(..., description="daily/weekly/monthly/yearly/every N days")
       end_date: Optional[str] = Field(None, description="Natural language or ISO format")

       class Config:
           json_schema_extra = {"example": {...}}
   ```

3. **Design Pydantic output schema**
   ```python
   class SetRecurringResult(BaseModel):
       task_id: int
       title: str
       is_recurring: bool
       recurrence_pattern: Optional[str]
       recurrence_end_date: Optional[datetime]
   ```

4. **Decide idempotency strategy**
   - Database constraints (unique indexes)
   - Application-level checks (query before insert)
   - IntegrityError handling

### Phase 2: Implement Tool Function

1. **Create tool file** in `backend/src/mcp_tools/<tool_name>.py`

2. **Implement validation**
   ```python
   def _validate_pattern(pattern: str) -> None:
       """Validate recurrence pattern."""
       simple = ["daily", "weekly", "monthly", "yearly", "none"]
       custom_regex = r"^every\s+(\d+)\s+(day|days|week|weeks)$"

       if pattern.lower() in simple:
           return

       match = re.match(custom_regex, pattern, re.IGNORECASE)
       if match:
           interval = int(match.group(1))
           if interval <= 0:
               raise ValueError("Interval must be positive")
           if interval > 365:
               raise ValueError("Interval too large (max 365)")
           return

       raise ValueError(f"Invalid pattern: '{pattern}'")
   ```

3. **Implement natural language parsing (if needed)**
   ```python
   def _parse_end_date(end_date_str: str) -> datetime:
       """Parse natural language or ISO format dates."""
       import dateparser

       parsed = dateparser.parse(
           end_date_str,
           settings={
               'PREFER_DATES_FROM': 'future',
               'RETURN_AS_TIMEZONE_AWARE': False
           }
       )

       if not parsed:
           raise ValueError(f"Could not parse date: '{end_date_str}'")

       if parsed <= datetime.utcnow():
           raise ValueError("Date must be in the future")

       return parsed
   ```

4. **Implement main tool function**
   ```python
   async def set_recurring(
       user_id: int,
       task_id: int,
       pattern: str,
       end_date: Optional[str] = None
   ) -> dict:
       """Set task as recurring with validation and user isolation."""
       # Normalize inputs
       pattern = pattern.lower().strip()

       # Validate inputs
       _validate_pattern(pattern)

       # Parse natural language (if provided)
       parsed_end_date = _parse_end_date(end_date) if end_date else None

       # Database operations with user isolation
       with Session(engine) as session:
           statement = select(Task).where(
               Task.id == task_id,
               Task.user_id == str(user_id)  # User isolation
           )
           task = session.exec(statement).first()

           if not task:
               raise ValueError("Task not found or access denied")

           # Update task
           if pattern == "none":
               task.is_recurring = False
               task.recurrence_pattern = None
               task.recurrence_end_date = None
           else:
               task.is_recurring = True
               task.recurrence_pattern = pattern
               task.recurrence_end_date = parsed_end_date

           task.updated_at = datetime.utcnow()

           session.add(task)
           session.commit()
           session.refresh(task)

           # Return structured result
           return {
               "task_id": task.id,
               "title": task.title,
               "is_recurring": task.is_recurring,
               "recurrence_pattern": task.recurrence_pattern,
               "recurrence_end_date": task.recurrence_end_date.isoformat() if task.recurrence_end_date else None
           }
   ```

5. **Implement helper functions for complex logic**
   ```python
   def _create_next_occurrence(
       session: Session,
       parent_task: Task,
       next_due: datetime
   ) -> Optional[Task]:
       """Helper: Create next occurrence with idempotency."""
       next_occ = Task(
           user_id=parent_task.user_id,
           title=parent_task.title,
           description=parent_task.description,
           parent_task_id=parent_task.id,
           due_date=next_due,
           completed=False
       )

       try:
           session.add(next_occ)
           session.commit()
           session.refresh(next_occ)
           return next_occ
       except IntegrityError as e:
           # Duplicate occurrence already exists (idempotency)
           session.rollback()
           logger.warning(f"Next occurrence already exists: {e}")
           return None  # Or return existing occurrence
   ```

### Phase 3: Register Tool with Agent

1. **Add to tools registry** (`backend/src/ai_agent/tools.py`)
   ```python
   from ..mcp_tools.set_recurring import set_recurring

   TOOLS = [
       add_task,
       update_task,
       delete_task,
       list_tasks,
       complete_task,
       set_recurring,  # NEW
   ]
   ```

2. **Update agent runner** (if needed for parsing)
   ```python
   # In agent runner, enhance natural language understanding
   if "recurring" in user_message.lower():
       # Extract pattern from message
       # e.g., "make it recurring daily" → pattern="daily"
   ```

### Phase 4: Test Tool

1. **Unit tests** (validation)
   ```python
   def test_validate_pattern_simple():
       assert _validate_pattern("daily") is None
       assert _validate_pattern("weekly") is None

   def test_validate_pattern_custom():
       assert _validate_pattern("every 3 days") is None
       assert _validate_pattern("every 2 weeks") is None

   def test_validate_pattern_invalid():
       with pytest.raises(ValueError, match="Invalid pattern"):
           _validate_pattern("every tuesday")

   def test_validate_pattern_zero_interval():
       with pytest.raises(ValueError, match="must be positive"):
           _validate_pattern("every 0 days")
   ```

2. **Integration tests** (database)
   ```python
   def test_set_recurring_daily(db_session, test_user):
       task = Task(user_id=test_user.id, title="Test")
       db_session.add(task)
       db_session.commit()

       result = await set_recurring(
           user_id=test_user.id,
           task_id=task.id,
           pattern="daily"
       )

       assert result["is_recurring"] is True
       assert result["recurrence_pattern"] == "daily"
   ```

3. **E2E tests** (chatbot)
   ```python
   def test_chatbot_set_recurring(client, auth_headers):
       response = client.post(
           "/chat",
           headers=auth_headers,
           json={"message": "make task 1 recurring daily"}
       )

       assert response.status_code == 200
       assert "recurring" in response.json()["response"].lower()
   ```

## Key Patterns

### Pattern 1: Natural Language Input Parsing

**Use Case:** Tool accepts natural language (dates, patterns, priorities)

**Libraries:**
- `dateparser` - Natural language dates
- `re` (regex) - Pattern matching
- Custom parsers - Domain-specific logic

**Example:**
```python
import dateparser

def parse_natural_language_input(user_input: str, input_type: str) -> Any:
    """Parse natural language input based on type."""
    if input_type == "date":
        parsed = dateparser.parse(
            user_input,
            settings={'PREFER_DATES_FROM': 'future', 'RETURN_AS_TIMEZONE_AWARE': False}
        )
        if not parsed:
            raise ValueError(f"Could not parse date: '{user_input}'")
        return parsed

    elif input_type == "pattern":
        # Normalize and validate pattern
        pattern = user_input.lower().strip()
        if pattern in ["daily", "weekly", "monthly", "yearly"]:
            return pattern

        # Check custom patterns
        match = re.match(r"^every\s+(\d+)\s+(days?|weeks?|months?)$", pattern)
        if match:
            return pattern

        raise ValueError(f"Invalid pattern: '{pattern}'")

    elif input_type == "priority":
        priority_map = {
            "high": ["high", "urgent", "important", "asap"],
            "medium": ["medium", "normal", "regular"],
            "low": ["low", "someday", "later", "minor"]
        }
        for level, keywords in priority_map.items():
            if user_input.lower() in keywords:
                return level

        raise ValueError(f"Unknown priority: '{user_input}'")
```

### Pattern 2: Helper Function for Complex Logic

**Use Case:** Tool logic is too complex for main function

**Benefits:**
- Separation of concerns
- Testable independently
- Reusable across tools

**Example:**
```python
async def complete_task(user_id: int, task_id: int) -> dict:
    """Main tool function - simple orchestration."""
    with Session(engine) as session:
        task = _get_task_with_isolation(session, task_id, user_id)

        task.completed = True
        task.updated_at = datetime.utcnow()

        # Complex logic in helper function
        next_occurrence = None
        if task.is_recurring:
            next_occurrence = _create_next_occurrence(session, task)

        session.commit()

        return {
            "task_id": task.id,
            "completed": True,
            "next_occurrence": next_occurrence.id if next_occurrence else None
        }


def _get_task_with_isolation(session: Session, task_id: int, user_id: int) -> Task:
    """Helper: Get task with user isolation check."""
    statement = select(Task).where(Task.id == task_id, Task.user_id == str(user_id))
    task = session.exec(statement).first()
    if not task:
        raise ValueError("Task not found or access denied")
    return task


def _create_next_occurrence(session: Session, parent_task: Task) -> Optional[Task]:
    """Helper: Create next recurring occurrence."""
    next_due = calculate_next_due_date(
        parent_task.due_date,
        parent_task.recurrence_pattern,
        parent_task.recurrence_end_date
    )

    if not next_due:
        return None  # Recurrence ended

    next_occ = Task(
        user_id=parent_task.user_id,
        title=parent_task.title,
        parent_task_id=parent_task.id,
        due_date=next_due,
        completed=False
    )

    try:
        session.add(next_occ)
        session.flush()  # Don't commit yet (part of larger transaction)
        return next_occ
    except IntegrityError:
        session.rollback()
        logger.warning("Next occurrence already exists (idempotency)")
        return None
```

### Pattern 3: IntegrityError Handling for Idempotency

**Use Case:** Prevent duplicate operations with database constraints

**Pattern:**
1. Define unique constraint in database
2. Catch IntegrityError in application
3. Return existing entity or gracefully handle

**Example:**
```python
from sqlalchemy.exc import IntegrityError

async def create_task_idempotent(user_id: int, title: str, unique_key: str) -> dict:
    """Create task with idempotency using unique constraint."""
    with Session(engine) as session:
        task = Task(
            user_id=user_id,
            title=title,
            unique_key=unique_key  # Unique constraint on (user_id, unique_key)
        )

        try:
            session.add(task)
            session.commit()
            session.refresh(task)
            logger.info(f"Created new task: {task.id}")
            return {"task_id": task.id, "created": True}

        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Task already exists (idempotency): {e}")

            # Return existing task
            existing = session.exec(
                select(Task)
                .where(Task.user_id == user_id)
                .where(Task.unique_key == unique_key)
            ).first()

            return {"task_id": existing.id, "created": False}
```

### Pattern 4: Enum Parameter Validation

**Use Case:** Tool accepts enum values (priority, status, pattern)

**Pattern:**
```python
from enum import Enum
from pydantic import BaseModel, Field, validator

class PriorityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class UpdateTaskParams(BaseModel):
    user_id: str
    task_id: int
    priority: Optional[PriorityLevel] = None

    @validator('priority', pre=True)
    def normalize_priority(cls, v):
        """Normalize priority input to enum."""
        if v is None:
            return v

        # Accept case-insensitive input
        v = str(v).lower()

        # Map keywords to enum
        priority_map = {
            "high": PriorityLevel.HIGH,
            "urgent": PriorityLevel.HIGH,
            "important": PriorityLevel.HIGH,
            "medium": PriorityLevel.MEDIUM,
            "normal": PriorityLevel.MEDIUM,
            "low": PriorityLevel.LOW,
            "someday": PriorityLevel.LOW,
            "later": PriorityLevel.LOW
        }

        if v in priority_map:
            return priority_map[v]

        # Try direct enum match
        try:
            return PriorityLevel(v)
        except ValueError:
            raise ValueError(f"Invalid priority: '{v}'. Must be high/medium/low")
```

### Pattern 5: Regex Pattern Validation

**Use Case:** Tool accepts string patterns with specific format

**Example:**
```python
import re

def _validate_recurrence_pattern(pattern: str) -> None:
    """Validate recurrence pattern format."""
    # Simple patterns
    simple = ["daily", "weekly", "monthly", "yearly", "none"]
    if pattern.lower() in simple:
        return

    # Custom patterns: "every N units"
    custom_regex = r"^every\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)$"
    match = re.match(custom_regex, pattern, re.IGNORECASE)

    if match:
        interval = int(match.group(1))

        # Validate interval range
        if interval <= 0:
            raise ValueError("Interval must be positive")
        if interval > 365:
            raise ValueError("Interval too large (max 365)")

        return

    # Pattern not recognized
    raise ValueError(
        f"Invalid pattern: '{pattern}'. "
        f"Supported: daily, weekly, monthly, yearly, 'every N days', 'every N weeks', 'none'"
    )
```

## Common Pitfalls

### Pitfall 1: Not Normalizing Input

**Problem:** Tool fails on "Daily" vs "daily", "  weekly  " vs "weekly"

**Solution:** Always normalize input
```python
pattern = pattern.lower().strip()
end_date = end_date.strip() if end_date else None
```

### Pitfall 2: Missing User Isolation

**Problem:** User can operate on other users' tasks

**Solution:** Always filter by user_id
```python
statement = select(Task).where(
    Task.id == task_id,
    Task.user_id == str(user_id)  # REQUIRED
)
```

### Pitfall 3: Vague Error Messages

**Problem:** Agent doesn't know how to fix invalid input

**Solution:** Provide actionable error messages
```python
# BAD
raise ValueError("Invalid pattern")

# GOOD
raise ValueError(
    f"Invalid recurrence pattern: '{pattern}'. "
    f"Supported patterns: daily, weekly, monthly, yearly, 'every N days', 'every N weeks', 'none'"
)
```

### Pitfall 4: Not Handling IntegrityError

**Problem:** Tool crashes on duplicate operations

**Solution:** Catch IntegrityError and handle gracefully
```python
try:
    session.add(next_occurrence)
    session.commit()
except IntegrityError:
    session.rollback()
    logger.warning("Next occurrence already exists (idempotency)")
    # Return existing or continue
```

### Pitfall 5: Complex Logic in Main Function

**Problem:** Main tool function is 200+ lines, hard to test

**Solution:** Extract helper functions
```python
# BAD: All logic in main function
async def complete_task(...):
    # 200 lines of validation, date calculation, database operations

# GOOD: Helper functions
async def complete_task(...):
    task = _get_task_with_isolation(session, task_id, user_id)
    next_occ = _create_next_occurrence(session, task) if task.is_recurring else None
    _mark_complete(session, task)
    return _format_result(task, next_occ)
```

## Testing Strategy

### Unit Tests (Validation Logic)

Test validation functions independently:
```python
def test_validate_pattern_simple():
    assert _validate_pattern("daily") is None  # No exception

def test_validate_pattern_invalid():
    with pytest.raises(ValueError, match="Invalid pattern"):
        _validate_pattern("every tuesday")

def test_parse_end_date_natural_language():
    result = _parse_end_date("next year")
    assert result.year > datetime.now().year

def test_parse_end_date_past():
    with pytest.raises(ValueError, match="must be in the future"):
        _parse_end_date("yesterday")
```

### Integration Tests (Database Operations)

Test tool with real database:
```python
@pytest.mark.asyncio
async def test_set_recurring_daily(db_session, test_user):
    task = Task(user_id=test_user.id, title="Test task")
    db_session.add(task)
    db_session.commit()

    result = await set_recurring(
        user_id=test_user.id,
        task_id=task.id,
        pattern="daily",
        end_date="next year"
    )

    assert result["is_recurring"] is True
    assert result["recurrence_pattern"] == "daily"
    assert result["recurrence_end_date"] is not None
```

### E2E Tests (Chatbot Integration)

Test tool through chat endpoint:
```python
def test_chatbot_set_recurring_natural_language(client, auth_headers):
    # Create task first
    response = client.post("/chat", headers=auth_headers,
                          json={"message": "add task to buy milk"})
    task_id = extract_task_id(response.json()["response"])

    # Set as recurring
    response = client.post("/chat", headers=auth_headers,
                          json={"message": f"make task {task_id} recurring weekly"})

    assert response.status_code == 200
    assert "recurring" in response.json()["response"].lower()
    assert "weekly" in response.json()["response"].lower()
```

## Examples

See `examples/` directory for:
- `example-1-set-recurring.md`: Natural language parsing + validation (Phase V)
- `example-2-complete-task.md`: Helper function pattern + IntegrityError handling (Phase V)

## Related Skills

- `/sp.pydantic-validation` - Input validation patterns
- `/sp.user-isolation` - Enforce user isolation in tools
- `/sp.database-schema-expander` - Database constraints for idempotency
- `/sp.edge-case-tester` - Test tool edge cases
- `/sp.chatbot-endpoint` - Integrate tools with chat endpoint

## Success Criteria

- [ ] Tool has clear purpose (verb-first name)
- [ ] Pydantic input/output schemas defined
- [ ] Natural language input parsing (if applicable)
- [ ] Validation with actionable error messages
- [ ] User isolation enforced (user_id filtering)
- [ ] Helper functions for complex logic (if >50 lines)
- [ ] IntegrityError handling (if using unique constraints)
- [ ] Unit tests for validation logic
- [ ] Integration tests for database operations
- [ ] E2E tests through chatbot endpoint
- [ ] Tool registered with agent runtime
- [ ] Idempotency strategy documented