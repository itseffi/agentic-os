---
name: tdd
description: Test-driven development - write failing test first, then minimal code. Use before implementing any feature or bugfix.
---

# Test-Driven Development (TDD)

Use when implementing any feature or bugfix, before writing implementation code.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Delete means delete

## Red-Green-Refactor

### RED - Write Failing Test
Write one minimal test showing what should happen.
- One behavior
- Clear name
- Real code (no mocks unless unavoidable)

### Verify RED - Watch It Fail
**MANDATORY. Never skip.**
- Run the test, confirm it fails (not errors)
- Failure message is expected
- Test passes? You're testing existing behavior. Fix test.

### GREEN - Minimal Code
Write simplest code to pass the test.
- Just enough to pass
- No extra features
- Don't add behavior beyond the test

### Verify GREEN - Watch It Pass
**MANDATORY.**
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)

### REFACTOR - Clean Up
After green only:
- Remove duplication
- Improve names
- Extract helpers
Keep tests green. Don't add behavior.

## Why Order Matters

**"I'll write tests after"**
Tests written after pass immediately. Passing immediately proves nothing. Test-first forces you to see the test fail, proving it actually tests something.

**"Tests after achieve same goals"**
No. Tests-after answer "What does this do?" Tests-first answer "What should this do?"

**"Deleting X hours of work is wasteful"**
Sunk cost fallacy. The time is gone. The waste is keeping code you can't trust.

## Red Flags - STOP and Start Over

- Code before test
- Test after implementation
- Test passes immediately
- "I already manually tested it"
- "Tests after achieve the same purpose"
- "This is different because..."

**All mean: Delete code. Start over with TDD.**

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "TDD will slow me down" | TDD faster than debugging later. |

## Verification Checklist

Before marking work complete:
- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)

Can't check all boxes? You skipped TDD. Start over.

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
