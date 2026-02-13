---
name: connection-pooling
description: Configure database connection pooling for optimal performance and resource management (Phase 2 pattern)
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

Configure DB connection pooling to avoid:
- too many open connections
- slow cold starts / reconnect storms
- resource starvation under load

## Key Decisions

- Driver/stack (sync vs async)
- Pool sizing strategy (per instance) + max overflow
- Health checks (`pre_ping`) and recycle time
- Whether to use PgBouncer / managed pooling

## Workflow

### Phase 1: Baseline
- Identify DB type (Postgres) and client (SQLAlchemy/asyncpg)
- Measure current connection counts and error patterns

### Phase 2: Configure
- Set pool params (e.g., `pool_size`, `max_overflow`, `pool_timeout`)
- Enable connection validation (`pool_pre_ping`)
- Consider `pool_recycle` for long-lived connections

### Phase 3: Deploy-Safe Notes
- For serverless/multi-instance deployments: keep pool small per instance
- If using PgBouncer in transaction mode: beware session features

### Phase 4: Observe
- Track active connections, timeouts, error rates
- Adjust based on real concurrency

## Deliverables

- [ ] Documented pool strategy + rationale
- [ ] Config applied (env-driven)
- [ ] Metrics/logging added for connection errors