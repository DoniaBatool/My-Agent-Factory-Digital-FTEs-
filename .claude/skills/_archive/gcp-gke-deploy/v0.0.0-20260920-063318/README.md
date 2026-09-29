# GCP GKE Deployment Skill - Quick Start

**One-command GCP GKE cluster deployment - No cloud specialist needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py check-prerequisites
```

**Output:**
```
==> Checking Prerequisites
✓ gcloud SDK installed
✓ Authenticated as: user@example.com
✓ kubectl installed

✅ All prerequisites met!
```

### 2. Create GKE Cluster

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py create-cluster \
  --cluster-name my-app-cluster \
  --project my-gcp-project \
  --zone us-central1-a \
  --nodes 2 \
  --machine-type e2-small
```

**Output:**
```
==> Creating GKE Cluster: my-app-cluster
ℹ Project: my-gcp-project
ℹ Zone: us-central1-a
ℹ Nodes: 2
ℹ Machine type: e2-small

ℹ Creating GKE cluster... (10-15 minutes)
✓ GKE cluster created successfully! ✅
✓ kubectl configured
```

### 3. Deploy Application

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py deploy \
  --manifest-dir ./k8s/manifests \
  --namespace my-app
```

### 4. Run Tests

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py test \
  --namespace my-app
```

**Output:**
```
Total tests: 6
Passed: 6
Failed: 0

✅ All tests passed!
```

### 5. Health Check

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py health-check \
  --namespace my-app
```

### 6. Cleanup

```bash
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py cleanup \
  --cluster-name my-app-cluster \
  --zone us-central1-a \
  --project my-gcp-project
```

---

## 💡 Common Workflows

### Workflow 1: Free Tier Cluster

**GCP Free Tier includes:**
- $300 credit for 90 days
- 1x e2-micro instance (always free)
- 30 GB standard persistent disk

```bash
# Create free tier cluster
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py create-cluster \
  --cluster-name free-tier \
  --project my-project \
  --zone us-central1-a \
  --nodes 1 \
  --machine-type e2-micro

# Deploy
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py deploy \
  --manifest-dir ./k8s/minimal

# Test
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py test

# Cleanup when done
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py cleanup \
  --cluster-name free-tier \
  --zone us-central1-a \
  --project my-project \
  --force
```

---

### Workflow 2: Cost-Optimized with Preemptible VMs

```bash
# Use preemptible VMs (up to 80% savings)
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py create-cluster \
  --cluster-name cost-optimized \
  --project my-project \
  --zone us-central1-a \
  --nodes 3 \
  --machine-type e2-small \
  --preemptible
```

**Savings:** Up to 80% compared to regular VMs!

---

### Workflow 3: Production Cluster

```bash
# Production-ready cluster
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py create-cluster \
  --cluster-name production \
  --project my-project \
  --zone us-central1-a \
  --nodes 3 \
  --machine-type e2-medium

# Deploy application
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py deploy \
  --manifest-dir ./k8s/production \
  --namespace production

# Test
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py test \
  --namespace production

# Health check
python3 .claude/skills/gcp-gke-deploy/scripts/tool.py health-check \
  --namespace production
```

---

## 🔧 Machine Type Selection

| Type | vCPU | RAM | Best For | Cost/hr |
|------|------|-----|----------|---------|
| **e2-micro** | 0.25-2 | 1 GB | Free tier, testing | $0.0084 |
| **e2-small** | 0.5-2 | 2 GB | Dev/testing | $0.0168 |
| **e2-medium** | 1-2 | 4 GB | Small production | $0.0336 |
| **e2-standard-2** | 2 | 8 GB | Production | $0.0670 |
| **n1-standard-2** | 2 | 7.5 GB | General purpose | $0.0950 |

**Recommendation:**
- **Free tier:** e2-micro (1 node)
- **Development:** e2-small (2 nodes)
- **Production:** e2-medium+ (3+ nodes)

---

## 🌍 GCP Zones

### Popular Zones

| Zone | Location | Best For |
|------|----------|----------|
| **us-central1-a** | Iowa, USA | US Central, low latency |
| **us-east1-b** | South Carolina | US East Coast |
| **us-west1-a** | Oregon | US West Coast |
| **europe-west1-b** | Belgium | European users |
| **asia-southeast1-a** | Singapore | Southeast Asia |

---

## 🆘 Troubleshooting

### Issue 1: "Not authenticated to GCP"

**Fix:**
```bash
gcloud auth login
gcloud config set project PROJECT_ID
```

---

### Issue 2: "gcloud not found"

**Fix:**
```bash
# Install gcloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

---

### Issue 3: "Insufficient quota"

**Fix:**
- Check quotas in GCP Console
- Request quota increase
- Try different zone/region
- Use smaller machine type

---

## ✨ Features

- ✅ No cloud specialist expertise required
- ✅ Production-ready cluster in 15 minutes
- ✅ Comprehensive testing (6-test suite)
- ✅ Edge case handling (30+ scenarios)
- ✅ Automated troubleshooting
- ✅ Free tier optimization
- ✅ Preemptible VMs support (80% savings)
- ✅ Auto-scaling, auto-repair, auto-upgrade
- ✅ TDD approach
- ✅ Token-efficient

---

## 📊 Testing Coverage

**Tests:**
- ✅ Prerequisites (gcloud, kubectl, auth)
- ✅ Cluster accessibility
- ✅ Nodes health
- ✅ Pods health
- ✅ Services
- ✅ GCP resources

**Edge cases: 30+ scenarios tested**

---

**Last Updated:** 2026-02-09
**GKE Version:** 1.28+
**Status:** Production-ready ✅
**No cloud expertise needed!** 🚀
