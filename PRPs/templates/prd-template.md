# PRD Template

Use this template for large features that require multiple implementation phases.

---

# {Feature Name}

> **Status**: Draft | **Version**: 1.0
> **Author**: {Author Name} | **Created**: {YYYY-MM-DD}
> **Last Updated**: {YYYY-MM-DD}
> **Archon Project**: {project-id}

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Goals & Success Metrics](#goals--success-metrics)
- [User Stories](#user-stories)
- [Functional Requirements](#functional-requirements)
- [Non-Functional Requirements](#non-functional-requirements)
- [Technical Considerations](#technical-considerations)
- [Implementation Phases](#implementation-phases)
- [Dependencies](#dependencies)
- [Risks & Mitigations](#risks--mitigations)
- [Out of Scope](#out-of-scope)
- [Open Questions](#open-questions)

---

## Overview

### What

{2-3 sentences describing what we're building}

### Why

{Why this feature is needed - business value, user impact, technical debt}

### Who

- **Primary Users**: {Who will use this feature}
- **Secondary Users**: {Other stakeholders}
- **Affected Systems**: {Systems that will be impacted}

---

## Problem Statement

{Describe the problem in detail}

**Current State:**
{What users/systems experience today}

**Pain Points:**
1. {Pain point 1}
2. {Pain point 2}
3. {Pain point 3}

**Impact of Not Solving:**
{Consequences of leaving the problem unsolved}

---

## Goals & Success Metrics

### Goals

| Priority | Goal | Description |
|----------|------|-------------|
| P0 | {Goal} | {Description} |
| P0 | {Goal} | {Description} |
| P1 | {Goal} | {Description} |
| P2 | {Goal} | {Description} |

### Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| {Metric} | {Value} | {Value} | {Timeframe} |
| {Metric} | {Value} | {Value} | {Timeframe} |
| {Metric} | {Value} | {Value} | {Timeframe} |

### Key Hypothesis

We believe {capability} will {solve problem} for {users}.
We'll know we're right when {measurable outcome}.

---

## User Stories

### US-1: {Story Title}

**As a** {user type}
**I want to** {action}
**So that** {benefit}

**Acceptance Criteria:**
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

### US-2: {Story Title}

**As a** {user type}
**I want to** {action}
**So that** {benefit}

**Acceptance Criteria:**
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

### US-3: {Story Title}

**As a** {user type}
**I want to** {action}
**So that** {benefit}

**Acceptance Criteria:**
- [ ] {Criterion 1}
- [ ] {Criterion 2}
- [ ] {Criterion 3}

---

## Functional Requirements

### FR-1: {Category}

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-1.1 | {Requirement} | P0 | {Notes} |
| FR-1.2 | {Requirement} | P0 | {Notes} |
| FR-1.3 | {Requirement} | P1 | {Notes} |

### FR-2: {Category}

| ID | Requirement | Priority | Notes |
|----|-------------|----------|-------|
| FR-2.1 | {Requirement} | P0 | {Notes} |
| FR-2.2 | {Requirement} | P1 | {Notes} |
| FR-2.3 | {Requirement} | P2 | {Notes} |

---

## Non-Functional Requirements

| Category | Requirement | Target | Notes |
|----------|-------------|--------|-------|
| **Performance** | {Requirement} | {Target} | {Notes} |
| **Security** | {Requirement} | {Target} | {Notes} |
| **Availability** | {Requirement} | {Target} | {Notes} |
| **Scalability** | {Requirement} | {Target} | {Notes} |
| **Compliance** | {Requirement} | {Target} | {Notes} |

---

## Technical Considerations

### Architecture

```
{ASCII diagram or description of architecture}
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| {Component} | {Technology} | {Why this choice} |
| {Component} | {Technology} | {Why this choice} |
| {Component} | {Technology} | {Why this choice} |

### Integration Points

| System | Integration Type | Notes |
|--------|------------------|-------|
| {System} | {Type: API/Event/Direct} | {Notes} |
| {System} | {Type: API/Event/Direct} | {Notes} |

### Data Model Changes

{Describe any database/schema changes needed}

### API Changes

{Describe any API additions/modifications}

---

## Implementation Phases

<!--
  STATUS: pending | in-progress | complete
  Update status as work progresses
  Link to plan files once created
-->

| # | Phase | Description | Status | Est. Duration | Plan |
|---|-------|-------------|--------|---------------|------|
| 1 | {Phase name} | {What this phase delivers} | pending | {X days/weeks} | - |
| 2 | {Phase name} | {What this phase delivers} | pending | {X days/weeks} | - |
| 3 | {Phase name} | {What this phase delivers} | pending | {X days/weeks} | - |
| 4 | {Phase name} | {What this phase delivers} | pending | {X days/weeks} | - |

### Phase 1: {Name}

**Goal**: {What we're trying to achieve}

**Scope**:
- {Deliverable 1}
- {Deliverable 2}
- {Deliverable 3}

**Success Signal**: {How we know it's done}

**Validation**: `{validation command}`

### Phase 2: {Name}

**Goal**: {What we're trying to achieve}

**Scope**:
- {Deliverable 1}
- {Deliverable 2}
- {Deliverable 3}

**Success Signal**: {How we know it's done}

**Validation**: `{validation command}`

### Phase 3: {Name}

**Goal**: {What we're trying to achieve}

**Scope**:
- {Deliverable 1}
- {Deliverable 2}
- {Deliverable 3}

**Success Signal**: {How we know it's done}

**Validation**: `{validation command}`

### Phase 4: {Name}

**Goal**: {What we're trying to achieve}

**Scope**:
- {Deliverable 1}
- {Deliverable 2}
- {Deliverable 3}

**Success Signal**: {How we know it's done}

**Validation**: `{validation command}`

---

## Dependencies

### External Dependencies

| Dependency | Version | Status | Installation | Notes |
|------------|---------|--------|--------------|-------|
| {Package} | {Version} | {Installed/Required} | {Command} | {Notes} |
| {Package} | {Version} | {Installed/Required} | {Command} | {Notes} |

### Internal Dependencies

| Dependency | Owner | Status | Notes |
|------------|-------|--------|-------|
| {System/Feature} | {Team/Person} | {Available/Blocked} | {Notes} |
| {System/Feature} | {Team/Person} | {Available/Blocked} | {Notes} |

### Environment Requirements

```bash
# Required environment variables
{VAR_NAME}={description}
{VAR_NAME}={description}
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| {Risk description} | High/Med/Low | High/Med/Low | {Mitigation strategy} | {Owner} |
| {Risk description} | High/Med/Low | High/Med/Low | {Mitigation strategy} | {Owner} |
| {Risk description} | High/Med/Low | High/Med/Low | {Mitigation strategy} | {Owner} |

---

## Out of Scope

Explicit exclusions to prevent scope creep:

| Item | Reason | Future Consideration |
|------|--------|---------------------|
| {Item} | {Why not included} | {When might be added} |
| {Item} | {Why not included} | {When might be added} |
| {Item} | {Why not included} | {When might be added} |

---

## Open Questions

| # | Question | Owner | Status | Resolution |
|---|----------|-------|--------|------------|
| 1 | {Question} | {Owner} | Open/Resolved | {Resolution if resolved} |
| 2 | {Question} | {Owner} | Open/Resolved | {Resolution if resolved} |
| 3 | {Question} | {Owner} | Open/Resolved | {Resolution if resolved} |

---

## Decisions Log

| Date | Decision | Alternatives Considered | Rationale |
|------|----------|------------------------|-----------|
| {Date} | {Decision} | {Options} | {Why this choice} |
| {Date} | {Decision} | {Options} | {Why this choice} |

---

## Appendix

### Related Documents

- [Implementation Plan (Phase 1)](../plans/{feature-slug}-phase-1.plan.md)
- [Architecture Diagram]({link})
- [API Specification]({link})

### References

- [{Reference title}]({url})
- [{Reference title}]({url})

### Archon Tasks

```python
# View related tasks
find_tasks(filter_by="project", filter_value="{project-id}")
```

---

> **Next Step**: Create implementation plan with `/prp-plan PRPs/prds/{feature-slug}.prd.md`

---

*Generated: {timestamp}*
*Status: DRAFT - needs validation*
