---
name: oracle-oke-deploy
description: Automated Oracle Cloud OKE deployment with free tier optimization and ARM instance support
---

# Oracle Cloud OKE Deploy - Quick Start

**One-command OKE cluster - No Oracle Cloud expertise needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 scripts/tool.py check-prerequisites
```

### 2. Create OKE Cluster (Free Tier)
```bash
python3 scripts/tool.py create-cluster \
  --cluster-name todo-app \
  --nodes 2 \
  --free-tier
```

### 3. Configure kubectl
```bash
python3 scripts/tool.py configure-kubectl
```

### 4. Deploy Application
```bash
python3 scripts/tool.py deploy-app \
  --backend-image ghcr.io/user/backend:latest \
  --frontend-image ghcr.io/user/frontend:latest
```

### 5. Test Deployment
```bash
python3 scripts/tool.py test
```

---

## ✨ Features

- ✅ No Oracle Cloud expertise needed
- ✅ Free tier optimization (4 OCPU, 24 GB RAM)
- ✅ ARM instances (A1.Flex - Always Free)
- ✅ Multi-node cluster support
- ✅ LoadBalancer configuration
- ✅ Comprehensive testing (6+ scenarios)
- ✅ Production-ready

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Cost:** $0/month (Free Tier) ✅
