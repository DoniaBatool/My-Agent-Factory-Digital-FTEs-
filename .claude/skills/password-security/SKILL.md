---
name: password-security
description: Implement secure password hashing with bcrypt following industry best practices (Phase 2 pattern)
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

Implement secure password handling:
- hash passwords with a slow, salted algorithm (bcrypt/argon2)
- never store or log plaintext passwords
- provide safe reset and verification flows

## Rules

- Store only hash (and algorithm metadata if needed)
- Use per-password salt (bcrypt includes this)
- Rate limit login attempts
- Use constant-time comparisons where applicable

## Workflow

### Phase 1: Hashing
- Choose cost factor appropriate for environment
- Add helper functions: `hash_password`, `verify_password`

### Phase 2: Auth Flows
- Signup: validate password policy, store hash
- Login: verify, return auth token/session
- Reset: time-limited token; invalidate after use

### Phase 3: Hardening
- Do not reveal whether email exists
- Add audit logs for auth events (without secrets)

## Deliverables

- [ ] Password hashing + verification utilities
- [ ] Login/signup/reset flows hardened
- [ ] Tests for verification + edge cases