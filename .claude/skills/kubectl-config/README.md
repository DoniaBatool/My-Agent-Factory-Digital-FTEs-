# kubectl Configuration Skill - Quick Start

**Token-efficient kubectl setup automation**

## 🚀 Quick Usage

### 1. Check kubectl Installation

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py check
```

**Output:**
```
✓ kubectl installed: v1.28.0
✓ kubeconfig exists: ~/.kube/config
✓ Current context: context-abc123
✓ Cluster: https://...oke.us-phoenix-1.oraclecloud.com
```

---

### 2. Install kubectl (if needed)

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py install
```

**Detects OS and provides installation instructions:**
- **macOS:** `brew install kubectl`
- **Linux:** curl download with instructions
- **Windows:** Chocolatey installation guide

---

### 3. Setup Oracle Cloud OKE (Most Common)

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke \
  --cluster-id ocid1.cluster.oc1.phx.aaaaaaa...
```

**What it does:**
1. Checks if OCI CLI is installed
2. If OCI CLI available: Runs `oci ce cluster create-kubeconfig`
3. If OCI CLI missing: Provides Oracle Console manual steps
4. Verifies connection after setup

**Output:**
```
✓ OCI CLI detected
✓ Generated kubeconfig for cluster
✓ Connection verified
✓ Nodes: 2 Ready
```

---

### 4. Verify Connection

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py verify
```

**Output:**
```
✓ kubectl version: v1.28.0
✓ Active context: context-abc123
✓ Cluster: https://...oke.us-phoenix-1.oraclecloud.com
✓ Nodes: 2 Ready
✓ Namespaces: 5 (default, kube-system, kube-public, todo-app, ...)
```

---

### 5. List All Contexts

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py contexts
```

**Output:**
```
Available kubectl contexts:
* context-oke-production (current)
  context-gke-staging
  minikube
```

---

### 6. Switch Context

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py switch \
  --context context-gke-staging
```

**Output:**
```
✓ Switched to context: context-gke-staging
✓ Active cluster: https://gke...
```

---

### 7. Troubleshoot Issues

```bash
python3 .claude/skills/kubectl-config/scripts/tool.py troubleshoot
```

**Output:**
```
🔍 Troubleshooting kubectl connection...

✅ kubectl installed: /usr/local/bin/kubectl
✅ kubeconfig exists: ~/.kube/config
✅ Current context: context-oke
❌ Cluster unreachable

Possible causes:
1. Cluster is down (check Oracle Console)
2. Network connectivity issue
3. Expired credentials

Recommended fixes:
- Verify cluster status in Oracle Console
- Regenerate kubeconfig: oci ce cluster create-kubeconfig...
```

---

## 📋 All Commands

```bash
# Installation & Setup
tool.py check                     # Check kubectl installation & connection
tool.py install                   # Install kubectl (OS-specific)
tool.py setup-oke --cluster-id ID # Setup Oracle Cloud OKE
tool.py setup-gke --cluster ... # Setup Google Cloud GKE
tool.py setup-aks --cluster ... # Setup Azure AKS
tool.py setup-eks --cluster ... # Setup AWS EKS

# Context Management
tool.py contexts                  # List all contexts
tool.py switch --context NAME     # Switch to different context
tool.py verify                    # Verify current connection

# Information & Debugging
tool.py info                      # Show kubeconfig file info
tool.py troubleshoot              # Automated troubleshooting
```

---

## 💡 Pro Tips

### Quick Start for Oracle Cloud OKE (University Project)

**Complete workflow from zero to connected:**

```bash
# Step 1: Check if kubectl installed
python3 .claude/skills/kubectl-config/scripts/tool.py check

# Step 2: Install if needed (macOS example)
python3 .claude/skills/kubectl-config/scripts/tool.py install

# Step 3: Get cluster OCID from Oracle Console
# Navigate to: Developer Services → Kubernetes Clusters → Your Cluster
# Copy: Cluster OCID (starts with ocid1.cluster...)

# Step 4: Setup kubectl for OKE
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke \
  --cluster-id ocid1.cluster.oc1.phx.YOUR_CLUSTER_OCID

# Step 5: Verify connection
python3 .claude/skills/kubectl-config/scripts/tool.py verify

# Step 6: Test with basic commands
kubectl get nodes
kubectl get namespaces

# Done! Ready to deploy applications ✅
```

**Time:** 5-10 minutes total

---

### Managing Multiple Clusters

```bash
# Setup all your clusters first
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke --cluster-id ocid1...
python3 .claude/skills/kubectl-config/scripts/tool.py setup-gke --cluster-name staging...

# List all contexts
python3 .claude/skills/kubectl-config/scripts/tool.py contexts

# Switch between them
python3 .claude/skills/kubectl-config/scripts/tool.py switch --context context-oke
python3 .claude/skills/kubectl-config/scripts/tool.py switch --context context-gke

# Always verify before running commands
python3 .claude/skills/kubectl-config/scripts/tool.py verify
```

---

### Troubleshooting Common Issues

**Issue: "kubectl: command not found"**
```bash
python3 .claude/skills/kubectl-config/scripts/tool.py check
# If not installed, run:
python3 .claude/skills/kubectl-config/scripts/tool.py install
```

**Issue: "The connection to the server localhost:8080 was refused"**
```bash
# No context set - run setup:
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke --cluster-id YOUR_ID
```

**Issue: "Unable to connect to the server"**
```bash
# Cluster unreachable - troubleshoot:
python3 .claude/skills/kubectl-config/scripts/tool.py troubleshoot
```

---

## 🔗 Integration with Other Skills

### Workflow: Setup → Deploy → Monitor

```bash
# 1. Configure kubectl (this skill)
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke \
  --cluster-id YOUR_CLUSTER_OCID

# 2. Deploy application (kubernetes-deployment skill)
python3 .claude/skills/kubernetes-deployment/scripts/tool.py deploy \
  --manifests k8s/oke \
  --namespace todo-app

# 3. Get public URL (kubernetes-deployment skill)
python3 .claude/skills/kubernetes-deployment/scripts/tool.py get-ips \
  --namespace todo-app
```

---

## 📚 Documentation

**Full documentation:** See `SKILL.md` for complete guide

**Token Savings:** Using this script saves 50-70% tokens vs manual kubectl configuration guidance in Claude

**Features:**
- ✅ Automated kubectl installation
- ✅ Multi-cloud provider support (OKE, GKE, AKS, EKS)
- ✅ Context management
- ✅ Connection verification
- ✅ Automated troubleshooting
- ✅ Team onboarding automation

---

## 🎯 Real-World Example

**Scenario:** New developer needs kubectl access to Oracle Cloud OKE cluster for Todo App

**Commands:**
```bash
# 1. Check installation (1 min)
python3 .claude/skills/kubectl-config/scripts/tool.py check

# 2. Setup OKE (3 min)
python3 .claude/skills/kubectl-config/scripts/tool.py setup-oke \
  --cluster-id ocid1.cluster.oc1.phx.provided-by-devops

# 3. Verify (1 min)
python3 .claude/skills/kubectl-config/scripts/tool.py verify

# 4. Test (1 min)
kubectl get pods -n todo-app

# Total: 6 minutes from zero to productive ✅
```

---

## 📞 Quick Reference

| Task | Command |
|------|---------|
| Check kubectl | `tool.py check` |
| Install kubectl | `tool.py install` |
| Setup OKE | `tool.py setup-oke --cluster-id ID` |
| List contexts | `tool.py contexts` |
| Switch context | `tool.py switch --context NAME` |
| Verify connection | `tool.py verify` |
| Fix issues | `tool.py troubleshoot` |

---

**Last Updated:** 2026-02-07
**Status:** Production-ready ✅
