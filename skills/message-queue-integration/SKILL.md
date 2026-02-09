---
name: message-queue-integration
description: Integrate message queues (RabbitMQ, Kafka, AWS SQS) for async processing, event-driven architecture, and distributed systems communication.
---

# Message Queue Integration Skill

## Purpose
Implement asynchronous message processing using message queues for scalable, decoupled systems.

## When to Use
- Background job processing
- Event-driven architecture
- Microservices communication
- Long-running tasks
- Email/notification sending
- Data pipeline workflows

## Message Queue Options

| Queue | Best For | Pattern |
|-------|----------|---------|
| **RabbitMQ** | General purpose | Pub/Sub, Work queues |
| **Kafka** | Event streaming | Event sourcing, CQRS |
| **AWS SQS** | AWS ecosystem | Simple queues |
| **Redis** | Lightweight | Simple pub/sub |

## Implementation Examples

### RabbitMQ (Python)
```python
import pika
from pydantic import BaseModel

class TaskMessage(BaseModel):
    task_id: str
    user_id: str
    action: str

# Producer
def send_task(message: TaskMessage):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()
    channel.queue_declare(queue='tasks', durable=True)

    channel.basic_publish(
        exchange='',
        routing_key='tasks',
        body=message.json(),
        properties=pika.BasicProperties(delivery_mode=2)  # persistent
    )
    connection.close()

# Consumer
def process_tasks():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()
    channel.queue_declare(queue='tasks', durable=True)

    def callback(ch, method, properties, body):
        message = TaskMessage.parse_raw(body)
        print(f"Processing: {message.task_id}")
        # Do work...
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='tasks', on_message_callback=callback)
    channel.start_consuming()
```

### FastAPI Integration
```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

async def send_email_task(email: str, message: str):
    # Send to queue instead of processing immediately
    await queue.send({
        "type": "email",
        "to": email,
        "body": message
    })

@app.post("/register")
async def register(email: str, background_tasks: BackgroundTasks):
    # ... save user ...

    background_tasks.add_task(send_email_task, email, "Welcome!")
    return {"status": "registered"}
```

## Patterns

### 1. Work Queue (Task Distribution)
```
Producer → Queue → Worker1
                 → Worker2
                 → Worker3
```

### 2. Pub/Sub (Broadcasting)
```
Publisher → Exchange → Queue1 → Consumer1
                     → Queue2 → Consumer2
```

### 3. Event Sourcing
```
Event → Kafka Topic → Consumer1 (update read model)
                    → Consumer2 (send notification)
                    → Consumer3 (analytics)
```

## Best Practices

✅ **Idempotency**: Handle duplicate messages
✅ **Dead Letter Queue**: Handle failed messages
✅ **Retry Logic**: Exponential backoff
✅ **Monitoring**: Track queue depth, processing time
✅ **Ordering**: Use partition keys when order matters

## Use Cases

1. **Email Sending**: Queue emails, process async
2. **Image Processing**: Queue uploads, resize async
3. **Report Generation**: Queue requests, generate async
4. **Event Broadcasting**: Publish events, multiple consumers
5. **Data Sync**: Queue changes, sync to multiple destinations

---

**Status:** Active
**Priority:** 🔴 High (Scalability essential)
**Version:** 1.0.0
**Category:** Async Processing
