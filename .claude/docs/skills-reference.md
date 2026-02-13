# Complete Skills Reference (ALL 32 Skills)

**CRITICAL**: Before implementing ANYTHING, you MUST check `.claude/skills/` directory for applicable skills.

**Location**: All skills are in `.claude/skills/` directory (32 total)
**Constitution Reference**: See `.specify/memory/constitution.md` Section "Phase III+ Requirements: Reusable Intelligence Skills"

---

## 🤖 Automation & Orchestration (1 skill) - NEW!

**When user says**: ANY request (auto-triggers on every prompt)

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.prompt-analyzer` | `.claude/skills/prompt-analyzer/SKILL.md` | **AUTO-TRIGGER on EVERY user request** - Analyzes prompts, detects intent, maps to skills, assigns agents |

**Auto-Use**: **ALWAYS** - This skill automatically runs before ANY implementation to determine which skills and agents to use.

**Purpose**: Eliminates manual skill selection by intelligently analyzing user prompts and creating execution plans.

**See:** `.claude/skills/prompt-analyzer/EXAMPLES.md` for test cases and examples

---

## 1️⃣ Workflow & Planning Skills (5 skills)

**When user says**: "Create new feature", "Plan implementation", "Break down tasks"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.specify` | `.claude/skills/skill-creator.md` | Creating feature specifications |
| `/sp.plan` | `.claude/skills/skill-creator.md` | Generating implementation plans |
| `/sp.tasks` | `.claude/skills/skill-creator.md` | Breaking down into actionable tasks |
| `/sp.implement` | `.claude/skills/skill-creator.md` | Executing implementation |
| `/sp.new-feature` | `.claude/skills/new-feature.md` | Complete spec→plan→tasks in one workflow |

**Auto-Use**: When user requests "new feature from scratch"

---

## 2️⃣ Core Implementation Skills - Phase III (5 skills)

**When user says**: "Create chatbot", "Add MCP tool", "Add chat endpoint"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.mcp-tool-builder` | `.claude/skills/mcp-tool-builder.md` | Creating MCP tools (add_task, list_tasks, etc.) |
| `/sp.ai-agent-setup` | `.claude/skills/ai-agent-setup.md` | Configuring OpenAI Agents SDK |
| `/sp.chatbot-endpoint` | `.claude/skills/chatbot-endpoint.md` | Creating stateless chat API endpoints |
| `/sp.conversation-manager` | `.claude/skills/conversation-manager.md` | Managing conversation state in database |
| `/sp.database-schema-expander` | `.claude/skills/database-schema-expander.md` | Adding new database tables |

**Auto-Use**: When user mentions "chatbot", "AI agent", "MCP tools", "conversation"

---

## 3️⃣ Foundation Skills - Phase II Patterns (6 skills)

**When user says**: "Add authentication", "Secure user data", "Add validation"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.jwt-authentication` | `.claude/skills/jwt-authentication.md` | JWT creation/verification, protected endpoints |
| `/sp.user-isolation` | `.claude/skills/user-isolation.md` | Protecting user-owned resources, preventing data leakage |
| `/sp.password-security` | `.claude/skills/password-security.md` | bcrypt hashing, signup/login endpoints |
| `/sp.pydantic-validation` | `.claude/skills/pydantic-validation.md` | Request/response DTOs, input validation |
| `/sp.connection-pooling` | `.claude/skills/connection-pooling.md` | Database pool configuration, health monitoring |
| `/sp.transaction-management` | `.claude/skills/transaction-management.md` | Try/commit/rollback patterns, atomicity |

**Auto-Use**: When user mentions "auth", "security", "database", "validation"

---

## 4️⃣ Role-Based Development Skills (7 skills)

**When user says**: "Implement backend", "Create UI", "Design system", "Deploy"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.backend-developer` | `.claude/skills/backend-developer.md` | Backend API implementation (FastAPI, SQLModel) |
| `/sp.frontend-developer` | `.claude/skills/frontend-developer.md` | Frontend UI implementation (Next.js, React) |
| `/sp.fullstack-architect` | `.claude/skills/fullstack-architect.md` | System design & end-to-end architecture |
| `/sp.database-engineer` | `.claude/skills/database-engineer.md` | Database optimization, schema design, indexes |
| `/sp.devops-engineer` | `.claude/skills/devops-engineer.md` | Infrastructure, Docker, CI/CD |
| `/sp.security-engineer` | `.claude/skills/security-engineer.md` | OWASP audit, vulnerability scanning, security tests |
| `/sp.uiux-designer` | `.claude/skills/uiux-designer.md` | Wireframes, user flows, component design |

**Auto-Use**: Based on complexity - use appropriate role-based skill for implementation

---

## 5️⃣ Quality & Testing Skills (3 skills)

**When user says**: "Test this feature", "Run A/B test", "Comprehensive testing"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.edge-case-tester` | `.claude/skills/edge-case-tester.md` | 57+ edge case scenarios (AUTO after /sp.implement) |
| `/sp.ab-testing` | `.claude/skills/ab-testing.md` | A/B test framework, variant configs, analytics |
| `/sp.qa-engineer` | `.claude/skills/qa-engineer.md` | Unit tests, integration tests, smoke tests, E2E |

**Auto-Trigger**: `/sp.edge-case-tester` MUST run automatically after ANY implementation

---

## 6️⃣ Production & Deployment Skills (5 skills)

**When user says**: "Add logging", "Optimize performance", "Deploy", "Production ready"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.performance-logger` | `.claude/skills/performance-logger.md` | Execution time logging, structured metrics |
| `/sp.structured-logging` | `.claude/skills/structured-logging.md` | JSON logging, log aggregation compatibility |
| `/sp.deployment-automation` | `.claude/skills/deployment-automation.md` | Deploy scripts, validation, health checks |
| `/sp.production-checklist` | `.claude/skills/production-checklist.md` | Production readiness validation, checklists |
| `/sp.vercel-deployer` | `.claude/skills/vercel-deployer.md` | Vercel deployment, environment config |

**Auto-Use**: When user mentions "production", "deploy", "performance", "logging"

---

## 7️⃣ Specialized Utility Skills (5 skills)

**When user says**: "Document API", "Modify feature", "Create skill", "GitHub operations"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.api-docs-generator` | `.claude/skills/api-docs-generator.md` | OpenAPI/Swagger docs, deployment guides |
| `/sp.change-management` | `.claude/skills/change-management.md` | Modify existing features safely |
| `/sp.skill-creator` | `.claude/skills/skill-creator.md` | Create new reusable skills |
| `/sp.github-specialist` | `.claude/skills/github-specialist.md` | **GitHub operations, branch management, PRs, issues** |
| `/sp.conversation-manager` | `.claude/skills/conversation-manager.md` | Conversation/Message models, chat state |

**IMPORTANT**: Use `/sp.github-specialist` for ALL git/GitHub operations:
- Branch merging/deletion
- Push to remote
- PR creation
- Issue management
- Release creation

**Auto-Use**: When user mentions "git", "GitHub", "merge", "branch", "PR", "issue"

---

## 8️⃣ 🆕 Modern Architecture Skills (10 skills) - NEW!

**When user says**: "Add caching", "Optimize performance", "Real-time chat", "Deploy to Kubernetes"

| Skill | File | When to Use |
|-------|------|-------------|
| `/sp.caching-strategy` | `.claude/skills/caching-strategy/SKILL.md` | Redis/Memcached caching, performance optimization |
| `/sp.api-contract-design` | `.claude/skills/api-contract-design/SKILL.md` | OpenAPI specifications, contract-first API development |
| `/sp.message-queue-integration` | `.claude/skills/message-queue-integration/SKILL.md` | RabbitMQ/Kafka, async processing, event-driven architecture |
| `/sp.observability-apm` | `.claude/skills/observability-apm/SKILL.md` | OpenTelemetry, distributed tracing, production monitoring |
| `/sp.microservices-patterns` | `.claude/skills/microservices-patterns/SKILL.md` | Circuit breaker, saga, service mesh patterns |
| `/sp.infrastructure-as-code` | `.claude/skills/infrastructure-as-code/SKILL.md` | Terraform, CloudFormation, IaC automation |
| `/sp.feature-flags-management` | `.claude/skills/feature-flags-management/SKILL.md` | Feature toggles, A/B testing, gradual rollouts |
| `/sp.websocket-realtime` | `.claude/skills/websocket-realtime/SKILL.md` | WebSocket, real-time communication, live updates |
| `/sp.graphql-api` | `.claude/skills/graphql-api/SKILL.md` | GraphQL schema, queries, mutations, subscriptions |
| `/sp.container-orchestration` | `.claude/skills/container-orchestration/SKILL.md` | Kubernetes deployment, Helm charts, auto-scaling |

**Auto-Use**: When user mentions "caching", "Redis", "real-time", "WebSocket", "Kubernetes", "microservices", "message queue", "GraphQL", "monitoring", "IaC"

**Enterprise Capabilities:**
- ✅ 10x performance with caching
- ✅ Real-time features (chat, dashboards)
- ✅ Cloud-native deployment (Kubernetes)
- ✅ Microservices architecture
- ✅ Production observability (APM)
- ✅ Event-driven systems (message queues)
- ✅ Flexible APIs (GraphQL)
- ✅ Modern deployment (feature flags)
- ✅ Infrastructure as Code

---

## Quick Reference: User Request → Skills

| User Says | Use These Skills |
|-----------|-----------------|
| "Create chatbot" | ai-agent-setup, chatbot-endpoint, conversation-manager |
| "Add authentication" | jwt-authentication, password-security, user-isolation |
| "Test feature" | edge-case-tester, qa-engineer |
| "Deploy to production" | deployment-automation, production-checklist |
| "Merge branches" | **github-specialist** |
| "Create PR" | **github-specialist** |
| "Optimize performance" | performance-logger, connection-pooling |
| "Add API endpoint" | backend-developer, pydantic-validation |
| "Create UI" | frontend-developer, uiux-designer |
| "Security audit" | security-engineer |
| "Add logging" | structured-logging, performance-logger |

---

**REMEMBER**: Check `.claude/skills/` directory FIRST, display skill plan, wait for approval, then execute using Skill tool. NO manual implementation when skills exist!
