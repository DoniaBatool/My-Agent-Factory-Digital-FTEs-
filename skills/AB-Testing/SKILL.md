---
name: AB-Testing
description: A/B testing framework for validating features, AI agent responses, and user experience variations (project)
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This skill creates A/B testing infrastructure to validate Phase 3 features before full deployment.

### 1. Create A/B Test Framework

**File: `backend/src/testing/ab_test_framework.py`**

```python
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
import hashlib

class Variant(str, Enum):
    """A/B test variants"""
    CONTROL = "control"
    VARIANT_A = "variant_a"
    VARIANT_B = "variant_b"

class ABTest(BaseModel):
    """A/B test configuration"""
    name: str
    description: str
    variants: Dict[Variant, Any]
    traffic_split: Dict[Variant, float]  # e.g., {CONTROL: 0.5, VARIANT_A: 0.5}

class ABTestRunner:
    """Execute A/B tests with consistent user assignment"""

    def assign_variant(self, user_id: str, test_name: str, test: ABTest) -> Variant:
        """
        Consistently assign user to variant based on hash

        Args:
            user_id: User identifier
            test_name: Test name for consistent hashing
            test: A/B test configuration

        Returns:
            Assigned variant
        """
        # Hash user_id + test_name for consistent assignment
        hash_input = f"{user_id}:{test_name}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        percentage = (hash_value % 100) / 100.0

        # Assign based on traffic split
        cumulative = 0.0
        for variant, split in test.traffic_split.items():
            cumulative += split
            if percentage < cumulative:
                return variant

        return Variant.CONTROL

    def get_variant_config(self, variant: Variant, test: ABTest) -> Any:
        """Get configuration for assigned variant"""
        return test.variants[variant]
```

### 2. Create A/B Tests for Phase 3 Features

**File: `specs/[feature]/ab-tests/agent-response-style.md`**

```markdown
# A/B Test: Agent Response Style

## Hypothesis
More conversational responses increase user engagement vs. brief confirmations.

## Variants

### Control (50% traffic)
- Brief, direct confirmations
- Example: "Task added."

### Variant A (50% traffic)
- Conversational, friendly responses
- Example: "Great! I've added 'Buy milk' to your task list."

## Success Metrics
- User retention rate
- Messages per session
- Task completion rate

## Implementation

\`\`\`python
test = ABTest(
    name="agent_response_style",
    description="Test conversational vs brief responses",
    variants={
        Variant.CONTROL: {"style": "brief"},
        Variant.VARIANT_A: {"style": "conversational"}
    },
    traffic_split={Variant.CONTROL: 0.5, Variant.VARIANT_A: 0.5}
)
\`\`\`
```

### 3. Create A/B Test Integration

**File: `backend/src/api/chat_with_ab_test.py`**

```python
from ..testing.ab_test_framework import ABTestRunner, ABTest, Variant

# Define A/B test
response_style_test = ABTest(
    name="agent_response_style",
    description="Test response styles",
    variants={
        Variant.CONTROL: {"style": "brief"},
        Variant.VARIANT_A: {"style": "conversational"}
    },
    traffic_split={Variant.CONTROL: 0.5, Variant.VARIANT_A: 0.5}
)

@router.post("/api/{user_id}/chat")
async def chat_with_ab_test(user_id: str, request: ChatRequest):
    """Chat endpoint with A/B testing"""

    # Assign user to variant
    runner = ABTestRunner()
    variant = runner.assign_variant(user_id, "agent_response_style", response_style_test)
    config = runner.get_variant_config(variant, response_style_test)

    # Modify agent instructions based on variant
    if config["style"] == "conversational":
        agent_instructions = "Be friendly and conversational"
    else:
        agent_instructions = "Be brief and direct"

    # Run agent with variant-specific instructions
    # ...

    # Log variant assignment for analysis
    await log_ab_test_event(
        user_id=user_id,
        test_name="agent_response_style",
        variant=variant
    )

    return response
```

### 4. Create A/B Test Analytics

**File: `backend/src/testing/ab_analytics.py`**

```python
from sqlmodel import Session, select
from typing import Dict
import statistics

class ABAnalytics:
    """Analyze A/B test results"""

    async def get_test_results(self, test_name: str) -> Dict:
        """
        Calculate A/B test metrics

        Returns:
            {
                "control": {"metric1": value, "metric2": value},
                "variant_a": {"metric1": value, "metric2": value},
                "statistical_significance": True/False
            }
        """
        # Query test events and user metrics
        # Calculate conversion rates, engagement, etc.
        # Run statistical significance test (chi-square, t-test)
        pass

    async def should_graduate_variant(self, test_name: str) -> bool:
        """
        Determine if variant should be promoted to production

        Criteria:
        - Statistically significant improvement (p < 0.05)
        - No regression in key metrics
        - Minimum sample size reached (e.g., 1000 users per variant)
        """
        pass
```

### 5. Create A/B Test Documentation

**File: `docs/ab-testing-guide.md`**

```markdown
# A/B Testing Guide

## Running A/B Tests

1. Define hypothesis in `specs/[feature]/ab-tests/`
2. Create test configuration in code
3. Deploy with traffic split
4. Monitor metrics for 7-14 days
5. Analyze results with statistical significance
6. Graduate winning variant or rollback

## Active Tests

| Test Name | Start Date | Variants | Traffic Split | Status |
|-----------|------------|----------|---------------|--------|
| agent_response_style | 2025-12-30 | Control vs Conversational | 50/50 | Active |

## Best Practices

- Minimum 1000 users per variant
- Run for at least 7 days
- Monitor key metrics: retention, engagement, task completion
- Use statistical significance (p < 0.05) for decisions
```

### 6. Display A/B Test Summary

```text
✅ A/B Testing Framework Created

📁 Files Generated:
  - backend/src/testing/ab_test_framework.py
  - backend/src/testing/ab_analytics.py
  - specs/[feature]/ab-tests/agent-response-style.md
  - docs/ab-testing-guide.md

🧪 Test Capabilities:
  ✓ Consistent user-to-variant assignment
  ✓ Multiple variants support
  ✓ Traffic splitting configuration
  ✓ Statistical significance analysis
  ✓ Automated variant graduation

📋 Next Steps:
  1. Define A/B test hypothesis
  2. Implement variant configurations
  3. Deploy with traffic split
  4. Monitor metrics for 7-14 days
  5. Analyze and graduate winning variant
```

## Success Criteria

- [ ] Framework supports multiple variants
- [ ] User assignment is consistent
- [ ] Traffic splits configurable
- [ ] Metrics tracked per variant
- [ ] Statistical significance calculated
- [ ] Tests documented with hypothesis

## Notes

- Run A/B tests on critical features before full rollout
- Used after `/sp.implementation` to validate features
- Helps catch edge cases and UX issues
