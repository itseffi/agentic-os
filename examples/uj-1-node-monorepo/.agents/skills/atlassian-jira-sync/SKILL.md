---
name: atlassian-jira-sync
description: Sync Jira issues with local tasks. Use during daily planning or when user asks about Jira issues.
---

# Jira Issue Sync

Check Jira for assigned issues and sync with local task management.

## Instructions

### Step 1: Fetch Assigned Issues

Call `jira_search` with JQL:
```
assignee = currentUser() AND status != Done ORDER BY priority DESC
```

### Step 2: Compare with Local Tasks

Check `Tasks/` for existing files with Jira references:
- Look for `jira_key` in YAML frontmatter
- Identify new issues not yet in Tasks/

### Step 3: Present Summary

```
Jira Issues (8 active):

**Blockers/Critical**
- PROJ-123: Production bug in auth [In Progress]

**High Priority**
- PROJ-124: API rate limiting [To Do]
- PROJ-125: Update deployment docs [In Review]

**Normal**
- PROJ-126: Refactor logging [Backlog]

3 issues not yet in local Tasks. Create them?
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
title: [Issue summary]
category: technical
priority: [Map from Jira priority]
status: n
jira_key: PROJ-XXX
---
```

## Priority Mapping

| Jira | Personal OS |
|------|-------------|
| Blocker | P0 |
| Critical | P0 |
| High | P1 |
| Medium | P2 |
| Low | P3 |

## Example Flow

**User:** "What should I work on today?"

**Agent:**
1. Fetches Jira issues
2. Compares with local tasks
3. "You have 5 Jira tickets..."
4. Offers to create local tasks
5. Continues with planning

## Notes

- Keep `jira_key` in frontmatter for bidirectional sync
- Update Jira status when local task completes
- Include Jira link in task context section

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
