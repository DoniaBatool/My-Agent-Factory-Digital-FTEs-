---
name: transaction-management
description: Implement atomic database operations with proper transaction management and rollback handling (Phase 2 pattern)
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

Ensure multi-step database operations are **atomic**:
- either all changes persist, or none do
- failures roll back reliably
- callers get clear errors

## Rules

- Wrap write sequences in a transaction boundary
- Commit only after all validation/side effects succeed
- Roll back on exceptions
- Avoid partial writes across multiple tables without a transaction

## Workflow

### Phase 1: Identify Atomic Units
- Create + related records
- Update with audit trail
- Delete with cascades and integrity constraints

### Phase 2: Implement Transactions
- Use framework/session transaction helpers
- Centralize patterns in service layer (not scattered in routes)

### Phase 3: Error Handling
- Translate DB errors to appropriate HTTP errors
- Preserve enough context for debugging (without leaking secrets)

### Phase 4: Verification
- Add tests that simulate mid-transaction failure and assert rollback

## Deliverables

- [ ] Transaction boundary implemented for write flows
- [ ] Rollback behavior verified (tests)
- [ ] Clear error mapping for common DB exceptions