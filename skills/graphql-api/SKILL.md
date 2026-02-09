---
name: graphql-api
description: Implement GraphQL API with schema design, resolvers, queries, mutations, subscriptions, and integration with existing REST APIs.
---

# GraphQL API Skill

## Purpose
Provide flexible, efficient API alternative to REST with client-specified data fetching.

## Schema Definition

```python
import strawberry
from typing import List, Optional

@strawberry.type
class Task:
    id: str
    title: str
    description: Optional[str]
    status: str
    user_id: str

@strawberry.type
class User:
    id: str
    email: str
    tasks: List[Task]

@strawberry.input
class CreateTaskInput:
    title: str
    description: Optional[str]

@strawberry.type
class Query:
    @strawberry.field
    async def task(self, id: str) -> Optional[Task]:
        return await task_service.get_task(id)

    @strawberry.field
    async def tasks(self, status: Optional[str] = None) -> List[Task]:
        return await task_service.list_tasks(status)

    @strawberry.field
    async def user(self, id: str) -> Optional[User]:
        return await user_service.get_user(id)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_task(self, input: CreateTaskInput) -> Task:
        return await task_service.create_task(input)

    @strawberry.mutation
    async def update_task(self, id: str, title: str) -> Task:
        return await task_service.update_task(id, title)

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def task_created(self) -> Task:
        async for task in task_service.watch_tasks():
            yield task

# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation, subscription=Subscription)
```

## FastAPI Integration

```python
from strawberry.fastapi import GraphQLRouter

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")
```

## Client Queries

```graphql
# Query with specific fields
query GetTasks {
  tasks(status: "pending") {
    id
    title
    status
  }
}

# Query with nested data
query GetUserWithTasks {
  user(id: "123") {
    email
    tasks {
      id
      title
    }
  }
}

# Mutation
mutation CreateTask {
  createTask(input: {title: "New task"}) {
    id
    title
  }
}

# Subscription
subscription TaskCreated {
  taskCreated {
    id
    title
  }
}
```

## Benefits Over REST

✅ **No Over-fetching**: Client requests only needed fields
✅ **No Under-fetching**: Single request for multiple resources
✅ **Strong Typing**: Schema-based type system
✅ **Introspection**: Self-documenting API
✅ **Real-time**: Built-in subscription support

---

**Status:** Active
**Priority:** 🟡 Medium (Alternative to REST)
**Version:** 1.0.0
