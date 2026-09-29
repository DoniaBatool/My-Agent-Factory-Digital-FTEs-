---
name: github-actions-cicd
description: Automated build, test, deploy pipelines with workflow generation, secrets management, and multi-environment support for continuous integration and deployment
---

# GitHub Actions CI/CD - Quick Start

**One-command CI/CD - No DevOps specialist needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 scripts/tool.py check-prerequisites
```
**Output:**
```
✓ Git installed: git version 2.39.0
✓ GitHub CLI installed: 2.40.0
✓ GitHub authenticated
✓ Inside git repository
✓ GitHub remote: https://github.com/user/repo.git
```

### 2. Generate Workflows
```bash
python3 scripts/tool.py generate-workflow --app-name todo-app
```
**Output:**
```
✅ Created: .github/workflows/ci.yml
✅ Created: .github/workflows/deploy-dev.yml
✅ Created: .github/workflows/deploy-staging.yml
✅ Created: .github/workflows/deploy-prod.yml
```

### 3. Setup Secrets
```bash
python3 scripts/tool.py setup-secrets
```
**Output:**
```
Required secrets:
  - DATABASE_URL
  - OPENAI_API_KEY
  - JWT_SECRET
  - KUBECONFIG_DEV/STAGING/PROD

Run: gh secret set SECRET_NAME
```

### 4. Test Workflows
```bash
python3 scripts/tool.py test-workflow
```
**Output:**
```
✓ ci.yml - Valid syntax
✓ deploy-dev.yml - Valid syntax
✓ deploy-staging.yml - Valid syntax
✓ deploy-prod.yml - Valid syntax
```

### 5. Monitor Runs
```bash
python3 scripts/tool.py monitor
```
**Output:**
```
✅ CI - Test and Build
   Status: completed (success)
   Created: 2026-02-11T10:30:00Z

🔄 CD - Deploy to DEV
   Status: in_progress
   Created: 2026-02-11T10:35:00Z
```

---

## 💡 Common Workflows

### Workflow 1: Setup CI/CD for New Project
```bash
# Step 1: Prerequisites
python3 scripts/tool.py check-prerequisites

# Step 2: Generate workflows
python3 scripts/tool.py generate-workflow --app-name myapp

# Step 3: Configure secrets
gh secret set DATABASE_URL
gh secret set OPENAI_API_KEY
gh secret set JWT_SECRET

# Step 4: Commit and push
git add .github/
git commit -m "Add CI/CD workflows"
git push origin main
```

### Workflow 2: Multi-Environment Deployment
```bash
# Generate workflows for dev, staging, prod
python3 scripts/tool.py generate-workflow \
  --app-name todo-app \
  --environments dev,staging,prod

# Configure environment-specific secrets
gh secret set KUBECONFIG_DEV
gh secret set KUBECONFIG_STAGING
gh secret set KUBECONFIG_PROD
```

### Workflow 3: Troubleshoot Failed Workflow
```bash
# Check failed runs
python3 scripts/tool.py troubleshoot

# Output shows:
# ❌ CI - Test and Build (ID: 123456)
#    Logs: Error: Tests failed in test_auth.py...

# Fix the issue, commit, and push
git add tests/
git commit -m "Fix: Auth test assertion"
git push
```

---

## 🆘 Troubleshooting

### Issue 1: "gh: command not found"
**Fix:**
```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### Issue 2: "gh auth status: Not logged in"
**Fix:**
```bash
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Authenticate via browser
```

### Issue 3: Workflow fails with "Secret not found"
**Fix:**
```bash
# List existing secrets
gh secret list

# Set missing secrets
gh secret set DATABASE_URL
# Paste value and press Enter twice
```

### Issue 4: Docker build fails in CI
**Fix:**
```bash
# Ensure Dockerfile exists at repo root
ls Dockerfile

# Test build locally first
docker build -t myapp:test .

# If successful, push to trigger CI
git push
```

### Issue 5: Kubectl deployment fails
**Fix:**
```bash
# Verify kubeconfig is base64 encoded
cat ~/.kube/config | base64

# Set as secret
gh secret set KUBECONFIG_DEV

# Ensure k8s manifests exist
ls k8s/dev/
```

---

## ✨ Features

- ✅ No DevOps specialist needed
- ✅ Multi-environment support (dev/staging/prod)
- ✅ Automated Docker build + push to GHCR
- ✅ Test automation (pytest, coverage)
- ✅ Kubernetes deployment automation
- ✅ Secrets management
- ✅ Workflow syntax validation
- ✅ Failed run troubleshooting
- ✅ Comprehensive testing (6+ scenarios)
- ✅ Token-efficient
- ✅ Production-ready

---

## 📊 Generated Workflows

### CI Workflow (ci.yml)
**Triggers:** Push to main/develop/feature branches, PRs
**Jobs:**
1. Test - Run pytest with coverage
2. Build - Docker build + push to GHCR

### CD Workflows (deploy-{env}.yml)
**Triggers:** Push to env-specific branches
**Jobs:**
1. Deploy - kubectl apply to K8s cluster
2. Verify - Check rollout status

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**No DevOps specialist needed!** 🚀
