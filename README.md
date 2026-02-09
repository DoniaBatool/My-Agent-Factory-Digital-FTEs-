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

---

**Digital Agent Factory** — Spec first. Plan then. Implement with skills. Test always. 🚀
