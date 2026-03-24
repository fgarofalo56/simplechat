---
name: harness-setup
description: Launch the autonomous agent harness setup wizard for long-running development projects
---

# Autonomous Agent Harness Setup

Launch the interactive wizard to set up a new autonomous coding agent harness.

## What This Creates

- **Archon Project** with tasks, documents, and session tracking
- **Feature Tasks** generated from your application specification
- **Agent Pipeline** (Initializer -> Coder -> Tester -> Reviewer)
- **Local Configuration** for harness management

## Setup Modes

### 1. Full Setup (Default)

Complete interactive wizard with all configuration options.

```
I want to set up a new autonomous agent harness project.
```

### 2. Quick Setup

Minimal questions, smart defaults for existing codebases.

```
Quick setup for the current directory with these defaults:
- Project name: [infer from directory]
- Language: [detect from files]
- Testing: unit + integration
- Features: 30
```

### 3. Resume Project

Continue an existing harness project.

```
Resume the existing harness project in this directory.
```

---

## Requirements

Before starting, ensure:

- [ ] **Archon MCP** is configured and running
- [ ] **Working directory** is where you want the project
- [ ] **Application specification** is ready (you'll provide this)

---

## Setup Process

### Step 1: Project Information

```
- Project name?
- Project type (web app, API, CLI, library)?
- Primary language/framework?
- Where should the project live?
```

### Step 2: Application Specification

Provide your application specification document describing:
- Core features and functionality
- User stories or requirements
- Technical constraints
- Acceptance criteria

### Step 3: Task Generation

The wizard will:
1. Parse your specification
2. Generate 20-50 detailed tasks
3. Organize tasks by feature
4. Set priority ordering

### Step 4: Environment Setup

```bash
# Project structure
mkdir -p src tests docs .harness

# Initialize git if needed
git init

# Install dependencies based on language
npm install / pip install / etc.
```

### Step 5: Archon Integration

```python
# Create project
manage_project("create",
    title="[Project Name]",
    description="[From spec]",
    github_repo="[URL]"
)

# Create session document
manage_document("create",
    project_id="...",
    title="Session Notes",
    document_type="note",
    content={"sessions": [], "blockers": []}
)

# Create tasks from spec
for task in generated_tasks:
    manage_task("create", project_id="...", ...)
```

---

## After Setup

Run these commands in order:

| Order | Command | Purpose |
|-------|---------|---------|
| 1 | `/harness-init` | Generate tasks from spec |
| 2 | `/harness-status` | Verify setup complete |
| 3 | `/harness-next` | Start first coding session |

---

## Arguments

$ARGUMENTS

Tell me about your project and I'll guide you through setup.
