---
name: slack-message-check
description: Check Slack for important messages and activity. Use during daily planning or when user asks about Slack updates.
---

# Slack Message Check

Check Slack channels for important messages and summarize activity.

## Instructions

### Step 1: List Relevant Channels

Call `slack_list_channels` to see available channels.

### Step 2: Check Priority Channels

For each important channel (determined by user preferences or channel activity):
1. Call `slack_get_channel_history` with limit of 20 messages
2. Filter for messages since last check

### Step 3: Summarize Activity

Present findings to user:

```
Slack activity since yesterday:

**#general** (3 new messages)
- @alice mentioned the deployment schedule

**#engineering** (12 new messages)  
- Discussion about API changes
- @bob asked for review on PR #234

**DMs** (2 unread)
- @carol: Question about meeting time
```

### Step 4: Offer Actions

| Option | Description |
|--------|-------------|
| Create task | Turn a message into a task |
| Reply | Draft a response |
| Mark read | Continue without action |

### Step 5: Continue Daily Flow

After Slack check, continue with normal planning workflow.

## Example Flow

**User:** "What should I work on today?"

**Agent:**
1. Checks Slack for new activity
2. "You have 5 new messages across 2 channels..."
3. Summarizes key items
4. Offers to create tasks from actionable messages
5. Continues with task planning

## Notes

- Focus on actionable messages, not all activity
- Prioritize DMs and mentions over general channel noise
- Respect user's channel preferences if configured

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
