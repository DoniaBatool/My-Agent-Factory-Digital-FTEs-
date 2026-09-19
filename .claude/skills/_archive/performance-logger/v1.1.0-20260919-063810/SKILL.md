---
name: performance-logger
description: Add performance monitoring and execution time logging to backend services with structured JSON output (Phase 3)
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

Add lightweight performance instrumentation to identify slow paths and regressions.

## What to Measure

- Request latency (total + key sub-steps)
- DB query time and count (where possible)
- External calls duration (MCP/tools/APIs)
- Error rates for endpoints and tools

## Workflow

### Phase 1: Identify Hot Paths
- Chat endpoint
- Task CRUD endpoints
- Tool execution wrapper

### Phase 2: Implement Logging
- Use structured JSON logs (fields: `route`, `duration_ms`, `user_id?`, `status`)
- Add a request/correlation ID for linking logs

### Phase 3: Validate
- Ensure logs don’t include secrets/PII
- Ensure overhead is minimal

## Deliverables

- [ ] Timing logs for key endpoints/tools
- [ ] Correlation/request ID propagation
- [ ] Documented interpretation of metrics