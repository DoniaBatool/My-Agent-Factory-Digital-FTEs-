# Architect Guidelines

## Planning & Architecture

Instructions: As an expert architect, generate a detailed architectural plan for [Project Name]. Address each of the following thoroughly.

### 1. Scope and Dependencies

- **In Scope**: boundaries and key features
- **Out of Scope**: explicitly excluded items
- **External Dependencies**: systems/services/teams and ownership

### 2. Key Decisions and Rationale

- **Options Considered**, Trade-offs, Rationale
- **Principles**: measurable, reversible where possible, smallest viable change

### 3. Interfaces and API Contracts

- **Public APIs**: Inputs, Outputs, Errors
- **Versioning Strategy**
- **Idempotency, Timeouts, Retries**
- **Error Taxonomy** with status codes

### 4. Non-Functional Requirements (NFRs) and Budgets

- **Performance**: p95 latency, throughput, resource caps
- **Reliability**: SLOs, error budgets, degradation strategy
- **Security**: AuthN/AuthZ, data handling, secrets, auditing
- **Cost**: unit economics

### 5. Data Management and Migration

- **Source of Truth**, Schema Evolution, Migration and Rollback, Data Retention

### 6. Operational Readiness

- **Observability**: logs, metrics, traces
- **Alerting**: thresholds and on-call owners
- **Runbooks** for common tasks
- **Deployment and Rollback** strategies
- **Feature Flags** and compatibility

### 7. Risk Analysis and Mitigation

- Top 3 Risks, blast radius, kill switches/guardrails

### 8. Evaluation and Validation

- **Definition of Done** (tests, scans)
- **Output Validation** for format/requirements/safety

### 9. Architectural Decision Record (ADR)

- For each significant decision, create an ADR and link it

---

## Architecture Decision Records (ADR) - Intelligent Suggestion

After design/architecture work, test for ADR significance:

- **Impact**: long-term consequences? (e.g., framework, data model, API, security, platform)
- **Alternatives**: multiple viable options considered?
- **Scope**: cross‑cutting and influences system design?

If ALL true, suggest:

```
📋 Architectural decision detected: [brief-description]
   Document reasoning and tradeoffs? Run `/sp.adr [decision-title]`
```

Wait for consent; never auto‑create ADRs. Group related decisions (stacks, authentication, deployment) into one ADR when appropriate.

---

## Execution Contract for Every Request

1. Confirm surface and success criteria (one sentence)
2. List constraints, invariants, non‑goals
3. Produce the artifact with acceptance checks inlined (checkboxes or tests where applicable)
4. Add follow‑ups and risks (max 3 bullets)
5. Create PHR in appropriate subdirectory under `history/prompts/` (constitution, feature-name, or general)
6. If plan/tasks identified decisions that meet significance, surface ADR suggestion text as described above

---

## Minimum Acceptance Criteria

- Clear, testable acceptance criteria included
- Explicit error paths and constraints stated
- Smallest viable change; no unrelated edits
- Code references to modified/inspected files where relevant
