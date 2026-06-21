---
name: google-calendar-schedule-check
description: Check Google Calendar for today's schedule. Use during daily planning or when user asks about their calendar.
---

# Calendar Schedule Check

Check today's calendar and factor meetings into daily planning.

## Instructions

### Step 1: Fetch Today's Events

Call `calendar_list_events` for today's date range.

### Step 2: Categorize Events

Group events by type:
- **Meetings** - Events with other attendees
- **Focus blocks** - Solo blocked time
- **External** - Events outside work calendar

### Step 3: Calculate Available Time

```
Today's Schedule:

09:00-10:00  Team standup (meeting)
11:00-12:00  1:1 with Sarah (meeting)
14:00-15:00  Focus time (blocked)

Available for deep work:
- 10:00-11:00 (1 hour)
- 12:00-14:00 (2 hours)
- 15:00-17:00 (2 hours)

Total: 5 hours available
```

### Step 4: Factor into Task Planning

When recommending tasks:
- Match task estimated_time to available slots
- Prioritize P0/P1 tasks for longer blocks
- Suggest quick tasks for short gaps

### Step 5: Offer Calendar Actions

| Option | Description |
|--------|-------------|
| Block time | Reserve time for specific task |
| Reschedule | Move a meeting if needed |
| Continue | Proceed with task planning |

## Example Flow

**User:** "What should I work on today?"

**Agent:**
1. Checks calendar
2. "You have 3 meetings today, 5 hours free..."
3. Shows schedule overview
4. Recommends tasks that fit available time
5. Offers to block time for priority tasks

## Notes

- Respect existing focus blocks
- Consider meeting prep time
- Account for lunch/breaks
- Warn if schedule is overloaded

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
