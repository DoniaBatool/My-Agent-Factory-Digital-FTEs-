---
name: microservices-patterns
description: Implement proven microservices patterns including Circuit Breaker, Saga, API Gateway, Service Mesh, and event-driven communication.
---

# Microservices Patterns Skill

## Purpose
Implement resilient microservices architecture using proven patterns.

## Core Patterns

### 1. Circuit Breaker
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_external_service():
    # If fails 5 times, circuit opens for 60 seconds
    response = await http_client.get("https://api.example.com")
    return response.json()
```

### 2. Saga Pattern (Distributed Transactions)
```python
# Choreography-based saga
async def create_order_saga(order):
    # Step 1: Reserve inventory
    inventory_reserved = await inventory_service.reserve(order.items)
    if not inventory_reserved:
        return {"status": "failed", "reason": "inventory"}

    # Step 2: Process payment
    payment_success = await payment_service.charge(order.total)
    if not payment_success:
        await inventory_service.release(order.items)  # Compensate
        return {"status": "failed", "reason": "payment"}

    # Step 3: Create shipment
    await shipment_service.create(order)
    return {"status": "success"}
```

### 3. API Gateway
- Single entry point for all clients
- Authentication/authorization
- Rate limiting
- Request routing
- Response aggregation

### 4. Service Discovery
```python
# Consul service registration
from consul import Consul

consul = Consul()
consul.agent.service.register(
    name="task-service",
    service_id="task-service-1",
    address="localhost",
    port=8001,
    check={
        "http": "http://localhost:8001/health",
        "interval": "10s"
    }
)
```

### 5. Event-Driven Communication
```python
# Publish events
async def on_task_created(task):
    await event_bus.publish("task.created", {
        "task_id": task.id,
        "user_id": task.user_id
    })

# Subscribe to events
@event_bus.subscribe("task.created")
async def send_notification(event):
    await notification_service.send(event["user_id"], "Task created!")
```

## Best Practices

✅ **Database per Service**: Each service owns its data
✅ **Async Communication**: Use message queues
✅ **Fault Tolerance**: Circuit breakers, retries, timeouts
✅ **Observability**: Distributed tracing
✅ **Versioning**: API versioning for backward compatibility

---

**Status:** Active
**Priority:** 🔴 High (Scalable architecture)
**Version:** 1.0.0
