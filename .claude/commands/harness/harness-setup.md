---
name: harness-setup
description: Launch the autonomous agent harness setup wizard for long-running development projects
---

# Autonomous Agent Harness Setup

Launch the interactive wizard to set up a new autonomous coding agent harness.

## What This Creates

- **`.harness/` directory** with config, task ledger (`state.json`), and session log (`session-notes.md`)
- **Feature Tasks** generated from your application specification (into `.harness/state.json`)
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

- [ ] **Working directory** is where you want the project
- [ ] **Application specification** is ready (you'll provide this — it gets written to `.harness/spec.md`)
- [ ] **`git` and `gh`** available (cross-session tracking uses GitHub Issues for project-wide initiatives)

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

### Step 5: Initialize Harness Filesystem State

Create the three core files:

```bash
# 1. Config (paths, language, framework, test command)
cat > .harness/config.json << 'EOF'
{
  "project_name": "[Project Name]",
  "language": "[Language]",
  "framework": "[Framework]",
  "spec_path": ".harness/spec.md",
  "test_command": "npm test"
}
EOF

# 2. Spec (the application description)
cp <user-provided-spec> .harness/spec.md
# (or write inline if user provided spec text directly)

# 3. Initial task ledger (will be populated by harness-init)
cat > .harness/state.json << 'EOF'
{
  "schema_version": 1,
  "current_session": 0,
  "tasks": [],
  "meta": {
    "created_at": "<now>",
    "last_updated": "<now>",
    "last_agent": "harness-setup",
    "progress": { "done": 0, "total": 0, "percent": 0 }
  }
}
EOF

# 4. Session log
touch .harness/session-notes.md
```

---

## After Setup

Run these commands in order:

| Order | Command | Purpose |
|-------|---------|---------|
| 1 | `/harness:harness-init` | Generate tasks from spec |
| 2 | `/harness:harness-status` | Verify setup complete |
| 3 | `/harness:harness-next` | Start first coding session |

---

## Arguments

$ARGUMENTS

Tell me about your project and I'll guide you through setup.
