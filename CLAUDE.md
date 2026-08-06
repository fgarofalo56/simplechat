# SimpleChat — Project Instructions

> **Note:** This project previously used Archon v1 for task tracking. Archon v1 was archived by its author in April 2026. Historical Archon task records were exported to `.claude/migrated-archon-tasks.md` at migration time. Use TodoWrite + GitHub Issues going forward (see Rule 0).

SimpleChat is a Flask web application using Azure Cosmos DB, Azure AI Search, and Azure OpenAI. It supports personal, group, and public workspaces for document management and AI-powered chat.

---

## Critical Rules (Override Everything)

### Rule 0: Task Tracking — Native-First

For tracking work in the current session and across sessions, use **native Claude Code tools**:

| Scope | Tool | When |
|-------|------|------|
| Within-turn / within-session checklist | `TodoWrite` | Multi-step task you'll finish soon |
| Cross-session work | **GitHub Issues** (`gh issue`) | Work that spans days or needs visibility |
| Long-form planning | `PRPs/plans/<name>.plan.md` (if PRP framework selected) | Multi-PR initiatives with phases |
| Recurring backlog item | GitHub Issue with a label | Anything you'll reference more than twice |

`TodoWrite` is the right default. Use it freely. Cross-session durability comes from the **filesystem** (`.claude/reference/`, plan files, this CLAUDE.md) and **GitHub** (Issues, PRs, commit messages) — not from a separate task database.

### Rule 1: Load Context First

When starting substantive work:

1. Run the [Startup Protocol](#startup-protocol).
2. Read this `CLAUDE.md` and any relevant `.claude/reference/*.md`.
3. Check `git status` and `git log -10` for in-flight work.
4. Check open GitHub Issues / PRs if relevant: `gh pr list` / `gh issue list`.
5. Check `MEMORY.md` if there's per-project auto-memory at `~/.claude/projects/<slug>/memory/`.

### Rule 2: Preserve Context in the Filesystem

Project knowledge that survives context resets lives in **files**, not in your conversation:

| Document | Where | When to update |
|----------|-------|----------------|
| Architecture decisions | `.claude/reference/architecture.md` | After any architectural decision |
| Deployment runbook | `.claude/reference/deployment.md` | After deployment changes |
| Session handoff | `.claude/reference/session-context.md` | End of each significant session, before `/compact` or `/clear` |
| API surface | `.claude/reference/api.md` (or generated OpenAPI) | After API surface changes |
| Non-obvious facts / gotchas | `MEMORY.md` (auto-memory) | When you hit something a future session needs |

Auto-compaction manages context; update `session-context.md` before ending significant sessions. Load specific reference docs on demand with `@.claude/reference/<file>.md` syntax — don't preload everything.

### Rule 3: Skills Discovery

Before implementing anything non-trivial, check available skills (`.claude/skills/` and `~/.claude/skills/`). Skills are tested, opinionated workflows - prefer them over ad-hoc solutions.

### Rule 4: Temporary Files Go in `temp/`

All temp files MUST be created under `./temp/` (gitignored), never the repo root. Create the directory if it doesn't exist. Never commit temp files.

### Rule 5: Never Tamper with Security Software

This machine may be Intune-managed. Claude must NEVER attempt to disable, stop, or modify Windows Defender, antivirus, or any security software. If a task seems blocked by security, STOP and ask the user - do not work around it.

### Rule 6: Never Read Secrets

Forbidden paths: `.env`, `.env.*`, `secrets/**`, `~/.ssh/**`, `~/.aws/**`, `**/credentials.json`, `**/service-account.json`. Use `.env.example` as a template only.

### Rule 7: Automatic Behaviors Live in Hooks, Not Memory

If you want Claude to "always do X when Y happens" (e.g., run a linter after every edit, post to Slack on session end, validate env vars before deploy), that **must** be a hook in `.claude/settings.json` (create it if needed) — not a memory entry or a CLAUDE.md instruction.

| Mechanism | Fires when | Best for |
|-----------|-----------|----------|
| **Hooks** (`settings.json`) | Deterministic events: PreToolUse, PostToolUse, UserPromptSubmit, Stop, etc. | "Always run X after Y" |
| **Memory** (`MEMORY.md`) | Recalled by Claude when relevant context appears | Facts, preferences, prior decisions |
| **CLAUDE.md** | Loaded into every session | Project-wide policies and conventions |
| **Skills** | Auto-invoked when description matches user intent | Reusable workflows |

If your rule says "from now on, when X, do Y" — write a hook. Memory cannot enforce; it only informs.

---

## Project Reference

| Field | Value |
|-------|-------|
| **Project Title** | Simplechat |
| **GitHub Repo** | https://github.com/fgarofalo56/simplechat.git |
| **Repository Path** | E:\Repos\GitHub\simplechat |
| **Primary Stack** | Python 3.12 / Flask + Azure OpenAI (RAG), Azure Cosmos DB, Azure AI Search |

```bash
gh repo view https://github.com/fgarofalo56/simplechat.git              # current state
gh issue list --state open               # in-flight backlog
gh pr list --state open                  # in-flight changes
```

---

## Startup Protocol

Run when starting substantive work:

1. **Read this file** + any reference docs the task touches (`@.claude/reference/<topic>.md`).

2. **Check git state**:

   ```bash
   git status
   git log --oneline -10
   ```

3. **Check in-flight GitHub work** (if relevant):

   ```bash
   gh pr list --state open
   gh issue list --state open --assignee @me
   ```

4. **Check `.claude/reference/session-context.md`** if it exists — picks up where the prior session left off.

5. **Brief the user** with: what was being worked on, uncommitted changes, recommended next step.

---

## PRP Framework

> **PRP = PRD + curated codebase intelligence + agent/runbook**

The PRP (Product Requirement Prompt) framework enables AI agents to ship production-ready code on the first pass.

### Quick Reference

| Command | Purpose | Usage |
|---------|---------|-------|
| `/prp-prd` | Create PRD with phases | `/prp-prd "feature description"` |
| `/prp-plan` | Create implementation plan | `/prp-plan PRPs/prds/feature.prd.md` |
| `/prp-implement` | Execute plan | `/prp-implement PRPs/plans/feature.plan.md` |
| `/prp-review` | Code review | `/prp-review` |
| `/prp-issue-investigate` | Analyze issue | `/prp-issue-investigate 123` |
| `/prp-issue-fix` | Fix from investigation | `/prp-issue-fix 123` |
| `/prp-debug` | Root cause analysis | `/prp-debug "problem"` |

### Workflow Selection

| Feature Size | Workflow | Commands |
|--------------|----------|----------|
| **Large** (multi-phase) | PRD -> Plan -> Implement | `/prp-prd` -> `/prp-plan` -> `/prp-implement` |
| **Medium** (single plan) | Plan -> Implement | `/prp-plan` -> `/prp-implement` |
| **Bug Fix** | Investigate -> Fix | `/prp-issue-investigate` -> `/prp-issue-fix` |

### Artifacts Structure

```
PRPs/
+-- prds/              # Product requirement documents
+-- plans/             # Implementation plans
|   +-- completed/     # Archived completed plans
+-- reports/           # Implementation reports
+-- issues/            # Issue investigations
|   +-- completed/     # Archived investigations
+-- templates/         # Reusable templates
```

---

## Autonomous Harness

Multi-agent pipeline for greenfield development: Initializer -> Coder -> Tester -> Reviewer.
Each agent operates with its own prompt and constraints; the pipeline iterates until all tasks are complete.

| Command | Purpose |
|---------|---------|
| `/harness-setup` | Configure for this project |
| `/harness-init` | Parse spec, generate tasks |
| `/harness-next` | Run next iteration |
| `/harness-status` | Check pipeline status |

Config: `.harness/config.json`. Logs: `.harness/logs/`.

---

## SpecKit Framework

Specification-driven development with formal verification checklists.

### Workflow

1. Create specification using `specs/SPEC_TEMPLATE.md`
2. Validate specification completeness
3. Implement following the spec
4. Verify using `checklists/VERIFICATION_CHECKLIST.md`

### Traceability

Requirements are traced through: Requirement -> Design -> Code -> Test

---

## Project Type: Backend API

| Concern | Guidance |
|---------|----------|
| **Validate at boundaries** | Pydantic / DTO / Zod at request ingress. Trust internal code; don't re-validate between layers. |
| **Error responses** | Generic message to client + `logger.exception(...)` server-side. Never `return {"error": str(exc)}` — leaks stack traces (CodeQL `py/stack-trace-exposure`). |
| **Database access** | Parameterized queries only. Connection pooling at the app boundary, not per-request. |
| **Auth** | At middleware level, not per-route. Never trust client-provided user IDs. |
| **Integration tests** | Hit a real database (testcontainers or ephemeral instance). Mocking the DB hides migration breakage. |
| **API versioning** | URL-versioned (`/v1/`) or header-versioned. Never silently break clients. |

Long-running operations: return a job ID + status endpoint, not a hung connection.

---

## Code Style Guidelines

### General Principles

| Principle | Description |
|-----------|-------------|
| **Single Responsibility** | Each function/class does one thing well |
| **Readable over Clever** | Prefer clarity over brevity |
| **DRY** | Don't Repeat Yourself - extract after the third repetition, not the second |
| **Testable** | Write code that's easy to test |
| **Minimal Dependencies** | Only add libraries when truly needed |

### Language-Specific Guidelines

See [Code Style — Python](#code-style--python) and [Code Style — JavaScript](#code-style--javascript) below for this project's conventions.

### Anti-Patterns to Avoid

| Don't | Do Instead |
|-------|------------|
| Put business logic in components | Extract to services |
| Create deeply nested folders (>4 levels) | Flatten structure |
| Mix test files with source | Use dedicated `tests/` folder |
| Create catch-all `utils` folders | Create specific utility modules |
| Duplicate types across features | Use shared types |
| Hardcode configuration values | Use environment variables |

---

## Testing Requirements

### Test Coverage Standards

| Test Type | Coverage Target | Location |
|-----------|----------------|----------|
| **Unit Tests** | 80%+ on changed code | `tests/unit/` |
| **Integration Tests** | Critical paths | `tests/integration/` |
| **E2E Tests** | Happy paths + critical flows | `tests/e2e/` |

### Test Structure (AAA Pattern)

```
describe("ServiceName", () => {
    describe("methodName", () => {
        it("should [expected behavior] when [condition]", async () => {
            // Arrange
            const input = { /* test data */ };

            // Act
            const result = await service.method(input);

            // Assert
            expect(result).toBeDefined();
        });
    });
});
```

Run tests before marking work complete.

---

## Security Guidelines

### Never Commit

| Item | Alternative |
|------|-------------|
| API keys | Environment variables |
| Passwords | Secret manager |
| Private keys | Vault/HSM |
| Connection strings | Config files (gitignored) |
| .env files | .env.example template |

The `.env.example` in this repo lists required variables.

### Security Checklist

- [ ] Validate all user input
- [ ] Sanitize output (prevent XSS)
- [ ] Use parameterized queries (prevent SQL injection)
- [ ] Implement rate limiting
- [ ] Use HTTPS everywhere
- [ ] Keep dependencies updated

### Files Never to Access

```
.env
.env.*
secrets/**
~/.ssh/**
~/.aws/**
**/credentials.json
**/service-account.json
```

---

## Git Workflow

### Branch Strategy

| Branch Type | Pattern | Purpose |
|-------------|---------|---------|
| `main` | Protected | Production-ready code |
| `develop` | Integration | Development integration |
| `feature/*` | `feature/[ticket]-description` | New features |
| `bugfix/*` | `bugfix/[ticket]-description` | Bug fixes |
| `hotfix/*` | `hotfix/[ticket]-description` | Production fixes |

### Commit Message Format

```
<type>(<scope>): <short summary>

<body - optional>

<footer - optional>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`

### PR Requirements

| Requirement | Description |
|-------------|-------------|
| **Description** | Clear summary of changes |
| **Linked Issue** | Reference ticket number |
| **Tests** | New/updated tests included |
| **CI Passing** | All checks green |

---

## End of Session Protocol

1. Update `.claude/reference/session-context.md` with: what was completed, decisions made, next steps, blockers.
2. Update or close any open `TodoWrite` items (mark completed as you go, don't batch).
3. Commit uncommitted work with a descriptive message.
4. If the work warrants a follow-up GitHub Issue (something you'll want to find later), open it now: `gh issue create`.
5. Brief the user with a session summary.

---

## Available Tools

Tools are auto-discovered by Claude Code — no need to hand-maintain tool tables here.
Browse `.claude/commands/` for slash commands and `.claude/agents/` for subagents;
global skills live in `~/.claude/skills/`.

No project MCP servers configured.

---

## Project Structure

```
simplechat/
+-- CLAUDE.md                    # This file
+-- README.md                    # Project overview
+-- .env.example                 # Environment variable template
+-- .gitignore                   # Git ignore rules
+-- .claude/
|   +-- config.yaml              # Project config (template metadata)
|   +-- skills/                  # Project-specific skills
|   +-- commands/                # Project-specific commands
|   +-- agents/                  # Project-specific agents
+-- .github/
|   +-- workflows/               # CI/CD pipelines
|   +-- CODEOWNERS               # Code ownership
+-- .vscode/
|   +-- settings.json            # VS Code settings
|   +-- extensions.json          # Recommended extensions
|   +-- mcp.json                 # MCP server configuration
+-- src/                         # Source code
+-- tests/                       # Test suites
+-- docs/                        # Documentation
+-- scripts/                     # Build/deploy scripts
+-- temp/                        # Temporary files (gitignored)
```

---

## Quick Reference

| Phrase | Action |
|--------|--------|
| `/start` | Run startup protocol |
| `/status` | Project status (git + open issues + recent commits) |
| `/end` | End-of-session protocol (update session-context, commit, summarize) |
| `@.claude/reference/<file>.md` | Load a specific reference doc into context on demand |

---

## Code Style — Python

- Start every file with a filename comment: `# filename.py`
- Place imports at the top, after the module docstring (exceptions must be documented)
- Use 4-space indentation, never tabs
- Use `log_event` from `functions_appinsights.py` for logging instead of `print()`

## Code Style — JavaScript

- Start every file with a filename comment: `// filename.js`
- Group imports at the top of the file (exceptions must be documented)
- Use 4-space indentation, never tabs
- Use camelCase for variables and functions: `myVariable`, `getUserData()`
- Use PascalCase for classes: `MyClass`
- Never use `display:none` in JavaScript; use Bootstrap's `d-none` class instead
- Use Bootstrap alert classes for notifications, not `alert()` calls

## Route Decorators — Swagger Security

**Every Flask route MUST include the `@swagger_route(security=get_auth_security())` decorator.**

- Import `swagger_route` and `get_auth_security` from `swagger_wrapper`
- Place `@swagger_route(security=get_auth_security())` immediately after the `@app.route(...)` decorator and before any authentication decorators (`@login_required`, `@user_required`, etc.)
- This applies to all new and existing routes — no exceptions

Correct pattern:
```python
from swagger_wrapper import swagger_route, get_auth_security

@app.route("/api/example", methods=["GET"])
@swagger_route(security=get_auth_security())
@login_required
@user_required
def example_route():
    ...
```

## Security — Settings Sanitization

**NEVER send raw settings or configuration data to the frontend without sanitization.**

- Always use `sanitize_settings_for_user()` from `functions_settings.py` before passing settings to `render_template()` or `jsonify()`
- **Exception**: Admin routes should NOT be sanitized (breaks admin features)
- Sanitization strips: API keys, Cosmos DB connection strings, Azure Search admin keys, Document Intelligence keys, authentication secrets, internal endpoint URLs, database credentials, and any field containing "key", "secret", "password", or "connection"

Correct pattern:
```python
from functions_settings import get_settings, sanitize_settings_for_user

settings = get_settings()
public_settings = sanitize_settings_for_user(settings)
return render_template('page.html', settings=public_settings)
```

## Version Management

- Version is stored in `config.py`: `VERSION = "X.XXX.XXX"`
- When incrementing, only change the third segment (e.g., `0.238.024` -> `0.238.025`)
- Include the current version in functional test file headers and documentation files

## Documentation Locations

- **Feature documentation**: `docs/explanation/features/[FEATURE_NAME].md` (uppercase with underscores)
- **Fix documentation**: `docs/explanation/fixes/[ISSUE_NAME]_FIX.md` (uppercase with underscores)
- **Release notes**: `docs/explanation/release_notes.md`

### Feature Documentation Structure

1. Header: title, overview, version, dependencies
2. Technical specifications: architecture, APIs, configuration, file structure
3. Usage instructions: enable/configure, workflows, examples
4. Testing and validation: coverage, performance, limitations

### Fix Documentation Structure

1. Header: title, issue description, root cause, version
2. Technical details: files modified, code changes, testing, impact
3. Validation: test results, before/after comparison

## Release Notes

After completing code changes, offer to update `docs/explanation/release_notes.md`.

- Add entries under the current version from `config.py`
- If the version was bumped, create a new section at the top: `### **(vX.XXX.XXX)**`
- Entry categories: **New Features**, **Bug Fixes**, **User Interface Enhancements**, **Breaking Changes**
- Format each entry with a bold title, bullet-point details, and a `(Ref: ...)` line referencing relevant files/concepts

## Functional Tests

- **Location**: `functional_tests/`
- **Naming**: `test_{feature_area}_{specific_test}.py` or `.js`
- **When to create**: bug fixes, new features, API changes, database migration, UI/UX changes, authentication/security changes

Every test file must include a version header:
```python
#!/usr/bin/env python3
"""
Functional test for [feature/fix name].
Version: [current version from config.py]
Implemented in: [version when fix/feature was added]

This test ensures that [description of what is being tested].
"""
```

Test template pattern:
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_primary_functionality():
    """Test the main functionality."""
    print("Testing [Feature Name]...")
    try:
        # Setup, execute, validate, cleanup
        print("Test passed!")
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_primary_functionality()
    sys.exit(0 if success else 1)
```

## Key Project Files

| File | Purpose |
|------|---------|
| `application/single_app/config.py` | App configuration and `VERSION` |
| `application/single_app/functions_settings.py` | `get_settings()`, `sanitize_settings_for_user()` |
| `application/single_app/functions_appinsights.py` | `log_event()` for logging |
| `application/single_app/functions_documents.py` | Document CRUD, chunk operations, tag management |
| `application/single_app/functions_group.py` | Group workspace operations |
| `application/single_app/functions_public_workspaces.py` | Public workspace operations |
| `application/single_app/route_backend_documents.py` | Personal document API routes |
| `application/single_app/route_backend_group_documents.py` | Group document API routes |
| `application/single_app/route_external_public_documents.py` | Public document API routes |
| `application/single_app/route_backend_chats.py` | Chat API routes and AI search integration |

## Frontend Architecture

- Templates: `application/single_app/templates/` (Jinja2 HTML)
- Static JS: `application/single_app/static/js/`
  - `chat/` — Chat interface modules (chat-messages.js, chat-documents.js, chat-citations.js, chat-streaming.js)
  - `workspace/` — Personal workspace (workspace-documents.js, workspace-tags.js)
  - `public/` — Public workspace (public_workspace.js)
- Group workspace JS is inline in `templates/group_workspaces.html`
- Uses Bootstrap 5 for UI components and styling

---

## Task & Knowledge Workflow

Suggested workflow:

```
1. Plan            -> TodoWrite (breaks the work into trackable steps)
2. Research        -> Use the project-kb skill (Context7 for libs, filesystem for project docs)
3. Implement
4. Test            -> Run the project's test command before claiming done
5. Mark complete   -> Update TodoWrite as you finish each step
6. Commit          -> Conventional commit format (see Git Workflow below)
```

For multi-day work: open a GitHub Issue with a clear acceptance bar, link PRs that move it forward, close it when shipped.

Research discipline: 2-5 keyword queries beat one long question. Run multiple focused queries rather than one broad one. See the `project-kb` skill for the full lookup flow.

---

## Optional: Archon RAG

> **Skip this section unless you have a substantial private/internal corpus** that genuinely needs vector search. For library docs (FastAPI, React, Pydantic, etc.), use the `project-kb` skill — it wraps Context7 MCP, which already indexes 1000+ libraries with fresher content than any local corpus.

For projects with extracted internal documentation:

1. Drop markdown files in `.claude/kb/` (gitignored if confidential, committed if public).
2. The `project-kb` skill will grep them automatically.
3. No vector store, no MCP server, no background indexing — just filesystem search with `Grep`.

If you genuinely need vector retrieval (semantic similarity, fuzzy concept matching across a large private corpus), evaluate options like LanceDB-on-disk or a self-hosted Qdrant — but that's a deliberate, scoped infrastructure decision, not a default.

---

> **Template Version**: 5.0.0 | **Updated**: 2026-08-06 | **Source**: claude-code-tools project wizard

