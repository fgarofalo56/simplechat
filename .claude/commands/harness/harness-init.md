---
name: harness-init
description: Run the harness initializer to generate feature tasks from specification
---

# Initialize Harness

Run the initializer to set up the autonomous coding harness from your specification.

## When to Use

Use this **once** after running `/harness-setup`:

1. You've run `/harness-setup` wizard
2. `.harness/config.json` exists
3. Application specification file exists (typically `.harness/spec.md`)
4. Feature tasks need to be generated into `.harness/state.json`

## What Initialization Does

### 1. Read Application Specification

From `.harness/spec.md` (or whichever path is named in `.harness/config.json:spec_path`).

### 2. Generate Feature Tasks

Writes 20-50 detailed tasks into `.harness/state.json` based on the spec:
- Clear acceptance criteria
- Test steps for verification
- Priority ordering (task_order)
- Feature grouping

### 3. Set Up Project Structure

Creates appropriate directories:
```
src/
tests/
docs/
.harness/
```

### 4. Initialize Environment

Runs setup commands for dependencies.

### 5. Initialize Git

Creates initial commit with project structure.

### 6. Create Handoff Notes

Appends a session-1 entry to `.harness/session-notes.md` for the coding agent.

---

## Timing Expectations

This takes 5-15 minutes depending on spec complexity.

The agent is generating detailed tasks - it may appear slow but is working.

---

## After Initialization

When complete, you'll have:
- [ ] Feature tasks in `.harness/state.json` (view with `/harness-status`)
- [ ] Project structure created
- [ ] Git repository initialized
- [ ] Ready for coding sessions

Then run:
```bash
/harness:harness-next   # Start first coding session
```

---

## Task Generation Pattern

Tasks are entries in `.harness/state.json` with this structure:

```json
{
  "id": "task-007",
  "title": "Implement user authentication",
  "description": "## Requirements\n- JWT-based authentication\n- Login/logout endpoints\n- Token refresh mechanism\n\n## Acceptance Criteria\n- [ ] POST /auth/login returns JWT\n- [ ] POST /auth/logout invalidates session\n- [ ] POST /auth/refresh renews token\n\n## Test Steps\n1. Test valid login credentials\n2. Test invalid credentials\n3. Test token expiration",
  "feature": "Authentication",
  "task_order": 90,
  "status": "todo",
  "assignee": "harness-coder"
}
```

---

## Arguments

$ARGUMENTS

Running harness initialization...
