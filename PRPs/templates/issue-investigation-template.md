# Issue Investigation Template

Use this template for analyzing bugs, errors, and unexpected behavior.

---

[Home](../../README.md) > [PRPs](../README.md) > [Issues](./) > Issue #{issue-number}

# Issue Investigation: {Brief Issue Title}

> **Issue**: #{issue-number} | **Status**: Investigating
> **Reporter**: {reporter} | **Reported**: {YYYY-MM-DD}
> **Investigator**: {name} | **Investigation Started**: {YYYY-MM-DD}
> **Severity**: Critical/High/Medium/Low
> **Archon Task**: {task-id}

---

## Table of Contents

- [Issue Reference](#issue-reference)
- [Symptoms](#symptoms)
- [Environment](#environment)
- [Investigation Steps](#investigation-steps)
- [Root Cause Analysis](#root-cause-analysis)
- [Findings](#findings)
- [Recommended Fix](#recommended-fix)
- [Verification Steps](#verification-steps)
- [Prevention](#prevention)

---

## Issue Reference

### Original Report

**Source**: {GitHub Issue #N / Support Ticket / User Report / Monitoring Alert}

**Link**: [{Issue Title}]({url-to-issue})

**Original Description**:
> {Paste the original issue description here}

### Reproduction Information

**Reproducible**: Yes/No/Intermittent

**Reproduction Steps** (from report):
1. {Step 1}
2. {Step 2}
3. {Step 3}
4. {Expected result}
5. {Actual result}

### Impact Assessment

| Factor | Assessment |
|--------|------------|
| Users Affected | {Count or description} |
| Frequency | {How often does this occur?} |
| Business Impact | {Revenue/Operations/UX impact} |
| Data Integrity | {Any data corruption risk?} |

---

## Symptoms

### Observed Behavior

{Detailed description of what is happening}

### Expected Behavior

{What should be happening instead}

### Error Messages

```
{Paste exact error messages, stack traces, or logs}
```

### Visual Evidence

{Screenshots, recordings, or diagrams if applicable}

### Related Symptoms

- {Any related issues or behaviors noticed}
- {Patterns in when the issue occurs}
- {Conditions that trigger or avoid the issue}

---

## Environment

### System Information

| Component | Version/Value |
|-----------|---------------|
| Application Version | {version} |
| Environment | {dev/staging/production} |
| OS/Platform | {OS and version} |
| Browser (if applicable) | {browser and version} |
| Node/Python/Runtime | {version} |
| Database | {type and version} |

### Configuration

```{language}
# Relevant configuration that may affect the issue
{configuration snippet}
```

### Recent Changes

| Date | Change | Commit/PR |
|------|--------|-----------|
| {Date} | {What changed} | {Link} |
| {Date} | {What changed} | {Link} |

---

## Investigation Steps

### Step 1: {Investigation Action}

**What I Did**:
{Describe the investigation action taken}

**Command/Query** (if applicable):
```bash
{command or query executed}
```

**Result**:
```
{output or finding}
```

**Conclusion**:
{What this tells us}

---

### Step 2: {Investigation Action}

**What I Did**:
{Describe the investigation action taken}

**Code Examined**:
```{language}
// {file}:{lines}
{relevant code snippet}
```

**Result**:
{What was found}

**Conclusion**:
{What this tells us}

---

### Step 3: {Investigation Action}

**What I Did**:
{Describe the investigation action taken}

**Result**:
{What was found}

**Conclusion**:
{What this tells us}

---

### Step 4: {Investigation Action}

**What I Did**:
{Describe the investigation action taken}

**Result**:
{What was found}

**Conclusion**:
{What this tells us}

---

## Root Cause Analysis

### Primary Cause

{Clear statement of the root cause}

**Location**: `{file}:{line}` or `{component/service}`

**Explanation**:
{Detailed explanation of why this causes the issue}

### Contributing Factors

1. **{Factor 1}**: {Explanation}
2. **{Factor 2}**: {Explanation}
3. **{Factor 3}**: {Explanation}

### Why It Wasn't Caught

{Explain why existing tests/validation didn't catch this}

### Code at Fault

```{language}
// {file}:{lines}
// PROBLEMATIC CODE:
{the code causing the issue}
```

---

## Findings

### Summary

{2-3 sentence summary of what was found}

### Technical Details

{More detailed technical explanation}

### Related Issues

| Issue | Relationship |
|-------|-------------|
| #{number} | {How it relates} |
| #{number} | {How it relates} |

### Data Analysis (if applicable)

{Any data analysis performed}

```sql
-- Query used for analysis
{query}
```

**Results**:
| {Column} | {Column} |
|----------|----------|
| {Data} | {Data} |

---

## Recommended Fix

### Approach

{Description of the recommended fix approach}

### Option 1: {Fix Name} (Recommended)

**Pros**:
- {Advantage}
- {Advantage}

**Cons**:
- {Disadvantage}

**Implementation**:
```{language}
// {file}:{lines}
// REPLACE WITH:
{corrected code}
```

**Estimated Effort**: {Low/Medium/High}

### Option 2: {Alternative Fix Name}

**Pros**:
- {Advantage}

**Cons**:
- {Disadvantage}
- {Disadvantage}

**Implementation**:
```{language}
// Alternative approach
{code}
```

**Estimated Effort**: {Low/Medium/High}

### Recommendation

{Which option is recommended and why}

### Files to Change

| File | Action | Description |
|------|--------|-------------|
| `{path}` | UPDATE | {What to change} |
| `{path}` | UPDATE | {What to change} |
| `{path}` | CREATE | {What to add} |

---

## Verification Steps

### Pre-Fix Verification

Confirm the issue exists:

```bash
# Steps to reproduce before fix
{commands}
```

**Expected**: {The bug should manifest}

### Post-Fix Verification

Confirm the fix works:

```bash
# Steps to verify fix
{commands}
```

**Expected**: {The bug should be resolved}

### Regression Tests

New test cases to add:

```{language}
// {test file}
{test code to add}
```

### Test Checklist

- [ ] Issue no longer reproducible
- [ ] New unit tests pass
- [ ] Existing tests still pass
- [ ] Edge cases covered
- [ ] Integration tests pass
- [ ] Manual verification completed

---

## Prevention

### Test Gap

{What test should have caught this?}

**New Test to Add**:
```{language}
{test code}
```

### Process Improvement

{Any process changes to prevent similar issues}

- [ ] {Action item 1}
- [ ] {Action item 2}

### Monitoring

{Any new monitoring/alerting to add}

```{language}
// Monitoring configuration or alert definition
{configuration}
```

### Documentation

{Any documentation to update}

- [ ] Update `{doc}` with {what}
- [ ] Add to troubleshooting guide

---

## Timeline

| Date | Event |
|------|-------|
| {Date} | Issue reported |
| {Date} | Investigation started |
| {Date} | Root cause identified |
| {Date} | Fix implemented |
| {Date} | Fix deployed |
| {Date} | Issue verified resolved |

---

## Archon Tracking

### Create Fix Task

```python
manage_task("create",
    project_id="{project-id}",
    title="Fix: {issue title}",
    description="Implement fix for issue #{issue-number}. See investigation: PRPs/issues/{filename}.md",
    feature="bug-fix",
    status="todo"
)
```

### Link to Investigation

Update Archon task with investigation findings once complete.

---

## Sign-Off

- [ ] Root cause identified
- [ ] Fix approach approved
- [ ] Implementation plan ready
- [ ] Investigation document complete

**Investigator**: {Name}
**Date**: {YYYY-MM-DD}

---

> **Next Step**: Implement fix with `/prp-issue-fix {issue-number}`

---

*Investigation Started: {timestamp}*
*Last Updated: {timestamp}*
