---
name: observability-apm
description: Implement Application Performance Monitoring (APM), distributed tracing, and observability using tools like OpenTelemetry, Prometheus, Grafana, and Jaeger.
---

# Observability & APM Skill

## Purpose
Implement comprehensive observability for production systems with monitoring, logging, and tracing.

## The Three Pillars

### 1. Logs (What happened)
### 2. Metrics (How much/how many)
### 3. Traces (Where time was spent)

## Implementation

### OpenTelemetry Setup (FastAPI)
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

# Setup tracing
trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

# Instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

# Custom tracing
tracer = trace.get_tracer(__name__)

@app.get("/tasks")
async def get_tasks():
    with tracer.start_as_current_span("fetch_tasks"):
        tasks = await db.fetch_tasks()

        with tracer.start_as_current_span("process_tasks"):
            result = process(tasks)

        return result
```

### Metrics (Prometheus)
```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    with request_duration.time():
        response = await call_next(request)

    request_count.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()

    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Observability Stack

```
Application → OpenTelemetry → Backend (Jaeger/Tempo)
           → Prometheus       → Grafana (Dashboards)
           → Structured Logs  → Loki/ELK
```

## Key Metrics to Track

### Application Metrics
- Request rate (requests/second)
- Error rate (errors/second)
- Response time (p50, p95, p99)
- Database query time
- Cache hit rate

### Business Metrics
- User signups
- Task completions
- API usage per user
- Feature adoption

### Infrastructure Metrics
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

## Alerting Rules

```yaml
# Prometheus alert rules
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, http_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "95th percentile response time > 1s"
```

## Grafana Dashboard

```json
{
  "title": "API Performance",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }
      ]
    }
  ]
}
```

## Best Practices

✅ **Structured Logging**: Use JSON format
✅ **Correlation IDs**: Track requests across services
✅ **Sampling**: Sample traces in high-traffic systems
✅ **SLOs**: Define Service Level Objectives
✅ **Runbooks**: Document how to respond to alerts

---

**Status:** Active
**Priority:** 🔴 Critical (Production monitoring essential)
**Version:** 1.0.0
**Category:** Monitoring & Observability
