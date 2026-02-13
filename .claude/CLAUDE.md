# Digital Agent Factory - Claude Code Instructions

**Project Type:** AI-Powered Development System with FTE Agents & Reusable Intelligence

---

## Core Philosophy

> **Specify first. Plan then. Implement with skills. Test always.**

This project follows three integrated methodologies:
1. **Spec-Driven Development (SDD)** - No code without specification
2. **AI-Driven Development (AIDD)** - AI agents orchestrate development
3. **Test-Driven Development (TDD)** - Quality built-in through testing

---

## Critical Rules for All Agents

### ⛔ Absolute Requirements

1. **NEVER generate code without a referenced Task ID**
2. **NEVER modify architecture without updating `speckit.plan`**
3. **NEVER propose features without updating `speckit.specify`**
4. **NEVER change principles without updating `speckit.constitution`**
5. **If spec is missing → STOP and request it** - DO NOT improvise

---

## Spec-Kit Workflow (Source of Truth)

### The SDD Loop
```
Constitution (WHY) → Specify (WHAT) → Plan (HOW) → Tasks (BREAKDOWN) → Implement (CODE)
```

| Phase | File | Purpose |
|-------|------|---------|
| **Constitution** | `speckit.constitution` | WHY — Principles, constraints, architecture values, security rules |
| **Specify** | `speckit.specify` | WHAT — Requirements, user journeys, acceptance criteria, domain rules |
| **Plan** | `speckit.plan` | HOW — Architecture, components, APIs, service boundaries |
| **Tasks** | `speckit.tasks` | BREAKDOWN — Atomic, testable work units with Task IDs |
| **Implement** | Code files | CODE — Implementation referencing Task IDs |

### File Hierarchy (in case of conflict)
```
Constitution > Specify > Plan > Tasks
```

---

## Working with Agents

### Available FTE Agents

**Master Orchestrator:**
- `orchestrator.md` - Analyzes prompts, maps skills, coordinates multi-agent workflows

**Specialist Agents:**
- `backend-developer.md` - APIs, auth, database integration
- `frontend-developer.md` - UI/UX with React, Next.js
- `fullstack-architect.md` - System design, architecture
- `database-engineer.md` - Schema, migrations, optimization
- `devops-engineer.md` - Infrastructure, deployment, monitoring
- `security-engineer.md` - OWASP, auth, vulnerability testing
- `qa-engineer.md` - Testing, quality assurance
- `uiux-designer.md` - Interface and experience design
- `github-specialist.md` - Git, CI/CD, code review
- `vercel-deployer.md` - Vercel deployment, Next.js optimization
- `data-engineer.md` - Data pipelines, ETL, analytics
- `technical-writer.md` - Docs, guides, API reference
- `cloud-architect.md` - AWS/GCP/Azure, Kubernetes
- `api-architect.md` - REST/GraphQL/gRPC, microservices
- `product-manager.md` - Requirements, roadmap, user stories

**Special Agents:**
- `live-skill-learner/` - Captures fixes and improvements, updates skills automatically

### How to Invoke Agents

When a user requests work:
1. Read the appropriate agent file from `/agents/`
2. Follow the agent's instructions and skill mappings
3. Use the agent's primary skills for implementation
4. Coordinate with other agents as needed

---

## Working with Skills

Skills are reusable intelligence stored in `/skills/` directory. Each skill contains:
- `SKILL.md` - Instructions, patterns, best practices
- Optional scripts, templates, examples

### Key Skill Categories

**Workflow & Planning:**
- `new-feature` - Scaffold spec, plan, tasks
- `change-management` - Manage spec updates
- `skill-creator` - Create new skills
- `prompt-analyzer` - Intent & skill mapping

**Security & Auth:**
- `jwt-authentication`, `password-security`, `user-isolation`

**Quality & Testing:**
- `edge-case-tester`, `qa-engineer`, `ab-testing`, `production-checklist`

**Infrastructure & Deployment:**
- `deployment-automation`, `aws-eks-deploy`, `azure-aks-deploy`, `gcp-gke-deploy`

**API & Design:**
- `api-contract-design`, `api-docs-generator`, `graphql-api`

### How to Use Skills

1. Check if a relevant skill exists in `/skills/`
2. Read the `SKILL.md` file
3. Follow the skill's instructions
4. Reference the skill in your implementation

---

## Code Implementation Rules

### When Generating Code

Every code file MUST contain comments linking to:
```python
# [Task]: T-001
# [From]: speckit.specify §2.1, speckit.plan §3.4
# [Skill]: jwt-authentication
```

### Code Generation Process

1. **Verify Task ID exists** in `speckit.tasks`
2. **Check referenced sections** in `speckit.specify` and `speckit.plan`
3. **Follow relevant skills** for implementation patterns
4. **Write code** with proper references
5. **Never freestyle** - stick to the spec

---

## Agent Behavior Patterns

### ✅ When Proposing Code
```
Reference: [Task]: T-001 from speckit.tasks
Implements: speckit.specify §2.1 (User authentication)
Architecture: speckit.plan §3.4 (JWT middleware)
Skill: jwt-authentication
```

### ✅ When Proposing Architecture Changes
```
⚠️ Update Required in speckit.plan
New Component: API Gateway
Reason: [explain architectural need]
Affects: [list impacted components]
```

### ✅ When Proposing New Features
```
⚠️ Update Required in speckit.specify
New Requirement: [describe feature]
User Journey: [explain user flow]
Acceptance Criteria: [define success]
```

### ✅ When Changing Principles
```
⚠️ Modify speckit.constitution
Principle Change: [describe change]
Rationale: [explain why]
Impact: [assess consequences]
```

---

## Prohibited Agent Behaviors

### ⛔ NEVER Do This

- ❌ Freestyle code or architecture
- ❌ Generate missing requirements
- ❌ Create tasks independently
- ❌ Alter tech stack without justification
- ❌ Add endpoints/fields/flows not in spec
- ❌ Ignore acceptance criteria
- ❌ Produce "creative" implementations violating the plan
- ❌ Skip spec updates when proposing changes

---

## Development Workflow

### For New Features

1. **User Request** → Analyze intent
2. **Check Spec-Kit** → Does spec exist?
3. **If No Spec:**
   - Use `new-feature` skill to scaffold
   - Create: `speckit.constitution`, `speckit.specify`, `speckit.plan`, `speckit.tasks`
   - Get user approval
4. **If Spec Exists:**
   - Read constitution, specify, plan, tasks
   - Identify relevant agents and skills
   - Implement according to tasks
5. **Testing:**
   - Use `edge-case-tester` skill
   - Run `qa-engineer` checks
   - Validate with `production-checklist`
6. **Continuous Learning:**
   - `live-skill-learner` captures improvements
   - Skills updated for future use

### For Modifications

1. **Read existing spec-kit files**
2. **Determine what needs updating:**
   - Constitution? (principles changed)
   - Specify? (requirements changed)
   - Plan? (architecture changed)
   - Tasks? (work breakdown changed)
3. **Update spec-kit first**
4. **Then implement code changes**
5. **Update tests**

---

## Directory Structure

```
digital_factory/
├── .claude/
│   ├── CLAUDE.md           # This file - instructions for Claude
│   ├── ignore              # Files to ignore
│   └── project.json        # Project metadata
├── agents/                 # FTE Agent definitions (16+ agents)
│   ├── orchestrator.md
│   ├── backend-developer.md
│   ├── frontend-developer.md
│   └── ... (15+ more)
├── skills/                 # Reusable Intelligence (40+ skills)
│   ├── new-feature/
│   ├── api-contract-design/
│   ├── jwt-authentication/
│   └── ... (40+ more)
└── README.md              # Project overview
```

---

## Session Initialization

Before every session, read:
1. `.claude/CLAUDE.md` (this file)
2. Relevant agent files from `/agents/`
3. Relevant skill files from `/skills/`
4. Spec-Kit files if they exist:
   - `speckit.constitution`
   - `speckit.specify`
   - `speckit.plan`
   - `speckit.tasks`

---

## Integration with AI-Driven Development

### Orchestrator Pattern

When user gives a prompt:
1. **Orchestrator analyzes** → Intent detection
2. **Maps to skills** → Which skills apply?
3. **Assigns agents** → Which specialists needed?
4. **Creates execution plan** → Sequential or parallel?
5. **Waits for approval** → User confirms
6. **Coordinates execution** → Agents execute tasks

### Multi-Agent Coordination

Complex features may require:
- **Parallel execution:** Independent tasks (frontend + backend)
- **Sequential execution:** Dependent tasks (schema → API → tests)
- **Skill chaining:** One skill's output feeds another

---

## Quality Gates

Before marking any feature complete:

✅ **Spec Compliance**
- All code references Task IDs
- Implementation matches Plan
- Requirements from Specify are met

✅ **Testing**
- Unit tests written and passing
- Edge cases covered (`edge-case-tester`)
- Production checklist validated

✅ **Documentation**
- API docs generated (`api-docs-generator`)
- Code comments reference specs
- Skills updated if new patterns learned

---

## Emergency Scenarios

### Spec Missing or Incomplete
```
⚠️ STOP - Specification Required

Missing: [constitution/specify/plan/tasks]
Cannot proceed without: [explain what's needed]
Recommend: Use `new-feature` skill to scaffold

❓ Should I create the spec now? [yes/no]
```

### Spec Conflict
```
⚠️ Spec Conflict Detected

Conflict between: speckit.specify §X and speckit.plan §Y
Issue: [describe contradiction]
Resolution needed before proceeding

Hierarchy: Constitution > Specify > Plan > Tasks
```

### Task Underspecified
```
⚠️ Task T-XXX Underspecified

Missing: [preconditions/outputs/acceptance criteria]
Cannot implement without clarification

❓ Please clarify: [specific questions]
```

---

## Benefits of This Approach

| Benefit | How Achieved |
|---------|--------------|
| **No Vibe Coding** | SDD ensures specs exist before code |
| **Consistent Quality** | Skills embed best practices; TDD enforces coverage |
| **Faster Development** | Right agents/skills chosen automatically (AIDD) |
| **Compounding Intelligence** | `live-skill-learner` keeps skills improving |
| **Scalability** | New agents/skills added without changing core flow |
| **Traceability** | Every line of code traces to spec |
| **Predictability** | Deterministic development process |

---

## Quick Reference

### User Commands
```bash
# Invoke orchestrator (recommended)
"Build feature X with Y requirements"

# Use specific agent
Use agent: backend-developer, frontend-developer, etc.

# Use specific skill
Use skill: new-feature, api-contract-design, edge-case-tester
```

### File References
```
Constitution: speckit.constitution
Requirements: speckit.specify
Architecture: speckit.plan
Work Units: speckit.tasks
```

---

**Remember:** Specify first. Plan then. Implement with skills. Test always. 🚀
