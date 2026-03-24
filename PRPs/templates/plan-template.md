# Implementation Plan Template

Use this template for creating detailed implementation plans from PRDs or for medium-sized features.

---

[Home](../../README.md) > [PRPs](../README.md) > [Plans](./) > {Feature Name}

# Implementation Plan: {Feature Name}

> **PRD**: [{PRD Title}](../prds/{prd-filename}.prd.md) *(if applicable)*
> **Phase**: {N} of {Total} | **Status**: Ready
> **Estimated Duration**: {X days/weeks} | **Complexity**: Low/Medium/High
> **Archon Project**: {project-id}

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Codebase Context](#codebase-context)
- [Implementation Steps](#implementation-steps)
- [Code Patterns to Follow](#code-patterns-to-follow)
- [Testing Requirements](#testing-requirements)
- [Validation Commands](#validation-commands)
- [Rollback Plan](#rollback-plan)
- [Archon Task Checklist](#archon-task-checklist)
- [Handoff Notes](#handoff-notes)

---

## Overview

### Summary

{One paragraph describing what this plan accomplishes}

### Goal

{Clear statement of the primary goal}

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| {Item} | {Item} |
| {Item} | {Item} |
| {Item} | {Item} |

### Success Criteria

- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}
- [ ] All validation commands pass
- [ ] No regressions in existing tests

---

## Prerequisites

### Pre-Implementation Checklist

- [ ] PRD reviewed and approved (if applicable)
- [ ] Codebase context loaded
- [ ] Dependencies identified and available
- [ ] Environment variables configured
- [ ] Local development environment ready

### Dependencies

| Dependency | Version | Status | Installation |
|------------|---------|--------|--------------|
| {Package} | {Version} | Installed/To Install | `{install command}` |
| {Package} | {Version} | Installed/To Install | `{install command}` |

### Environment Variables

```bash
# Add to .env if not present
{VAR_NAME}={description or example value}
{VAR_NAME}={description or example value}
```

### Infrastructure Requirements

- [ ] {Requirement 1}
- [ ] {Requirement 2}

---

## Codebase Context

### Existing Patterns

#### Pattern 1: {Pattern Name}

```{language}
// SOURCE: {file}:{lines}
// COPY THIS PATTERN:
{actual code snippet from codebase}
```

**When to use**: {Description of when this pattern applies}

#### Pattern 2: {Pattern Name}

```{language}
// SOURCE: {file}:{lines}
// COPY THIS PATTERN:
{actual code snippet from codebase}
```

**When to use**: {Description of when this pattern applies}

### Error Handling Pattern

```{language}
// SOURCE: {file}:{lines}
// COPY THIS PATTERN:
{actual code snippet from codebase}
```

### Logging Pattern

```{language}
// SOURCE: {file}:{lines}
// COPY THIS PATTERN:
{actual code snippet from codebase}
```

### File Structure

```
{relevant_directory}/
├── {file/folder}      # {Purpose}
├── {file/folder}      # {Purpose}
├── {NEW_FILE}         # NEW - {Purpose}
└── {MODIFIED_FILE}    # UPDATE - {What's changing}
```

### Mandatory Reading

**CRITICAL: Read these files before starting any task:**

| Priority | File | Lines | Why Read This |
|----------|------|-------|---------------|
| P0 | `{path/to/file}` | {line range} | {Reason - e.g., Pattern to MIRROR} |
| P1 | `{path/to/file}` | {line range} | {Reason - e.g., Types to IMPORT} |
| P2 | `{path/to/file}` | {line range} | {Reason - e.g., Test pattern to FOLLOW} |

---

## Implementation Steps

Execute in order. Each task is atomic and independently verifiable.

### Task 1: {Task Title}

**File**: `{file path}` ({CREATE/UPDATE})
**Archon Task**: `{task-id}` (create if needed)

**Description**:
{What this task accomplishes}

**Implementation**:
```{language}
// {file path}
{code to write or changes to make}
```

**Mirror**: `{file}:{lines}` - follow existing pattern
**Imports**: {what to import}
**Gotcha**: {known issue to avoid}

**Validation**:
```bash
{validation command}
```

**Expected Result**: {What success looks like}

---

### Task 2: {Task Title}

**File**: `{file path}` ({CREATE/UPDATE})
**Archon Task**: `{task-id}` (create if needed)

**Description**:
{What this task accomplishes}

**Implementation**:
```{language}
// {file path}
{code to write or changes to make}
```

**Mirror**: `{file}:{lines}` - follow existing pattern
**Imports**: {what to import}
**Gotcha**: {known issue to avoid}

**Validation**:
```bash
{validation command}
```

**Expected Result**: {What success looks like}

---

### Task 3: {Task Title}

**File**: `{file path}` ({CREATE/UPDATE})
**Archon Task**: `{task-id}` (create if needed)

**Description**:
{What this task accomplishes}

**Implementation**:
```{language}
// {file path}
{code to write or changes to make}
```

**Mirror**: `{file}:{lines}` - follow existing pattern
**Imports**: {what to import}
**Gotcha**: {known issue to avoid}

**Validation**:
```bash
{validation command}
```

**Expected Result**: {What success looks like}

---

### Task 4: {Task Title}

**File**: `{file path}` ({CREATE/UPDATE})
**Archon Task**: `{task-id}` (create if needed)

**Description**:
{What this task accomplishes}

**Implementation**:
```{language}
// {file path}
{code to write or changes to make}
```

**Mirror**: `{file}:{lines}` - follow existing pattern
**Imports**: {what to import}
**Gotcha**: {known issue to avoid}

**Validation**:
```bash
{validation command}
```

**Expected Result**: {What success looks like}

---

## Code Patterns to Follow

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | {convention} | `{example}` |
| Functions | {convention} | `{example}` |
| Classes | {convention} | `{example}` |
| Constants | {convention} | `{example}` |

### Import Order

```{language}
// 1. Standard library
{example}

// 2. Third-party packages
{example}

// 3. Local imports
{example}
```

### Documentation Standards

```{language}
// {example of expected documentation format}
```

---

## Testing Requirements

### Unit Tests to Write

| Test File | Test Cases | Validates |
|-----------|------------|-----------|
| `{test file path}` | {test cases} | {what it validates} |
| `{test file path}` | {test cases} | {what it validates} |

### Test Implementation

```{language}
// {test file path}
{test code example}
```

### Edge Cases Checklist

- [ ] Empty/null inputs
- [ ] Invalid inputs
- [ ] Boundary conditions
- [ ] Error scenarios
- [ ] Authorization failures
- [ ] {Feature-specific edge case}
- [ ] {Feature-specific edge case}

### Integration Tests

```{language}
// {integration test example if needed}
```

---

## Validation Commands

### Level 1: Static Analysis

```bash
{lint/format/type-check commands}
```

**Expected**: Exit 0, no errors

### Level 2: Unit Tests

```bash
{unit test command with coverage}
```

**Expected**: All tests pass, coverage meets threshold

### Level 3: Integration Tests

```bash
{integration test command}
```

**Expected**: All integration tests pass

### Level 4: Full Validation (Run Before PR)

```bash
{complete validation command chain}
```

**Expected**: All checks pass, build succeeds

---

## Rollback Plan

If issues arise after deployment:

### Immediate Rollback

```bash
# Revert the changes
git revert HEAD
```

### Database Rollback

{If applicable, describe database migration rollback}

```bash
{rollback command if applicable}
```

### Cache/State Cleanup

{If applicable, describe any cache or state cleanup needed}

```bash
{cleanup command if applicable}
```

### Feature Flag Fallback

```{language}
// If using feature flags
if (process.env.FEATURE_{NAME}_ENABLED === 'false') {
  // Use old behavior
}
```

---

## Archon Task Checklist

### Creating Tasks

```python
# Create tasks for each implementation step
manage_task("create",
    project_id="{project-id}",
    title="Task 1: {title}",
    description="{description}",
    feature="{feature-label}",
    status="todo"
)
```

### Task Tracking

| Task | Archon ID | Status | Notes |
|------|-----------|--------|-------|
| Task 1: {title} | {task-id} | todo | - |
| Task 2: {title} | {task-id} | todo | - |
| Task 3: {title} | {task-id} | todo | - |
| Task 4: {title} | {task-id} | todo | - |
| Write tests | {task-id} | todo | - |
| Validation | {task-id} | todo | - |

### Updating Status

```python
# Starting a task
manage_task("update", task_id="{task-id}", status="doing")

# Completing a task
manage_task("update", task_id="{task-id}", status="done")
```

---

## Handoff Notes

### Completed Items

- [ ] {Deliverable 1}
- [ ] {Deliverable 2}
- [ ] {Deliverable 3}
- [ ] All tests written and passing
- [ ] Documentation updated

### Known Issues

*Update during implementation*

| Issue | Severity | Workaround | Ticket |
|-------|----------|------------|--------|
| {Issue} | Low/Med/High | {Workaround if any} | {Link} |

### Context for Next Session

Key decisions made:
- {Decision 1}
- {Decision 2}
- {Decision 3}

Files modified:
- `{file path}` - {what changed}
- `{file path}` - {what changed}

### Next Phase (if applicable)

After this plan is complete, proceed to:
- **Phase {N+1}**: {Phase name}
- Command: `/prp-plan "{next phase description}"`

---

## Acceptance Criteria

- [ ] All specified functionality implemented per user story
- [ ] Validation commands pass with exit 0
- [ ] Unit tests cover >= 80% of new code
- [ ] Code mirrors existing patterns exactly
- [ ] No regressions in existing tests
- [ ] Documentation updated
- [ ] Archon tasks marked complete

---

## Completion Checklist

- [ ] All tasks completed in dependency order
- [ ] Each task validated immediately after completion
- [ ] Level 1: Static analysis passes
- [ ] Level 2: Unit tests pass
- [ ] Level 3: Integration tests pass (if applicable)
- [ ] Level 4: Full validation suite passes
- [ ] All acceptance criteria met
- [ ] Implementation report generated
- [ ] Plan moved to `completed/` folder

---

> **Execute this plan**: `/prp-implement PRPs/plans/{plan-filename}.plan.md`

---

*Generated: {timestamp}*
*Last Updated: {timestamp}*
