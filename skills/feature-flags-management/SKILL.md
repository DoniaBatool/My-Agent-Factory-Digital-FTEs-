---
name: feature-flags-management
description: Implement feature flags for gradual rollouts, A/B testing, canary releases, and safe production deployments without code changes.
---

# Feature Flags Management Skill

## Purpose
Enable/disable features dynamically without deploying code, supporting gradual rollouts and A/B testing.

## Implementation

```python
from enum import Enum
from pydantic import BaseModel

class FeatureFlag(str, Enum):
    NEW_UI = "new_ui"
    BETA_FEATURE = "beta_feature"
    AI_CHATBOT = "ai_chatbot"

class FeatureFlagService:
    def __init__(self, redis_client):
        self.redis = redis_client

    def is_enabled(self, flag: FeatureFlag, user_id: str = None) -> bool:
        # Global flag check
        global_enabled = self.redis.get(f"flag:{flag}")
        if global_enabled == "false":
            return False

        # User-specific override
        if user_id:
            user_flag = self.redis.get(f"flag:{flag}:user:{user_id}")
            if user_flag == "true":
                return True

        # Percentage rollout
        rollout_pct = int(self.redis.get(f"flag:{flag}:rollout") or 100)
        user_hash = hash(user_id) % 100 if user_id else 0
        return user_hash < rollout_pct

# Usage
feature_flags = FeatureFlagService(redis)

@app.get("/tasks")
async def get_tasks(user_id: str = Depends(get_current_user)):
    tasks = await task_service.get_tasks(user_id)

    if feature_flags.is_enabled(FeatureFlag.AI_CHATBOT, user_id):
        # New AI-enhanced feature
        tasks = await ai_service.enhance_tasks(tasks)

    return tasks
```

## Use Cases

### 1. Gradual Rollout
```python
# Start with 10% of users
redis.set("flag:new_ui:rollout", 10)

# Increase to 50%
redis.set("flag:new_ui:rollout", 50)

# Full rollout
redis.set("flag:new_ui:rollout", 100)
```

### 2. Beta Testing
```python
# Enable for specific users
redis.set("flag:beta_feature:user:user-123", "true")
```

### 3. Emergency Kill Switch
```python
# Disable immediately
redis.set("flag:problematic_feature", "false")
```

## Best Practices

✅ **Cleanup**: Remove old flags after full rollout
✅ **Documentation**: Document what each flag controls
✅ **Monitoring**: Track flag usage
✅ **Default Values**: Safe defaults when flag service fails

---

**Status:** Active
**Priority:** 🟡 Medium (Modern deployment)
**Version:** 1.0.0
