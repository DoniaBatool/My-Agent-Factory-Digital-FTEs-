---
name: chatbot-endpoint
description: Create stateless chat endpoint with conversation history management and AI agent integration (project)
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

Implement a **stateless** chat endpoint that:
- persists messages and conversations
- loads recent history for context
- runs intent detection + AI agent + tool calls
- returns a clean user-facing response

## Required Properties

- **Stateless server**: every request must include `conversation_id` (or create one)
- **User isolation**: conversation/message access scoped to authenticated user
- **Persistence**: save user message + assistant response (and tool_calls metadata)
- **Deterministic tool use**: for actions (add/update/delete/complete), prefer tool calls over free-form text

## Recommended API Shape

- `POST /api/chat` (body: message, conversation_id?)
- `GET /api/conversations` (list)
- `GET /api/conversations/{id}/messages` (history)
- `DELETE /api/conversations/{id}` and `DELETE /api/conversations` (cleanup)

## Workflow

### Phase 1: Request Handling
- Authenticate user
- Resolve conversation (create or verify ownership)
- Append user message to DB

### Phase 2: Decision Layer
- Run intent detector on current message + recent history
- If intent needs clarification/confirmation, ask a question (do not execute tool)

### Phase 3: Execution
- Call MCP tools for task actions
- Collect tool results in structured form for audit/history

### Phase 4: Response + Persistence
- Produce final response (human-friendly, concise)
- Save assistant message + tool_calls to DB

## Edge Cases

- Partial titles → ask for disambiguation
- Updates without fields → ask “what to update?”
- Time parsing/timezone formatting clarity
- Duplicate send / retry idempotency (avoid double-creates)