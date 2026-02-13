# Skills Usage Scenarios & Mappings

## Skills Discovery Protocol (MANDATORY)

**Before implementing ANYTHING:**

### Step 1: Check Skills Directory
```bash
ls .claude/skills/
# Returns 31 skill files
```

### Step 2: Analyze User Request
Identify keywords:
- "chatbot" → ai-agent-setup, chatbot-endpoint, conversation-manager
- "auth" → jwt-authentication, password-security, user-isolation
- "test" → edge-case-tester, qa-engineer, ab-testing
- "deploy" → deployment-automation, production-checklist, vercel-deployer
- "git/GitHub" → github-specialist
- "performance" → performance-logger, connection-pooling
- "API" → backend-developer, api-docs-generator
- "UI" → frontend-developer, uiux-designer

### Step 3: Display Skill Plan
```text
🔧 Skills Analysis for: "[user request]"

Applicable Skills Found:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. /sp.skill-name → Purpose
2. /sp.skill-name → Purpose
...

Skills Execution Plan:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. /sp.skill-name → Task description
2. /sp.skill-name → Task description
...

Approve? (yes/no) ✋
```

### Step 4: Wait for Approval
User responds: "yes", "approved", "1" → Proceed

### Step 5: Execute Skills Sequentially
```text
🔧 Using Skill: /sp.skill-name
Purpose: [Clear purpose]
Tasks: [Task IDs if applicable]
Files Generated: [List of files]
✅ Skill Complete
```

### Step 6: Document in PHR
Add to PHR:
```yaml
skills_used:
  - name: /sp.skill-name
    purpose: [Purpose]
    files: [Files modified/created]
```

---

## Common Scenarios → Skills Mapping

### Scenario 1: "Create AI chatbot"
```
/sp.database-schema-expander → Tables
/sp.mcp-tool-builder (5x) → MCP tools
/sp.ai-agent-setup → Agent config
/sp.chatbot-endpoint → API
/sp.conversation-manager → State
/sp.edge-case-tester → Tests (auto)
```

### Scenario 2: "Add authentication"
```
/sp.database-schema-expander → Users table
/sp.jwt-authentication → JWT setup
/sp.password-security → Auth endpoints
/sp.user-isolation → Protect data
/sp.security-engineer → Audit
```

### Scenario 3: "Prepare for production"
```
/sp.security-engineer → Security audit
/sp.performance-logger → Monitoring
/sp.structured-logging → Logging
/sp.api-docs-generator → Documentation
/sp.deployment-automation → Deploy scripts
/sp.qa-engineer → Smoke tests
/sp.production-checklist → Validation
```

### Scenario 4: "Merge branches to main"
```
/sp.github-specialist → Branch operations
  - Checkout main
  - Merge feature branch
  - Push to remote
  - Delete feature branch
```

### Scenario 5: "Optimize performance"
```
/sp.connection-pooling → Pool config
/sp.performance-logger → Execution logging
/sp.database-engineer → Query optimization
/sp.ab-testing → Load testing
```

---

## Skill Usage Rules (MUST FOLLOW)

### ✅ ALWAYS Use Skills When:
- Creating new features
- Modifying existing code
- Adding authentication/security
- Database operations
- Testing and QA
- Performance optimization
- Production deployment
- **Git/GitHub operations** (merge, push, branch, PR, issue)
- Documentation generation

### ❌ NEVER Do Manually When Skill Exists:
- Manual git commands → Use `/sp.github-specialist`
- Manual file creation → Use appropriate skill
- Manual testing → Use `/sp.edge-case-tester` or `/sp.qa-engineer`
- Manual deployment → Use `/sp.deployment-automation`

### 🚨 Violations Result In:
- IMMEDIATE STOP
- Document violation
- Redo using proper skill-based approach
- Update constitution if needed

---

## Skill Usage Contract

### Automatic Skill Selection

Based on user prompts, automatically select and use relevant skills:

**Examples:**
1. **User**: "Create a new feature for user notifications"
   - **Auto-use**: `/sp.new-feature` (creates spec.md, plan.md, tasks.md automatically)

2. **User**: "Add task management chatbot"
   - **Auto-use**: `/sp.database-schema-expander`, `/sp.mcp-tool-builder`, `/sp.ai-agent-setup`, `/sp.chatbot-endpoint`, `/sp.conversation-manager`

3. **User**: "Implement add task functionality"
   - **Auto-use**: `/sp.mcp-tool-builder`

4. **User**: "Add due dates to existing tasks"
   - **Auto-use**: `/sp.change-management`

5. **After** `/sp.implementation` **completes**:
   - **Auto-use**: `/sp.edge-case-tester`

### Terminal Output Format

When using skills, display:
```text
🔧 Using Skill: /sp.mcp-tool-builder

Purpose: Build MCP tool for add_task operation
Constitution Check: ✓ Passed
Files Generated:
  - backend/src/mcp_tools/add_task_tool.py
  - tests/test_add_task_tool.py
  - specs/tasks/contracts/mcp-tools/add_task.md

✅ Skill Complete
```

### Skill Chaining

Skills can chain automatically:
```text
Feature: AI Chatbot
│
├─> /sp.database-schema-expander
│   ✅ Conversation & Message tables created
│
├─> /sp.mcp-tool-builder (5x for each tool)
│   ✅ add_task, list_tasks, complete_task, delete_task, update_task
│
├─> /sp.ai-agent-setup
│   ✅ OpenAI Agents SDK configured
│
├─> /sp.chatbot-endpoint
│   ✅ Stateless chat endpoint at /api/{user_id}/chat
│
└─> /sp.edge-case-tester (automatic after implementation)
    ✅ 57/57 edge cases passed
```

## Skill Integration Points

### When to Use Each Skill

| User Request Pattern | Skills to Use | Order |
|---------------------|---------------|-------|
| "Create chatbot" | database-schema-expander → mcp-tool-builder → ai-agent-setup → chatbot-endpoint → conversation-manager → edge-case-tester | Sequential |
| "Add [MCP tool]" | mcp-tool-builder → edge-case-tester | Sequential |
| "Change [existing feature]" | change-management | Standalone |
| "Test [feature]" | edge-case-tester, ab-testing | Parallel |
| "Create skill for [X]" | skill-creator | Standalone |

### Constitution Enforcement

All skills enforce constitution principles:
- Stateless architecture
- User isolation
- MCP-first design
- Test-driven development
- Database-centric state

Skill output includes constitution compliance verification.

## Skill Learning

**You MUST:**
1. Recognize patterns in user requests
2. Select appropriate skills automatically
3. Display skill usage in terminal
4. Chain skills when needed
5. Use edge-case-tester after implementation
6. Suggest ab-testing for new features

**Remember:**
- Skills are reusable intelligence
- They enforce best practices automatically
- They work across projects
- They self-improve via skill-creator
- They ensure constitution compliance

When in doubt about which skill to use, refer to constitution.md "Reusable Intelligence Skills" section.
