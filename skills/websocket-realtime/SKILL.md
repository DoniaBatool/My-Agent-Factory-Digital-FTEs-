---
name: websocket-realtime
description: Implement WebSocket connections for real-time bidirectional communication, live updates, chat applications, and real-time dashboards.
---

# WebSocket & Real-time Communication Skill

## Purpose
Enable real-time bidirectional communication between client and server.

## FastAPI WebSocket Implementation

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, Set

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id].remove(websocket)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Process message
            await handle_message(user_id, data)
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

# Send real-time updates
async def on_task_created(task):
    await manager.send_to_user(task.user_id, {
        "type": "task_created",
        "data": task.dict()
    })
```

## Client-Side (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user-123');

ws.onopen = () => {
    console.log('Connected');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'task_created') {
        updateUI(message.data);
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('Disconnected');
    // Implement reconnection logic
};

// Send message
ws.send(JSON.stringify({
    type: 'create_task',
    data: { title: 'New task' }
}));
```

## Use Cases

1. **Chat Applications**: Real-time messaging
2. **Live Dashboards**: Real-time metrics
3. **Notifications**: Instant updates
4. **Collaborative Editing**: Multiple users editing
5. **Live Feed**: Social media-style updates

## Best Practices

✅ **Heartbeat**: Ping/pong to keep connection alive
✅ **Reconnection**: Auto-reconnect on disconnect
✅ **Authentication**: Validate user on connection
✅ **Rate Limiting**: Prevent message flooding
✅ **Message Queue**: Buffer messages during disconnect

---

**Status:** Active
**Priority:** 🟡 Medium (Real-time UX)
**Version:** 1.0.0
