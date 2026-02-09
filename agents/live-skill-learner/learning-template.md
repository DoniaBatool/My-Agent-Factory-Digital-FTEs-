# Learning Capture Template

**Use this template to capture learnings from fixes/corrections**

---

## Basic Information

```yaml
Timestamp: [YYYY-MM-DD HH:MM:SS]
Feature: [Feature name being implemented]
Skill Used: [Which skill was being used]
User Prompt: [Exact user request for fix]
```

---

## Issue Details

```yaml
Issue Description:
  What went wrong: |
    [Detailed description of the error/issue]

  Error message (if any): |
    [Exact error message or symptoms]

  When it occurred: |
    [At what step/stage the issue appeared]
```

---

## Root Cause Analysis

```yaml
Root Cause:
  Why it happened: |
    [Underlying reason for the issue]

  Missing consideration: |
    [What edge case or scenario wasn't initially considered]

  Environment/Context: |
    [Specific conditions that caused the issue]
```

---

## Fix Applied

```yaml
Solution:
  What you changed: |
    [Exact changes made to code/config/setup]

  Files modified: |
    - file1.py: [changes]
    - file2.yml: [changes]

  Commands run: |
    [Any commands executed to fix]

  Code diff: |
    ```diff
    - old code
    + new code
    ```
```

---

## Edge Case Discovered

```yaml
Edge Case:
  Scenario: |
    [Description of the new scenario discovered]

  Conditions: |
    [When/how this scenario occurs]

  Handling: |
    [How the fix handles this scenario]

  Test for it: |
    [How to test for this edge case in future]
```

---

## Skill Update Plan

```yaml
Update Target: [tool.py | README.md | SKILL.md | multiple]

tool.py Updates:
  Function/Method: [function name]
  Change: |
    [What code to add/modify]
  Comment: |
    # Edge case: [scenario]
    # Solution: [fix]

README.md Updates:
  Section: Troubleshooting
  Entry: |
    ### Issue: [issue title]
    **Cause:** [root cause]
    **Fix:** [solution]
    **Added:** [date]

SKILL.md Updates:
  Section: Edge Cases
  Entry: |
    - ✅ [edge case] - [handling]
```

---

## Test Coverage

```yaml
Test Case Needed:
  Test name: test_[scenario]
  Purpose: |
    Verify that [edge case] is handled correctly

  Test steps: |
    1. [step 1]
    2. [step 2]
    3. Assert [expected result]

  Mock/Setup needed: |
    [Any mocking or setup required]
```

---

## Verification

```yaml
Verification:
  Fix tested: [Yes/No]
  Works in: |
    - Development: [Yes/No]
    - Staging: [Yes/No]
    - Production: [Yes/No]

  Regression check: |
    [Any other features affected? Tested?]
```

---

## Future Prevention

```yaml
Prevention:
  How skill prevents this now: |
    [What automation/check was added]

  Early detection: |
    [How to detect this issue earlier if it recurs]

  Documentation: |
    [Where this is now documented]
```

---

## Example: Complete Learning Record

```yaml
# ============================================
# LEARNING RECORD
# ============================================

Timestamp: 2026-02-09 14:30:00
Feature: AWS EKS Cluster Deployment
Skill Used: aws-eks-deploy
User Prompt: "kubectl connection timeout, fix karo"

# Issue Details
Issue Description:
  What went wrong: |
    kubectl commands timing out when connecting to EKS cluster
    Error appears immediately after cluster creation

  Error message: |
    "Unable to connect to the server: dial tcp: i/o timeout"

  When it occurred: |
    After running create-cluster command, during configure-kubectl step

# Root Cause
Root Cause:
  Why it happened: |
    EKS cluster takes time to be fully ready after creation
    kubectl tried to connect before API server was accessible

  Missing consideration: |
    Cluster creation is async - API server readiness not guaranteed

  Environment: |
    Fresh cluster creation, API server still initializing

# Fix Applied
Solution:
  What you changed: |
    Added retry logic with exponential backoff in configure-kubectl
    Wait up to 5 minutes for API server to be ready

  Files modified: |
    - scripts/tool.py: Added retry_with_backoff() function

  Code diff: |
    ```python
    # Added retry logic
    def configure_kubectl_with_retry(cluster_name, region, max_retries=10):
        for i in range(max_retries):
            try:
                return configure_kubectl(cluster_name, region)
            except ConnectionTimeout:
                if i < max_retries - 1:
                    wait_time = 2 ** i  # Exponential backoff
                    print(f"Waiting {wait_time}s for API server...")
                    time.sleep(wait_time)
                else:
                    raise
    ```

# Edge Case
Edge Case:
  Scenario: |
    EKS cluster not immediately ready after creation

  Conditions: |
    Fresh cluster creation
    API server still starting up
    Usually takes 2-3 minutes

  Handling: |
    Retry with exponential backoff (up to 5 minutes)
    Clear progress messages to user
    Eventually timeout if server never responds

  Test for it: |
    Test with freshly created cluster
    Verify connection succeeds within timeout period

# Skill Updates
Update Target: tool.py, README.md, SKILL.md

tool.py Updates:
  Function: configure_kubectl()
  Change: |
    Wrap in retry_with_backoff()
    Add progress messages
    Handle ConnectionTimeout exception
  Comment: |
    # Edge case: API server not immediately ready after cluster creation
    # Solution: Retry with exponential backoff (up to 5 minutes)

README.md Updates:
  Section: Troubleshooting
  Entry: |
    ### Issue: kubectl connection timeout after cluster creation
    **Cause:** API server takes 2-3 minutes to be ready
    **Fix:** Connection now retries automatically with backoff
    **Added:** 2026-02-09

SKILL.md Updates:
  Section: Edge Cases
  Entry: |
    - ✅ API server delayed readiness - Auto-retry with backoff
    - ✅ Fresh cluster connection - Waits up to 5 minutes

# Test Coverage
Test Case Needed:
  Test name: test_configure_kubectl_with_retry
  Purpose: |
    Verify kubectl configuration retries on connection timeout

  Test steps: |
    1. Mock configure_kubectl to fail 3 times, then succeed
    2. Call configure_kubectl_with_retry()
    3. Assert it retries and eventually succeeds
    4. Assert correct backoff delays used

  Mock: |
    Mock configure_kubectl() to raise ConnectionTimeout

# Verification
Verification:
  Fix tested: Yes
  Works in: |
    - Development: Yes (tested with fresh cluster)
    - Connection established within 3 minutes

  Regression: |
    Tested with existing clusters - still works instantly
    No negative impact on fast connections

# Future Prevention
Prevention:
  How skill prevents this now: |
    Automatic retry logic built into configure-kubectl
    Users never see timeout on fresh clusters

  Early detection: |
    If timeout still occurs, clear error message
    Suggests checking AWS console for cluster status

  Documentation: |
    README troubleshooting section
    SKILL edge cases section
    Code comments in tool.py

# ============================================
# END LEARNING RECORD
# ============================================
```

---

## Usage

**By Agent:**
1. Agent detects fix request
2. Monitors your fix process
3. Fills this template automatically
4. Uses it to update skills

**Manual (if needed):**
1. Copy this template
2. Fill in all sections
3. Use to update skill manually
4. Or pass to agent for processing

---

**Remember:** The more detailed the learning capture, the better the skill update! 📝✨
