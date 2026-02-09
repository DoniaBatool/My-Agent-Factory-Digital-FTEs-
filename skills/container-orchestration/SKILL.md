---
name: container-orchestration
description: Implement Kubernetes deployment, scaling, service mesh, and container orchestration for production-grade containerized applications.
---

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

**Status:** Active
**Priority:** 🔴 High (Production deployment)
**Version:** 1.0.0
