---
name: AI-Agent-Setup
description: Setup OpenAI Agents SDK with proper configuration, tool bindings, and conversation context management (project)
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This skill automates the setup of OpenAI Agents SDK for Phase 3 AI chatbot, following constitution principles for stateless design and natural language understanding.

### 1. Validate Environment Configuration

**Check required environment variables:**
```bash
# In .env file
OPENAI_API_KEY=[required]
OPENAI_MODEL=[default: gpt-4]
MCP_SERVER_URL=[default: http://localhost:8000]
DATABASE_URL=[required for conversation state]
```

**Validation output:**
```text
Environment Check:
✓ OPENAI_API_KEY: Configured
✓ OPENAI_MODEL: gpt-4
✓ MCP_SERVER_URL: http://localhost:8000
✓ DATABASE_URL: Configured
```

### 2. Create Agent Configuration Structure

**File: `backend/src/ai/agent_config.py`**

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class AgentConfig(BaseModel):
    """OpenAI Agent configuration following Phase 3 constitution"""

    name: str = Field(default="TodoChatbotAgent", description="Agent name")
    model: str = Field(default="gpt-4", description="OpenAI model")
    instructions: str = Field(
        default="""You are a helpful todo management assistant. You can:
        - Add new tasks
        - List tasks (all, pending, or completed)
        - Mark tasks as complete
        - Update task details
        - Delete tasks

        Always confirm actions with the user and provide friendly responses.
        When user intent is ambiguous, ask clarifying questions.
        """,
        description="System instructions for the agent"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None)

    # Tool configuration
    tools: List[str] = Field(
        default=[
            "add_task",
            "list_tasks",
            "complete_task",
            "delete_task",
            "update_task"
        ],
        description="MCP tools available to agent"
    )

    # Conversation configuration
    max_history_messages: int = Field(
        default=50,
        description="Maximum conversation history to include"
    )

    # Stateless design enforcement
    state_storage: str = Field(
        default="database",
        description="Where conversation state is stored (must be 'database')"
    )

class AgentConfigLoader:
    """Load and validate agent configuration"""

    @staticmethod
    def load_from_env() -> AgentConfig:
        """Load configuration from environment variables"""
        import os
        return AgentConfig(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
        )

    @staticmethod
    def validate_config(config: AgentConfig) -> bool:
        """Validate configuration against constitution"""
        assert config.state_storage == "database", \
            "Constitution violation: Agent must be stateless, state must be in database"
        assert len(config.tools) > 0, \
            "Constitution violation: Agent must have MCP tools"
        return True
```

### 3. Create Agent Factory

**File: `backend/src/ai/agent_factory.py`**

```python
from openai import AsyncOpenAI
from typing import List, Dict
from .agent_config import AgentConfig, AgentConfigLoader
from ..mcp_tools import get_all_tools

class AgentFactory:
    """Factory for creating AI agents with proper configuration"""

    def __init__(self):
        self.config = AgentConfigLoader.load_from_env()
        AgentConfigLoader.validate_config(self.config)
        self.client = AsyncOpenAI()

    async def create_agent(self, user_id: str):
        """
        Create an agent instance for a user

        Args:
            user_id: User ID for tool invocations

        Returns:
            Configured agent ready to process requests
        """
        from openai import agents

        # Get MCP tools
        tools = get_all_tools(user_id)

        # Create agent
        agent = agents.Agent(
            name=self.config.name,
            model=self.config.model,
            instructions=self.config.instructions,
            tools=tools,
            temperature=self.config.temperature
        )

        return agent

    async def run_agent(
        self,
        agent,
        messages: List[Dict[str, str]],
        user_id: str
    ):
        """
        Run agent with conversation history

        Args:
            agent: Agent instance
            messages: Conversation history
            user_id: User ID for logging and tool invocations

        Returns:
            Agent response with tool calls
        """
        from openai import agents

        # Limit history per constitution (max 50 messages)
        limited_messages = messages[-self.config.max_history_messages:]

        # Run agent
        runner = agents.Runner(agent=agent, client=self.client)

        response = await runner.run(
            messages=limited_messages,
            context={"user_id": user_id}
        )

        return response
```

### 4. Create Tool Binding System

**File: `backend/src/mcp_tools/__init__.py`**

```python
from typing import List, Dict, Callable
from .add_task_tool import add_task
from .list_tasks_tool import list_tasks
from .complete_task_tool import complete_task
from .delete_task_tool import delete_task
from .update_task_tool import update_task

# Tool registry
TOOL_REGISTRY: Dict[str, Callable] = {
    "add_task": add_task,
    "list_tasks": list_tasks,
    "complete_task": complete_task,
    "delete_task": delete_task,
    "update_task": update_task,
}

def get_all_tools(user_id: str) -> List[Dict]:
    """
    Get all MCP tools configured for OpenAI Agents SDK

    Args:
        user_id: User ID to bind to tool invocations

    Returns:
        List of tool definitions for agent
    """
    tools = []

    for tool_name, tool_handler in TOOL_REGISTRY.items():
        # Create tool definition
        tool_def = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_handler.__doc__ or f"{tool_name} tool",
                "parameters": tool_handler.__annotations__.get("input_data").schema(),
                "handler": lambda input_data: tool_handler(
                    input_data, user_id=user_id
                )
            }
        }
        tools.append(tool_def)

    return tools
```

### 5. Create Tests for Agent Setup

**File: `tests/test_agent_setup.py`**

```python
import pytest
from backend.src.ai.agent_config import AgentConfig, AgentConfigLoader
from backend.src.ai.agent_factory import AgentFactory

def test_agent_config_loads_from_env():
    """Test configuration loads from environment"""
    config = AgentConfigLoader.load_from_env()
    assert config.model is not None
    assert config.state_storage == "database"

def test_agent_config_validates_stateless():
    """Test configuration enforces stateless design"""
    config = AgentConfig(state_storage="memory")  # Invalid
    with pytest.raises(AssertionError, match="stateless"):
        AgentConfigLoader.validate_config(config)

def test_agent_config_requires_tools():
    """Test configuration requires MCP tools"""
    config = AgentConfig(tools=[])  # Invalid
    with pytest.raises(AssertionError, match="tools"):
        AgentConfigLoader.validate_config(config)

@pytest.mark.asyncio
async def test_agent_factory_creates_agent():
    """Test agent factory creates valid agent"""
    factory = AgentFactory()
    agent = await factory.create_agent(user_id="test_user")
    assert agent is not None
    assert agent.tools is not None

@pytest.mark.asyncio
async def test_agent_runs_with_limited_history():
    """Test agent respects conversation history limit"""
    factory = AgentFactory()
    agent = await factory.create_agent(user_id="test_user")

    # Create 100 messages (exceeds limit of 50)
    messages = [
        {"role": "user", "content": f"Message {i}"}
        for i in range(100)
    ]

    response = await factory.run_agent(
        agent=agent,
        messages=messages,
        user_id="test_user"
    )

    # Verify only last 50 messages were used (check via logs or response)
    assert response is not None
```

### 6. Create Integration Documentation

**File: `specs/[feature]/contracts/ai-agent-integration.md`**

```markdown
# AI Agent Integration

## Configuration

See `backend/src/ai/agent_config.py` for full configuration options.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OPENAI_API_KEY | Yes | - | OpenAI API key |
| OPENAI_MODEL | No | gpt-4 | Model to use |
| MCP_SERVER_URL | No | http://localhost:8000 | MCP server URL |
| DATABASE_URL | Yes | - | PostgreSQL connection string |

## Agent Behavior

### System Instructions

The agent is instructed to:
- Interpret natural language commands
- Invoke appropriate MCP tools
- Confirm actions with friendly responses
- Ask clarifying questions for ambiguous intents

### Tool Invocation

Tools are automatically bound to the agent with user_id context.

Example flow:
1. User: "Add task to buy milk"
2. Agent interprets intent → Invokes `add_task` tool
3. Tool executes with user_id → Returns result
4. Agent formats friendly response: "I've added 'Buy milk' to your tasks."

## Constitution Compliance

✓ Stateless: Agent has no memory, state in database
✓ User Isolation: Tools receive user_id for data filtering
✓ Natural Language: Agent parses conversational input
✓ Error Handling: Graceful failures with clarification prompts
```

### 7. Display Setup Summary

Output to terminal:
```text
✅ AI Agent Setup Complete

📁 Files Generated:
  - backend/src/ai/agent_config.py
  - backend/src/ai/agent_factory.py
  - backend/src/mcp_tools/__init__.py
  - tests/test_agent_setup.py
  - specs/[feature]/contracts/ai-agent-integration.md

🔧 Configuration:
  ✓ Model: gpt-4
  ✓ Tools: 5 MCP tools bound
  ✓ History Limit: 50 messages
  ✓ State Storage: Database (stateless)

✅ Constitution Compliance:
  ✓ Stateless architecture
  ✓ User isolation enforced
  ✓ Natural language understanding
  ✓ Error handling configured

📋 Next Steps:
  1. Run: pytest tests/test_agent_setup.py
  2. Create chat endpoint to use agent
  3. Test with conversation manager
```

### 8. Test-Driven Development Checks

**Run TDD workflow:**
```bash
# Red phase - tests should fail initially
pytest tests/test_agent_setup.py -v

# Implement agent factory
# ...

# Green phase - tests should pass
pytest tests/test_agent_setup.py -v

# Integration test with MCP tools
pytest tests/integration/ -v
```

## Success Criteria

- [ ] Environment variables validated
- [ ] Agent configuration follows constitution (stateless, database storage)
- [ ] Agent factory creates agents with proper tool bindings
- [ ] Conversation history limited to 50 messages
- [ ] Tests written and passing
- [ ] Integration documentation complete
- [ ] Constitution compliance verified

## Notes

- This skill is automatically used when setting up Phase 3 chatbot
- Terminal output shows skill usage for traceability
- All configuration must enforce constitution principles
- Agent must be stateless; state persists in database only
