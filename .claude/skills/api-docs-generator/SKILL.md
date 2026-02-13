---
name: api-docs-generator
description: Generate comprehensive OpenAPI documentation and docstrings for all backend endpoints, services, and MCP tools (Phase 3)
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Professional Profile

**Role**: API Docs Generator (Backend Documentation Specialist)  
**Expertise**: OpenAPI/Swagger, FastAPI docstrings, schema examples, error contracts  
**Outcome**: Docs that match reality and are usable by frontend/QA without guessing.

## What This Skill Produces

- Clear endpoint summaries + descriptions
- Request/response schemas with examples
- Error contracts (401/403/404/422/500) documented consistently
- MCP tool contracts (inputs/outputs/errors) documented like APIs

## Workflow

### Phase 1: Inventory
- Enumerate routes and identify auth requirements
- Identify shared schemas and common errors

### Phase 2: Contract Hardening
- Ensure response models are explicit
- Specify date/time format as **ISO-8601** (timezone rules included)
- Document defaults and optional fields

### Phase 3: Examples
- Add examples for:
  - success
  - validation error (422)
  - auth failure (401/403)
  - not found (404)

### Phase 4: Verification
- Spot-check docs against implementation
- Ensure naming conventions are documented (snake_case vs camelCase)

## Edge Cases to Document

- Pagination/filtering/sorting
- Partial updates (PATCH) vs full replacement (PUT)
- Idempotency and retries

## Deliverables

- [ ] Updated OpenAPI docs (summaries/descriptions/response models/examples)
- [ ] MCP tool reference (params/results/errors)
- [ ] Minimal “how to call” section for frontend/QA (curl + JSON)
## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Professional Profile

**Role**: API Docs Generator (Backend Documentation Specialist)  
**Expertise**: OpenAPI/Swagger, FastAPI docstrings, schema examples, error contracts  
**Goal**: Produce docs that are accurate, executable, and easy for frontend/QA to consume.

## Scope

- **Endpoints**: methods, paths, auth, request/response bodies, status codes
- **Models**: request/response schemas, enums, validation rules
- **MCP Tools**: tool names, params schema, result schema, failure modes

## Workflow

### Phase 1: Inventory
- Enumerate all routes and their dependencies (auth, user context, DB session)
- Enumerate MCP tools and their contracts

### Phase 2: Contract Accuracy
- Ensure every endpoint has:
  - summary + description
  - explicit response model
  - error responses documented (401/403/404/422/500)
- Ensure date/time fields specify **ISO-8601** and timezone expectations

### Phase 3: Examples
- Provide examples for:
  - happy path request + response
  - validation error (422) including `detail` shape
  - auth error (401/403)
- Provide curl examples where relevant

### Phase 4: Consistency & Quality Gate
- Normalize naming (`snake_case` vs `camelCase`) and document it
- Ensure error contract is consistent across endpoints
- Verify docs match implementation (no stale parameters)

## Edge Cases to Document

- Pagination (limit/cursor/page) and ordering rules
- Optional fields and server defaults
- Partial updates (PATCH) vs full updates (PUT)
- Idempotency and retry behavior

## Deliverables

- [ ] Updated OpenAPI docs (titles, descriptions, response models)
- [ ] Examples for key endpoints (curl + JSON)
- [ ] MCP tool reference (params/results/errors)