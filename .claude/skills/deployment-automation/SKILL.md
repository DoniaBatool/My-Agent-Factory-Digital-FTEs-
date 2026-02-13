---
name: deployment-automation
description: Automate deployment workflow with Alembic migrations, environment setup, and staging/production deployment (Phase 3)
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

Make deployments repeatable and low-risk by automating:
- builds
- migrations
- releases
- smoke checks
- rollback guidance

## Workflow

### Phase 1: Environment & Secrets
- Ensure all required env vars exist (staging/prod)
- Prevent secrets from being logged

### Phase 2: Build & Test Gate
- Install deps, run type-check/lint/tests where configured
- Fail fast on missing migrations or schema drift

### Phase 3: Migrations
- Run Alembic upgrade as part of release step (or a pre-release job)
- Require migrations to be idempotent and reversible when possible

### Phase 4: Smoke Checks
- Health endpoint check
- Basic DB connectivity check
- One critical API call check (read-only)

### Phase 5: Rollback
- Document rollback procedure (deploy previous version, downgrade migration if safe)

## Deliverables

- [ ] Deployment script/config (CI or platform-specific)
- [ ] Migration runbook
- [ ] Smoke check checklist