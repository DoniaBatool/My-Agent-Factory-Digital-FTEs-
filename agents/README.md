# 🏭 Digital Agent Factory

## Full-Time Equivalent (FTE) AI Agents with Reusable Intelligence

This directory contains **16 specialized FTE agents** (EXPANDED!), each with expertise in their domain and access to relevant skills from the `.claude/skills/` directory.

## 🤖 Available Agents

### 🎯 Master Orchestrator (`/orchestrator`) - NEW!
**Role**: Intelligent orchestrator that analyzes prompts, assigns agents, and coordinates execution
**Skills**: prompt-analyzer + access to all 32 skills
**Special Capabilities**:
- Automatic prompt analysis using `/sp.prompt-analyzer`
- Intent detection and keyword extraction
- Skills mapping and agent assignment
- Execution plan generation
- Multi-agent coordination
- Constitution enforcement

**Use when**: **AUTO-TRIGGERS on EVERY user request** - This is the master agent that decides which specialized agents to use.

**How it works**:
1. User submits prompt → Orchestrator analyzes
2. Detects intent & keywords
3. Maps to required skills
4. Assigns specialized agents
5. Generates execution plan
6. Coordinates agent execution
7. Reports completion

**See**: `.claude/agents/orchestrator.md` for complete documentation

---

### 1. Backend Developer (`/backend-developer`)
**Role**: Backend API development and database integration
**Skills**: 11 skills
- jwt-authentication
- password-security
- pydantic-validation
- connection-pooling
- transaction-management
- database-schema-expander
- mcp-tool-builder
- chatbot-endpoint
- conversation-manager
- api-docs-generator
- user-isolation

**Use when**: Building APIs, implementing authentication, database operations, MCP tools

---

### 2. Frontend Developer (`/frontend-developer`)
**Role**: UI/UX implementation with React and Next.js
**Skills**: 3 skills
- vercel-deployer
- ab-testing
- uiux-designer

**Use when**: Building user interfaces, implementing responsive designs, deploying to Vercel

---

### 3. Full Stack Architect (`/fullstack-architect`)
**Role**: System design and architectural decisions
**Skills**: 8 skills
- new-feature
- change-management
- skill-creator
- backend-developer
- frontend-developer
- database-engineer
- devops-engineer
- security-engineer

**Use when**: Planning features, making architectural decisions, creating ADRs

---

### 4. Database Engineer (`/database-engineer`)
**Role**: Database design, optimization, and migrations
**Skills**: 4 skills
- database-schema-expander
- connection-pooling
- transaction-management
- user-isolation

**Use when**: Designing schemas, optimizing queries, creating migrations

---

### 5. DevOps Engineer (`/devops-engineer`)
**Role**: Infrastructure, deployment, and monitoring
**Skills**: 4 skills
- deployment-automation
- production-checklist
- structured-logging
- performance-logger

**Use when**: Deploying applications, setting up monitoring, infrastructure automation

---

### 6. Security Engineer (`/security-engineer`)
**Role**: Security audits, OWASP compliance, penetration testing
**Skills**: 5 skills
- jwt-authentication
- password-security
- user-isolation
- edge-case-tester
- pydantic-validation

**Use when**: Security audits, authentication implementation, vulnerability testing

---

### 7. QA Engineer (`/qa-engineer`)
**Role**: Testing automation, quality assurance
**Skills**: 3 skills
- edge-case-tester
- ab-testing
- production-checklist

**Use when**: Writing tests, performance testing, quality validation

---

### 8. UI/UX Designer (`/uiux-designer`)
**Role**: User experience and interface design
**Skills**: 2 skills
- frontend-developer
- ab-testing

**Use when**: Designing interfaces, creating design systems, user testing

---

### 9. GitHub Specialist (`/github-specialist`)
**Role**: Git workflows, CI/CD, code review
**Skills**: 3 skills
- change-management
- production-checklist
- deployment-automation

**Use when**: Managing Git workflows, setting up CI/CD, code reviews

---

### 10. Vercel Deployer (`/vercel-deployer`)
**Role**: Vercel platform deployment and optimization
**Skills**: 4 skills
- deployment-automation
- production-checklist
- frontend-developer
- performance-logger

**Use when**: Deploying to Vercel, optimizing Next.js apps, performance tuning

---

### 🆕 NEW SPECIALIST AGENTS (5)

### 11. Data Engineer (`/data-engineer`)
**Role**: Data pipelines, ETL/ELT, analytics infrastructure
**Skills**: 7 skills
- database-engineer
- performance-logger
- structured-logging
- message-queue-integration
- observability-apm
- microservices-patterns
- caching-strategy

**Use when**: Building data pipelines, analytics dashboards, ETL processes, BI integration

---

### 12. Technical Writer (`/technical-writer`)
**Role**: Technical documentation, user guides, API docs
**Skills**: 4 skills
- api-docs-generator
- frontend-developer
- backend-developer
- uiux-designer

**Use when**: Creating documentation, user guides, API reference, tutorials, release notes

---

### 13. Cloud Architect (`/cloud-architect`)
**Role**: Cloud infrastructure (AWS/GCP/Azure), Kubernetes
**Skills**: 7 skills
- devops-engineer
- infrastructure-as-code
- container-orchestration
- deployment-automation
- observability-apm
- performance-logger
- security-engineer

**Use when**: Cloud infrastructure design, Kubernetes setup, cloud migration, IaC (Terraform)

---

### 14. API Architect (`/api-architect`)
**Role**: API design, REST/GraphQL/gRPC, microservices
**Skills**: 6 skills
- api-contract-design
- graphql-api
- api-docs-generator
- backend-developer
- microservices-patterns
- observability-apm

**Use when**: API contract design, API versioning, microservices communication, GraphQL implementation

---

### 15. Product Manager (`/product-manager`)
**Role**: Requirements, user stories, roadmap planning
**Skills**: 4 skills
- new-feature
- change-management
- fullstack-architect
- technical-writer

**Use when**: Requirements gathering, feature prioritization, roadmap planning, user story creation

---

## 📊 Skills Matrix (Updated - 16 Agents)

| Agent | Total Skills | Primary Domain |
|-------|--------------|----------------|
| **Orchestrator** | All 42 | Task Delegation & Coordination |
| Backend Developer | 11 | Backend APIs & Database |
| Frontend Developer | 6 | UI/UX Implementation |
| Full Stack Architect | 8 | System Design |
| Database Engineer | 4 | Database & Performance |
| DevOps Engineer | 4 | Infrastructure & Deployment |
| Security Engineer | 5 | Security & Compliance |
| QA Engineer | 3 | Testing & Quality |
| UI/UX Designer | 2 | Design & User Experience |
| GitHub Specialist | 3 | Git & CI/CD |
| Vercel Deployer | 4 | Vercel Platform |
| **🆕 Data Engineer** | 7 | Data Pipelines & Analytics |
| **🆕 Technical Writer** | 4 | Documentation |
| **🆕 Cloud Architect** | 7 | Cloud Infrastructure |
| **🆕 API Architect** | 6 | API Design & Microservices |
| **🆕 Product Manager** | 4 | Requirements & Planning |

**Total Agents:** 16 (was 11)
**Total Skills Available:** 42 (was 32)

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

## 🔧 How It Works

Each agent:
1. **Has a specific role** with clear responsibilities
2. **Access to relevant skills** from `.claude/skills/` directory
3. **Follows constitution principles** (stateless, user isolation, etc.)
4. **Enforces best practices** for their domain
5. **Integrates with other agents** for complex workflows

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
/fullstack-architect → /backend-developer → /frontend-developer →
/security-engineer → /qa-engineer → /devops-engineer
```

## 📁 Directory Structure

```
.claude/
├── agents/               # FTE Agent definitions (this directory)
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
│   └── README.md (this file)
│
└── skills/              # Reusable Intelligence Skills (31 total)
    ├── jwt-authentication/
    ├── password-security/
    ├── database-schema-expander/
    └── ... (28 more)
```

## 🧠 Reusable Intelligence

All agents leverage **Reusable Intelligence Skills** from `.claude/skills/`:

**Total Skills Available**: 31 skills
**Categories**:
- Workflow & Planning (5 skills)
- Core Implementation (5 skills)
- Foundation Patterns (6 skills)
- Role-Based Development (7 skills)
- Quality & Testing (3 skills)
- Production & Deployment (5 skills)

See `.claude/skills/` directory for complete skill library.

## 🎓 Learning & Evolution

This Digital Agent Factory:
- ✅ **Evolves**: New skills can be added to any agent
- ✅ **Learns**: Skills improve based on usage
- ✅ **Scales**: New agents can be created as needed
- ✅ **Integrates**: Agents work together seamlessly
- ✅ **Enforces**: Constitution principles automatically

## 🏆 Best Practices

1. **Choose the right agent** for the task
2. **Use agent pipelines** for complex workflows
3. **Let agents use their skills** - don't implement manually
4. **Follow agent recommendations** - they enforce best practices
5. **Document agent usage** in PHRs (Prompt History Records)

---

**Digital Agent Factory** - Powered by Reusable Intelligence 🚀
