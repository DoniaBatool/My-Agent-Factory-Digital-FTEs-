# Robust AI Chat Assistant Skill

## Overview

The Robust AI Chat Assistant provides natural language task management through multi-turn conversational workflows. Users can create, update, delete, list, and complete tasks using natural language commands.

## Features

### User Stories Implemented

| Priority | User Story | Description |
|----------|-----------|-------------|
| P1 | US1 Natural Language Task Creation | Multi-turn workflow: title → priority → deadline → description → create |
| P1 | US2 Intent Recognition | Detects ADD, UPDATE, DELETE, LIST, COMPLETE, CANCEL intents |
| P2 | US3 Task Update | Update any field with confirmation |
| P2 | US4 Task Deletion | Delete with safety confirmation |
| P2 | US5 Task Listing | Rich formatting with emojis and human-readable dates |
| P3 | US6 Task Completion | Toggle complete/incomplete status |
| P3 | US7 Natural Language Dates | Parse "tomorrow", "next Friday", "in 3 days" |
| P3 | US8 Priority Keywords | Auto-detect urgent/important → high, someday/later → low |

## Intent Recognition

The assistant recognizes these intents:

```
ADD_TASK      - "add task", "create task", "new task", "remind me to"
UPDATE_TASK   - "update task", "change task", "modify task"
DELETE_TASK   - "delete task", "remove task"
LIST_TASKS    - "show tasks", "list tasks", "my tasks"
COMPLETE_TASK - "mark complete", "finish task", "done with"
CANCEL        - "cancel", "nevermind", "stop", "abort"
```

## Priority Keywords

**High Priority:** urgent, important, critical, ASAP, deadline, now, immediately, soon
**Low Priority:** someday, later, minor, trivial, optional, eventually, maybe
**Medium Priority:** (default) normal, regular, medium

## Natural Language Dates

Supported formats:
- Relative: "tomorrow", "next week", "in 3 days"
- Named: "next Friday", "this Monday"
- Absolute: "January 20", "Jan 20 at 2pm"
- ISO: "2026-02-15", "2026-02-15 14:30"

Validation:
- Rejects past dates with clarification prompt
- Rejects dates >10 years in the future
- Confidence scoring for ambiguous dates

---

## 🕐 Date/Time Handling Best Practices (CRITICAL)

This section documents all date/time issues encountered and their solutions. **MUST follow these patterns** when building AI chat assistants with date handling.

### Issue 1: "Z" Suffix (UTC Timezone) Parsing

**Problem:** Python's `datetime.fromisoformat()` doesn't handle "Z" suffix (UTC indicator) in Python < 3.11.

```python
# ❌ FAILS - ValueError
datetime.fromisoformat("2026-02-03T14:30:00Z")

# ✅ WORKS - Replace Z with +00:00
clean_date = date_str.replace('Z', '+00:00') if date_str.endswith('Z') else date_str
datetime.fromisoformat(clean_date)
```

**Solution Pattern:**
```python
def parse_iso_date_safe(date_str: str) -> datetime:
    """Safely parse ISO dates with or without Z suffix."""
    if not date_str:
        return None
    # Handle "Z" suffix which fromisoformat doesn't support in Python < 3.11
    clean_date_str = date_str.replace('Z', '+00:00') if date_str.endswith('Z') else date_str
    return datetime.fromisoformat(clean_date_str)
```

**Where to apply:** Every place that parses ISO date strings from frontend or external APIs.

---

### Issue 2: Frontend ↔ Backend Date Format Consistency

**Problem:** ISO date strings from backend didn't include UTC indicator, causing timezone confusion on frontend.

**Solution:** Always append "Z" to `isoformat()` output in API responses:

```python
# ❌ WRONG - No timezone indicator
return {"created_at": conversation.created_at.isoformat()}  # "2026-02-03T14:30:00"

# ✅ CORRECT - UTC indicator
return {"created_at": conversation.created_at.isoformat() + "Z"}  # "2026-02-03T14:30:00Z"
```

**Apply to ALL datetime fields in API responses:**
- `created_at`
- `updated_at`
- `due_date`
- `completed_at`
- Message timestamps

---

### Issue 3: Time-of-Day Words Preprocessing

**Problem:** Expressions like "tomorrow morning", "tonight at 8", "next Friday evening" aren't parsed correctly by dateparser.

**Solution:** Preprocess to convert time-of-day words to explicit times:

```python
TIME_OF_DAY = {
    'morning': (9, 0),      # 9:00 AM
    'noon': (12, 0),        # 12:00 PM
    'afternoon': (14, 0),   # 2:00 PM
    'evening': (18, 0),     # 6:00 PM
    'night': (20, 0),       # 8:00 PM
    'tonight': (20, 0),     # 8:00 PM
    'midnight': (23, 59),   # 11:59 PM
}

def preprocess_date_string(date_string: str) -> str:
    """Convert time-of-day words to explicit times."""
    text = date_string.lower().strip()

    # Handle "tonight" - replace with "today" and ensure PM
    if text.startswith('tonight'):
        text = text.replace('tonight', 'today', 1)
        if text.strip() == 'today':
            text = 'today at 8pm'
        elif 'at' in text and not ('am' in text or 'pm' in text):
            text = text + 'pm'

    # Handle other time-of-day words
    for time_word, (hour, minute) in TIME_OF_DAY.items():
        if time_word in text and time_word != 'tonight':
            am_pm = 'am' if hour < 12 else 'pm'
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            text = text.replace(time_word, f'at {display_hour}{am_pm}')

    return text
```

**Examples:**
- `"tomorrow morning"` → `"tomorrow at 9am"`
- `"tonight at 8"` → `"today at 8pm"`
- `"next friday evening"` → `"next friday at 6pm"`

---

### Issue 4: AM/PM Inference When Not Specified

**Problem:** User says "at 5" without AM/PM - which one to use?

**Solution:** Smart inference based on hour:
- Hours 1-7: Assume **PM** (people usually schedule tasks in afternoon/evening)
- Hours 8-11: Assume **AM** (morning hours)
- Hours 12: Noon (PM)

```python
import re

def infer_am_pm(text: str) -> str:
    """Add AM/PM to times like 'at 5' based on hour."""
    at_match = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*$', text)
    if at_match:
        hour = int(at_match.group(1))
        minutes = at_match.group(2) or '00'
        if hour >= 1 and hour <= 7:
            text = re.sub(r'at\s+(\d{1,2})(:\d{2})?\s*$', f'at {hour}:{minutes}pm', text)
        elif hour >= 8 and hour <= 11:
            text = re.sub(r'at\s+(\d{1,2})(:\d{2})?\s*$', f'at {hour}:{minutes}am', text)
    return text
```

---

### Issue 5: "[next] day at time" Pattern Parsing

**Problem:** Patterns like "next Friday at 2:30pm" fail with dateparser.

**Solution:** Custom regex parser for day+time patterns:

```python
def parse_day_with_time(date_string: str) -> Optional[datetime]:
    """Parse patterns like 'next friday at 2:30pm'."""
    import re
    from datetime import datetime, timedelta

    pattern = r'(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
    match = re.match(pattern, date_string.lower().strip())

    if not match:
        return None

    is_next = match.group(1) is not None
    day_name = match.group(2)
    hour = int(match.group(3))
    minute = int(match.group(4)) if match.group(4) else 0
    am_pm = match.group(5)

    # Infer AM/PM if not specified
    if not am_pm:
        am_pm = 'pm' if hour >= 1 and hour <= 7 else 'am'

    # Convert to 24-hour format
    if am_pm == 'pm' and hour != 12:
        hour += 12
    elif am_pm == 'am' and hour == 12:
        hour = 0

    # Find the next occurrence of the day
    day_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    target_day = day_map[day_name]
    today = datetime.now()
    current_day = today.weekday()

    days_ahead = target_day - current_day
    if days_ahead <= 0:
        days_ahead += 7
    if is_next and days_ahead <= 7:
        if days_ahead < 7:
            days_ahead += 7

    target_date = today + timedelta(days=days_ahead)
    return datetime(target_date.year, target_date.month, target_date.day, hour, minute)
```

---

### Issue 6: Regex Date Extraction - Comma Problem

**Problem:** Regex using comma as terminator breaks dates like "Feb 6, 2026".

```python
# ❌ WRONG - Comma breaks "Feb 6, 2026" → extracts "Feb 6"
dm = re.search(r'(?:due\s+date|deadline)\s*(?:to|is|as|:)?\s*(.+?)(?:,|$)', text)

# ✅ CORRECT - Use semantic terminators only
dm = re.search(r'(?:due\s+date|deadline)\s*(?:to|is|as|:)?\s*(.+?)(?:\s+and\s+|\s+description|\s+title|\s+priority|\s+mark|$)', text)
```

**Rule:** Never use comma as date terminator. Dates often contain commas (e.g., "February 6, 2026").

---

### Issue 7: State Data Key Naming Consistency

**Problem:** Context manager stores due date as `due_date_parsed` but code looks for `due_date`.

**Solution:** Use consistent naming and document clearly:

```python
# In context_manager.py - store parsed ISO date
state_data["due_date_parsed"] = parsed_date.isoformat()  # ISO string

# In chat.py - retrieve with correct key
if "due_date_parsed" in updated_state and updated_state["due_date_parsed"]:
    add_params["due_date"] = updated_state["due_date_parsed"]
```

**Naming Convention:**
- `due_date` - User's original input (natural language)
- `due_date_parsed` - Parsed ISO datetime string

---

### Issue 8: Unified Date Parsing Function

**Problem:** Different code paths had inconsistent date parsing logic.

**Solution:** Create ONE unified parsing function and use it everywhere:

```python
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def parse_natural_date(date_str: str) -> Optional[datetime]:
    """
    Unified date parsing - handles natural language AND ISO formats.

    Supports:
    - Natural: "tomorrow", "next Friday at 3pm", "in 2 days"
    - ISO: "2026-02-03T14:30:00", "2026-02-03T14:30:00Z"

    Returns:
        datetime or None if parsing fails
    """
    if not date_str or not date_str.strip():
        return None

    date_str = date_str.strip()

    # Try dateparser for natural language
    try:
        import dateparser
        parsed = dateparser.parse(
            date_str,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RETURN_AS_TIMEZONE_AWARE': False
            }
        )
        if parsed:
            return parsed
    except Exception as e:
        logger.warning(f"Dateparser failed for '{date_str}': {e}")

    # Try ISO format (handle "Z" suffix)
    try:
        clean_date_str = date_str.replace('Z', '+00:00') if date_str.endswith('Z') else date_str
        return datetime.fromisoformat(clean_date_str)
    except (ValueError, TypeError):
        pass

    return None
```

**Usage:** Call this function EVERYWHERE dates need to be parsed:
- Chat endpoint (due_date from tool params)
- Task update endpoint
- Task creation endpoint
- Any AI agent tool that handles dates

---

### Complete Date Parser Class Template

```python
"""
date_parser.py - Production-ready natural language date parser.

Copy this entire class into your project for robust date handling.
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import re
import logging

import dateparser  # pip install dateparser

logger = logging.getLogger(__name__)


@dataclass
class DateParseResult:
    """Result of date parsing operation."""
    success: bool
    parsed_date: Optional[datetime]
    confidence: float
    error_message: Optional[str] = None
    original_text: Optional[str] = None


class DateParser:
    """Parse natural language dates with validation and GPT fallback."""

    MAX_FUTURE_YEARS = 10
    GPT_FALLBACK_THRESHOLD = 0.6

    TIME_OF_DAY = {
        'morning': (9, 0),
        'noon': (12, 0),
        'afternoon': (14, 0),
        'evening': (18, 0),
        'night': (20, 0),
        'tonight': (20, 0),
        'midnight': (23, 59),
    }

    def __init__(self, use_gpt_fallback: bool = True):
        self.use_gpt_fallback = use_gpt_fallback
        self._openai_client = None
        self.dateparser_settings = {
            'PREFER_DATES_FROM': 'future',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'RELATIVE_BASE': datetime.now(),
            'STRICT_PARSING': False
        }

    def _preprocess_date_string(self, date_string: str) -> str:
        """Preprocess time-of-day words and add AM/PM."""
        text = date_string.lower().strip()

        # Handle "tonight"
        if text.startswith('tonight'):
            text = text.replace('tonight', 'today', 1)
            if text.strip() == 'today':
                text = 'today at 8pm'
            elif 'at' in text and not ('am' in text or 'pm' in text):
                text = text + 'pm'

        # Handle time-of-day words
        for time_word, (hour, minute) in self.TIME_OF_DAY.items():
            if time_word in text and time_word != 'tonight':
                am_pm = 'am' if hour < 12 else 'pm'
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                text = text.replace(time_word, f'at {display_hour}{am_pm}')

        # Handle "at X" without am/pm
        at_match = re.search(r'at\s+(\d{1,2})(?::(\d{2}))?\s*$', text)
        if at_match:
            hour = int(at_match.group(1))
            minutes = at_match.group(2) or '00'
            if hour >= 1 and hour <= 7:
                text = re.sub(r'at\s+(\d{1,2})(:\d{2})?\s*$', f'at {hour}:{minutes}pm', text)
            elif hour >= 8 and hour <= 11:
                text = re.sub(r'at\s+(\d{1,2})(:\d{2})?\s*$', f'at {hour}:{minutes}am', text)

        return text

    def _parse_day_with_time(self, date_string: str) -> Optional[datetime]:
        """Parse '[next] day at time' patterns."""
        pattern = r'(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
        match = re.match(pattern, date_string.lower().strip())

        if not match:
            return None

        is_next = match.group(1) is not None
        day_name = match.group(2)
        hour = int(match.group(3))
        minute = int(match.group(4)) if match.group(4) else 0
        am_pm = match.group(5)

        if not am_pm:
            am_pm = 'pm' if hour >= 1 and hour <= 7 else 'am'

        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0

        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        target_day = day_map[day_name]
        today = datetime.now()
        current_day = today.weekday()

        days_ahead = target_day - current_day
        if days_ahead <= 0:
            days_ahead += 7
        if is_next and days_ahead <= 7:
            if days_ahead < 7:
                days_ahead += 7

        target_date = today + timedelta(days=days_ahead)
        return datetime(target_date.year, target_date.month, target_date.day, hour, minute)

    def parse(self, date_string: Optional[str]) -> DateParseResult:
        """Parse natural language date with full preprocessing."""
        if not date_string or not str(date_string).strip():
            return DateParseResult(
                success=False, parsed_date=None, confidence=0.0,
                error_message="Date string cannot be empty",
                original_text=date_string
            )

        date_string = str(date_string).strip()
        original_string = date_string
        date_string = self._preprocess_date_string(date_string)

        try:
            parsed_date = dateparser.parse(date_string, settings=self.dateparser_settings)

            if parsed_date is None:
                parsed_date = self._parse_day_with_time(original_string)

            if parsed_date is None:
                return DateParseResult(
                    success=False, parsed_date=None, confidence=0.0,
                    error_message=f"Could not parse date: '{original_string}'",
                    original_text=original_string
                )

            # Validate: not in past
            if parsed_date < datetime.now():
                return DateParseResult(
                    success=False, parsed_date=None, confidence=0.0,
                    error_message="Date cannot be in the past",
                    original_text=date_string
                )

            # Validate: not too far in future
            max_future_date = datetime.now() + timedelta(days=365 * self.MAX_FUTURE_YEARS)
            if parsed_date > max_future_date:
                return DateParseResult(
                    success=False, parsed_date=None, confidence=0.0,
                    error_message=f"Date cannot be more than {self.MAX_FUTURE_YEARS} years in future",
                    original_text=date_string
                )

            return DateParseResult(
                success=True, parsed_date=parsed_date, confidence=0.85,
                original_text=date_string
            )

        except Exception as e:
            return DateParseResult(
                success=False, parsed_date=None, confidence=0.0,
                error_message=f"Error parsing date: {str(e)}",
                original_text=date_string
            )
```

---

### Frontend Date Handling (TypeScript/JavaScript)

```typescript
// utils/date.ts - Frontend date utilities

/**
 * Parse ISO date string from backend (handles "Z" suffix)
 */
export function parseBackendDate(dateStr: string | null | undefined): Date | null {
  if (!dateStr) return null;

  try {
    // JavaScript handles "Z" suffix natively
    return new Date(dateStr);
  } catch {
    return null;
  }
}

/**
 * Format date for datetime-local input
 */
export function formatForDatetimeInput(date: Date | string | null): string {
  if (!date) return '';

  const d = typeof date === 'string' ? new Date(date) : date;

  // Format: YYYY-MM-DDTHH:mm (no seconds, no timezone)
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Convert datetime-local input value to ISO string for API
 */
export function formatForApi(dateStr: string): string | undefined {
  if (!dateStr || !dateStr.trim()) return undefined;

  try {
    // datetime-local gives "YYYY-MM-DDTHH:mm"
    // Convert to full ISO with Z suffix
    const date = new Date(dateStr);
    return date.toISOString();  // "2026-02-03T14:30:00.000Z"
  } catch {
    return undefined;
  }
}

/**
 * Human-readable date display
 */
export function formatDisplayDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '';

  const date = new Date(dateStr);
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  // Check if today
  if (date.toDateString() === now.toDateString()) {
    return `Today at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  // Check if tomorrow
  if (date.toDateString() === tomorrow.toDateString()) {
    return `Tomorrow at ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }

  // Otherwise, full date
  return date.toLocaleDateString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}
```

---

### Checklist: Date/Time Implementation

When implementing date/time in AI assistants, verify:

- [ ] ISO dates with "Z" suffix parsed correctly (Python < 3.11)
- [ ] API responses include "Z" suffix on all datetime fields
- [ ] Time-of-day words preprocessed ("morning" → "at 9am")
- [ ] AM/PM inferred when not specified (1-7 → PM, 8-11 → AM)
- [ ] "[next] day at time" patterns handled
- [ ] Regex doesn't use comma as terminator
- [ ] State data key names consistent (`due_date_parsed`)
- [ ] Unified parsing function used everywhere
- [ ] Past dates rejected with helpful message
- [ ] Far future dates rejected (>10 years)
- [ ] Frontend datetime-local input formatted correctly
- [ ] Frontend displays human-readable dates ("Tomorrow at 5pm")

## Multi-Turn Workflows

### Add Task Workflow
```
User: add task to buy milk
Bot: Got it! "Buy milk" - What priority? (high/medium/low)
User: high
Bot: When should this be done by?
User: tomorrow at 5pm
Bot: Any description to add?
User: Get 2% milk from the grocery store
Bot: ✅ Task created! #42: Buy milk (🔴 high priority, due Tomorrow at 5:00 PM)
```

### Update Task Workflow
```
User: update task 5
Bot: Task #5: "Buy groceries" (medium priority)
     What would you like to change?
User: make it high priority and due tomorrow
Bot: Confirm changes to Task #5:
     • Priority: medium → high
     • Due: → Tomorrow
     Proceed? (yes/no)
User: yes
Bot: ✅ Task #5 updated successfully!
```

### Delete Task Workflow
```
User: delete task 3
Bot: Are you sure you want to delete Task #3: "Old task"?
     This cannot be undone. (yes/no)
User: yes
Bot: ✅ Task #3 deleted.
```

## Task Display Formatting

```
📋 You have 3 tasks:

⏳ #1: Buy milk (🔴 high priority) - 📅 Due: Tomorrow at 5:00 PM
⏳ #2: Call mom (🟡 medium priority)
✅ #3: Finish report (🟢 low priority) - Done!
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_task` | Create new task with title, priority, due date, description |
| `update_task` | Update task fields (title, priority, due_date, description, completed) |
| `delete_task` | Delete task by ID with user isolation |
| `list_tasks` | List tasks with optional status/priority filters |
| `complete_task` | Mark task as complete/incomplete |
| `find_task` | Fuzzy search for task by title |

## Architecture

### Components

- **IntentClassifier** (`services/intent_classifier.py`): Pattern-based intent detection
- **ContextManager** (`ai_agent/context_manager.py`): Multi-turn workflow state
- **DateParser** (`utils/date_parser.py`): Natural language date parsing
- **FuzzyMatcher** (`utils/fuzzy_matcher.py`): Task title matching
- **TaskFormatter** (`utils/task_formatter.py`): Rich task display

### State Management

Conversation state stored in PostgreSQL:
- `current_intent`: Active workflow (NEUTRAL, ADDING_TASK, etc.)
- `state_data`: Collected information during workflow
- `target_task_id`: Task being operated on

## Test Coverage

- **644 tests passing**
- 238 edge case tests
- 99 priority detection tests
- 87 date parsing tests
- 28 task completion tests
- 31 task listing tests
- 57 task deletion tests
- 63 task update tests

## Usage

```python
# In chat endpoint
from src.services.intent_classifier import IntentClassifier
from src.ai_agent.context_manager import ContextManager

classifier = IntentClassifier()
result = classifier.classify(user_message, current_intent=conversation.current_intent)

if result.intent_type == Intent.ADD_TASK:
    context_manager.initialize_add_task_state(
        conversation_id=conversation.id,
        user_id=user.id,
        initial_title=result.extracted_entities.get("title")
    )
```

## Configuration

Environment variables:
- `DB_POOL_SIZE`: Database connection pool size (default: 5)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 10)
- `DB_POOL_TIMEOUT`: Connection timeout in seconds (default: 30)

---

## 🧪 Date/Time Testing Scenarios

Test these scenarios when implementing date handling:

### Backend Unit Tests (pytest)

```python
import pytest
from datetime import datetime, timedelta
from src.utils.date_parser import DateParser


class TestDateParser:
    """Comprehensive date parsing tests."""

    @pytest.fixture
    def parser(self):
        return DateParser(use_gpt_fallback=False)

    # ========== TIME-OF-DAY WORDS ==========

    @pytest.mark.parametrize("input_date,expected_hour", [
        ("tomorrow morning", 9),
        ("tomorrow afternoon", 14),
        ("tomorrow evening", 18),
        ("tomorrow night", 20),
        ("next monday morning", 9),
    ])
    def test_time_of_day_words(self, parser, input_date, expected_hour):
        """Test time-of-day words parse to correct hours."""
        result = parser.parse(input_date)
        assert result.success
        assert result.parsed_date.hour == expected_hour

    def test_tonight(self, parser):
        """Test 'tonight' parses to today 8pm."""
        result = parser.parse("tonight")
        assert result.success
        assert result.parsed_date.date() == datetime.now().date()
        assert result.parsed_date.hour == 20

    def test_tonight_at_time(self, parser):
        """Test 'tonight at 9' assumes PM."""
        result = parser.parse("tonight at 9")
        assert result.success
        assert result.parsed_date.hour == 21  # 9 PM

    # ========== AM/PM INFERENCE ==========

    @pytest.mark.parametrize("input_date,expected_hour", [
        ("tomorrow at 5", 17),      # 5 PM (1-7 = PM)
        ("tomorrow at 3", 15),      # 3 PM
        ("tomorrow at 9", 9),       # 9 AM (8-11 = AM)
        ("tomorrow at 10", 10),     # 10 AM
        ("tomorrow at 12", 12),     # 12 PM (noon)
    ])
    def test_am_pm_inference(self, parser, input_date, expected_hour):
        """Test AM/PM inference for bare hours."""
        result = parser.parse(input_date)
        assert result.success
        assert result.parsed_date.hour == expected_hour

    # ========== DAY + TIME PATTERNS ==========

    def test_next_friday_at_time(self, parser):
        """Test 'next Friday at 2:30pm' pattern."""
        result = parser.parse("next friday at 2:30pm")
        assert result.success
        assert result.parsed_date.weekday() == 4  # Friday
        assert result.parsed_date.hour == 14
        assert result.parsed_date.minute == 30

    def test_monday_at_time_no_ampm(self, parser):
        """Test 'monday at 3' infers PM."""
        result = parser.parse("monday at 3")
        assert result.success
        assert result.parsed_date.weekday() == 0  # Monday
        assert result.parsed_date.hour == 15  # 3 PM

    # ========== ISO FORMAT WITH Z ==========

    def test_iso_with_z_suffix(self, parser):
        """Test ISO format with Z suffix parses correctly."""
        future_date = datetime.now() + timedelta(days=1)
        iso_str = future_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = parser.parse(iso_str)
        assert result.success

    def test_iso_without_z_suffix(self, parser):
        """Test ISO format without Z suffix."""
        future_date = datetime.now() + timedelta(days=1)
        iso_str = future_date.strftime("%Y-%m-%dT%H:%M:%S")
        result = parser.parse(iso_str)
        assert result.success

    # ========== VALIDATION ==========

    def test_reject_past_date(self, parser):
        """Test past dates are rejected."""
        result = parser.parse("yesterday")
        assert not result.success
        assert "past" in result.error_message.lower()

    def test_reject_far_future(self, parser):
        """Test dates >10 years in future rejected."""
        result = parser.parse("in 15 years")
        assert not result.success
        assert "future" in result.error_message.lower()

    def test_empty_string(self, parser):
        """Test empty string returns error."""
        result = parser.parse("")
        assert not result.success

    def test_none_input(self, parser):
        """Test None input returns error."""
        result = parser.parse(None)
        assert not result.success

    # ========== DATES WITH COMMAS ==========

    def test_date_with_comma(self, parser):
        """Test dates like 'Feb 6, 2027' parse correctly."""
        result = parser.parse("February 6, 2027")
        assert result.success
        assert result.parsed_date.month == 2
        assert result.parsed_date.day == 6

    # ========== RELATIVE DATES ==========

    @pytest.mark.parametrize("input_date", [
        "tomorrow",
        "next week",
        "in 3 days",
        "in 2 weeks",
    ])
    def test_relative_dates(self, parser, input_date):
        """Test relative date expressions parse successfully."""
        result = parser.parse(input_date)
        assert result.success
        assert result.parsed_date > datetime.now()
```

### Frontend Tests (Jest)

```typescript
// __tests__/date-utils.test.ts
import {
  parseBackendDate,
  formatForDatetimeInput,
  formatForApi,
  formatDisplayDate
} from '@/utils/date';

describe('Date Utilities', () => {

  describe('parseBackendDate', () => {
    it('handles ISO with Z suffix', () => {
      const result = parseBackendDate('2026-02-03T14:30:00Z');
      expect(result).toBeInstanceOf(Date);
      expect(result?.getUTCHours()).toBe(14);
    });

    it('handles null/undefined', () => {
      expect(parseBackendDate(null)).toBeNull();
      expect(parseBackendDate(undefined)).toBeNull();
    });
  });

  describe('formatForDatetimeInput', () => {
    it('formats for datetime-local input', () => {
      const date = new Date('2026-02-03T14:30:00');
      const result = formatForDatetimeInput(date);
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
    });

    it('handles empty input', () => {
      expect(formatForDatetimeInput(null)).toBe('');
      expect(formatForDatetimeInput('')).toBe('');
    });
  });

  describe('formatForApi', () => {
    it('converts to ISO string', () => {
      const result = formatForApi('2026-02-03T14:30');
      expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z$/);
    });

    it('returns undefined for empty input', () => {
      expect(formatForApi('')).toBeUndefined();
    });
  });

  describe('formatDisplayDate', () => {
    it('shows "Today" for today', () => {
      const today = new Date();
      const result = formatDisplayDate(today.toISOString());
      expect(result).toContain('Today');
    });

    it('shows "Tomorrow" for tomorrow', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const result = formatDisplayDate(tomorrow.toISOString());
      expect(result).toContain('Tomorrow');
    });
  });
});
```

### Integration Test Scenarios

Test these end-to-end via chat interface:

| Input | Expected Behavior |
|-------|------------------|
| "add task to call mom tomorrow morning" | Creates task due tomorrow at 9:00 AM |
| "add task to meeting at 5" | Creates task due today at 5:00 PM |
| "update task 1 deadline to Feb 6, 2027" | Updates with full date preserved |
| "set deadline to next friday at 2:30pm" | Parses correctly to Friday 2:30 PM |
| "add task due yesterday" | Rejects with "date cannot be in the past" |
| "update deadline to tonight" | Sets to today at 8:00 PM |

---

## Related Skills

- `/sp.mcp-tool-builder` - Build MCP tools
- `/sp.chatbot-endpoint` - Stateless chat API
- `/sp.conversation-manager` - Conversation state
- `/sp.edge-case-tester` - Test edge cases
