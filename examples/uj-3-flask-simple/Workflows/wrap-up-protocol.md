# Phase Wrap-Up Protocol

Apply this when completing phases, features, or fixes. Evidence before claims, always.

## Before Calling Work Complete

### 1. Run Verification Commands (Show Output)

- Run tests: show "X/X pass" (not "tests should pass")
- Run linter: show "0 errors" (not "linter looks clean")
- Run build: show "exit 0" (not "build probably works")
- Test manually: follow actual steps, show results

### 2. Verify Objectives

- Read requirements/plan line by line
- Check each objective off with evidence
- If any incomplete, state what remains

### 3. Update Documentation

- README status section - what works now
- Any testing docs if new features added
- Spec/plan if implementation differed

### 4. Proactive Completion Signal

Say explicitly: "Let's wrap up [Phase/Feature X]"

### 5. Walk Through Testing

Concrete steps: "Click X, you should see Y"
Not vague: "test the feature"

### 6. Wait for Confirmation

Never proceed to next phase without user sign-off.

### 7. Memory Sweep

Ask: "What did I learn this session that future sessions need to know?"

Check:
- [ ] Any gotchas discovered? -> Add to AGENTS.md
- [ ] Any patterns that worked well? -> Add to AGENTS.md
- [ ] Any divergence from spec? -> Update spec with decision + rationale
- [ ] Any new capabilities? -> Update README
- [ ] Any new testing needed? -> Document

Don't let hard-won knowledge die with this session.

### 8. Commit Readiness

- Suggest clear commit message
- Verify all changed files included
- Check no temporary/debug code remains

## Red Flags - Never Say

- "Should work now"
- "Tests passed" (without showing output)
- "Phase complete, moving to Phase X" (without confirmation)

## Scale to Work Size

- **Big phases**: Full checklist
- **Small tasks**: Abbreviated but still intentional
- **Always**: Verify it works and signal completion clearly

## Why This Matters

- Prevents building on broken foundations
- Maintains documentation accuracy
- Creates natural stopping points
- Ensures we can return to working state
- Makes each phase independently valuable
