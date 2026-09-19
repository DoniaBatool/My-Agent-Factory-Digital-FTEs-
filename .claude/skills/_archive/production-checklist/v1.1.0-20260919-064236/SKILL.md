---
name: production-checklist
description: Comprehensive production readiness validation checklist covering security, performance, monitoring, and deployment (Phase 3)
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

Prevent production incidents by running a repeatable “go live” checklist.

## Checklist

### Security
- [ ] Secrets are in env vars, not in repo/logs
- [ ] Auth enforced on all protected routes
- [ ] User isolation verified (no cross-user reads/writes)

### Data & Migrations
- [ ] Migrations applied successfully (upgrade + downgrade reviewed)
- [ ] Backfills completed (if any) and validated
- [ ] Indexes exist for hot queries

### Reliability
- [ ] Health endpoint works
- [ ] Graceful handling of tool failures/timeouts
- [ ] Retry/idempotency considered for creates

### Observability
- [ ] Structured logs enabled
- [ ] Error traces are visible in platform logs
- [ ] Basic metrics available (latency/error rate)

### UX
- [ ] Mobile responsiveness verified
- [ ] Clear error messages on failures

## Deliverables

- [ ] Completed checklist with notes
- [ ] Known risks + mitigations