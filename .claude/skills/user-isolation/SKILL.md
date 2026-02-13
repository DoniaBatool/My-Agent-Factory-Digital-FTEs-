---
name: user-isolation
description: Enforce user isolation with ownership checks at database query level to prevent horizontal privilege escalation (Phase 2 pattern)
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

Prevent cross-user data leaks (IDOR / horizontal privilege escalation) by enforcing:
- user scoping on every query
- ownership checks on every mutation
- consistent 403/404 behavior

## Core Rules

- Never accept `user_id` from client payloads as authority
- Always scope reads: `WHERE resource.user_id = current_user.id`
- Always scope writes/deletes similarly (or check ownership before acting)

## Workflow

### Phase 1: Identify Resources
- Tasks, conversations, messages, etc.

### Phase 2: Enforce in Queries
- Move ownership checks into repository/service queries
- Avoid “get by id then check” patterns when possible; prefer scoped queries

### Phase 3: Error Semantics
- Prefer `404` for “not found” without leaking existence
- Use `403` for known resources when policy requires explicit deny

### Phase 4: Verification
- Add tests that attempt cross-user access
- Add logging for denied access (without leaking sensitive data)

## Deliverables

- [ ] User-scoped queries for all resources
- [ ] Tests for cross-user access denial
- [ ] Documented error behavior (404 vs 403)