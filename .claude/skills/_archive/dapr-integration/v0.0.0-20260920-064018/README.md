---
name: dapr-integration
description: Complete Dapr distributed application runtime setup with Pub/Sub, State, Secrets, Cron bindings, and sidecar injection for microservices
---

# Dapr Integration - Quick Start

**One-command distributed runtime - No microservices expertise needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 scripts/tool.py check-prerequisites
```

### 2. Initialize Dapr in Cluster
```bash
python3 scripts/tool.py init-dapr
```

### 3. Setup Pub/Sub (Kafka/Redpanda)
```bash
python3 scripts/tool.py setup-pubsub \
  --brokers redpanda-0.redpanda.svc.cluster.local:9092
```

### 4. Setup State Store (Redis)
```bash
python3 scripts/tool.py setup-state \
  --redis-host redis-master.redis.svc.cluster.local:6379
```

### 5. Setup Cron for Reminders
```bash
python3 scripts/tool.py setup-cron --schedule "*/5 * * * *"
```

### 6. Inject Sidecar into Deployment
```bash
python3 scripts/tool.py inject-sidecar \
  --deployment-file k8s/backend-deployment.yaml \
  --app-id todo-backend \
  --app-port 8000
```

---

## 💡 Common Workflows

### Workflow 1: Complete Dapr Setup for Phase 5
```bash
# Prerequisites
python3 scripts/tool.py check-prerequisites

# Initialize Dapr
python3 scripts/tool.py init-dapr

# Configure components
python3 scripts/tool.py setup-pubsub
python3 scripts/tool.py setup-state
python3 scripts/tool.py setup-secrets
python3 scripts/tool.py setup-cron

# Inject sidecars
python3 scripts/tool.py inject-sidecar \
  --deployment-file k8s/backend-deployment.yaml \
  --app-id todo-backend \
  --app-port 8000

# Apply deployments
kubectl apply -f k8s/

# Verify
python3 scripts/tool.py test
```

### Workflow 2: Publish Event to Kafka via Dapr
```python
# In FastAPI
import httpx

async def publish_task_created(task_id: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:3500/v1.0/publish/kafka-pubsub/task-events",
            json={
                "task_id": task_id,
                "event": "task.created",
                "timestamp": "2026-02-11T10:00:00Z"
            }
        )
```

### Workflow 3: Subscribe to Kafka Events
```python
# FastAPI endpoint
@app.post("/dapr/subscribe")
def subscribe():
    return [{
        "pubsubname": "kafka-pubsub",
        "topic": "task-events",
        "route": "/events/task-events"
    }]

@app.post("/events/task-events")
def handle_task_event(event: dict):
    # Process event
    return {"status": "ok"}
```

---

## 🆘 Troubleshooting

### Issue 1: "dapr: command not found"
**Fix:**
```bash
curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | bash
```

### Issue 2: Dapr pods not starting
**Fix:**
```bash
# Check logs
kubectl logs -n dapr-system -l app=dapr-operator

# Reinitialize
dapr uninstall --kubernetes
python3 scripts/tool.py init-dapr
```

### Issue 3: Component not loading
**Fix:**
```bash
# Check component status
kubectl describe component kafka-pubsub

# Verify namespace matches
kubectl get components --all-namespaces
```

---

## ✨ Features

- ✅ No microservices expertise needed
- ✅ Kafka/Redpanda Pub/Sub integration
- ✅ Redis state store
- ✅ Kubernetes secrets management
- ✅ Cron bindings for scheduled tasks
- ✅ Automatic sidecar injection
- ✅ Service-to-service invocation
- ✅ Production-ready configurations
- ✅ Comprehensive testing (6+ scenarios)

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Based on official Dapr documentation** 📚
