---
name: jwt-authentication
description: Implement JWT-based stateless authentication with FastAPI for scalable, horizontally-scalable APIs (Phase 2 pattern)
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

Implement **stateless JWT auth** with clear security guarantees:
- access token verification on every request
- optional refresh flow (if required)
- strict authorization checks (RBAC/ownership)

## Core Rules

- Never store plaintext secrets in code
- Use strong signing (HS256 with strong secret or RS256 with keypair)
- Validate `exp`, `iat`, issuer/audience if used
- Keep tokens short-lived; rotate secrets safely

## Workflow

### Phase 1: Token Design
- Claims: `sub` (user id), `exp`, optional roles
- Decide refresh strategy (or explicitly skip)

### Phase 2: Middleware/Dependencies
- FastAPI dependency to extract and verify token
- Provide `current_user` to routes (single source of truth)

### Phase 3: Authorization
- Enforce ownership checks at query level
- Deny by default for missing permissions

### Phase 4: Hardening
- Consistent 401 vs 403 behavior
- Tests for invalid/expired tokens

## Deliverables

- [ ] JWT verification dependency
- [ ] Auth error contract documented
- [ ] Tests for auth + authorization