---
name: grafana-expert
description: Complete A-Z Grafana management - installation, dashboards, datasources, alerting, provisioning, and visualization
---

# Grafana Expert - Quick Start

**A-Z Grafana automation - No Grafana expert needed!**

## 🚀 Quick Usage

### 1. Install Grafana
```bash
python3 tool.py install
```

### 2. Check Prerequisites
```bash
python3 tool.py check-prerequisites
```

### 3. Setup Datasource (Prometheus)
```bash
python3 tool.py setup-datasource \
  --name Prometheus \
  --type prometheus \
  --url http://localhost:9090 \
  --default
```

### 4. Create Dashboard
```bash
python3 tool.py create-dashboard \
  --name "System Metrics" \
  --tags "monitoring,system" \
  --query "up"
```

### 5. Setup Provisioning (Infrastructure as Code)
```bash
python3 tool.py provision \
  --include-datasources \
  --include-dashboards
```

### 6. Configure Alerting
```bash
python3 tool.py configure-alerting \
  --alert-name "High CPU" \
  --condition gt \
  --threshold 80 \
  --check-interval 60
```

---

## 💡 Common Workflows

### Workflow 1: Complete Setup (Grafana + Prometheus)
```bash
# Install Grafana
python3 tool.py install

# Wait for service to start
sleep 5

# Add Prometheus datasource
python3 tool.py setup-datasource \
  --name Prometheus \
  --type prometheus \
  --url http://localhost:9090 \
  --default

# Create monitoring dashboard
python3 tool.py create-dashboard \
  --name "Infrastructure Monitoring" \
  --query "rate(node_cpu_seconds_total[5m])"

# Access: http://localhost:3000 (admin/admin)
```

### Workflow 2: Infrastructure as Code (Provisioning)
```bash
# Setup provisioning directories
python3 tool.py provision \
  --include-datasources \
  --include-dashboards

# Edit files:
# - /etc/grafana/provisioning/datasources/*.yaml
# - /etc/grafana/provisioning/dashboards/*.yaml

# Restart to apply
sudo systemctl restart grafana-server
```

---

## 🆘 Troubleshooting

### Issue 1: "Grafana not installed"
**Fix:**
```bash
python3 tool.py install
```

### Issue 2: "Port 3000 not accessible"
**Fix:**
```bash
# Check firewall
sudo ufw allow 3000

# Check service
sudo systemctl status grafana-server
```

### Issue 3: "Cannot add datasource"
**Fix:**
```bash
# Verify Grafana is running
curl http://localhost:3000/api/health

# Check default credentials
curl -u admin:admin http://localhost:3000/api/org
```

---

## ✨ Features

- ✅ No Grafana expert needed
- ✅ A-Z handling (install → dashboards → alerts)
- ✅ Multiple datasources (Prometheus, InfluxDB, MySQL, Postgres)
- ✅ Provisioning support (Infrastructure as Code)
- ✅ API & file-based configuration
- ✅ 6-test suite
- ✅ 30+ edge cases handled
- ✅ Based on official Grafana docs (2026)

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Official Docs:** [grafana.com/docs](https://grafana.com/docs/grafana/latest/)
