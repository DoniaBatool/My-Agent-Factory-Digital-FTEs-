---
name: conversation-manager
description: Manage conversation state in database with message history, user isolation, and efficient querying (project)
---


## 🚀 Expert-Level Automation (Upgraded)

**Upgraded:** 2026-02-11

**Automation Added:** 8 commands in `scripts/tool.py`



## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Purpose

Provide reliable conversation persistence and retrieval:
- list conversations (with latest message preview)
- load messages (paginated / limited)
- delete a conversation or delete all for a user
- ensure strict user isolation

## Data Model Expectations

- `Conversation`: id, user_id, title/metadata, timestamps
- `Message`: id, conversation_id, role, content, tool_calls (optional), timestamps

## Workflow

### Phase 1: Query Design
- Index `conversation.user_id`, `message.conversation_id`, and timestamps
- Prefer “latest message per conversation” queries for sidebar lists

### Phase 2: API Endpoints
- List conversations (user-scoped)
- Get conversation messages (user-scoped)
- Delete one / delete all (user-scoped, cascade messages)

### Phase 3: History Strategy
- Return recent N messages for chat context
- Store assistant tool_calls for debugging/auditing

## Edge Cases

- Conversation exists but no messages yet
- Large histories → pagination or last-N strategy
- Deleting conversations must not leak cross-user data

## Deliverables

- [ ] Conversation CRUD with user isolation
- [ ] Efficient list query (latest message preview)
- [ ] Message pagination/limit support