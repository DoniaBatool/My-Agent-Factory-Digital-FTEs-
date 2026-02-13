---
name: prometheus-monitoring
description: Complete Prometheus setup - installation, configuration, scrape targets, exporters, and metrics collection
---

# Prometheus Monitoring - Quick Start

**Complete metrics collection - No Prometheus expert needed!**

## 🚀 Quick Usage

### 1. Install Prometheus + Node Exporter
```bash
python3 tool.py install
```

### 2. Configure Scrape Target
```bash
python3 tool.py configure-scrape \
  --job-name node \
  --targets localhost:9100
```

### 3. Query Metrics
```bash
python3 tool.py query-metrics \
  --query "rate(node_cpu_seconds_total[5m])"
```

### 4. Run Tests
```bash
python3 tool.py test
```

---

## 💡 Common Workflows

### Workflow 1: Full Monitoring Stack (Prometheus + Node Exporter + Grafana)
```bash
# Install Prometheus and Node Exporter
python3 tool.py install

# Configure scrape target
python3 tool.py configure-scrape \
  --job-name node \
  --targets localhost:9100

# Query metrics
python3 tool.py query-metrics --query "up"

# Access Prometheus: http://localhost:9090
```

### Workflow 2: Multi-Target Monitoring
```bash
# Add web server
python3 tool.py configure-scrape \
  --job-name web \
  --targets web1:9100,web2:9100

# Add database
python3 tool.py configure-scrape \
  --job-name database \
  --targets db1:9100,db2:9100

# Reload Prometheus
kill -HUP $(pidof prometheus)
```

---

## 🆘 Troubleshooting

### Issue 1: "Prometheus not installed"
**Fix:** `python3 tool.py install`

### Issue 2: "Port 9090 not accessible"
**Fix:** `systemctl start prometheus`

### Issue 3: "No metrics available"
**Fix:** Check targets at http://localhost:9090/targets

---

## ✨ Features

- ✅ No Prometheus expert needed
- ✅ Install + Configure in minutes
- ✅ Node Exporter included
- ✅ PromQL query support
- ✅ 5-test suite
- ✅ Pull-based metrics
- ✅ Official Prometheus patterns

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Sources:** [Prometheus Docs](https://prometheus.io/docs/), [Getting Started](https://prometheus.io/docs/prometheus/latest/getting_started/), [Node Exporter Guide](https://prometheus.io/docs/guides/node-exporter/)
