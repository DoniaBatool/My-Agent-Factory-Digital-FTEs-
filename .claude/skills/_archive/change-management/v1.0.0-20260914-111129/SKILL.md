---
name: change-management
description: Manage changes to existing features by creating change subfolders with spec, plan, tasks and automatically updating all affected areas of the project (project)
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

Make safe, traceable changes to existing features without regressions by:
- writing a clear change spec
- mapping impacted areas
- implementing in small, verifiable steps
- adding rollback notes

## Workflow

### Phase 1: Change Spec
- What is changing and why
- Non-goals (what will *not* change)
- User-visible behavior changes
- API/DB contract changes

### Phase 2: Impact Map
- Identify impacted modules (frontend, backend, DB, migrations)
- Identify required updates (tests, docs, types)

### Phase 3: Implementation Plan
- Break into small commits
- Backward-compatible rollout when possible (dual-read/dual-write)

### Phase 4: Verification + Rollback
- Add/adjust tests for changed behavior
- Document rollback steps (feature flags / migration downgrade / config)

## Quality Bar

- No silent breaking changes
- Migration safety reviewed
- Error handling remains user-friendly

## Deliverables

- [ ] Change spec (what/why/impact)
- [ ] Task breakdown
- [ ] Updated code + tests
- [ ] Rollback plan