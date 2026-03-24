---
name: harness-next
description: Start the next coding session in an autonomous agent harness
---

# Next Coding Session

Start a new coding session in your autonomous agent harness project.

## Session Protocol

This will:

1. **Orient** - Read Archon session notes and git history
2. **Verify** - Run health checks on completed features
3. **Select** - Choose highest priority TODO task
4. **Implement** - Write code for one feature
5. **Test** - Run tests and verify functionality
6. **Review** - Code quality check
7. **Handoff** - Update Archon and commit cleanly

---

## Before Starting

Ensure:
- [ ] Harness is initialized (ran `/harness-init` at least once)
- [ ] Archon MCP is accessible
- [ ] Development environment is ready

---

## Session Execution

### 1. Get Bearings

```bash
pwd
cat .harness/config.json 2>/dev/null || echo "No harness config"
```

### 2. Query Archon

```python
# Get project tasks
tasks = find_tasks(filter_by="project", filter_value=PROJECT_ID)

# Get session notes
notes = find_documents(project_id=PROJECT_ID, query="Session Notes")
```

### 3. Check for In-Progress Work

If a task is in "doing" status, continue it rather than starting new.

### 4. Select Next Task

Highest `task_order` value among TODO tasks.

### 5. Implement & Test

Write code, run tests, fix issues.

### 6. Update & Handoff

Update Archon tasks and session notes, commit to git.

---

## Task Selection Priority

Tasks are selected by:

1. **In Progress First**: Continue any task in "doing" status
2. **Highest Priority**: Select by `task_order` (higher = more important)
3. **Feature Grouping**: Prefer tasks in same feature as recent work
4. **Dependencies**: Skip tasks blocked by incomplete prerequisites

---

## Session Workflow

```
/harness-next
    |
    v
[Read Archon context]
    |
    v
[Check for in-progress task]
    |
    +--[Yes]--> [Continue task]
    |
    +--[No]---> [Select next TODO]
                    |
                    v
            [Update status to "doing"]
                    |
                    v
            [Implement feature]
                    |
                    v
            [Run tests]
                    |
                    +--[Fail]--> [Fix issues]
                    |
                    +--[Pass]--> [Update to "done"]
                                      |
                                      v
                              [Commit changes]
                                      |
                                      v
                              [Update session notes]
                                      |
                                      v
                              [Report summary]
```

---

## Expected Output

At session end, you'll see:

```markdown
## Session Complete

### Task Completed
**Feature**: User Authentication
**Task**: Implement login endpoint
**Status**: Done

### Changes Made
- `src/auth/login.ts` - Created login handler
- `src/auth/jwt.ts` - Added token generation
- `tests/auth/login.test.ts` - Added tests

### Test Results
- 12 tests passed
- 0 tests failed
- Coverage: 85%

### Progress
- 13/45 tasks complete (29%)
- Next: Implement logout endpoint

### Git
- Branch: main
- Commit: abc123 "feat(auth): implement login endpoint"
```

---

## Arguments

$ARGUMENTS

Beginning coding session...
