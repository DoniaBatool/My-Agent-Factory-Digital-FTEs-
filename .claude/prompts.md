# Common Prompts & Templates

This file contains ready-to-use prompts for working with the Digital Agent Factory.

---

## Starting a New Feature

```
I want to build [feature description].

Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Please use the orchestrator to:
1. Analyze this request
2. Create spec-kit files (constitution, specify, plan, tasks)
3. Assign appropriate agents and skills
4. Propose an execution plan for approval
```

---

## Requesting Spec Creation

```
Create spec-kit files for [feature/project name]:

Context: [describe the project/feature]

Please create:
- speckit.constitution (WHY - principles, constraints)
- speckit.specify (WHAT - requirements, journeys, criteria)
- speckit.plan (HOW - architecture, components, APIs)
- speckit.tasks (BREAKDOWN - atomic work units)

Use the `new-feature` skill to scaffold these files.
```

---

## Using a Specific Agent

```
Use the [agent-name] agent to:
[describe task]

Relevant context:
- [context 1]
- [context 2]

Expected output:
- [expected output 1]
- [expected output 2]
```

---

## Using a Specific Skill

```
Apply the [skill-name] skill to:
[describe what you want the skill to do]

Input:
- [input 1]
- [input 2]

Requirements:
- [requirement 1]
- [requirement 2]
```

---

## Requesting Architecture Review

```
Review the architecture for [component/feature]:

Current Plan: [reference to speckit.plan section]

Questions:
1. [question 1]
2. [question 2]

Please use the fullstack-architect agent to:
- Validate the approach
- Identify potential issues
- Suggest improvements
- Update speckit.plan if needed
```

---

## Requesting Security Review

```
Security review needed for [feature/component]:

Implementation: [describe or reference files]

Please use the security-engineer agent to:
- Check for OWASP vulnerabilities
- Review authentication/authorization
- Validate input sanitization
- Apply edge-case-tester skill
- Update security requirements in speckit.specify if needed
```

---

## Requesting Testing

```
Test [feature/component]:

Task ID: [T-XXX]
Implementation: [file references]

Please use the qa-engineer agent to:
1. Review test coverage
2. Apply edge-case-tester skill
3. Run production-checklist
4. Report any gaps
```

---

## Requesting Deployment

```
Deploy [project/feature] to [platform]:

Platform: [Vercel/AWS/Azure/GCP/Homelab]
Environment: [production/staging/preview]

Please use the appropriate deployment agent:
- vercel-deployer for Vercel
- devops-engineer for AWS/Azure/GCP
- cloud-architect for Kubernetes

Steps:
1. Run production-checklist
2. Prepare deployment configuration
3. Execute deployment
4. Validate post-deployment
```

---

## Creating a New Agent

```
Create a new agent: [agent-name]

Role: [describe the agent's role]
Responsibilities: [list key responsibilities]
Primary Skills: [list relevant skills]

Please:
1. Read existing agent files for template
2. Create agents/[agent-name].md
3. Follow agent structure:
   - Role definition
   - Responsibilities
   - Primary skills
   - Workflow
   - Examples
4. Update README.md agent list
```

---

## Creating a New Skill

```
Create a new skill: [skill-name]

Purpose: [what problem does this skill solve]
Category: [Workflow/Security/Quality/Infrastructure/API/etc]

Please use the skill-creator skill to:
1. Create skills/[skill-name]/ directory
2. Generate SKILL.md with:
   - Purpose
   - When to use
   - Instructions
   - Best practices
   - Examples
3. Add any necessary scripts/templates
4. Update README.md skills list
```

---

## Updating Spec-Kit

```
Update spec-kit files:

File to update: [constitution/specify/plan/tasks]
Section: [section identifier]
Change: [describe the change]

Reason: [why this update is needed]
Impact: [what else might be affected]

Please:
1. Read current spec-kit file
2. Make the update
3. Check for conflicts with other spec files
4. Update dependent sections if needed
```

---

## Learning from a Fix

```
Capture this fix as learning:

Problem: [describe the issue]
Solution: [describe the fix]
Root Cause: [explain why it happened]

Context:
- Task: [T-XXX]
- Files: [affected files]
- Skill used: [if any]

Please use the live-skill-learner agent to:
1. Analyze the fix
2. Determine if it's a pattern worth capturing
3. Update relevant skill if applicable
4. Document the learning
```

---

## Orchestrator Full Workflow

```
Orchestrate: [high-level goal]

Description: [detailed description]

Requirements:
- [requirement 1]
- [requirement 2]
- [requirement 3]

Constraints:
- [constraint 1]
- [constraint 2]

Please:
1. Analyze intent using prompt-analyzer skill
2. Check if spec-kit exists
3. Create/update spec-kit as needed
4. Map to relevant skills
5. Assign specialist agents
6. Create execution plan (sequential/parallel)
7. Present plan for approval
8. Execute after approval
9. Validate with qa-engineer
10. Use live-skill-learner to capture learnings
```

---

## Emergency: Spec Recovery

```
⚠️ Spec-kit is missing or incomplete for [feature/project]

Current state:
- Constitution: [exists/missing]
- Specify: [exists/missing]
- Plan: [exists/missing]
- Tasks: [exists/missing]

Code exists in: [file paths]

Please:
1. Analyze existing code
2. Reverse-engineer spec-kit files from implementation
3. Create missing spec-kit files
4. Validate consistency
5. Document assumptions made
```

---

## Code Review with Spec Validation

```
Review code in [file/directory]:

Files: [list files]

Please validate:
1. Every code block references a Task ID
2. Task IDs exist in speckit.tasks
3. Implementation matches speckit.plan
4. Requirements from speckit.specify are met
5. No freestyle code or undocumented features
6. Tests exist and pass

Report any violations and suggest fixes.
```

---

## Template Variables Reference

Common variables you can use in prompts:

- `[feature-name]` - Name of the feature
- `[agent-name]` - Name of the agent (backend-developer, qa-engineer, etc.)
- `[skill-name]` - Name of the skill (jwt-authentication, edge-case-tester, etc.)
- `[T-XXX]` - Task ID from speckit.tasks
- `[platform]` - Deployment platform (Vercel, AWS, Azure, GCP, Homelab)
- `[file-path]` - Path to file(s)
- `§X.Y` - Section reference in spec-kit files

---

**Tip:** Copy these prompts and customize them for your specific needs. The more specific you are, the better the agents can help you.
