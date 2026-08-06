# Context Files

This directory contains **context files** for persistent session memory and project knowledge.

## Purpose

Context files store information that should persist across Claude Code sessions:
- Project architecture decisions
- Session state and progress
- Important discoveries
- Team conventions

## How Context Works

1. **Automatic Loading**: Files listed in `settings.json` → `contextFiles` are loaded at session start
2. **Manual Loading**: Use `@.claude/context/filename.md` to reference specific files
3. **Durability**: These files are version-controlled — commit updates so context survives resets; track cross-session work in GitHub Issues

## Recommended Files

### SESSION_KNOWLEDGE.md (Parent Directory)

Current session state - what you're working on, blockers, next steps.
Updated frequently during work sessions.

### architecture.md

High-level system design decisions:
- Component structure
- Data flow patterns
- Technology choices and rationale

### conventions.md

Team coding standards:
- Naming conventions
- File organization
- Testing patterns
- Git workflow

### decisions.md

Architectural Decision Records (ADRs):
- What was decided
- Why it was decided
- What alternatives were considered

### local-notes.md (gitignored)

Personal notes that shouldn't be committed:
- Local environment quirks
- Personal workflow preferences
- Temporary debugging notes

## File Format

Context files are markdown with clear section headers:

```markdown
# File Title

## Section 1

Content here...

## Section 2

More content...

---
Last Updated: 2025-01-23
```

## Best Practices

1. **Keep files focused** - One topic per file
2. **Update regularly** - Stale context is worse than no context
3. **Use clear headers** - Makes scanning easier
4. **Date your updates** - Know when information was last verified
5. **Commit your updates** - Version-controlled context is the backup; open GitHub Issues for cross-session work items

## Context Loading Strategy

| Context Level | What to Load | When |
|--------------|--------------|------|
| Minimal | CLAUDE.md only | Quick questions |
| Standard | + SESSION_KNOWLEDGE.md | Normal work |
| Full | + architecture.md, conventions.md | Major features |
| Research | + specific topic files | Deep dives |

## Durable Context

Important project knowledge lives in these version-controlled files — commit updates alongside your work.
Track cross-session work items in GitHub Issues (`gh issue`).

---

*Add context files here to preserve knowledge across sessions.*
