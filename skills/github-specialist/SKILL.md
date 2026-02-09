---
name: github-specialist
description: Full-time equivalent GitHub Specialist agent with expertise in Git workflows, GitHub Actions, code review, and repository management (Digital Agent Factory)
---
about: Report a bug
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. See error

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: [e.g. macOS]
- Browser: [e.g. Chrome 120]
- Version: [e.g. 1.0.0]

## Screenshots
If applicable

## Additional Context
Any other relevant information
```

### 8. GitHub Secrets Management

```bash
# Add secrets via GitHub CLI
gh secret set OPENAI_API_KEY --body "sk-..."
gh secret set DATABASE_URL --body "postgresql://..."
gh secret set VERCEL_TOKEN --body "..."

# List secrets
gh secret list

# Delete secret
gh secret delete SECRET_NAME
```

### 9. Release Management

**Creating a Release:**
```bash
# Tag version
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create release via GitHub CLI
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes "
## Features
- Natural language task creation
- Conversation history
- User authentication

## Bug Fixes
- Fixed auth token expiration
- Improved error messages

## Breaking Changes
- API endpoint paths changed
"
```

### 10. GitHub Projects (Kanban)

**Board Columns:**
```
Backlog → To Do → In Progress → In Review → Done
```

**Automation:**
- Issue created → Backlog
- Issue assigned → To Do
- PR opened → In Review
- PR merged → Done

## Deliverables

- [ ] Repository initialized with proper structure
- [ ] Branch protection rules configured
- [ ] PR/Issue templates created
- [ ] GitHub Actions CI/CD setup
- [ ] Code review guidelines documented
- [ ] Commit convention established
- [ ] GitHub Secrets configured
- [ ] Release process documented

## References

- GitHub Docs: https://docs.github.com/
- Conventional Commits: https://www.conventionalcommits.org/
- GitHub Actions: https://docs.github.com/actions
- Git Flow: https://nvie.com/posts/a-successful-git-branching-model/
