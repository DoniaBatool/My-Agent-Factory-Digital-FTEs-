# Kubernetes Deployment Skill - Quick Start

**Token-efficient K8s deployment automation**

## 🚀 Quick Usage

### 1. Generate Manifests for Oracle Cloud OKE (Free Tier)

```bash
python3 .claude/skills/kubernetes-deployment/scripts/tool.py generate \
  --app-name todo-app \
  --backend-image ghcr.io/YOUR_USERNAME/todo-backend:latest \
  --frontend-image ghcr.io/YOUR_USERNAME/todo-frontend:latest \
  --provider oke \
  --free-tier \
  --output k8s/oke
```

**Output:** Creates all K8s manifests in `k8s/oke/`

---

### 2. Deploy to Cluster

```bash
# After editing secrets in k8s/oke/backend-secret.yaml
python3 .claude/skills/kubernetes-deployment/scripts/tool.py deploy \
  --manifests k8s/oke \
  --namespace todo-app
```

---

### 3. Get Public URLs

```bash
python3 .claude/skills/kubernetes-deployment/scripts/tool.py get-ips \
  --namespace todo-app
```

**Output:**
```
✓ todo-app-frontend: http://140.238.X.X
✓ todo-app-backend: http://140.238.Y.Y
```

---

### 4. Check Health

```bash
python3 .claude/skills/kubernetes-deployment/scripts/tool.py health-check \
  --namespace todo-app
```

---

### 5. View Logs

```bash
# Backend logs
python3 .claude/skills/kubernetes-deployment/scripts/tool.py logs \
  --namespace todo-app \
  --app backend \
  --tail 100

# Follow frontend logs
python3 .claude/skills/kubernetes-deployment/scripts/tool.py logs \
  --namespace todo-app \
  --app frontend \
  --follow
```

---

### 6. Scale Deployment

```bash
python3 .claude/skills/kubernetes-deployment/scripts/tool.py scale \
  --namespace todo-app \
  --deployment todo-app-backend \
  --replicas 5
```

---

## 📋 All Commands

```bash
# Generate manifests
tool.py generate --app-name NAME --backend-image IMG --frontend-image IMG \
                 --provider [oke|gke|aks|eks] --free-tier --output DIR

# Deploy to cluster
tool.py deploy --manifests DIR --namespace NS

# Get LoadBalancer IPs
tool.py get-ips --namespace NS

# Health check
tool.py health-check --namespace NS

# View logs
tool.py logs --namespace NS --app [backend|frontend] --tail N [--follow]

# Scale deployment
tool.py scale --namespace NS --deployment NAME --replicas N
```

---

## 💡 Pro Tips

### Free Tier Optimization
```bash
# Use --free-tier flag for cost optimization
# Backend becomes ClusterIP (internal only)
# Frontend stays LoadBalancer (public)
# Saves ~$10-15/month on 2nd LoadBalancer
```

### Production Deployment
```bash
# Generate with higher replicas
tool.py generate ... --replicas 3 --output k8s/prod
```

### Multi-Environment
```bash
# Development
tool.py generate ... --replicas 1 --output k8s/dev

# Production
tool.py generate ... --replicas 3 --output k8s/prod
```

---

## 📚 Documentation

**Full documentation:** See `SKILL.md` for complete guide

**Token Savings:** Using this script saves 70-80% tokens vs generating manifests in Claude

**Features:**
- ✅ Zero-downtime rolling updates
- ✅ Health checks (liveness + readiness)
- ✅ Resource limits
- ✅ Security best practices
- ✅ Free tier optimizations
- ✅ Multi-cloud support

---

**Last Updated:** 2026-02-07
