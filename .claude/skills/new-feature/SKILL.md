---
name: new-feature
description: Automatically scaffold a complete new feature with spec.md, plan.md, and tasks.md from a feature description
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Turn a feature request into an executable implementation packet:
- `spec.md` (requirements and acceptance criteria)
- `plan.md` (technical design and steps)
- `tasks.md` (checklist with sequencing)

## Workflow

### Phase 1: Spec
- User story + goals
- Non-goals
- Acceptance criteria (testable)
- UI/API/DB impacts

### Phase 2: Plan
- Proposed architecture changes
- Data model changes (with migration approach)
- API contract and error behavior
- Rollout and rollback plan

### Phase 3: Tasks
- Break down into small tasks with clear done criteria
- Call out dependencies and order

## Deliverables

- [ ] `spec.md`
- [ ] `plan.md`
- [ ] `tasks.md`