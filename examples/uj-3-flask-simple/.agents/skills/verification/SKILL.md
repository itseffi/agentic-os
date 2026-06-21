---
name: verification
description: Verify before claiming completion. No claims without fresh verification evidence. Use before marking work done.
---

# Verification Before Completion

Use when about to claim work is complete, fixed, or passing.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

Before claiming any status or completion:

1. **IDENTIFY** - What command proves this claim?
2. **RUN** - Execute the FULL command (fresh, complete)
3. **READ** - Full output, check exit code, count failures
4. **VERIFY** - Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. **ONLY THEN** - Make the claim

Skip any step = lying, not verifying.

## What Requires Verification

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check |
| Build succeeds | Build command: exit 0 | Linter passing |
| Bug fixed | Test original symptom: passes | Code changed |
| Phase complete | All objectives verified | Tests passing |
| Task done | Checklist items verified | "I did everything" |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Done!")
- About to commit/push without verification
- Relying on partial verification
- ANY wording implying success without having run verification

## Patterns

**Tests:**
```
OK: [Run test] [See: 34/34 pass] "All tests pass"
BAD: "Should pass now"
```

**Build:**
```
OK: [Run build] [See: exit 0] "Build passes"
BAD: "Linter passed" (linter != compiler)
```

**Task completion:**
```
OK: Re-read requirements -> checklist -> verify each -> report
BAD: "Tests pass, task complete"
```

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Should work now" | Run the verification |
| "I'm confident" | Confidence != evidence |
| "Just this once" | No exceptions |
| "Partial check is enough" | Partial proves nothing |

## The Bottom Line

Run the command. Read the output. Then claim the result.

No shortcuts. Non-negotiable.

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
