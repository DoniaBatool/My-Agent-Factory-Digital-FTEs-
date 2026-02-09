# Skill Learner - Continuous Skill Evolution

## Overview

The Skill Learner captures learnings from feature implementations and updates relevant skills to make them smarter and more powerful over time. This creates a "learning loop" where every project improves the skill library.

## When to Use

Use `/sp.skill-learner` after completing ANY feature implementation when you have:

- Fixed bugs that others might encounter
- Discovered better patterns or approaches
- Found edge cases not previously covered
- Developed reusable code templates
- Created testing scenarios worth preserving

## Workflow

```
┌─────────────────────────────────────────────┐
│  1. Identify Learnings                       │
│     - What issues did you encounter?         │
│     - What solutions did you develop?        │
│     - What patterns did you discover?        │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  2. Map to Skills                            │
│     - Which existing skill(s) apply?         │
│     - Does a new skill need to be created?   │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  3. Format the Learning                      │
│     - Issue description (problem)            │
│     - Solution with code example             │
│     - Checklist item if applicable           │
│     - Test case if applicable                │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  4. Update the Skill                         │
│     - Add new section or subsection          │
│     - Include code templates                 │
│     - Add to existing checklist              │
│     - Include test scenarios                 │
└─────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────┐
│  5. Document in PHR                          │
│     - Record which skills were updated       │
│     - Document what was learned              │
└─────────────────────────────────────────────┘
```

## Learning Categories

### 1. Bug Fixes

**Template:**
```markdown
### Issue X: [Problem Title]

**Problem:** [Clear description of what went wrong]

```python
# ❌ FAILS - [Why it fails]
[broken_code]

# ✅ WORKS - [Why it works]
[fixed_code]
```

**Solution Pattern:**
```python
[Reusable solution code]
```

**Where to apply:** [Where this fix should be used]
```

### 2. Edge Cases

**Template:**
```markdown
### Edge Case: [Scenario Title]

**Scenario:** [When this happens]

**Expected Behavior:** [What should happen]

**Implementation:**
```python
[Code to handle edge case]
```

**Test Case:**
```python
def test_[scenario]():
    # [Test code]
```
```

### 3. Best Practices

**Template:**
```markdown
### Best Practice: [Practice Title]

**Why:** [Rationale]

**Do:**
```python
# ✅ CORRECT
[good_code]
```

**Don't:**
```python
# ❌ WRONG
[bad_code]
```

**Checklist Item:** [ ] [Actionable item]
```

### 4. Code Templates

**Template:**
```markdown
### [Component Name] Template

**Purpose:** [What this template does]

**Usage:** Copy this entire class/function into your project.

```python
[Complete, production-ready code]
```

**Customization Points:**
- [What to modify for specific needs]
```

### 5. Test Scenarios

**Template:**
```markdown
### Testing [Feature]

```python
import pytest

class Test[Feature]:
    """[Description]"""

    @pytest.mark.parametrize("input,expected", [
        # [Test cases]
    ])
    def test_[scenario](self, input, expected):
        [test_code]
```

**Integration Tests:**
| Input | Expected Behavior |
|-------|------------------|
| [input] | [expected] |
```

## Skill Update Protocol

### Step 1: Read Current Skill

```bash
cat .claude/skills/[skill-name]/SKILL.md
```

### Step 2: Identify Update Location

- **New Section:** Add at end before "Related Skills"
- **Existing Section:** Add as new subsection
- **Checklist:** Add new items to existing checklist
- **Code Template:** Add to or replace existing template

### Step 3: Apply Update

Use Edit tool to update the skill file:
```
File: .claude/skills/[skill-name]/SKILL.md
Add: [new content]
Location: [appropriate section]
```

### Step 4: Verify Update

```bash
# Check skill was updated
head -50 .claude/skills/[skill-name]/SKILL.md
tail -50 .claude/skills/[skill-name]/SKILL.md
```

## Example Session

```text
🧠 Skill Learning Session

Feature: Robust AI Assistant - Date Handling
Status: Completed

Issues Encountered:
1. Python fromisoformat() fails with "Z" suffix (UTC)
2. "tomorrow morning" not parsed correctly
3. Regex comma terminator broke "Feb 6, 2026"
4. State data key naming inconsistency

Skills to Update:
├── /sp.robust-ai-assistant
│   └── Add "Date/Time Handling Best Practices" section
│       - 8 issues with solutions
│       - Complete DateParser class template
│       - Frontend TypeScript utilities
│       - Test scenarios (pytest + Jest)
│       - Implementation checklist

Learning Format:
- Issue + Problem + Solution + Code
- Reusable templates
- Test cases
- Checklists

Updating skill... ✏️

Skills Updated:
✅ /sp.robust-ai-assistant (added ~800 lines)
   - Date/Time Best Practices section
   - 8 documented issues with solutions
   - Complete DateParser class (copy-paste ready)
   - Frontend utilities (TypeScript)
   - 20+ pytest test cases
   - Jest frontend tests
   - Integration test scenarios
   - Implementation checklist (12 items)

PHR Record: history/prompts/003-robust-ai-assistant/skill-learning.md

🧠 Skill Learning Complete
```

## Skill Update Checklist

When updating skills, ensure:

- [ ] **Problem clearly stated** - Others can understand the issue
- [ ] **Code shows before/after** - ❌ WRONG vs ✅ CORRECT
- [ ] **Solution is reusable** - Not project-specific
- [ ] **Comments explain WHY** - Not just what
- [ ] **Test cases included** - Verify the fix works
- [ ] **Checklist item added** - Actionable for implementation
- [ ] **Location is logical** - Easy to find in skill

## Skills That Should Evolve

Every skill should grow with usage:

| Skill | Common Learnings |
|-------|------------------|
| `/sp.jwt-authentication` | Token refresh patterns, edge cases |
| `/sp.mcp-tool-builder` | Tool parameter validation, error handling |
| `/sp.chatbot-endpoint` | Conversation state issues, timeout handling |
| `/sp.database-schema-expander` | Migration patterns, index strategies |
| `/sp.robust-ai-assistant` | Date parsing, intent detection, fuzzy matching |
| `/sp.pydantic-validation` | Custom validators, error messages |
| `/sp.user-isolation` | Query scoping patterns, ownership checks |

## PHR Documentation

After skill updates, record in PHR:

```yaml
skill_learning:
  feature: [Feature Name]
  issues_count: [Number]
  skills_updated:
    - skill: /sp.[skill-name]
      sections_added:
        - [Section 1]
        - [Section 2]
      lines_added: [Number]
      key_learnings:
        - [Learning 1]
        - [Learning 2]
  new_skills_created: [If any]
  knowledge_preserved: true
```

## Integration with Other Skills

This skill works with:

- `/sp.skill-creator` - Create new skills when learnings don't fit existing ones
- `/sp.edge-case-tester` - Generate test cases to include in skills
- `/sp.change-management` - Track skill modifications

## Remember

**Skills are living documents.**

Every bug fixed, every pattern discovered, every edge case found should be captured in the appropriate skill so future projects benefit from this knowledge.

**Goal:** Never solve the same problem twice. Once solved, it should be in a skill.
