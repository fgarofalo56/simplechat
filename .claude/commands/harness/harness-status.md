---
name: harness-status
description: Check the status of an autonomous agent harness project
---

# Harness Status Report

Get a comprehensive status report for your autonomous agent harness project.

## What This Shows

### Progress Overview
- Total tasks vs completed
- Progress percentage
- Estimated sessions remaining

### Task Board

```
TODO        DOING       REVIEW      DONE
--------    --------    --------    --------
Task A      Task B                  Task C
Task D                              Task E
Task F                              Task G
```

### Session History
- Last 5 sessions with summaries
- Tasks completed per session
- Blockers encountered

### Health Checks
- [ ] Tests passing
- [ ] Environment working
- [ ] No stale "doing" tasks
- [ ] Git status clean

### Blockers
- Active blockers from session notes
- Failed tests
- Stale tasks

---

## Status Report Generation

Query Archon and local files:

```python
# Get project info
project = find_projects(project_id=PROJECT_ID)

# Get all tasks
tasks = find_tasks(filter_by="project", filter_value=PROJECT_ID)

# Get session notes
notes = find_documents(project_id=PROJECT_ID, query="Session Notes")
```

```bash
# Check test status
npm test / pytest / dotnet test

# Check git status
git status --porcelain
```

---

## Expected Output

```markdown
## Harness Status: [Project Name]

### Progress
- **Total Tasks**: 45
- **Completed**: 12 (27%)
- **In Progress**: 1
- **Remaining**: 32

### Task Board

| Status | Count | Tasks |
|--------|-------|-------|
| TODO | 32 | Auth, API, ... |
| DOING | 1 | User profile |
| REVIEW | 0 | - |
| DONE | 12 | Setup, DB, ... |

### Health Checks

| Check | Status |
|-------|--------|
| Tests | Pass (45/45) |
| Build | Pass |
| Git | Clean |
| Stale Tasks | None |

### Recent Sessions

| # | Date | Tasks | Duration |
|---|------|-------|----------|
| 5 | Today | User settings | 45min |
| 4 | Yesterday | Profile API | 1hr |
| 3 | Jan 20 | Auth refresh | 30min |

### Blockers

None currently.

### Next Steps

Run `/harness-next` to continue development.
```

---

## Quick Commands After Status

| Situation | Command |
|-----------|---------|
| Ready to continue | `/harness-next` |
| Has blockers | Fix blockers first |
| Tests failing | Run test suite manually |
| Need review | Review latest changes |

---

## Arguments

$ARGUMENTS

Checking harness project status...
