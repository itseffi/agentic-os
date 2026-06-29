---
name: linear-issue-sync
description: Sync Linear issues with local tasks. Use during daily planning or when user asks about Linear issues.
---

# Linear Issue Sync

Check Linear for assigned issues and sync with local task management.

## Instructions

### Step 1: Fetch Assigned Issues

Call `linear_list_issues` filtered to:
- Assigned to current user
- Status not "Done" or "Canceled"

### Step 2: Compare with Local Tasks

Check `Tasks/` for existing files with Linear references:
- Look for `linear_id` in YAML frontmatter
- Identify new issues not yet in Tasks/

### Step 3: Present Summary

```
Linear Issues (5 active):

**High Priority**
- LIN-123: Fix authentication timeout [In Progress]
- LIN-124: Update API documentation [Todo]

**Normal Priority**  
- LIN-125: Refactor user service [Backlog]

2 issues not yet in local Tasks. Create them?
```

### Step 4: Sync Options

| Option | Description |
|--------|-------------|
| Create all | Add all new issues as local tasks |
| Select specific | Choose which to sync |
| Skip | Continue without syncing |

### Step 5: Create Local Tasks

For each issue to sync, create task file:

```yaml
---
title: [Issue title]
category: technical
priority: [Map from Linear priority]
status: n
linear_id: LIN-XXX
---
```

## Example Flow

**User:** "What should I work on today?"

**Agent:**
1. Fetches Linear issues
2. Compares with local tasks
3. "You have 3 new Linear issues..."
4. Offers to create local tasks
5. Continues with planning

## Notes

- Map Linear priorities to P0-P3
- Keep `linear_id` in frontmatter for bidirectional sync
- Update Linear status when local task completes

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
