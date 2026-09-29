---
name: digitalocean-deploy
description: Complete droplet creation, app deployment, configuration, and monitoring setup for DigitalOcean cloud platform
---

# DigitalOcean Deploy - Quick Start

**One-command DigitalOcean deployment - No cloud specialist needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 scripts/tool.py check-prerequisites
```

### 2. Create Droplet
```bash
python3 scripts/tool.py create-droplet \
  --name myapp-prod \
  --region nyc3 \
  --size s-1vcpu-1gb \
  --enable-monitoring
```

### 3. Deploy Application
```bash
python3 scripts/tool.py deploy-app \
  --method docker \
  --docker-image myapp:latest
```

### 4. Configure Monitoring
```bash
python3 scripts/tool.py configure-monitoring
```

### 5. Health Check
```bash
python3 scripts/tool.py health-check --health-endpoint /health
```

### 6. Test
```bash
python3 scripts/tool.py test
```

### 7. Troubleshoot
```bash
python3 scripts/tool.py troubleshoot
```

### 8. Cleanup
```bash
python3 scripts/tool.py cleanup --force
```

## 💡 Common Workflows

### Workflow 1: Simple Deployment
```bash
# Create droplet with monitoring
python3 scripts/tool.py create-droplet --name myapp --enable-monitoring

# Deploy Docker app
python3 scripts/tool.py deploy-app --method docker --docker-image nginx:latest

# Check health
python3 scripts/tool.py health-check
```

### Workflow 2: From Git Repository
```bash
python3 scripts/tool.py create-droplet --name myapp
python3 scripts/tool.py deploy-app --method git --git-repo https://github.com/user/repo.git
```

## 🆘 Troubleshooting

### Issue 1: Not authenticated
**Fix:** `doctl auth init`

### Issue 2: SSH not accessible
**Fix:** Wait 2-3 minutes after droplet creation

### Issue 3: Port not accessible
**Fix:** Configure firewall rules

## ✨ Features
- ✅ No cloud specialist needed
- ✅ Official doctl CLI commands
- ✅ Docker & Git deployment
- ✅ Monitoring integration
- ✅ 6+ comprehensive tests
- ✅ 30+ edge cases
- ✅ Production-ready

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Based on official DigitalOcean documentation** 📚
