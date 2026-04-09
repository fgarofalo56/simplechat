# Skills Builder

## Overview
The Skills Builder enables users to create, share, and execute reusable AI skills (prompt templates) within SimpleChat. Skills are parameterized prompt templates that can be invoked as `/commands` in chat. A built-in marketplace allows users to publish and discover skills, with optional admin approval workflows.

**Version Implemented:** 0.239.003
**Phase:** Skills Builder Phases 1-3

## Dependencies
- Azure Cosmos DB (`skills` and `skill_executions` containers)
- Azure OpenAI (skill execution via GPT)
- Bootstrap 5 (UI components)
- Flask (backend routes)

## Architecture Overview

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Skills CRUD | `functions_skills.py` | 425 | Create, read, update, delete skills; marketplace; execution logging |
| Skills API | `route_backend_skills.py` | 420 | REST endpoints for skill operations |
| Skills Marketplace | `templates/skills_marketplace.html` | — | Marketplace browsing UI |

### Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `skills` | `/workspace_id` | Skill definitions (prompt template, parameters, metadata) |
| `skill_executions` | `/skill_id` | Execution history (input, output, duration, status) |

### Skill Data Model

```json
{
    "id": "uuid",
    "workspace_id": "user_id or group_id",
    "name": "Summarize Text",
    "command": "/summarize-text",
    "description": "Summarize any text into key points",
    "prompt_template": "Summarize the following text into {num_points} key points:\n\n{input_text}",
    "parameters": [
        {"name": "num_points", "type": "number", "default": 5},
        {"name": "input_text", "type": "text", "required": true}
    ],
    "scope": "personal|group|global",
    "status": "draft|published|pending_approval|approved|rejected",
    "category": "writing|analysis|coding|research|other",
    "author_id": "user_id",
    "author_name": "display_name",
    "rating_avg": 4.5,
    "rating_count": 12,
    "install_count": 45,
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
}
```

### Key Functions (`functions_skills.py`)

#### CRUD Operations
- **`create_skill(user_id, user_name, payload)`**: Create a new skill with validation. Auto-generates the `/command` from the skill name.
- **`get_skill(skill_id, workspace_id)`**: Retrieve a skill by ID.
- **`update_skill(skill_id, workspace_id, updates)`**: Update skill properties.
- **`delete_skill(skill_id, workspace_id)`**: Delete a skill.
- **`list_skills(workspace_id, scope, status)`**: List skills filtered by workspace, scope, and status.

#### Marketplace
- **`list_marketplace_skills(category, search, sort_by)`**: Browse approved skills with filtering and sorting.
- **`publish_skill(skill_id, workspace_id, require_approval)`**: Publish a skill to the marketplace (may require admin approval).
- **`approve_skill(skill_id, admin_user_id, notes)`**: Admin approves a pending skill.
- **`reject_skill(skill_id, admin_user_id, reason)`**: Admin rejects a pending skill with reason.
- **`install_skill(skill_id, user_id)`**: Install a marketplace skill for personal use.
- **`rate_skill(skill_id, user_id, rating)`**: Rate a skill (1-5 stars).

#### Command Resolution
- **`get_skill_by_command(command, user_id, group_id)`**: Resolve a `/command` to a skill definition. Searches personal → group → global scopes in priority order.

#### Execution Tracking
- **`log_skill_execution(skill_id, skill_name, user_id, input_text, output_text, duration_ms, status)`**: Log execution for analytics.
- **`get_skill_executions(skill_id, user_id, limit)`**: Retrieve execution history.

### API Endpoints (`route_backend_skills.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/skills/marketplace` | Marketplace page |
| `POST` | `/api/skills` | Create a skill |
| `GET` | `/api/skills` | List user's skills |
| `GET` | `/api/skills/<id>` | Get skill details |
| `PUT` | `/api/skills/<id>` | Update a skill |
| `DELETE` | `/api/skills/<id>` | Delete a skill |
| `POST` | `/api/skills/<id>/execute` | Execute a skill |
| `GET` | `/api/skills/<id>/executions` | Execution history |
| `GET` | `/api/skills/marketplace` | Browse marketplace |
| `POST` | `/api/skills/<id>/publish` | Publish to marketplace |
| `POST` | `/api/skills/<id>/install` | Install from marketplace |
| `POST` | `/api/skills/<id>/rate` | Rate a skill |
| `GET` | `/api/skills/pending` | Pending approvals (admin) |
| `POST` | `/api/skills/<id>/approve` | Approve skill (admin) |
| `POST` | `/api/skills/<id>/reject` | Reject skill (admin) |

### Skill Execution Flow

```
User types /command in chat
    ↓
Resolve command → skill definition
    ↓
Extract parameters from user input
    ↓
Render prompt template with parameters
    ↓
Send to GPT for execution
    ↓
Log execution (input, output, duration)
    ↓
Return result to chat
```

## Admin Settings

Located in **Admin Settings > Skills Builder** tab:

- **Enable Skills Builder**: Master toggle for skills functionality
- **Require Approval**: Whether published skills require admin approval before marketplace listing
- **Max Skills per User**: Maximum number of skills a user can create
- **Allowed Categories**: Which skill categories are available

## Testing

### Functional Tests
- `functional_tests/test_skills_builder.py` — CRUD operations, marketplace, execution, command resolution

## Files Modified/Added

| File | Changes |
|------|---------|
| `functions_skills.py` (425 lines) | New file: skills CRUD, marketplace, execution |
| `route_backend_skills.py` (420 lines) | New file: REST API endpoints |
| `templates/skills_marketplace.html` | New file: marketplace UI |
| `admin_settings.html` | Skills Builder tab |
| `_sidebar_nav.html` | Skills Builder sidebar navigation entry |
| `app.py` | Route registration |
| `config.py` | Cosmos container configuration, default settings |

(Ref: Skills Builder, Marketplace, Prompt Templates, Skill Execution)
