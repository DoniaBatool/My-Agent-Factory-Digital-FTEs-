---
name: context7-docs
description: On-demand access to official library documentation via Context7 MCP server
---

# Context7 Documentation Lookup Skill

## Overview

This skill provides on-demand access to library documentation via the Context7 MCP server. Use this when you need to look up documentation for any library, framework, or tool.

## When to Use

Use `/sp.context7-docs` when you need:

- Library documentation (FastAPI, Next.js, SQLModel, etc.)
- Framework guides and examples
- API references for any package
- Code examples from official docs
- Best practices from documentation

## MCP Configuration

This skill uses the Context7 MCP server:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp", "--api-key", "YOUR_API_KEY"]
    }
  }
}
```

**Note:** API key is stored in `.claude/.mcp.json` (gitignored)

## Usage

### Direct Invocation

```bash
# Look up FastAPI documentation
/sp.context7-docs fastapi routing

# Look up Next.js App Router
/sp.context7-docs nextjs app-router

# Look up Kubernetes Helm charts
/sp.context7-docs helm charts templates
```

### Via Python Script

```bash
cd .claude/skills/context7-docs/scripts
python tool.py --library fastapi --query "dependency injection"
```

## Available Commands

| Command | Description |
|---------|-------------|
| `resolve <library>` | Get library ID for documentation lookup |
| `search <library> <query>` | Search documentation for specific topic |
| `examples <library>` | Get code examples from docs |

## Examples

### Example 1: FastAPI Dependency Injection

```text
User: How do I use dependency injection in FastAPI?

Claude:
╔══════════════════════════════════════════════════════════════╗
║  🔧 USING SKILL: /sp.context7-docs                           ║
╠══════════════════════════════════════════════════════════════╣
║  Purpose: Look up FastAPI dependency injection docs          ║
║  Library: fastapi                                            ║
║  Query: dependency injection                                 ║
╚══════════════════════════════════════════════════════════════╝

[Documentation retrieved from Context7...]

┌──────────────────────────────────────────────────────────────┐
│  ✅ SKILL COMPLETE: /sp.context7-docs                        │
├──────────────────────────────────────────────────────────────┤
│  Source: FastAPI Official Documentation                      │
│  Topic: Dependencies - First Steps                           │
└──────────────────────────────────────────────────────────────┘
```

### Example 2: Kubernetes Helm Templates

```text
User: How do I create Helm chart templates?

Claude:
╔══════════════════════════════════════════════════════════════╗
║  🔧 USING SKILL: /sp.context7-docs                           ║
╠══════════════════════════════════════════════════════════════╣
║  Purpose: Look up Helm chart template documentation          ║
║  Library: helm                                               ║
║  Query: chart templates                                      ║
╚══════════════════════════════════════════════════════════════╝

[Documentation retrieved...]
```

## Supported Libraries

Context7 supports documentation for 1000+ libraries including:

| Category | Libraries |
|----------|-----------|
| **Python** | FastAPI, Django, Flask, SQLAlchemy, Pydantic, pytest |
| **JavaScript** | Next.js, React, Vue, Express, TypeScript |
| **Databases** | PostgreSQL, MongoDB, Redis, SQLite |
| **DevOps** | Docker, Kubernetes, Helm, Terraform |
| **AI/ML** | OpenAI, LangChain, Hugging Face |

## Integration with Other Skills

This skill is automatically invoked by other skills when documentation is needed:

| Skill | Uses Context7 For |
|-------|-------------------|
| `/sp.devops-engineer` | Docker, K8s, Helm docs |
| `/sp.backend-developer` | FastAPI, SQLModel docs |
| `/sp.frontend-developer` | Next.js, React docs |
| `/sp.container-orchestration` | Kubernetes, Helm docs |

## Error Handling

| Error | Solution |
|-------|----------|
| `Library not found` | Try alternative library name (e.g., "nextjs" vs "next.js") |
| `API key invalid` | Check `.claude/.mcp.json` configuration |
| `Connection timeout` | Retry or check network connection |

## Best Practices

1. **Be specific with queries** - "fastapi dependency injection" is better than "fastapi"
2. **Use official library names** - "nextjs" not "next"
3. **Combine with other skills** - Use docs to inform implementation

## Related Skills

- `/sp.devops-engineer` - Uses this for Docker/K8s docs
- `/sp.backend-developer` - Uses this for FastAPI/Python docs
- `/sp.frontend-developer` - Uses this for Next.js/React docs
