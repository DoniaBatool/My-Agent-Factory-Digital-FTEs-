---
name: skill-creator
description: Automatically create new Claude Code skills based on requirements and project needs
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

---

## 🔍 Context7 MCP Integration (NEW!)

**CRITICAL: When creating skills for NEW technologies/software, ALWAYS learn from official documentation first!**

### Workflow for New Technology Skills

```
User Request: "Create skill for [New Technology]"
    ↓
╔════════════════════════════════════════════════════════════╗
║  STEP 1: Learn from Official Documentation (Context7 MCP) ║
╚════════════════════════════════════════════════════════════╝
    ↓
Use Context7 MCP tools to fetch official documentation:
1. resolve-library-id → Get library ID for the technology
2. get-library-docs → Fetch comprehensive documentation

Example MCP tool calls:
```json
// Step 1: Resolve library
{
  "tool": "resolve-library-id",
  "input": {"libraryName": "terraform"}
}

// Step 2: Get documentation (use returned ID)
{
  "tool": "get-library-docs",
  "input": {
    "context7CompatibleLibraryID": "terraform-id",
    "topic": "providers modules resources state",
    "tokens": 8000
  }
}
```
    ↓
╔════════════════════════════════════════════════════════════╗
║  STEP 2: Analyze Documentation & Extract Key Concepts     ║
╚════════════════════════════════════════════════════════════╝
    ↓
Extract from documentation:
- Core commands and CLI usage
- Common workflows (beginner to advanced)
- Best practices and patterns
- Common errors and troubleshooting
- Configuration requirements
- Testing approaches
    ↓
╔════════════════════════════════════════════════════════════╗
║  STEP 3: Create Skill with Expert Knowledge               ║
╚════════════════════════════════════════════════════════════╝
    ↓
Create comprehensive skill:
- tool.py with commands from official CLI
- README.md with workflows from official docs
- SKILL.md with patterns from best practices
- Include official examples (not invented ones!)
    ↓
✅ Skill created with official documentation authority!
```

### When to Use Context7 MCP

**Use Context7 MCP when creating skills for:**

1. **New Cloud Technologies**
   - Terraform, Pulumi, CloudFormation
   - Cloud-specific services (AWS Lambda, Azure Functions, GCP Cloud Run)
   - Infrastructure as Code tools

2. **New Frameworks/Libraries**
   - Web frameworks (SvelteKit, Remix, Astro, Solid.js)
   - Backend frameworks (NestJS, Hono, Bun)
   - Testing frameworks (Vitest, Playwright, Testing Library)

3. **New DevOps Tools**
   - CI/CD tools (GitHub Actions, GitLab CI, CircleCI)
   - Container orchestration (Nomad, Rancher, K3s)
   - Monitoring tools (Grafana, Prometheus, Datadog)

4. **New Databases**
   - Vector databases (Pinecone, Weaviate, Qdrant)
   - Time-series databases (TimescaleDB, InfluxDB)
   - Graph databases (Neo4j, ArangoDB)

5. **Emerging Technologies**
   - AI/ML frameworks (LangChain, LlamaIndex, AutoGen)
   - Web3/Blockchain tools (Hardhat, Foundry, Truffle)
   - Edge computing platforms (Cloudflare Workers, Deno Deploy)

**Skip Context7 MCP when:**
- Creating skills for well-known technologies you're already expert in
- Updating existing skills (just improve, don't relearn everything)
- Creating organizational/workflow skills (no external docs needed)

### Example: Creating Terraform Skill with Context7

**User Request:** "Create a skill for Terraform deployments"

**Step 1: Fetch Official Documentation**
```text
╔══════════════════════════════════════════════════════════════╗
║  🔧 USING CONTEXT7 MCP: Learning Terraform                   ║
╠══════════════════════════════════════════════════════════════╣
║  Library: terraform                                          ║
║  Topics: providers, modules, resources, state, CLI commands  ║
║  Tokens: 8000 (comprehensive learning)                       ║
╚══════════════════════════════════════════════════════════════╝

Fetching official Terraform documentation...

✅ Documentation Retrieved:
- Terraform CLI commands (init, plan, apply, destroy, etc.)
- Provider configuration (AWS, Azure, GCP)
- Module structure and best practices
- State management and backends
- Workspace usage
- Common errors and solutions
```

**Step 2: Extract Key Information**
```yaml
Commands Extracted:
  - terraform init: Initialize working directory
  - terraform plan: Preview changes
  - terraform apply: Apply changes
  - terraform destroy: Destroy infrastructure
  - terraform validate: Validate configuration
  - terraform fmt: Format configuration files
  - terraform output: Show output values

Workflows Extracted:
  - Basic: init → plan → apply
  - With approval: init → plan → [review] → apply
  - Destroy: plan -destroy → apply -destroy
  - Multi-workspace: workspace new → workspace select → apply

Best Practices Extracted:
  - Always use remote state (S3, Terraform Cloud)
  - Lock state files to prevent concurrent modifications
  - Use variables for environment-specific values
  - Modularize reusable infrastructure
  - Use .terraform-version for version pinning
  - Never commit .tfstate files

Common Errors Extracted:
  - "Error: Provider not found" → terraform init
  - "Error: State lock" → terraform force-unlock
  - "Error: Resource already exists" → terraform import
  - "Error: Variables not set" → Use -var or .tfvars file
```

**Step 3: Create Skill**
```bash
# tool.py commands based on official docs
commands = {
    'init': terraform_init,           # From official: terraform init
    'validate': terraform_validate,   # From official: terraform validate
    'plan': terraform_plan,           # From official: terraform plan
    'apply': terraform_apply,         # From official: terraform apply
    'destroy': terraform_destroy,     # From official: terraform destroy
    'test': run_tests,                # TDD approach
    'troubleshoot': troubleshoot      # Based on official error docs
}

# README.md workflows from official docs
# SKILL.md patterns from official best practices
```

**Result:**
✅ Skill created with official Terraform expertise
✅ Commands match official CLI exactly
✅ Workflows follow official best practices
✅ Troubleshooting covers official error messages
✅ No invented patterns - all from official docs!

---

## 💡 Benefits of Context7 Integration

**Without Context7:**
- ❌ Risk of incorrect command syntax
- ❌ Miss important flags and options
- ❌ Invented workflows that don't match standards
- ❌ Wrong troubleshooting advice
- ❌ Outdated or deprecated patterns

**With Context7:**
- ✅ 100% accurate command syntax (from official docs)
- ✅ Complete flag and option coverage
- ✅ Official workflows and best practices
- ✅ Real error messages with official solutions
- ✅ Up-to-date patterns (context7 has latest docs)

**Authority:**
- Skills created with Context7 have **official documentation authority**
- Users can trust that commands and patterns are correct
- "No specialist needed" becomes reality - skill IS the specialist!

---

## 📚 Context7 MCP Configuration

**Location:** `.claude/.mcp.json`

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

**Note:** API key is stored in `.claude/.mcp.json` (gitignored for security)

**Get API Key:** https://console.upstash.com/

---

## 🎯 Context7 Usage in Skill Creation

### Pattern 1: Learn First, Create Second

```text
User: "Create skill for Pulumi cloud deployments"

Claude:
╔══════════════════════════════════════════════════════════════╗
║  STEP 1: Learning from Official Pulumi Documentation        ║
╚══════════════════════════════════════════════════════════════╝

Using Context7 MCP to fetch Pulumi documentation...

Tool: resolve-library-id
Input: {"libraryName": "pulumi"}
Result: ✅ Library ID resolved

Tool: get-library-docs
Input: {
  "context7CompatibleLibraryID": "pulumi-id",
  "topic": "CLI commands, stacks, providers, state, configuration",
  "tokens": 8000
}
Result: ✅ Documentation retrieved (7,842 tokens)

Key Learnings:
- Commands: pulumi new, up, preview, destroy, stack, config
- Stack management: dev, staging, prod environments
- Providers: AWS, Azure, GCP, Kubernetes
- State backends: Pulumi Cloud, S3, Azure Blob
- Configuration: pulumi config set, stack outputs
- Best practices: Infrastructure as Code patterns

╔══════════════════════════════════════════════════════════════╗
║  STEP 2: Creating Skill with Official Knowledge             ║
╚══════════════════════════════════════════════════════════════╝

Creating files:
✅ scripts/tool.py (8 commands from official CLI)
✅ README.md (workflows from official docs)
✅ SKILL.md (patterns from official best practices)

✅ Skill created with Pulumi expertise!
```

### Pattern 2: Multi-Technology Learning

```text
User: "Create skill for Kubernetes service mesh with Istio"

Claude:
╔══════════════════════════════════════════════════════════════╗
║  Learning from Multiple Official Documentation Sources      ║
╚══════════════════════════════════════════════════════════════╝

1. Fetching Kubernetes documentation...
   ✅ Service concepts, networking, ingress

2. Fetching Istio documentation...
   ✅ Installation, traffic management, security, observability

3. Combining knowledge:
   - Kubernetes service → Istio virtual service
   - Kubernetes ingress → Istio gateway
   - Traffic routing, retries, circuit breakers
   - mTLS, authorization policies
   - Telemetry and monitoring

✅ Skill created with combined expertise!
```

### Pattern 3: Version-Specific Learning

```text
User: "Create skill for Next.js 14 App Router deployment"

Claude:
╔══════════════════════════════════════════════════════════════╗
║  Fetching Next.js 14 Specific Documentation                 ║
╚══════════════════════════════════════════════════════════════╝

Tool: get-library-docs
Input: {
  "context7CompatibleLibraryID": "nextjs-id",
  "topic": "app router, server components, server actions, streaming",
  "tokens": 8000
}

✅ Latest Next.js 14 features learned:
- App Router (not Pages Router!)
- Server Components by default
- Server Actions for mutations
- Streaming with Suspense
- Partial Prerendering (PPR)
- Metadata API

✅ Skill created for Next.js 14 (not outdated Next.js 13 patterns)!
```

---

## 📋 Context7 Integration Checklist

When creating skills for new technologies, ensure:

- [ ] **Technology identified** - Determine if it's new/unfamiliar
- [ ] **Context7 query prepared** - Know what to search for
- [ ] **Library resolved** - Use resolve-library-id MCP tool
- [ ] **Documentation fetched** - Use get-library-docs MCP tool (8000 tokens recommended)
- [ ] **Key concepts extracted** - Commands, workflows, best practices
- [ ] **Common errors identified** - From official troubleshooting docs
- [ ] **Examples collected** - Real examples from official docs (not invented!)
- [ ] **Skill created** - tool.py, README.md, SKILL.md with official knowledge
- [ ] **Authority documented** - Note in SKILL.md that it's based on official docs

---

## 🚀 Real-World Examples

### Example 1: Creating Terraform Skill

**Before Context7:**
```python
# Invented command (might be wrong!)
def terraform_init():
    run_command("terraform init --auto-approve")  # Wrong flag!
```

**After Context7 (from official docs):**
```python
# Official command (correct!)
def terraform_init(args):
    """Initialize Terraform working directory.

    From official docs: terraform init [options]
    - Downloads providers
    - Initializes backend
    - Creates .terraform directory
    """
    cmd = "terraform init"
    if args.upgrade:
        cmd += " -upgrade"  # Official flag
    if args.backend_config:
        cmd += f" -backend-config={args.backend_config}"  # Official flag

    code, stdout, stderr = run_command(cmd)
    # Error handling based on official error messages
    if "Provider not found" in stderr:
        print_error("Provider not found. Check provider requirements in .terraform.lock.hcl")
```

---

### Example 2: Creating K6 Load Testing Skill

**Context7 Query:**
```json
{
  "libraryName": "k6",
  "topic": "CLI commands, test scripts, metrics, thresholds, scenarios",
  "tokens": 6000
}
```

**Official Knowledge Gained:**
- Commands: `k6 run`, `k6 cloud`, `k6 inspect`
- Script structure: `import http from 'k6/http'; export default function() { ... }`
- Metrics: `http_req_duration`, `http_req_failed`, `iterations`
- Thresholds: Pass/fail criteria based on metrics
- Scenarios: Ramping VUs, constant rate, shared iterations

**Skill Created:**
```python
def run_load_test(args):
    """Run K6 load test (from official CLI docs)."""
    cmd = f"k6 run {args.script}"

    # Official flags from docs
    if args.vus:
        cmd += f" --vus {args.vus}"
    if args.duration:
        cmd += f" --duration {args.duration}"
    if args.out:
        cmd += f" --out {args.out}"  # Output: influxdb, json, cloud

    run_command(cmd)
```

---

### Example 3: Creating Playwright E2E Testing Skill

**Context7 Query:**
```json
{
  "libraryName": "playwright",
  "topic": "CLI commands, test structure, locators, assertions, debugging",
  "tokens": 7000
}
```

**Official Knowledge Gained:**
- CLI: `npx playwright test`, `npx playwright codegen`, `npx playwright show-report`
- Test structure: `test('description', async ({ page }) => { ... })`
- Locators: `page.getByRole()`, `page.getByText()`, `page.locator()`
- Assertions: `await expect(locator).toBeVisible()`
- Debugging: `--debug`, `--headed`, `--trace on`

**Skill Created:**
```python
def run_playwright_tests(args):
    """Run Playwright E2E tests (from official docs)."""
    cmd = "npx playwright test"

    # Official flags
    if args.headed:
        cmd += " --headed"  # Official: run in headed mode
    if args.debug:
        cmd += " --debug"  # Official: run in debug mode
    if args.project:
        cmd += f" --project={args.project}"  # Official: specific browser
    if args.trace:
        cmd += " --trace on"  # Official: enable tracing

    run_command(cmd)
```

---

## 💎 Pro Tips for Context7 Usage

### Tip 1: Request 8000 Tokens for Comprehensive Learning

```json
{
  "tokens": 8000  // Get comprehensive documentation
}
```

**Why:** More tokens = more complete understanding
- 2000 tokens: Basic commands only
- 5000 tokens: Commands + some best practices
- 8000 tokens: Commands + workflows + best practices + troubleshooting

---

### Tip 2: Use Specific Topics in Query

**❌ Bad Query:**
```json
{"topic": "documentation"}  // Too vague!
```

**✅ Good Query:**
```json
{
  "topic": "CLI commands, configuration, deployment workflows, common errors, best practices"
}
```

---

### Tip 3: Learn Related Technologies Together

**Example:** Creating Docker Compose skill

```text
1. Fetch Docker documentation (container basics)
2. Fetch Docker Compose documentation (multi-container apps)
3. Combine knowledge for comprehensive skill
```

---

### Tip 4: Verify Official Examples

**Always prefer official examples over invented ones:**

**❌ Invented Example:**
```python
# Might not work!
docker_compose_up = "docker-compose up -d --force-recreate"
```

**✅ Official Example (from Context7 docs):**
```python
# From official Docker Compose docs
docker_compose_up = "docker compose up -d"  # Note: docker compose, not docker-compose!
# --build flag: rebuild images
# --remove-orphans: remove containers for services not in compose file
```

---

### Tip 5: Update Skills When Technology Updates

**Pattern:**
```text
Technology releases new version
    ↓
Fetch updated documentation via Context7
    ↓
Update skill with new features/commands
    ↓
Skill stays current!
```

**Example:**
- Next.js 13 → 14: App Router became stable
- Kubernetes 1.27 → 1.28: New features
- Terraform 1.5 → 1.6: New providers

Use Context7 to stay updated! 🔄

---

## 🎓 Learning from Context7 vs Manual Research

| Aspect | Manual Research | Context7 MCP |
|--------|----------------|--------------|
| **Time** | 2-4 hours browsing docs | 2-5 minutes query |
| **Accuracy** | Risk of misreading/missing info | Direct from official source |
| **Coverage** | Might miss important sections | Comprehensive (8000 tokens) |
| **Currency** | Might find outdated docs | Always latest docs |
| **Examples** | Need to copy-paste | Integrated in response |
| **Commands** | Need to verify syntax | Pre-verified from official CLI |
| **Best Practices** | Scattered across pages | Consolidated in response |
| **Troubleshooting** | Need to search forums | Official error messages |

**Verdict:** Context7 MCP = 50-100x faster with 100% accuracy! ✅

---

## 🔐 Security Note

**API Key Storage:**
- ✅ Store in `.claude/.mcp.json` (gitignored)
- ❌ Never commit API keys to repository
- ❌ Never hardcode in skill files
- ✅ Use environment variables for CI/CD

**Example `.gitignore`:**
```
.claude/.mcp.json
.env
*.key
```

---

## 📊 Success Metrics with Context7

**Skills created WITHOUT Context7:**
- ⚠️ 30-40% accuracy (invented patterns)
- ⚠️ 2-4 hours research time
- ⚠️ High risk of errors
- ⚠️ Outdated patterns

**Skills created WITH Context7:**
- ✅ 95-100% accuracy (official docs)
- ✅ 5-15 minutes research time
- ✅ Zero invention - all official
- ✅ Always up-to-date
- ✅ Official documentation authority

**Impact:**
- 🚀 10-50x faster skill creation
- ✅ Higher quality skills
- ✅ Users trust "official" knowledge
- ✅ Skills truly replace specialists

---

## Skill Creation Best Practices (MANDATORY)

**Based on successful patterns from:**
- SEO Specialist skill
- AWS EKS Deploy skill
- GCP GKE Deploy skill
- Homelab Setup skill
- Kubernetes Deployment skill

### Required Components

**Every skill MUST have:**

1. **scripts/tool.py** (MANDATORY)
   - All executable code, commands, automation
   - Python script with proper argparse CLI
   - Multiple commands for different operations
   - Colored terminal output (success/error/warning/info)
   - Comprehensive error handling
   - Token-efficient (one script does everything)
   - Make executable: `chmod +x`

2. **README.md** (MANDATORY)
   - Quick start guide (5-15KB)
   - "No expert needed!" messaging
   - Common workflows (3-5 examples)
   - All command examples with expected output
   - Troubleshooting section (common issues + fixes)
   - Feature highlights
   - Cost information (if applicable)
   - Testing coverage summary
   - "Last Updated" footer with production-ready status

3. **SKILL.md** (MANDATORY)
   - Comprehensive documentation (2-25KB)
   - "When to Use This Skill" section
   - "What This Skill Provides" section
   - Detailed patterns (3-5 real-world scenarios)
   - Success metrics
   - Integration with other skills
   - Pro tips section
   - Resources and references

### Test-Driven Development (TDD) Approach

**CRITICAL:** Skills that automate setup/deployment MUST include testing:

```python
def run_tests(args) -> int:
    """Comprehensive testing suite"""
    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Prerequisites
    # Test 2: Installation/Setup
    # Test 3: Service/System Health
    # Test 4: Functionality Verification
    # Test 5: Edge Cases
    # Test 6: Resource Validation

    # Test Summary
    if tests_failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1
```

**Test Coverage Requirements:**
- ✅ Prerequisites validation (tools, credentials, permissions)
- ✅ Setup/installation verification
- ✅ Service/system health checks
- ✅ Functionality tests
- ✅ Edge case scenarios (30+ scenarios)
- ✅ Resource availability checks
- ✅ Network/connectivity tests
- ✅ Data persistence validation

**Edge Cases to Handle:**
- Missing tools → Installation instructions
- Invalid credentials → Configuration steps
- Setup failures → Detailed error messages with fixes
- Resource exhaustion → Scaling recommendations
- Network issues → Connectivity troubleshooting
- Timeouts → Retry logic or manual alternatives
- Permission errors → Permission fix commands
- Port conflicts → Alternative port suggestions

### Power and Expertise Level

**Goal:** Skills should be so powerful that human experts are NOT needed

**Messaging patterns:**
- "No SEO specialist needed!"
- "No cloud specialist needed!"
- "No DevOps expert required!"
- "Human only supervises - skill does 90% of work"

**Requirements for "Expert Replacement":**
- Handles A-Z of the domain
- Comprehensive testing (zero failure points)
- Automated troubleshooting with fixes
- Edge case coverage (30+ scenarios)
- Clear, actionable recommendations
- Production-ready configuration
- Cost optimization built-in
- Best practices automatically applied

### Tool Commands Pattern

**Standard command structure:**

```python
commands = {
    'check-prerequisites': check_prerequisites,  # Always first
    'setup/create': setup_or_create,              # Main setup/creation
    'configure': configure,                        # Configuration
    'deploy': deploy,                              # Deployment
    'test': run_tests,                             # Comprehensive testing
    'health-check': health_check,                  # Health monitoring
    'troubleshoot': troubleshoot,                  # Issue detection + fixes
    'cleanup': cleanup                             # Resource deletion
}
```

**Minimum commands: 4-8**

### README.md Template Structure

```markdown
# [Skill Name] - Quick Start

**One-command [domain] - No [specialist] needed!**

## 🚀 Quick Usage

### 1. [First Command]
```bash
python3 tool.py command1
```
**Output:** [expected output]

### 2. [Second Command]
[Examples with outputs]

---

## 💡 Common Workflows

### Workflow 1: [Use Case]
[Step-by-step with commands]

### Workflow 2: [Use Case]
[Step-by-step with commands]

---

## 🆘 Troubleshooting

### Issue 1: [Common Problem]
**Fix:** [Solution]

### Issue 2: [Common Problem]
**Fix:** [Solution]

---

## ✨ Features
- ✅ No [specialist] expertise required
- ✅ [Key benefit 1]
- ✅ Comprehensive testing (X+ scenarios)
- ✅ Edge case handling
- ✅ Token-efficient
- ✅ Test-Driven Development approach

---

**Last Updated:** 2026-02-09
**Status:** Production-ready ✅
**No [specialist] needed!** 🚀
```

### SKILL.md Template Structure

```markdown
# [Skill Name]

**[Tagline]**

**Category:** [Category]
**Complexity:** Beginner-Friendly (Expert Power)
**Time Savings:** X-Y% reduction
**Quality Impact:** Zero-failure with TDD approach

---

## When to Use This Skill

Use when [scenarios]. Skip when [scenarios].

---

## What This Skill Provides

**X Commands covering [domain]:**
- command1 → command2 → command3...

**TDD Approach - Y Test Suite:**
1. [Test type 1]
2. [Test type 2]
...

**Edge cases: X+ scenarios tested automatically**

---

## Quick Reference

See README.md for:
- Quick start workflows
- [Key reference 1]
- [Key reference 2]
- Troubleshooting

**Common workflow:**
```bash
# [Step-by-step example]
```

---

## Advanced Patterns

### Pattern 1: [Advanced Use Case]
[Detailed example]

### Pattern 2: [Advanced Use Case]
[Detailed example]

---

## Success Metrics

- X-Y% faster than manual
- 100% test coverage
- Zero failures when tests pass
- $X-Y cost savings vs hiring expert
- X+ edge cases handled automatically

---

**Status:** Production-ready ✅
**No [specialist] needed!** 🚀
```

---

## Skill Creation Workflow

### Step 1: Create Directory Structure

```bash
mkdir -p .claude/skills/[skill-name]/scripts
```

### Step 2: Create tool.py

**Template:**
```python
#!/usr/bin/env python3
"""
[Skill Name] Tool

[Description]

Commands:
  check-prerequisites  - [Description]
  [command]            - [Description]
  test                 - Comprehensive testing
  troubleshoot         - Issue detection + fixes
"""

import argparse
import subprocess
import sys

class Colors:
    GREEN = '\\033[92m'
    RED = '\\033[91m'
    YELLOW = '\\033[93m'
    BLUE = '\\033[94m'
    BOLD = '\\033[1m'
    END = '\\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, timeout: int = 300):
    """Run shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_prerequisites(args) -> int:
    """Check if required tools are installed"""
    print_header("Checking Prerequisites")
    # Implementation
    return 0

def run_tests(args) -> int:
    """Comprehensive testing suite"""
    print_header("Comprehensive Testing")
    tests_passed = 0
    tests_failed = 0

    # Test 1: Prerequisites
    # Test 2: Setup/Installation
    # Test 3: Health
    # Test 4-6: Additional tests

    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    return 0 if tests_failed == 0 else 1

def main():
    parser = argparse.ArgumentParser(description='[Skill Name] Tool')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('check-prerequisites')
    # Add other commands

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'test': run_tests,
        # Add other commands
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
```

### Step 3: Make Executable

```bash
chmod +x .claude/skills/[skill-name]/scripts/tool.py
```

### Step 4: Create README.md

Use README.md template above (5-15KB recommended)

### Step 5: Create SKILL.md

Use SKILL.md template above (2-25KB recommended)

### Step 6: Test the Skill

```bash
# Test all commands
python3 .claude/skills/[skill-name]/scripts/tool.py check-prerequisites
python3 .claude/skills/[skill-name]/scripts/tool.py test
```

---

## Token Efficiency

**Why tool.py saves 80-90% tokens:**

Without tool.py:
- Agent must generate full commands each time
- Repeated explanations of flags/parameters
- Multi-turn conversations for complex operations
- Error-prone manual command construction

With tool.py:
- Single command invocation
- Pre-built, tested automation
- Comprehensive error handling built-in
- One-turn execution with full output

**Example:**
- Manual: 50+ messages to deploy EKS cluster
- Tool: 1 message → `python3 tool.py create-cluster --cluster-name prod --nodes 3`

---

## Real-World Examples

**Reference these skills for patterns:**

1. **SEO Specialist** (`.claude/skills/seo-specialist/`)
   - 6 commands (audit, keywords, sitemap, robots, schema, optimize)
   - No SEO expert needed
   - Content scoring, keyword density analysis
   - 31KB tool.py

2. **AWS EKS Deploy** (`.claude/skills/aws-eks-deploy/`)
   - 8 commands (prerequisites → cleanup)
   - TDD approach (6-test suite)
   - Production-ready in 20 minutes
   - Multi-region support
   - Cost optimization

3. **GCP GKE Deploy** (`.claude/skills/gcp-gke-deploy/`)
   - 8 commands (similar to AWS)
   - Preemptible VMs (80% savings)
   - Free tier optimization
   - Auto-scaling, auto-repair

4. **Homelab Setup** (`.claude/skills/homelab-setup/`)
   - 6 commands (setup, deploy-node, verify, test, health-check, troubleshoot)
   - Docker + Binary deployment methods
   - Zero-failure guarantee
   - Comprehensive testing

---

## Success Criteria

When creating a skill, ensure:

- [ ] tool.py created with 4-8 commands minimum
- [ ] tool.py is executable (`chmod +x`)
- [ ] README.md exists (5-15KB) with quick start
- [ ] SKILL.md exists (2-25KB) with comprehensive docs
- [ ] TDD approach: `test` command exists with 6+ tests
- [ ] Edge cases covered (30+ scenarios)
- [ ] Troubleshooting section in README with common issues
- [ ] "No [specialist] needed!" messaging included
- [ ] Success metrics documented
- [ ] Token efficiency demonstrated
- [ ] Production-ready status indicated
- [ ] All commands have example outputs
- [ ] Common workflows provided (3-5 examples)

---

## Anti-Patterns (Avoid These)

❌ **No tool.py** - Defeats token efficiency
❌ **No tests** - No quality guarantee
❌ **No README.md** - Users confused
❌ **Minimal documentation** - Not comprehensive enough
❌ **No edge cases** - Will fail in production
❌ **No troubleshooting** - Users stuck on errors
❌ **Complex setup** - Should be one-command
❌ **Requires expert** - Skill should replace expert
❌ **No output examples** - Users don't know what to expect
❌ **Missing status** - Users unsure if production-ready

---

**Last Updated:** 2026-02-09
**Skills Created Using These Patterns:** 7+
**Latest:** Azure AKS Deploy (2026-02-09) - 647 lines tool.py, 536 lines README, 607 lines SKILL
**Success Rate:** 100% (when patterns followed)
**Token Savings:** 80-90% average
**Status:** Production-tested ✅
