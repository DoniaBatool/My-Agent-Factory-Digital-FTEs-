---
name: container-orchestration
description: Implement Kubernetes deployment, scaling, service mesh, and container orchestration for production-grade containerized applications.
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



# Container Orchestration Skill

## Purpose
Deploy and manage containerized applications at scale using Kubernetes.

## Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: todo-api
  labels:
    app: todo-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: todo-api
  template:
    metadata:
      labels:
        app: todo-api
    spec:
      containers:
      - name: api
        image: todo-api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: todo-api
spec:
  selector:
    app: todo-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer

---
# hpa.yaml (Horizontal Pod Autoscaler)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: todo-api
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: todo-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: todo-api
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.example.com
    secretName: api-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: todo-api
            port:
              number: 80
```

## Helm Chart

```yaml
# Chart.yaml
apiVersion: v2
name: todo-api
version: 1.0.0
appVersion: "1.0.0"

# values.yaml
replicaCount: 3

image:
  repository: todo-api
  tag: "1.0.0"
  pullPolicy: IfNotPresent

service:
  type: LoadBalancer
  port: 80

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: api.example.com
      paths:
        - path: /
          pathType: Prefix
```

## Deploy Commands

```bash
# Apply manifests
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Using Helm
helm install todo-api ./todo-api-chart

# Scale deployment
kubectl scale deployment todo-api --replicas=5

# Update image
kubectl set image deployment/todo-api api=todo-api:1.1.0

# View logs
kubectl logs -f deployment/todo-api

# Exec into pod
kubectl exec -it pod/todo-api-xxx -- /bin/bash
```

## Best Practices

✅ **Resource Limits**: Always set CPU/memory limits
✅ **Health Checks**: Liveness and readiness probes
✅ **Auto-scaling**: HPA for dynamic scaling
✅ **Secrets**: Use Kubernetes secrets, not env vars
✅ **RBAC**: Least privilege access
✅ **Monitoring**: Prometheus + Grafana
✅ **Logging**: Centralized logging (ELK/Loki)

---

## Docker Containerization (Phase 4 Learnings)

### Backend Dockerfile (FastAPI/Python)

```dockerfile
# Multi-stage build for Python/FastAPI
FROM python:3.13-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 -s /bin/bash appuser
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile (Next.js/Node)

```dockerfile
# Multi-stage build for Next.js
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 1001 -S nodejs && adduser -S -u 1000 -G nodejs appuser
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME="0.0.0.0"
COPY --from=builder --chown=appuser:nodejs /app/public ./public
COPY --from=builder --chown=appuser:nodejs /app/.next/standalone ./
COPY --from=builder --chown=appuser:nodejs /app/.next/static ./.next/static
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD wget -q --spider http://localhost:3000/api/health || exit 1
CMD ["node", "server.js"]
```

### Health Endpoint Patterns

**Liveness Probe (Backend):**
```python
@router.get("/health")
async def health_check():
    """Liveness probe - is the service running?"""
    return {"status": "healthy"}
```

**Readiness Probe (Backend):**
```python
@router.get("/ready")
async def readiness_check(session: Session = Depends(get_session)):
    """Readiness probe - is the service ready?"""
    try:
        session.exec(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {str(e)}")
```

**Frontend Health Endpoint (Next.js App Router):**
```typescript
// app/api/health/route.ts
import { NextResponse } from 'next/server'
export async function GET() {
  return NextResponse.json({ status: 'healthy' })
}
```

### Next.js Standalone Output

**Required for Docker:**
```javascript
// next.config.mjs
const nextConfig = {
  output: 'standalone',  // Required for Docker
  // ... other config
}
```

### Docker Compose

```yaml
services:
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    restart: unless-stopped

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      backend:
        condition: service_healthy
```

### Containerization Checklist

- [ ] Multi-stage build (builder → production)
- [ ] Non-root user (UID 1000)
- [ ] HEALTHCHECK instruction
- [ ] .dockerignore file (exclude node_modules, __pycache__, .git, .env)
- [ ] Image size < 500MB
- [ ] Expose correct ports
- [ ] Environment variables for secrets (not hardcoded)
- [ ] Liveness probe (/health - simple, no DB)
- [ ] Readiness probe (/ready - checks DB)

---

**Status:** Active
**Priority:** 🔴 High (Production deployment)
**Version:** 1.1.0 (Phase 4 Learnings Added)
