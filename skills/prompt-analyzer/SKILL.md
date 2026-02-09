---
name: prompt-analyzer
description: Intelligent prompt analysis skill that automatically detects which skills and agents should be used for any given user request. Analyzes intent, extracts keywords, maps to skills, and creates execution plans.
---

# Prompt Analyzer Skill

## Purpose
Automatically analyze user prompts and intelligently determine which skills/agents should be invoked, eliminating manual skill selection.

## When to Use
- **Auto-trigger:** BEFORE any implementation work begins
- **Manual trigger:** User asks "what skills should I use?" or "analyze this prompt"
- **Continuous:** Should run in background for every user request

## What It Does

### 1. Intent Detection
Analyzes user prompt to determine primary intent:
- **Create:** New feature/component/system
- **Modify:** Change existing functionality
- **Test:** Quality assurance/testing
- **Deploy:** Production deployment
- **Debug:** Fix bugs/issues
- **Optimize:** Performance improvements
- **Document:** Create documentation
- **Analyze:** Code review/exploration

### 2. Keyword Extraction
Identifies key technical terms:
- "chatbot", "AI", "agent" → AI/MCP related
- "auth", "login", "JWT", "password" → Authentication
- "database", "table", "migration" → Database
- "test", "edge case", "QA" → Testing
- "deploy", "production", "vercel" → Deployment
- "git", "merge", "PR", "branch" → Git/GitHub
- "API", "endpoint", "route" → Backend
- "UI", "component", "page" → Frontend

### 3. Skills Mapping
Maps detected intent + keywords to skills:

**Backend Skills:**
- `/sp.backend-developer` - API implementation
- `/sp.database-schema-expander` - New tables
- `/sp.mcp-tool-builder` - MCP tools
- `/sp.pydantic-validation` - Input validation
- `/sp.transaction-management` - Database operations

**Frontend Skills:**
- `/sp.frontend-developer` - UI implementation
- `/sp.uiux-designer` - Design work
- `/sp.vercel-deployer` - Deployment

**Security Skills:**
- `/sp.jwt-authentication` - JWT setup
- `/sp.password-security` - Password hashing
- `/sp.user-isolation` - User data protection
- `/sp.security-engineer` - Security audit

**Testing Skills:**
- `/sp.edge-case-tester` - Comprehensive testing
- `/sp.qa-engineer` - Test suite
- `/sp.ab-testing` - A/B testing

**Infrastructure Skills:**
- `/sp.connection-pooling` - Database pooling
- `/sp.performance-logger` - Performance monitoring
- `/sp.structured-logging` - Logging setup
- `/sp.devops-engineer` - Infrastructure

**Workflow Skills:**
- `/sp.new-feature` - Complete feature workflow
- `/sp.change-management` - Modify existing features
- `/sp.skill-creator` - Create new skills
- `/sp.github-specialist` - Git operations

### 4. Agent Selection
Determines which agent(s) should handle the work:
- **backend-developer** - Backend implementation
- **frontend-developer** - Frontend implementation
- **fullstack-architect** - System design
- **database-engineer** - Database optimization
- **security-engineer** - Security work
- **qa-engineer** - Testing
- **devops-engineer** - Infrastructure
- **github-specialist** - Git/GitHub ops
- **uiux-designer** - UI/UX design
- **vercel-deployer** - Vercel deployment

### 5. Execution Plan Generation
Creates a detailed execution plan:
```
🔧 Prompt Analysis: "[user prompt]"

Intent Detected: [intent]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Keywords Found:
  - keyword1 (category)
  - keyword2 (category)
  - keyword3 (category)

Skills Required:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. /sp.skill-name → Purpose
2. /sp.skill-name → Purpose
3. /sp.skill-name → Purpose

Agents Required:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. agent-name → Responsibility

Execution Plan:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: /sp.skill-name → Action
Step 2: /sp.skill-name → Action
Step 3: /sp.skill-name → Action

Estimated Complexity: [Low/Medium/High]
Requires User Approval: [Yes/No]
```

## Analysis Algorithm

### Step 1: Intent Classification
```python
def detect_intent(prompt: str) -> str:
    keywords_map = {
        "create": ["create", "add", "new", "build", "implement", "generate"],
        "modify": ["update", "change", "modify", "refactor", "improve"],
        "test": ["test", "check", "verify", "validate", "QA"],
        "deploy": ["deploy", "production", "release", "launch"],
        "debug": ["fix", "debug", "resolve", "error", "bug"],
        "optimize": ["optimize", "performance", "speed", "improve"],
        "document": ["document", "docs", "readme", "guide"],
        "analyze": ["analyze", "review", "explore", "understand"]
    }
    # Match keywords to intent
    return detected_intent
```

### Step 2: Keyword Extraction
```python
def extract_keywords(prompt: str) -> List[Tuple[str, str]]:
    technical_keywords = {
        "ai": ["chatbot", "AI", "agent", "MCP", "OpenAI"],
        "auth": ["auth", "login", "JWT", "password", "signup"],
        "database": ["database", "table", "migration", "schema"],
        "test": ["test", "edge case", "QA", "E2E", "unit"],
        "deploy": ["deploy", "production", "vercel", "docker"],
        "git": ["git", "GitHub", "merge", "PR", "branch"],
        "backend": ["API", "endpoint", "route", "FastAPI"],
        "frontend": ["UI", "component", "page", "Next.js"]
    }
    # Extract and categorize keywords
    return keywords_with_categories
```

### Step 3: Skills Mapping
```python
def map_to_skills(intent: str, keywords: List[Tuple[str, str]]) -> List[str]:
    skills_map = {
        ("create", "ai"): ["database-schema-expander", "mcp-tool-builder", "ai-agent-setup"],
        ("create", "auth"): ["jwt-authentication", "password-security", "user-isolation"],
        ("test", "*"): ["edge-case-tester", "qa-engineer"],
        ("deploy", "*"): ["deployment-automation", "production-checklist"],
        ("create", "backend"): ["backend-developer", "pydantic-validation"],
        ("create", "frontend"): ["frontend-developer", "uiux-designer"],
        # ... more mappings
    }
    return matched_skills
```

### Step 4: Agent Selection
```python
def select_agents(skills: List[str], intent: str) -> List[str]:
    agent_map = {
        "backend-skills": ["backend-developer", "database-engineer"],
        "frontend-skills": ["frontend-developer", "uiux-designer"],
        "security-skills": ["security-engineer"],
        "test-skills": ["qa-engineer"],
        "infra-skills": ["devops-engineer"],
        "git-skills": ["github-specialist"]
    }
    return required_agents
```

## Example Analyses

### Example 1: "Create AI chatbot"
```
Intent: create
Keywords: AI (ai), chatbot (ai)

Skills:
1. /sp.database-schema-expander → Create conversation/message tables
2. /sp.mcp-tool-builder → Build MCP tools (5x)
3. /sp.ai-agent-setup → Configure OpenAI SDK
4. /sp.chatbot-endpoint → Create chat API
5. /sp.conversation-manager → Manage chat state
6. /sp.edge-case-tester → Comprehensive testing

Agents:
1. backend-developer → Implementation
2. database-engineer → Schema design

Complexity: High
```

### Example 2: "Add authentication"
```
Intent: create
Keywords: authentication (auth)

Skills:
1. /sp.database-schema-expander → Users table
2. /sp.jwt-authentication → JWT setup
3. /sp.password-security → Secure auth endpoints
4. /sp.user-isolation → Protect user data
5. /sp.security-engineer → Security audit

Agents:
1. backend-developer → Implementation
2. security-engineer → Audit

Complexity: Medium
```

### Example 3: "Merge feature branch to main"
```
Intent: modify
Keywords: merge (git), branch (git), main (git)

Skills:
1. /sp.github-specialist → Git operations

Agents:
1. github-specialist → Branch management

Complexity: Low
```

### Example 4: "Optimize database queries"
```
Intent: optimize
Keywords: database (database), queries (database)

Skills:
1. /sp.connection-pooling → Verify pool config
2. /sp.performance-logger → Add monitoring
3. /sp.database-engineer → Query optimization
4. /sp.ab-testing → Load testing

Agents:
1. database-engineer → Optimization
2. devops-engineer → Monitoring

Complexity: Medium
```

## Output Format

Always output analysis in this format:

```
🔧 Prompt Analysis Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 User Request: "[original prompt]"

🎯 Intent: [intent]

🔑 Keywords: keyword1, keyword2, keyword3

🧠 Skills Required (X total):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. /sp.skill-name → Purpose/Task
2. /sp.skill-name → Purpose/Task

🤖 Agents Required (X total):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. agent-name → Responsibility

📋 Execution Plan:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1: [Action with skill/agent]
Step 2: [Action with skill/agent]
Step 3: [Action with skill/agent]

⚡ Complexity: [Low/Medium/High]
✋ Waiting for approval to proceed...
```

## Constitution Compliance

This skill enforces:
- ✅ Skill-first approach (automatic skill detection)
- ✅ No manual implementation when skills exist
- ✅ Proper skill chaining
- ✅ Agent specialization
- ✅ User approval before execution

## Integration

This skill should be:
1. **Auto-invoked** before any implementation work
2. **First step** in any workflow
3. **Consulted** by orchestrator agent
4. **Updated** when new skills are added

## Success Criteria

- ✅ Correctly identifies intent 95%+ of the time
- ✅ Maps to appropriate skills
- ✅ Suggests correct agents
- ✅ Generates clear execution plan
- ✅ Reduces manual skill selection to zero
- ✅ Improves workflow efficiency

## Maintenance

When adding new skills:
1. Update keyword extraction map
2. Update skills mapping
3. Update agent selection logic
4. Test with sample prompts

---

**Status:** Active
**Priority:** 🔴 Critical (Core workflow automation)
**Version:** 1.0.0
**Last Updated:** 2026-01-06
