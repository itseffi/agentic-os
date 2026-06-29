---
name: davci
description: Define clear decision rights - Decider, Approver, Veto, Consulted, Informed. Use when clarifying who decides.
---

# DAVCI Decision Rights

Define clear decision rights using the DAVCI framework.

## When to Use

When you need to clarify who decides, approves, and must be consulted on a decision.

## The Framework

| Role | Definition | Rules |
|------|------------|-------|
| **D - Decider** | Single person accountable for outcome | Exactly one per decision |
| **A - Approver** | Can override the Decider | Optional; cannot be the D |
| **V - Veto** | Can block for specific domain | One per domain; time-boxed |
| **C - Consulted** | Has input before decision | Keep to 5 or fewer |
| **I - Informed** | Needs to know after decision | Keep targeted |

## The Process

### 1. Define the Decision Object

Be specific about what's being decided:
- Clear title
- Concrete deadline
- Decision type (Strategy, Scope, Design, Technical, Process, Risk, Commercial)

### 2. Assign Roles

**Decider (D):**
- Who is accountable for the outcome?
- Must be one person only

**Approver (A):**
- Does D need air cover for risk/budget/politics?
- If yes, name person one level up

**Veto (V):**
- Which domains apply? (Security, Legal, Privacy, Brand, Compliance)
- One person per domain
- Set veto window (default: 48 hours)

**Consulted (C):**
- Who has unique information to improve the decision?
- Cap at 5; merge by role if needed

**Informed (I):**
- Who must act after or needs awareness?
- Keep targeted to those who need it

### 3. Add Decision Metadata

- **Deadline:** Date and time
- **Escalation:** If blocked 24h, escalate to whom?
- **Success test:** One checkable sentence
- **Comms plan:** Channel, audience, timing

## Output Format

```
Decision: [title]
Deadline: [date/time]
Type: [Strategy/Scope/Design/Technical/Process/Risk/Commercial]

D: [name, role]
A: [name, role] or None
V: [Domain - name, window hours]
C: [role/name]; [role/name]
I: [role/name]; [role/name]

Escalation: [name, role]
Success test: [single checkable sentence]
Comms: [channel + audience + timing]
```

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
