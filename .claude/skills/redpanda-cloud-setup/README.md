---
name: redpanda-cloud-setup
description: Complete Redpanda Cloud Kafka setup with aiokafka integration for Python FastAPI event-driven applications
---

# Redpanda Cloud Setup - Quick Start

**One-command Kafka - No Kafka expertise needed!**

## 🚀 Quick Usage

### 1. Check Prerequisites
```bash
python3 scripts/tool.py check-prerequisites
```

### 2. Create Topics for Phase 5
```bash
python3 scripts/tool.py create-topics \
  --topics task-events,reminders,task-updates
```

###3. Generate Producer Code
```bash
python3 scripts/tool.py generate-producer \
  --output src/events/producer.py
```

### 4. Generate Consumer Code
```bash
python3 scripts/tool.py generate-consumer \
  --topic reminders \
  --output services/notification/consumer.py
```

### 5. Test Connection
```bash
python3 scripts/tool.py test-connection
```

---

## ✨ Features

- ✅ No Kafka expertise needed
- ✅ aiokafka async Python client
- ✅ Topic creation automation
- ✅ Producer/Consumer code generation
- ✅ FastAPI integration
- ✅ Event schema validation
- ✅ Production-ready

---

**Last Updated:** 2026-02-11
**Status:** Production-ready ✅
**Perfect for Phase 5 event-driven architecture** 🚀
