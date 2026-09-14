---
name: structured-logging
description: Setup comprehensive structured logging infrastructure with user context, request IDs, and error tracking (Phase 3)
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

Add consistent, queryable logs so production issues are debuggable:
- correlate requests with a request ID
- attach user/conversation context when safe
- record tool calls and failures with structured fields

## Recommended Log Fields (Backend)

- `timestamp`
- `level`
- `message`
- `request_id`
- `route` / `method`
- `status_code`
- `user_id` (only if safe and expected)
- `conversation_id` (for chat systems)
- `duration_ms`
- `error_type` / `stack` (for errors)

## Workflow

### Phase 1: Baseline
- Choose structured JSON logging format
- Standardize logger setup across app entrypoints

### Phase 2: Correlation
- Generate/propagate `request_id` per request
- Include it in all logs within request scope

### Phase 3: Context
- Add safe context (user id, conversation id, tool name)
- Ensure secrets/credentials never get logged

### Phase 4: Verification
- Confirm logs are readable in the deployment platform
- Validate error logs include actionable context

## Deliverables

- [ ] Structured logging enabled (JSON)
- [ ] Request ID correlation implemented
- [ ] Safe context fields added (user/conversation/tool)
- [ ] Error logs are actionable (type + stack + request_id)