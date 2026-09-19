---
name: pydantic-validation
description: Implement declarative input validation with Pydantic DTOs for FastAPI applications (Phase 2 pattern)
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

Use Pydantic models to enforce API contracts:
- validate inputs at the boundary
- normalize/clean data consistently
- return helpful validation errors

## Workflow

### Phase 1: Define DTOs
- Request models for create/update
- Response models for all endpoints
- Shared enums/types (status/priority)

### Phase 2: Validation + Normalization
- Use validators to trim whitespace, bound lengths, parse datetimes
- Prefer explicit constraints (min/max, regex) over ad-hoc code

### Phase 3: Error Contract
- Keep 422 responses consistent and understandable
- Map internal exceptions to clear HTTP errors

## Deliverables

- [ ] DTOs for all endpoints
- [ ] Validators for tricky fields (dates, titles, enums)
- [ ] Tests for validation edge cases