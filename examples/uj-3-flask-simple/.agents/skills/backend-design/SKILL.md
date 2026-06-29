---
name: backend-design
description: Design backend architecture for implementation with API contracts, data model changes, service boundaries, security, and observability.
---

# Backend Design

Use this skill to design robust backend changes before implementation.

## The Process

### Step 1: Define backend objective

Clarify:
- business objective
- service boundary
- latency/reliability expectations

### Step 2: Define API and contract changes

Specify:
- endpoints/events
- request/response schemas
- error model and status mapping

### Step 3: Define data model and migrations

Document:
- schema changes
- migration strategy
- backward-compatibility approach

### Step 4: Define security and observability

Include:
- authn/authz requirements
- rate limiting/abuse controls
- logging, metrics, tracing
- alerting conditions

### Step 5: Define rollout and verification

Provide:
- phased rollout or feature flags
- rollback strategy
- verification checks and commands

## Output Format

```markdown
# [Feature Name] Backend Design Spec

## Objective
- Goal:
- Service boundary:

## API Contracts
- Endpoint/event definitions:
- Request/response schema:
- Error model:

## Data Model
- Schema changes:
- Migration plan:
- Compatibility notes:

## Security and Reliability
- Authn/authz:
- Abuse controls:
- Reliability constraints:

## Observability
- Logs:
- Metrics:
- Traces:
- Alerts:

## Rollout and Verification
- Rollout plan:
- Rollback plan:
- Verification commands/evidence:
```

## Quality Bar

- Contracts must be explicit and testable
- Migration and rollback must be present for schema changes
- Verification must include observable evidence

## When to Use

Use this skill when the task directly matches the workflow described above.

## When Not to Use

Do not use this skill when the request is unrelated, low-stakes, or better handled by a simpler direct response.
