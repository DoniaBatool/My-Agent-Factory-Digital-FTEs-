# 🏭 Digital Agent Factory

## Full-Time Equivalent (FTE) AI Agents with Reusable Intelligence

This directory contains **18 specialized FTE agents**, each with a documented role, a
defined scope of responsibility, and access to relevant skills from the `.claude/skills/`
directory. Every agent has been through the agent-QA gate in `.claude/agents/_framework/`
(structural review + genuine live-simulation evaluation) — see **Agent QA Status** below.

## 🤖 Available Agents

### 🎯 Master Orchestrator (`/orchestrator`)
**Role**: Intelligent orchestrator that analyzes prompts, assigns agents, and coordinates execution
**Skills**: `prompt-analyzer` + delegates to all specialist agents/skills
**Special Capabilities**:
- Automatic prompt analysis using `/sp.prompt-analyzer`
- Intent detection and keyword extraction
- Skills mapping and agent assignment
- Execution plan generation (presented for approval before complex/multi-agent delegation)
- Multi-agent coordination and constitution enforcement

**Use when**: Deciding which specialized agent(s) a request should route to.

**See**: `.claude/agents/orchestrator.md` for complete documentation

---

### 1. Backend Developer (`/backend-developer`)
**Role**: Backend API development and database integration
**Skills**: jwt-authentication, password-security, pydantic-validation, connection-pooling,
transaction-management, database-schema-expander, mcp-tool-builder, chatbot-endpoint,
conversation-manager, api-docs-generator, user-isolation

**Use when**: Building APIs, implementing authentication, database operations, MCP tools

---

### 2. Frontend Developer (`/frontend-developer`)
**Role**: UI/UX implementation with React and Next.js
**Skills**: vercel-deployer, ab-testing, uiux-designer

**Use when**: Building user interfaces, implementing responsive designs, deploying to Vercel

---

### 3. Full Stack Architect (`/fullstack-architect`)
**Role**: System design and architectural decisions
**Skills**: new-feature, change-management, skill-creator, backend-developer,
frontend-developer, database-engineer, devops-engineer, security-engineer

**Use when**: Planning features, making architectural decisions, creating ADRs

---

### 4. Database Engineer (`/database-engineer`)
**Role**: Database design, optimization, and migrations
**Skills**: database-schema-expander, connection-pooling, transaction-management, user-isolation

**Use when**: Designing schemas, optimizing queries, creating migrations

---

### 5. DevOps Engineer (`/devops-engineer`)
**Role**: Infrastructure, deployment, and monitoring
**Skills**: deployment-automation, production-checklist, structured-logging, performance-logger

**Use when**: Deploying applications, setting up monitoring, infrastructure automation

---

### 6. Security Engineer (`/security-engineer`)
**Role**: Security audits, OWASP compliance, penetration testing
**Skills**: jwt-authentication, password-security, user-isolation, edge-case-tester, pydantic-validation

**Use when**: Security audits, authentication implementation, vulnerability testing

---

### 7. QA Engineer (`/qa-engineer`)
**Role**: Testing automation, quality assurance
**Skills**: edge-case-tester, ab-testing, production-checklist

**Use when**: Writing tests, performance testing, quality validation

---

### 8. UI/UX Designer (`/uiux-designer`)
**Role**: User experience and interface design
**Skills**: frontend-developer, ab-testing

**Use when**: Designing interfaces, creating design systems, user testing

---

### 9. GitHub Specialist (`/github-specialist`)
**Role**: Git workflows, CI/CD, code review, repository management
**Skills**: change-management, production-checklist, deployment-automation

**Use when**: Managing Git workflows, setting up CI/CD, code reviews, branch protection,
release management

---

### 10. Vercel Deployer (`/vercel-deployer`)
**Role**: Vercel platform deployment and optimization
**Skills**: deployment-automation, production-checklist, frontend-developer, performance-logger

**Use when**: Deploying to Vercel, optimizing Next.js apps, performance tuning

---

### 11. Data Engineer (`/data-engineer`)
**Role**: Data pipelines, ETL/ELT, analytics infrastructure
**Skills**: database-engineer, performance-logger, structured-logging, api-docs-generator,
microservices-patterns, message-queue-integration, observability-apm

**Use when**: Building data pipelines, analytics dashboards, ETL processes, BI integration

---

### 12. Technical Writer (`/technical-writer`)
**Role**: Technical documentation, user guides, API docs
**Skills**: api-docs-generator, frontend-developer, backend-developer, uiux-designer

**Use when**: Creating documentation, user guides, API reference, tutorials, release notes

---

### 13. Cloud Architect (`/cloud-architect`)
**Role**: Cloud infrastructure (AWS/GCP/Azure), Kubernetes
**Skills**: devops-engineer, infrastructure-as-code, container-orchestration,
deployment-automation, observability-apm, performance-logger, security-engineer

**Use when**: Cloud infrastructure design, Kubernetes setup, cloud migration, IaC (Terraform)

---

### 14. API Architect (`/api-architect`)
**Role**: API design, REST/GraphQL/gRPC, microservices
**Skills**: api-contract-design, graphql-api, api-docs-generator, backend-developer,
microservices-patterns, observability-apm

**Use when**: API contract design, API versioning, microservices communication, GraphQL implementation

---

### 15. Product Manager (`/product-manager`)
**Role**: Requirements, user stories, roadmap planning
**Skills**: new-feature, change-management, fullstack-architect, technical-writer

**Use when**: Requirements gathering, feature prioritization, roadmap planning, user story creation

---

### 16. Live Change-Management Agent (`live-change-management`)
**Role**: Automatically tracks code changes in real time and propagates consistent updates
across every affected file, layer, and test
**Skills**: change-management

**Use when**: A request updates/modifies/renames/refactors an existing component, model,
endpoint, or feature and every affected file (model, schema, types, UI, tests, docs) needs
to stay in sync

---

### 17. Live Skill-Learner Agent (`live-skill-learner`)
**Role**: Captures fixes and corrections made during feature implementation and turns them
into staged, gate-verified improvements to the relevant skill
**Skills**: skill-learner (writes through `.claude/skills/_framework/skill_gate.py promote`)

**Use when**: A bug fix, correction, or edge case discovered during feature work should be
preserved as a permanent improvement to the skill involved, without regressing its existing tests

---

## 📊 Skills Matrix

| Agent | Skills (approx.) | Primary Domain |
|-------|-------------------|-----------------|
| Orchestrator | routes to all specialists | Task Delegation & Coordination |
| Backend Developer | 11 | Backend APIs & Database |
| Frontend Developer | 3 | UI/UX Implementation |
| Full Stack Architect | 8 | System Design |
| Database Engineer | 4 | Database & Performance |
| DevOps Engineer | 4 | Infrastructure & Deployment |
| Security Engineer | 5 | Security & Compliance |
| QA Engineer | 3 | Testing & Quality |
| UI/UX Designer | 2 | Design & User Experience |
| GitHub Specialist | 3 | Git & CI/CD |
| Vercel Deployer | 4 | Vercel Platform |
| Data Engineer | 7 | Data Pipelines & Analytics |
| Technical Writer | 4 | Documentation |
| Cloud Architect | 7 | Cloud Infrastructure |
| API Architect | 6 | API Design & Microservices |
| Product Manager | 4 | Requirements & Planning |
| Live Change-Management | 1 (change-management) | Cross-file change propagation |
| Live Skill-Learner | 1 (skill-learner) | Continuous skill improvement |

**Total Agents:** 18
**Total Skills Available:** 60 (see `.claude/skills/` for the full library)

## ✅ Agent QA Status

All 18 agents in this directory have been onboarded through the agent-QA gate in
`.claude/agents/_framework/agent_gate.py`. Each agent has:

- Required frontmatter (`name`, `role`, `description`, `version`) and the six required body
  sections: Role, Scope, Tools Allowed, Guardrails, Escalation Rules, Out of Scope
- `_meta/<agent-name>/eval_scenarios.yaml` and `redteam_prompts.yaml` — at least 5 (in
  practice 6) genuine, agent-specific test scenarios each, covering normal use and
  adversarial/social-engineering attempts
- `_meta/<agent-name>/eval_results.json` — a full live simulation of the persona against
  every documented scenario/prompt, personally graded, with every verdict required to be PASS

Check any agent's status with:
```bash
python3 .claude/agents/_framework/agent_gate.py check --agents-dir .claude/agents --agent-name <name>
```

## 🎯 Usage Examples

### Example 1: Building a New Feature
```
1. /fullstack-architect - Plan the architecture
2. /backend-developer - Implement backend APIs
3. /frontend-developer - Build UI components
4. /security-engineer - Security audit
5. /qa-engineer - Comprehensive testing
6. /devops-engineer - Deploy to production
```

### Example 2: Adding Authentication
```
1. /security-engineer - Design auth strategy
2. /backend-developer - Implement JWT + password security
3. /database-engineer - User isolation at DB level
4. /qa-engineer - Security edge case testing
```

### Example 3: Performance Optimization
```
1. /database-engineer - Optimize queries and connection pooling
2. /backend-developer - Add performance logging
3. /devops-engineer - Setup monitoring
4. /qa-engineer - Load testing
```

### Example 4: Production Deployment
```
1. /devops-engineer - Production checklist validation
2. /security-engineer - Security audit
3. /qa-engineer - Smoke tests
4. /vercel-deployer - Deploy frontend to Vercel
5. /github-specialist - Create release and tag
```

### Example 5: Ongoing Change / Fix Propagation
```
1. live-change-management - Propagate a model/endpoint/component change across every
   affected file, layer, and test
2. live-skill-learner - Capture a fix made during implementation as a permanent,
   gate-verified skill improvement
```

## 🔧 How It Works

Each agent:
1. **Has a specific role** with clear responsibilities, documented Scope, and an explicit
   Out of Scope
2. **Has documented Guardrails and Escalation Rules** — what it will refuse to do
   unilaterally and when it hands off to another agent or a human
3. **Access to relevant skills** from `.claude/skills/` directory
4. **Follows constitution principles** (stateless, user isolation, etc.)
5. **Integrates with other agents** for complex workflows, coordinated by the orchestrator

## 🚀 Invoking Agents

Agents can be invoked in several ways:

### Method 1: Direct Reference
```markdown
I need backend API implementation.

Use: /backend-developer
```

### Method 2: Task-Based
```markdown
Task: Add authentication to the app

Relevant Agents:
- /security-engineer (design)
- /backend-developer (implementation)
- /qa-engineer (testing)
```

### Method 3: Workflow-Based
```markdown
Workflow: New Feature Development

Pipeline:
/fullstack-architect -> /backend-developer -> /frontend-developer ->
/security-engineer -> /qa-engineer -> /devops-engineer
```

## 📁 Directory Structure

```
.claude/
├── agents/                        # FTE Agent definitions (this directory)
│   ├── orchestrator.md
│   ├── backend-developer.md
│   ├── frontend-developer.md
│   ├── fullstack-architect.md
│   ├── database-engineer.md
│   ├── devops-engineer.md
│   ├── security-engineer.md
│   ├── qa-engineer.md
│   ├── uiux-designer.md
│   ├── github-specialist.md
│   ├── vercel-deployer.md
│   ├── data-engineer.md
│   ├── technical-writer.md
│   ├── cloud-architect.md
│   ├── api-architect.md
│   ├── product-manager.md
│   ├── live-change-management.md
│   ├── live-skill-learner.md
│   ├── _framework/                # agent_gate.py QA gate + its own test suite
│   ├── _meta/                     # per-agent eval_scenarios/redteam_prompts/eval_results
│   └── README.md                  # (this file)
│
└── skills/                        # Reusable Intelligence Skills (60 total)
    ├── jwt-authentication/
    ├── password-security/
    ├── database-schema-expander/
    └── ... (57 more)
```

## 🧠 Reusable Intelligence

All agents leverage **Reusable Intelligence Skills** from `.claude/skills/`:

**Total Skills Available**: 60 skills, each independently gated for coverage and mutation
score through `.claude/skills/_framework/skill_gate.py`

See `.claude/skills/` directory for the complete skill library.

## 🎓 Learning & Evolution

This Digital Agent Factory:
- ✅ **Evolves**: New skills can be added to any agent
- ✅ **Learns**: `live-skill-learner` captures fixes as gate-verified skill improvements
- ✅ **Scales**: New agents can be created as needed (onboard them through
  `.claude/agents/_framework/agent_gate.py`)
- ✅ **Integrates**: Agents work together seamlessly, coordinated by the orchestrator
- ✅ **Enforces**: Constitution principles and each agent's own documented guardrails

## 🏆 Best Practices

1. **Choose the right agent** for the task — the most specialized one available
2. **Use agent pipelines** for complex workflows
3. **Let agents use their skills** - don't implement manually
4. **Follow agent guardrails and escalation rules** - they exist to catch real failure modes
5. **Document agent usage** in PHRs (Prompt History Records)

---

**Digital Agent Factory** - Powered by Reusable Intelligence 🚀
