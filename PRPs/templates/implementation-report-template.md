# Implementation Report Template

Use this template to document completed implementations for future reference and knowledge sharing.

---

[Home](../../README.md) > [PRPs](../README.md) > [Reports](./) > {Feature Name} Report

# Implementation Report: {Feature Name}

> **Plan**: [{Plan Title}](../plans/{plan-filename}.plan.md) *(if applicable)*
> **PRD**: [{PRD Title}](../prds/{prd-filename}.prd.md) *(if applicable)*
> **Status**: Complete
> **Implemented By**: {name}
> **Implementation Date**: {YYYY-MM-DD}
> **Archon Project**: {project-id}

---

## Table of Contents

- [Summary](#summary)
- [Implementation Overview](#implementation-overview)
- [Files Changed](#files-changed)
- [Tests Added](#tests-added)
- [Validation Results](#validation-results)
- [Deviations from Plan](#deviations-from-plan)
- [Challenges & Solutions](#challenges--solutions)
- [Lessons Learned](#lessons-learned)
- [Follow-up Items](#follow-up-items)
- [Metrics](#metrics)

---

## Summary

### What Was Implemented

{2-3 sentence summary of what was built/changed}

### Business Value Delivered

{What business outcome this implementation enables}

### Technical Achievement

{Key technical accomplishments}

---

## Implementation Overview

### Goals Achieved

| Goal | Status | Notes |
|------|--------|-------|
| {Goal from plan} | Complete/Partial | {Notes} |
| {Goal from plan} | Complete/Partial | {Notes} |
| {Goal from plan} | Complete/Partial | {Notes} |

### Acceptance Criteria Results

| Criterion | Status | Evidence |
|-----------|--------|----------|
| {Criterion} | Pass/Fail | {How verified} |
| {Criterion} | Pass/Fail | {How verified} |
| {Criterion} | Pass/Fail | {How verified} |

### Architecture Changes

{Describe any architectural changes made}

```
{ASCII diagram if applicable}
```

### API Changes (if applicable)

| Endpoint | Method | Change Type | Description |
|----------|--------|-------------|-------------|
| `{endpoint}` | {GET/POST/etc} | New/Modified | {Description} |
| `{endpoint}` | {GET/POST/etc} | New/Modified | {Description} |

### Database Changes (if applicable)

| Table/Collection | Change Type | Description |
|-----------------|-------------|-------------|
| `{table}` | New/Modified | {Description} |
| `{table}` | New/Modified | {Description} |

---

## Files Changed

### New Files

| File | Purpose | Lines |
|------|---------|-------|
| `{path}` | {Purpose} | {count} |
| `{path}` | {Purpose} | {count} |
| `{path}` | {Purpose} | {count} |

### Modified Files

| File | Changes | Lines Changed |
|------|---------|---------------|
| `{path}` | {What changed} | +{added}/-{removed} |
| `{path}` | {What changed} | +{added}/-{removed} |
| `{path}` | {What changed} | +{added}/-{removed} |

### Deleted Files

| File | Reason |
|------|--------|
| `{path}` | {Why removed} |

### Key Code Snippets

#### {Feature/Component Name}

```{language}
// {file}:{lines}
// Key implementation
{code snippet}
```

#### {Feature/Component Name}

```{language}
// {file}:{lines}
// Key implementation
{code snippet}
```

---

## Tests Added

### Unit Tests

| Test File | Test Cases | Coverage |
|-----------|------------|----------|
| `{path}` | {count} | {%} |
| `{path}` | {count} | {%} |

### Integration Tests

| Test File | Scenarios | Status |
|-----------|-----------|--------|
| `{path}` | {count} | Pass |
| `{path}` | {count} | Pass |

### Test Coverage Summary

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Line Coverage | {%} | {%} | {+/-}% |
| Branch Coverage | {%} | {%} | {+/-}% |
| Function Coverage | {%} | {%} | {+/-}% |

### Key Test Cases

```{language}
// {test file}
// Example of important test added
{test code}
```

---

## Validation Results

### Level 1: Static Analysis

```bash
{command run}
```

**Result**: Pass
**Output**:
```
{relevant output}
```

### Level 2: Unit Tests

```bash
{command run}
```

**Result**: Pass
**Summary**: {X} tests passed, {Y} skipped, {Z} failed

### Level 3: Integration Tests

```bash
{command run}
```

**Result**: Pass
**Summary**: {X} tests passed

### Level 4: Full Validation

```bash
{command run}
```

**Result**: Pass
**Build Output**:
```
{relevant output}
```

### Manual Verification

| Scenario | Steps | Result |
|----------|-------|--------|
| {Scenario} | {Brief steps} | Pass |
| {Scenario} | {Brief steps} | Pass |

---

## Deviations from Plan

### Planned vs Actual

| Planned | Actual | Reason |
|---------|--------|--------|
| {What was planned} | {What was done} | {Why the change} |
| {What was planned} | {What was done} | {Why the change} |

### Added Scope

| Item | Reason | Impact |
|------|--------|--------|
| {Item added} | {Why it was needed} | {Effect on timeline/quality} |

### Removed Scope

| Item | Reason | Future Plan |
|------|--------|-------------|
| {Item removed} | {Why removed} | {When/if will be addressed} |

### Timeline Variance

| Phase | Estimated | Actual | Variance |
|-------|-----------|--------|----------|
| {Phase} | {time} | {time} | {+/- time} |
| {Phase} | {time} | {time} | {+/- time} |
| **Total** | {time} | {time} | {+/- time} |

---

## Challenges & Solutions

### Challenge 1: {Challenge Title}

**Problem**:
{Description of the challenge encountered}

**Solution**:
{How it was resolved}

**Code/Config Change**:
```{language}
{relevant code that solved it}
```

### Challenge 2: {Challenge Title}

**Problem**:
{Description of the challenge encountered}

**Solution**:
{How it was resolved}

### Challenge 3: {Challenge Title}

**Problem**:
{Description of the challenge encountered}

**Solution**:
{How it was resolved}

---

## Lessons Learned

### What Worked Well

1. **{Topic}**: {Explanation}
2. **{Topic}**: {Explanation}
3. **{Topic}**: {Explanation}

### What Could Be Improved

1. **{Topic}**: {Explanation and suggestion}
2. **{Topic}**: {Explanation and suggestion}

### Patterns Discovered

{New patterns that emerged during implementation}

```{language}
// Pattern that should be reused
{code example}
```

### Documentation Gaps Identified

- {Gap 1}: {What was missing}
- {Gap 2}: {What was missing}

### Process Improvements

- {Improvement 1}
- {Improvement 2}

---

## Follow-up Items

### Technical Debt

| Item | Priority | Ticket/Task |
|------|----------|-------------|
| {Debt item} | High/Med/Low | {Link or ID} |
| {Debt item} | High/Med/Low | {Link or ID} |

### Future Enhancements

| Enhancement | Priority | Notes |
|-------------|----------|-------|
| {Enhancement} | High/Med/Low | {Notes} |
| {Enhancement} | High/Med/Low | {Notes} |

### Documentation Updates Needed

- [ ] Update README with {topic}
- [ ] Add API documentation for {endpoint}
- [ ] Update architecture diagram

### Monitoring/Alerting

- [ ] Add monitoring for {metric}
- [ ] Create alert for {condition}

### Archon Tasks Created

```python
# Follow-up tasks created
manage_task("create",
    project_id="{project-id}",
    title="{follow-up title}",
    description="{description}",
    feature="{feature}",
    status="todo"
)
```

| Task | Archon ID | Status |
|------|-----------|--------|
| {Task title} | {task-id} | todo |
| {Task title} | {task-id} | todo |

---

## Metrics

### Performance Metrics

| Metric | Before | After | Target | Status |
|--------|--------|-------|--------|--------|
| {Metric} | {value} | {value} | {value} | Met/Not Met |
| {Metric} | {value} | {value} | {value} | Met/Not Met |

### Quality Metrics

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Test Coverage | {%} | {%} | Met/Not Met |
| Code Quality Score | {score} | {score} | Met/Not Met |
| Technical Debt | {value} | {value} | Met/Not Met |

### Implementation Metrics

| Metric | Value |
|--------|-------|
| Total Files Changed | {count} |
| Lines Added | {count} |
| Lines Removed | {count} |
| Tests Added | {count} |
| Implementation Time | {duration} |

---

## Deployment Notes

### Deployment Requirements

- [ ] {Requirement 1}
- [ ] {Requirement 2}

### Environment Variables

```bash
# New/changed environment variables
{VAR}={value/description}
```

### Migration Steps

1. {Step 1}
2. {Step 2}
3. {Step 3}

### Rollback Procedure

```bash
# If rollback needed
{rollback commands}
```

### Post-Deployment Verification

```bash
# Verify deployment success
{verification commands}
```

---

## Appendix

### Related Documents

- [Implementation Plan](../plans/{plan-filename}.plan.md)
- [PRD](../prds/{prd-filename}.prd.md)
- [Issue Investigation](../issues/{issue-filename}.md) *(if applicable)*

### Pull Requests

| PR | Title | Status |
|----|-------|--------|
| #{number} | {title} | Merged |
| #{number} | {title} | Merged |

### Commits

| Commit | Message |
|--------|---------|
| `{hash}` | {message} |
| `{hash}` | {message} |

### References

- [{Reference}]({url})
- [{Reference}]({url})

---

## Sign-Off

### Implementation Checklist

- [ ] All acceptance criteria met
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Deployed to production
- [ ] Monitoring verified
- [ ] Stakeholders notified

### Approvals

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | {name} | {date} | Approved |
| Reviewer | {name} | {date} | Approved |
| Tech Lead | {name} | {date} | Approved |

---

*Implementation Completed: {timestamp}*
*Report Generated: {timestamp}*
