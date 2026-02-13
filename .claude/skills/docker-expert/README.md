---
name: docker-expert
description: Complete Docker management - Build, run, optimize, and troubleshoot containers with production best practices
---

# Docker Expert - Quick Start

**One-command Docker management - No Docker specialist needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites

```bash
python3 scripts/tool.py check-prerequisites
```

**Output:**
```
==> Checking Docker Prerequisites
✓ Docker installed: Docker version 24.0.6
✓ Docker daemon is running
✓ Docker Compose installed: Docker Compose version v2.23.0
✓ Docker BuildKit available: github.com/docker/buildx v0.12.0

✅ All Docker prerequisites satisfied
```

### 2. Build Optimized Image

```bash
python3 scripts/tool.py build-image \
  --image-name myapp:latest \
  --dockerfile Dockerfile
```

**Output:**
```
==> Building Docker Image: myapp:latest
ℹ Using Dockerfile: Dockerfile
ℹ Running: DOCKER_BUILDKIT=1 docker build -f Dockerfile -t myapp:latest .
[+] Building 45.2s (12/12) FINISHED
✅ Image built successfully: myapp:latest
ℹ Image size: 125MB
```

### 3. Run Container

```bash
python3 scripts/tool.py run-container \
  --image-name myapp:latest \
  --container-name myapp \
  --ports 8080:8080 \
  --env-file .env
```

**Output:**
```
==> Running Container: myapp
✅ Container started: a3f5d2b1c9e4
ℹ Container status:
CONTAINER ID   IMAGE          STATUS         PORTS                    NAMES
a3f5d2b1c9e4   myapp:latest   Up 2 seconds   0.0.0.0:8080->8080/tcp   myapp
```

### 4. Start Multi-Container App

```bash
python3 scripts/tool.py compose-up \
  --compose-file docker-compose.yml \
  --build
```

**Output:**
```
==> Starting Docker Compose Application
ℹ Using compose file: docker-compose.yml
✅ Compose application started
ℹ Services status:
NAME      IMAGE           STATUS         PORTS
app       myapp:latest    Up 5 seconds   0.0.0.0:8080->8080/tcp
postgres  postgres:15     Up 5 seconds   5432/tcp
redis     redis:7-alpine  Up 5 seconds   6379/tcp
```

### 5. Optimize Dockerfile

```bash
python3 scripts/tool.py optimize --dockerfile Dockerfile
```

**Output:**
```
==> Analyzing Dockerfile for Optimization
✓ Using multi-stage build
✓ .dockerignore file exists
⚠️  Found 3 issues:
  • Line 8: Add --no-install-recommends to apt-get install
  • Line 15: Using :latest tag: FROM node:latest
  • Running as root user (security risk)

💡 Recommendations (2):
  • Pin specific image versions (e.g., node:18-alpine)
  • Add USER directive to run as non-root
```

### 6. Comprehensive Testing

```bash
python3 scripts/tool.py test
```

**Output:**
```
==> Docker Comprehensive Testing

[Test 1/6] Docker Installation
✓ Docker installed: Docker version 24.0.6

[Test 2/6] Docker Daemon
✓ Docker daemon running

[Test 3/6] Docker Compose
✓ Docker Compose available: v2.23.0

[Test 4/6] Docker Networking
✓ Docker networking functional

[Test 5/6] Docker Storage
✓ Docker storage functional

[Test 6/6] Image Pull Test
✓ Can pull images from Docker Hub

==> Test Summary
Total tests: 6
Passed: 6
Failed: 0

✅ All Docker tests passed!
```

### 7. Troubleshoot Issues

```bash
python3 scripts/tool.py troubleshoot
```

**Output:**
```
==> Docker Troubleshooting

[Check 1] Docker Daemon Status
✓ Docker daemon running

[Check 2] Disk Space
TYPE       TOTAL    ACTIVE   RECLAIMABLE
Images     2.5GB    1.2GB    1.3GB (52%)
Containers 150MB    100MB    50MB (33%)

[Check 3] Dangling Images
⚠ Found 5 dangling images
Fix: Run 'docker image prune -f'

[Check 4] Stopped Containers
⚠ Found 3 stopped containers
Fix: Run 'docker container prune -f'

[Check 5] Unused Networks
✓ No unused networks

[Check 6] Unused Volumes
⚠ Found 2 unused volumes
Fix: Run 'docker volume prune -f'
```

### 8. Cleanup Resources

```bash
python3 scripts/tool.py cleanup --all --force
```

**Output:**
```
==> Docker Cleanup
Current disk usage:
TYPE       TOTAL    ACTIVE   RECLAIMABLE
Images     2.5GB    1.2GB    1.3GB (52%)

🔄 Cleaning up...
Deleted Images:
deleted: sha256:abc123...
Total reclaimed space: 1.3GB

✅ Cleanup complete

New disk usage:
TYPE       TOTAL    ACTIVE   RECLAIMABLE
Images     1.2GB    1.2GB    0B (0%)
```

---

## 💡 Common Workflows

### Workflow 1: Local Development

```bash
# 1. Check setup
python3 scripts/tool.py check-prerequisites

# 2. Build image with development target
python3 scripts/tool.py build-image \
  --image-name myapp:dev \
  --target development \
  --build-args NODE_ENV=development

# 3. Run with hot reload
python3 scripts/tool.py run-container \
  --image-name myapp:dev \
  --container-name myapp-dev \
  --ports 8080:8080,9229:9229 \
  --volumes $(pwd):/app \
  --env NODE_ENV=development
```

### Workflow 2: Production Deployment

```bash
# 1. Optimize Dockerfile
python3 scripts/tool.py optimize --dockerfile Dockerfile

# 2. Build production image with multi-stage
python3 scripts/tool.py build-image \
  --image-name myapp:1.0.0 \
  --target production \
  --no-cache

# 3. Run comprehensive tests
python3 scripts/tool.py test

# 4. Run with production settings
python3 scripts/tool.py run-container \
  --image-name myapp:1.0.0 \
  --container-name myapp-prod \
  --ports 80:8080 \
  --env-file .env.production \
  --restart always \
  --memory 512m \
  --cpus 1
```

### Workflow 3: Multi-Container Stack

```bash
# 1. Start all services
python3 scripts/tool.py compose-up \
  --compose-file docker-compose.yml \
  --build \
  --remove-orphans

# 2. Check health
docker compose ps

# 3. View logs
docker compose logs -f app

# 4. Scale service
docker compose up -d --scale worker=3
```

### Workflow 4: Image Optimization

```bash
# 1. Analyze current Dockerfile
python3 scripts/tool.py optimize --dockerfile Dockerfile

# 2. Apply recommendations (manually edit Dockerfile)
# - Use multi-stage builds
# - Use alpine base images
# - Combine RUN commands
# - Add .dockerignore
# - Run as non-root user

# 3. Build optimized image
python3 scripts/tool.py build-image \
  --image-name myapp:optimized \
  --dockerfile Dockerfile

# 4. Compare sizes
docker images | grep myapp
```

### Workflow 5: Maintenance & Cleanup

```bash
# 1. Check for issues
python3 scripts/tool.py troubleshoot

# 2. View disk usage
docker system df

# 3. Cleanup (interactive)
python3 scripts/tool.py cleanup

# 4. Aggressive cleanup (non-interactive)
python3 scripts/tool.py cleanup --all --force

# 5. Verify
docker system df
```

---

## 🆘 Troubleshooting

### Issue 1: Docker daemon not running

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Fix:**
```bash
# macOS: Start Docker Desktop
open -a Docker

# Linux: Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

### Issue 2: Permission denied

**Symptoms:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Fix:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
# Or use:
newgrp docker
```

### Issue 3: Build fails with "no space left on device"

**Symptoms:**
```
ERROR: failed to solve: write /var/lib/docker/tmp/...: no space left on device
```

**Fix:**
```bash
# Cleanup unused resources
python3 scripts/tool.py cleanup --all --force

# Or use Docker commands directly
docker system prune -a --volumes -f
```

### Issue 4: Container exits immediately

**Symptoms:**
```
Container started but exits with code 0 or 1
```

**Fix:**
```bash
# Check logs
docker logs <container-name>

# Run interactively to debug
docker run -it myapp:latest /bin/sh

# Check if main process is running
docker inspect <container-name>
```

### Issue 5: Port already in use

**Symptoms:**
```
Bind for 0.0.0.0:8080 failed: port is already allocated
```

**Fix:**
```bash
# Find process using port
lsof -i :8080
# Or
netstat -tulpn | grep :8080

# Kill process or use different port
python3 scripts/tool.py run-container \
  --image-name myapp:latest \
  --ports 8081:8080
```

### Issue 6: Image too large

**Problem:** Image is 2GB+ (should be <200MB for simple apps)

**Fix:**
```bash
# 1. Analyze Dockerfile
python3 scripts/tool.py optimize --dockerfile Dockerfile

# 2. Use multi-stage builds
# 3. Use alpine base images (node:18-alpine, python:3.11-alpine)
# 4. Combine RUN commands
# 5. Remove dev dependencies in production stage
# 6. Add .dockerignore file
```

---

## ✨ Features

- ✅ No Docker expertise required
- ✅ Multi-stage build optimization
- ✅ BuildKit integration for faster builds
- ✅ Docker Compose orchestration
- ✅ Automated Dockerfile analysis
- ✅ Comprehensive testing (6+ tests)
- ✅ Edge case handling (30+ scenarios)
- ✅ Production-ready configurations
- ✅ Resource cleanup automation
- ✅ Security best practices
- ✅ Layer caching strategies
- ✅ Image size optimization
- ✅ Token-efficient
- ✅ Test-Driven Development approach

---

## 📚 Docker Best Practices

### 1. Multi-Stage Builds

```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 8080
USER node
CMD ["node", "dist/main.js"]
```

### 2. Layer Caching

```dockerfile
# ✅ CORRECT: Dependencies change less frequently
COPY package*.json ./
RUN npm install
COPY . .

# ❌ WRONG: Invalidates cache on any file change
COPY . .
RUN npm install
```

### 3. Use .dockerignore

```
node_modules/
npm-debug.log
.git/
.env*
*.md
tests/
```

### 4. Run as Non-Root

```dockerfile
FROM node:18-alpine
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
WORKDIR /app
```

### 5. Pin Versions

```dockerfile
# ✅ CORRECT
FROM node:18.19.0-alpine3.19

# ❌ WRONG
FROM node:latest
```

---

## 🎯 Advanced Usage

### Build with BuildKit

```bash
# Enable BuildKit (faster builds, better caching)
export DOCKER_BUILDKIT=1

python3 scripts/tool.py build-image \
  --image-name myapp:latest \
  --dockerfile Dockerfile
```

### Multi-Platform Builds

```bash
# Build for multiple architectures
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:latest \
  --push .
```

### Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD curl -f http://localhost:8080/health || exit 1
```

### Build Arguments

```bash
python3 scripts/tool.py build-image \
  --image-name myapp:latest \
  --build-args NODE_ENV=production,VERSION=1.0.0
```

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**No Docker specialist needed!** 🚀
**Based on official Docker documentation** 📚
