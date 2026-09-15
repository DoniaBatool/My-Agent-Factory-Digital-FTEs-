# 🏭 Digital Agent Factory

**Full-Time Equivalent (FTE) AI Agents with Reusable Intelligence — Building software through Spec-Driven, AI-Driven, and Test-Driven Development**

---

## 📋 Table of Contents

- [Overview](#overview)
- [Development Methodologies](#development-methodologies)
- [How We Achieve Them](#how-we-achieve-them)
- [Agents](#agents)
- [Reusable Intelligence (Skills)](#reusable-intelligence-skills)
- [Methodology Integration](#methodology-integration)
- [Skill Versioning & Regression Gate](#%EF%B8%8F-skill-versioning--regression-gate--architecture-deep-dive)
- [Visual Guides](#%EF%B8%8F-visual-guides)
- [Quick Start](#quick-start)
- [Directory Structure](#directory-structure)

---

## Overview

Digital Agent Factory is an **AI-powered development system** that combines specialized FTE (Full-Time Equivalent) agents with reusable intelligence skills. Instead of writing code manually, you describe what you need — and the right agents, armed with domain-specific skills, execute the work while enforcing best practices and compliance.

**Core Philosophy:**  
*Specify first. Plan then. Implement with skills. Test always.*

---

## Development Methodologies

We achieve production-ready software through three integrated methodologies:

### 1. 📐 Spec-Driven Development (SDD)

**Definition:** No code is written until the specification is complete and approved. Requirements, architecture, and tasks are defined *before* implementation.

**The SDD Loop:**
```
Specify (WHAT) → Plan (HOW) → Tasks (BREAKDOWN) → Implement (CODE)
```

| Phase | File / Output | Purpose |
|-------|---------------|---------|
| **Constitution** | `speckit.constitution` | WHY — Principles, constraints, architecture values, security rules |
| **Specify** | `speckit.specify` | WHAT — Requirements, user journeys, acceptance criteria, domain rules |
| **Plan** | `speckit.plan` | HOW — Architecture, components, APIs, service boundaries |
| **Tasks** | `speckit.tasks` | BREAKDOWN — Atomic, testable work units with Task IDs |

**Rules Agents Must Follow:**
- Never generate code without a referenced Task ID
- Never modify architecture without updating `speckit.plan`
- Never propose features without updating `speckit.specify`
- If spec is missing → **Stop and request it**, do not improvise

---

### 2. 🤖 AI-Driven Development (AIDD)

**Definition:** Development is orchestrated by AI agents that analyze prompts, select the right specialists, invoke reusable skills, and coordinate execution — reducing manual decisions and human bottlenecks.

**How It Works:**
```
User Prompt → Orchestrator analyzes → Skills mapped → Agents assigned → Execution plan → Implementation
```

**Key Capabilities:**
- **Intent Detection** — Create, modify, test, deploy, debug, optimize
- **Automatic Routing** — Right agent for the right task (e.g., backend-developer for APIs, qa-engineer for tests)
- **Skill-First** — Agents use existing skills instead of manual implementation
- **Multi-Agent Coordination** — Complex features split across specialists and executed in sequence or parallel

---

### 3. 🧪 Test-Driven Development (TDD)

**Definition:** Tests are written or enforced before or alongside implementation. Quality is baked in through automation and edge-case coverage.

**How We Enforce It:**
- **QA Engineer Agent** — Runs test suites, validates quality
- **edge-case-tester Skill** — Identifies and covers edge cases
- **ab-testing Skill** — A/B test generation
- **production-checklist Skill** — Pre-deploy validation

**Integration:** Every implementation task has a corresponding test or validation step. Agents do not mark a feature complete until tests pass.

---

## How We Achieve Them

| Methodology | Achieved Via |
|-------------|--------------|
| **Spec-Driven Development** | `new-feature` skill (spec.md, plan.md, tasks.md), `api-contract-design` (OpenAPI first), `change-management` (spec updates before changes), Constitution enforcement in Orchestrator |
| **AI-Driven Development** | Orchestrator + 16 FTE agents + `prompt-analyzer` skill + 40+ reusable skills + automatic routing and delegation |
| **Test-Driven Development** | `qa-engineer` agent, `edge-case-tester` skill, `ab-testing` skill, `production-checklist` skill |

---

## Agents

Specialized FTE agents, each with clear roles and access to relevant skills.

### Master Orchestrator
| Agent | Role |
|-------|------|
| **orchestrator** | Analyzes every user prompt, maps to skills and agents, creates execution plans, and coordinates multi-agent workflows |

### Specialist Agents

| Agent | Role | Primary Skills |
|-------|------|----------------|
| **backend-developer** | APIs, auth, database integration | jwt-authentication, pydantic-validation, chatbot-endpoint, mcp-tool-builder |
| **frontend-developer** | UI/UX with React, Next.js | vercel-deployer, ab-testing, uiux-designer |
| **fullstack-architect** | System design, architecture | new-feature, change-management, skill-creator |
| **database-engineer** | Schema, migrations, optimization | database-schema-expander, connection-pooling, transaction-management |
| **devops-engineer** | Infrastructure, deployment, monitoring | deployment-automation, production-checklist, structured-logging |
| **security-engineer** | OWASP, auth, vulnerability testing | jwt-authentication, password-security, user-isolation, edge-case-tester |
| **qa-engineer** | Testing, quality assurance | edge-case-tester, ab-testing, production-checklist |
| **uiux-designer** | Interface and experience design | frontend-developer, ab-testing |
| **github-specialist** | Git, CI/CD, code review | change-management, production-checklist, deployment-automation |
| **vercel-deployer** | Vercel deployment, Next.js optimization | deployment-automation, production-checklist, performance-logger |
| **data-engineer** | Data pipelines, ETL, analytics | database-engineer, message-queue-integration, observability-apm |
| **technical-writer** | Docs, guides, API reference | api-docs-generator, frontend-developer, backend-developer |
| **cloud-architect** | AWS/GCP/Azure, Kubernetes | infrastructure-as-code, container-orchestration, observability-apm |
| **api-architect** | REST/GraphQL/gRPC, microservices | api-contract-design, graphql-api, microservices-patterns |
| **product-manager** | Requirements, roadmap, user stories | new-feature, change-management, fullstack-architect |

### Special Agents

| Agent | Role |
|-------|------|
| **live-skill-learner** | Captures fixes and improvements during development and updates skills automatically |

---

## Reusable Intelligence (Skills)

Skills are reusable instructions and patterns that agents invoke. They encode best practices, edge cases, and domain knowledge.

### Categories

| Category | Examples |
|----------|----------|
| **Workflow & Planning** | new-feature, change-management, skill-creator, skill-learner, prompt-analyzer |
| **Core Implementation** | backend-developer, frontend-developer, database-engineer, fullstack-architect |
| **Security & Auth** | jwt-authentication, password-security, user-isolation |
| **Quality & Testing** | edge-case-tester, qa-engineer, ab-testing |
| **Infrastructure & Deployment** | deployment-automation, aws-eks-deploy, azure-aks-deploy, gcp-gke-deploy, vercel-deployer |
| **API & Design** | api-contract-design, api-docs-generator, graphql-api |
| **Observability** | structured-logging, performance-logger, observability-apm |

### How Skills Support SDD, AIDD, TDD

| Methodology | Supporting Skills |
|-------------|-------------------|
| **Spec-Driven** | `new-feature`, `api-contract-design`, `change-management` |
| **AI-Driven** | `prompt-analyzer`, `skill-creator`, `skill-learner` |
| **Test-Driven** | `edge-case-tester`, `qa-engineer`, `production-checklist` |

---

## Methodology Integration

End-to-end flow from idea to production:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. SPEC-DRIVEN (What & How First)                                          │
│  ─────────────────────────────────                                          │
│  User: "Build todo chatbot with auth"                                       │
│       → new-feature: spec.md, plan.md, tasks.md                             │
│       → api-contract-design: OpenAPI contract                               │
│       → Constitution check before any code                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. AI-DRIVEN (Right Agents & Skills)                                       │
│  ─────────────────────────────────────                                      │
│  Orchestrator + prompt-analyzer                                             │
│       → Maps: backend-developer, database-engineer, security-engineer       │
│       → Invokes: jwt-authentication, chatbot-endpoint, database-schema      │
│       → Coordinates execution in sequence                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. TEST-DRIVEN (Quality Built-In)                                          │
│  ───────────────────────────────────                                        │
│  qa-engineer + edge-case-tester                                             │
│       → Edge case coverage                                                  │
│       → production-checklist before deploy                                  │
│       → No sign-off until tests pass                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. CONTINUOUS LEARNING (Skills Improve)                                    │
│  ───────────────────────────────────────                                    │
│  live-skill-learner captures fixes → skill-learner updates skills           │
│       → Same issues don't repeat                                            │
│       → Skills become more reliable over time                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ Skill Versioning & Regression Gate — Architecture Deep-Dive

In late 2026, an external reviewer's LinkedIn comment flagged a real risk in how
this repo's skills were being updated: letting an agent rewrite a skill's code
**and** its tests in the same pass makes it easy to mistake a weaker test for an
improvement. An audit confirmed it had already happened once
(`grafana-expert` / `prometheus-monitoring` — see `.claude/CLAUDE.md` for the
full incident writeup). The fix is now a permanent part of this repo's
architecture.

**The rule:** no skill's `scripts/tool.py` or `tests/` may be changed except by
promotion through `.claude/skills/_framework/skill_gate.py`, which enforces
three checks before anything live is touched:

```mermaid
flowchart TD
    A["Edit skill in a FULL copy:\n&lt;skill&gt;.staged/"] --> B["skill_gate.py promote"]
    B --> C{"1. Any live file\nsilently missing\nfrom staged?"}
    C -- "yes" --> R["❌ REJECT\nnothing changes,\nreason logged"]
    C -- "no" --> D{"2. Baseline test\ncount shrunk?"}
    D -- "yes" --> R
    D -- "no" --> E{"3. Full pytest\nsuite passes?"}
    E -- "no" --> R
    E -- "yes" --> F["✅ Archive old version"]
    F --> G["Replace live directory"]
    G --> H["Bump version.json"]
    H --> I["Append CHANGELOG.md"]
```

**Why this matters for readers:** every skill in `.claude/skills/` now carries
its own `version.json`, `CHANGELOG.md`, `tests/test_tool.py`, and an
`_archive/` snapshot of every prior version — a skill's test suite can only
grow, never silently shrink, and every promotion is reversible. 39 skills have
been through this gate; 346 tests pass repo-wide.

For the full incident writeup, the near-miss that led to an extra safeguard,
and a dos/don'ts/red-flags list for anyone (human or AI) working on this repo
next, see **[`.claude/CLAUDE.md`](.claude/CLAUDE.md)** and
**[`.claude/docs/skill-versioning-policy.md`](.claude/docs/skill-versioning-policy.md)**.

---

## 🖼️ Visual Guides

| Format | Link |
|--------|------|
| Architecture infographic (Canva) | [View on Canva](https://www.canva.com/d/jtX0z4YkbxmQXeR) |
| Explainer video — problem, audit, fix, rollout, result (HyperFrames by HeyGen) | [Watch / download MP4](https://github.com/DoniaBatool/My-Agent-Factory-Digital-FTEs-/releases/download/media-v1/video.mp4) |
| Slide deck — architecture & engineering mechanism, 14 slides (Canva) | [View on Canva](https://www.canva.com/d/5t9mI8-0ZRIQcT_) |

---

## Quick Start

### 1. Invoke the Orchestrator (Recommended)

Describe your task in plain language. The Orchestrator will analyze, map skills, assign agents, and propose an execution plan:

```
User: "Add JWT authentication to the API"
→ Orchestrator analyzes
→ Assigns: backend-developer, security-engineer
→ Invokes: jwt-authentication, password-security, user-isolation
→ Waits for approval, then executes
```

### 2. Use Specific Agents

For direct control, invoke agents by name:

```
Use: /backend-developer — Implement API endpoints
Use: /qa-engineer — Run test suite
Use: /fullstack-architect — Design system architecture
```

### 3. Use Skills Directly

For targeted work:

```
/sp.new-feature — Scaffold spec, plan, tasks from a description
/sp.api-contract-design — Design OpenAPI contract
/sp.edge-case-tester — Add edge case tests
```

---

## Directory Structure

```
digital_factory/
├── agents/                    # FTE Agent definitions
│   ├── orchestrator.md        # Master orchestrator
│   ├── backend-developer.md
│   ├── frontend-developer.md
│   ├── fullstack-architect.md
│   ├── database-engineer.md
│   ├── devops-engineer.md
│   ├── security-engineer.md
│   ├── qa-engineer.md
│   ├── live-skill-learner/    # Real-time skill learning
│   └── ... (15+ agents)
│
├── skills/                    # Reusable Intelligence (40+ skills)
│   ├── new-feature/           # Spec scaffolding
│   ├── api-contract-design/   # OpenAPI contracts
│   ├── prompt-analyzer/       # Intent & skill mapping
│   ├── edge-case-tester/      # Edge case coverage
│   ├── jwt-authentication/
│   ├── aws-eks-deploy/
│   ├── azure-aks-deploy/
│   └── ... (40+ skills)
│
└── README.md                  # This file
```

---

## Benefits

| Benefit | How |
|---------|-----|
| **No Vibe Coding** | SDD ensures specs and tasks exist before code |
| **Consistent Quality** | Skills embed best practices; TDD enforces coverage |
| **Faster Development** | Right agents and skills are chosen automatically |
| **Compounding Intelligence** | live-skill-learner keeps skills improving |
| **Scalability** | New agents and skills can be added without changing core flow |

---

## Related Documents

- [Agents README](agents/README.md) — Full agent list and usage
- [40 AI Systems for Company](40_AI_Systems%20for%20company%20(must%20have).md) — Broader AI systems context
- [Wire Spec-KitPlus into Claude via MCP](Wire%20Spec-KitPlus%20into%20Claude%20via%20MCP.md) — MCP integration
- [Creating Agents](creating_agents_md.md) — Spec-Kit and agent workflow
- [.claude/CLAUDE.md](.claude/CLAUDE.md) — Full engineering instructions, plus the Skill Versioning & Regression Gate incident writeup, dos/don'ts, blacklist, greylist, and red flags for anyone working on this repo next
- [.claude/docs/skill-versioning-policy.md](.claude/docs/skill-versioning-policy.md) — The versioning policy in full

---

**Digital Agent Factory** — Spec first. Plan then. Implement with skills. Test always. 🚀
