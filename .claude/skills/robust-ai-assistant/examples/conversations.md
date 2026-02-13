# Conversation Examples

## Example 1: Basic Task Creation

```
User: add task to buy milk
Assistant: I'll add "buy milk" as a new task. What priority should it be?
          (high/medium/low)

User: medium
Assistant: Got it - medium priority. When should this be done by?
          (e.g., "tomorrow", "next Friday", "no deadline")

User: tomorrow at 5pm
Assistant: Would you like to add a description?

User: no
Assistant: ✅ Task created successfully!
          Task #42: Buy milk
          🟡 Medium priority
          📅 Due: Tomorrow at 5:00 PM
```

## Example 2: All-at-Once Task Creation

```
User: add urgent task to call client by Friday with description follow up on proposal
Assistant: ✅ Task created successfully!
          Task #43: Call client
          🔴 High priority (detected: urgent)
          📅 Due: Friday at 11:59 PM
          Description: Follow up on proposal
```

## Example 3: Task Update by ID

```
User: update task 42
Assistant: Here's Task #42:
          • Title: Buy milk
          • Priority: 🟡 Medium
          • Due: Tomorrow at 5:00 PM
          • Status: ⏳ Pending

          What would you like to change?

User: make it high priority and add description get 2% milk
Assistant: I'll make these changes to Task #42:
          • Priority: medium → high
          • Description: (none) → "Get 2% milk"

          Confirm changes? (yes/no)

User: yes
Assistant: ✅ Task #42 updated successfully!
          • Priority: 🔴 High
          • Description: Get 2% milk
```

## Example 4: Task Update by Name

```
User: update the milk task
Assistant: Found Task #42: "Buy milk" (85% match)

          • Title: Buy milk
          • Priority: 🔴 High
          • Due: Tomorrow at 5:00 PM

          What would you like to change?

User: change the deadline to next Monday
Assistant: I'll update Task #42:
          • Due: Tomorrow at 5:00 PM → Monday at 11:59 PM

          Confirm? (yes/no)

User: yes
Assistant: ✅ Task #42 deadline updated to Monday, February 3.
```

## Example 5: Task Deletion

```
User: delete task 42
Assistant: Are you sure you want to delete this task?

          Task #42: Buy milk
          🔴 High priority | 📅 Due: Monday

          ⚠️ This action cannot be undone.

          Delete this task? (yes/no)

User: yes
Assistant: ✅ Task #42 deleted successfully.
```

## Example 6: Delete by Name with Fuzzy Match

```
User: delete the grocery task
Assistant: Found Task #42: "Buy milk" (72% match)

          Is this the task you want to delete? (yes/no)

User: no
Assistant: No problem, I'll keep that task. Is there another task you're looking for?

User: the one about groceries
Assistant: I found Task #15: "Get groceries from store" (88% match)

          Delete this task? (yes/no)

User: yes
Assistant: ✅ Task #15 deleted.
```

## Example 7: List Tasks

```
User: show my tasks
Assistant: 📋 You have 5 tasks:

          🔴 HIGH PRIORITY
          ⏳ #43: Call client - 📅 Due: Friday

          🟡 MEDIUM PRIORITY
          ⏳ #44: Review code - 📅 Due: In 3 days
          ⏳ #45: Send email - 📅 Due: Tomorrow

          🟢 LOW PRIORITY
          ⏳ #46: Organize desk
          ✅ #47: Read article - Done!
```

## Example 8: List with Filter

```
User: show high priority tasks
Assistant: 📋 High priority tasks (1):

          ⏳ #43: Call client
             📅 Due: Friday at 5:00 PM
             📝 Follow up on proposal

User: show completed tasks
Assistant: 📋 Completed tasks (1):

          ✅ #47: Read article
             Completed on Jan 28, 2026
```

## Example 9: Complete Task

```
User: mark task 44 as complete
Assistant: ✅ Task #44 completed!
          "Review code" is now marked as done.

User: actually, uncomplete it
Assistant: ✅ Task #44 marked as pending.
          "Review code" is back on your to-do list.
```

## Example 10: Natural Language Completion

```
User: I finished calling the client
Assistant: Great! I found Task #43: "Call client"

          ✅ Task #43 marked as complete!
```

## Example 11: Cancellation

```
User: add task to organize files
Assistant: I'll add "organize files" as a new task. What priority?

User: actually, cancel
Assistant: No problem, I've cancelled adding that task.
          Is there something else I can help with?
```

## Example 12: Intent Switch Mid-Workflow

```
User: add task to buy groceries
Assistant: I'll add "buy groceries". What priority?

User: wait, show my tasks first
Assistant: 📋 You have 3 tasks:
          ⏳ #43: Call client (🔴 high)
          ⏳ #44: Review code (🟡 medium)
          ✅ #47: Read article (🟢 low)

          Would you like to continue adding "buy groceries"?

User: yes, make it low priority
Assistant: Got it - low priority. When should this be done?

User: no deadline
Assistant: Any description?

User: no
Assistant: ✅ Task created!
          Task #48: Buy groceries (🟢 low priority)
```

## Example 13: Date Validation

```
User: add task to submit report by yesterday
Assistant: That date appears to be in the past.
          When would you like this task to be due?
          (e.g., "tomorrow", "next week", "January 30")

User: by end of week
Assistant: Got it - due Friday. Any description?

User: no
Assistant: ✅ Task created!
          Task #49: Submit report
          🟡 Medium priority | 📅 Due: Friday
```

## Example 14: Priority Auto-Detection

```
User: add urgent task to fix production bug
Assistant: ✅ Task created!
          Task #50: Fix production bug
          🔴 High priority (detected from "urgent")

          Would you like to set a deadline?

User: in 2 hours
Assistant: ✅ Deadline set for 2 hours from now.
```

## Example 15: Empty Task List

```
User: show my tasks
Assistant: 📋 You don't have any tasks yet!

          Would you like to add one? Just say something like:
          "add task to buy groceries"
```
