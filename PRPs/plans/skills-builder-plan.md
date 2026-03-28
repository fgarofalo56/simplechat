# Implementation Plan: Phase A — Skills Builder

**PRD Reference:** PRPs/prds/enterprise-platform-features.prd.md (Phase A)
**Created:** 2026-03-28
**Author:** Claude Code (AI-assisted)
**Status:** Active
**Estimated Effort:** 32 days (~6-7 weeks)
**Current Version:** 0.239.003

---

## Overview

Build a visual Skills Builder that lets users create, share, and execute reusable AI skills without code. Skills are stored as Cosmos DB documents, executed via Semantic Kernel, and invocable from chat via `/skill-name` commands or natural language triggers. Includes a marketplace with approval workflow (reusing the agent template gallery pattern).

---

## Prerequisites

### Before Starting
- [x] PRD approved (Phase A section)
- [x] Development environment with Cosmos DB, Azure OpenAI, AI Search
- [x] Existing plugin architecture (BasePlugin, manifest system, SK loader)
- [x] Agent template gallery pattern (functions_agent_templates.py) — reuse for marketplace

### Dependencies
| Dependency | Status | Notes |
|------------|--------|-------|
| Azure Cosmos DB | Available | Need 2 new containers: `skills`, `skill_executions` |
| Semantic Kernel | Available | semantic-kernel[mcp]==1.39.4 already installed |
| Agent template approval pattern | Available | functions_agent_templates.py — copy pattern |
| Flask-Executor | Available | 30 workers, for async skill execution |

---

## Implementation Phases

### Phase 1: Foundation [Days 1-4]

**Objective:** Create Cosmos containers, data model, CRUD API, and settings.

#### Tasks

##### 1.1 Cosmos DB Containers for Skills
- **Description:** Add `skills` and `skill_executions` containers to config.py.
- **Files:** `application/single_app/config.py`
- **Estimated Time:** 2 hours
- **Implementation Notes:**
  ```python
  cosmos_skills_container = cosmos_database.create_container_if_not_exists(
      id="skills", partition_key=PartitionKey(path="/workspace_id"))
  cosmos_skill_executions_container = cosmos_database.create_container_if_not_exists(
      id="skill_executions", partition_key=PartitionKey(path="/user_id"))
  ```

##### 1.2 Skills Data Model & CRUD Functions
- **Description:** Create `functions_skills.py` with CRUD operations, validation, and scope-based queries. Follow `functions_agent_templates.py` pattern.
- **Files:** New: `application/single_app/functions_skills.py`
- **Estimated Time:** 8 hours
- **Data Model:**
  ```json
  {
    "id": "skill_uuid",
    "name": "summarize-meeting",
    "display_name": "Summarize Meeting",
    "description": "Creates a structured summary from meeting transcripts",
    "version": "1.0",
    "type": "prompt_skill|tool_skill|chain_skill",
    "category": "productivity|data|integration|analysis|other",
    "author_id": "user_uuid",
    "author_name": "User Name",
    "workspace_id": "workspace_uuid",
    "scope": "personal|group|global",
    "status": "draft|published|pending_approval|approved|rejected",
    "config": {
      "system_prompt": "You are an expert meeting summarizer...",
      "model": "gpt-4o",
      "max_tokens": 2000,
      "temperature": 0.3,
      "input_schema": {"type": "object", "properties": {...}},
      "output_format": "markdown|json|table",
      "tools": [],
      "trigger_phrases": ["summarize meeting"]
    },
    "commands": ["/summarize-meeting"],
    "usage_count": 0,
    "rating_sum": 0,
    "rating_count": 0,
    "created_at": "ISO",
    "updated_at": "ISO"
  }
  ```

##### 1.3 Skills REST API Endpoints
- **Description:** Create `route_backend_skills.py` with full CRUD, execution, marketplace, and approval endpoints.
- **Files:** New: `application/single_app/route_backend_skills.py`, modify `application/single_app/app.py`
- **Estimated Time:** 12 hours
- **Endpoints:**
  ```
  POST   /api/skills                    Create skill
  GET    /api/skills                    List skills (scope filter)
  GET    /api/skills/<id>               Get skill details
  PUT    /api/skills/<id>               Update skill
  DELETE /api/skills/<id>               Delete skill
  POST   /api/skills/<id>/execute       Execute skill
  GET    /api/skills/<id>/executions    Execution history
  POST   /api/skills/<id>/publish       Publish to marketplace
  GET    /api/skills/marketplace        Browse marketplace
  POST   /api/skills/<id>/install       Install to workspace
  POST   /api/skills/<id>/rate          Rate a skill
  POST   /api/admin/skills/<id>/approve Approve skill
  POST   /api/admin/skills/<id>/reject  Reject skill
  ```

##### 1.4 Admin Settings for Skills
- **Description:** Add settings defaults, admin UI tab, and POST handler.
- **Files:** `functions_settings.py`, `route_frontend_admin_settings.py`, `admin_settings.html`, `admin_settings.js`
- **Estimated Time:** 4 hours
- **Settings:**
  ```python
  'enable_skills_builder': False,
  'allow_user_skills': True,
  'allow_group_skills': True,
  'skills_require_approval': True,
  'max_skills_per_user': 50,
  ```

#### Phase 1 Validation
- [ ] Containers created in Cosmos DB on app startup
- [ ] CRUD endpoints return correct responses
- [ ] Settings visible in admin panel
- [ ] Skill creation validates required fields

---

### Phase 2: Skill Execution Engine [Days 5-10]

**Objective:** Execute skills via Semantic Kernel, with chat command interception and streaming response.

##### 2.1 Skill Execution Core
- **Description:** Create skill execution engine that wraps user-defined skills as SK function calls. Prompt Skills use direct GPT completion. Tool Skills register selected plugins and use SK orchestration.
- **Files:** New: `application/single_app/functions_skill_execution.py`
- **Estimated Time:** 16 hours
- **Key functions:**
  - `execute_prompt_skill(skill, user_input, settings)` — direct GPT call with skill's system prompt
  - `execute_tool_skill(skill, user_input, settings)` — SK kernel with selected plugins
  - `execute_chain_skill(skill, user_input, settings)` — sequential execution of sub-skills
  - `log_skill_execution(skill_id, user_id, input, output, duration, status)`

##### 2.2 Chat Command Interception
- **Description:** Intercept `/skill-name` commands in the chat stream endpoint. Parse command and arguments, lookup installed skill, execute, and stream results.
- **Files:** `application/single_app/route_backend_chats.py` (line ~2744)
- **Estimated Time:** 12 hours
- **Implementation Notes:**
  At line 2744 where `user_message = data.get('message', '')`:
  ```python
  # Skill command interception
  if user_message.startswith('/') and not user_message.startswith('//'):
      skill_result = handle_skill_command(user_message, user_id, settings, conversation_id)
      if skill_result:
          # Stream skill result using same SSE pattern
          yield from stream_skill_result(skill_result)
          return
  ```

##### 2.3 Skill Execution Logging
- **Description:** Log all skill executions to `skill_executions` container with timing, input/output, and status.
- **Files:** `application/single_app/functions_skill_execution.py`
- **Estimated Time:** 4 hours

##### 2.4 Natural Language Trigger Detection
- **Description:** Match user messages against installed skills' trigger phrases using fuzzy matching. If confidence > threshold, suggest skill invocation.
- **Files:** `application/single_app/functions_skill_execution.py`
- **Estimated Time:** 8 hours

#### Phase 2 Validation
- [ ] `/summarize-meeting Hello world` executes a test prompt skill
- [ ] Skill execution logged to Cosmos DB
- [ ] Streaming response works with same SSE pattern as normal chat
- [ ] Tool skill correctly loads and uses specified plugins
- [ ] Natural language triggers suggest matching skills

---

### Phase 3: Skills Builder UI [Days 11-20]

**Objective:** Visual skill creation interface with live preview/test panel.

##### 3.1 Skills Builder Page
- **Description:** Create a dedicated skills builder page accessible from workspace settings. Multi-step form: (1) Metadata, (2) Configuration, (3) Input/Output Schema, (4) Tools & Triggers, (5) Test & Preview.
- **Files:** New template + JS + route
- **Estimated Time:** 20 hours
- **UI Components:**
  - Step 1: Name, description, category, scope (reuse agent modal pattern)
  - Step 2: System prompt editor (textarea with variable placeholders `{{input}}`), model selection, temperature/max_tokens sliders
  - Step 3: Input schema builder (add fields: name, type, required, description), output format selector
  - Step 4: Tool selection (checkboxes for available plugins), trigger phrases, command name
  - Step 5: Live test panel — input form, execute button, output preview

##### 3.2 Skills List in Workspace
- **Description:** Add "Skills" tab to workspace page showing installed skills with search, filter, and management options.
- **Files:** `application/single_app/templates/workspace.html`, new JS module
- **Estimated Time:** 12 hours
- **Implementation Notes:**
  Add tab after agents tab (workspace.html line ~349). Show skill cards with: name, description, category badge, usage count, execute button, edit/delete actions.

##### 3.3 Skill Test Panel
- **Description:** Real-time skill testing within the builder. User enters sample input, clicks "Test", sees AI output streamed. Uses same SSE pattern as chat.
- **Files:** Skills builder JS
- **Estimated Time:** 8 hours

#### Phase 3 Validation
- [ ] Multi-step skill builder creates valid skill documents
- [ ] Skills appear in workspace "Skills" tab
- [ ] Test panel streams AI response in real-time
- [ ] Edit/delete operations work from skills list
- [ ] System prompt supports `{{variable}}` placeholders

---

### Phase 4: Marketplace & Sharing [Days 21-27]

**Objective:** Skill marketplace with approval workflow, installation, and rating.

##### 4.1 Skill Marketplace Page
- **Description:** Dedicated marketplace page listing approved skills. Card-based layout with search, category filter, and sort options.
- **Files:** New template + JS + route
- **Estimated Time:** 16 hours
- **Features:** Search by name/description, filter by category, sort by usage/rating/newest, skill detail modal

##### 4.2 Skill Publishing & Approval Workflow
- **Description:** Users can publish skills to marketplace. If `skills_require_approval` is enabled, skills go to "pending" status. Admin reviews in admin settings panel (copy agent template review modal pattern).
- **Files:** `route_backend_skills.py`, admin settings template
- **Estimated Time:** 8 hours

##### 4.3 Skill Installation & Rating
- **Description:** One-click install from marketplace. Skills installed as references (not copies) with scope tracking. Rating system (1-5 stars).
- **Files:** `route_backend_skills.py`, `functions_skills.py`
- **Estimated Time:** 8 hours

##### 4.4 Skill Import/Export
- **Description:** Export skill as JSON file for cross-instance sharing. Import from JSON with validation.
- **Files:** `route_backend_skills.py`
- **Estimated Time:** 4 hours

#### Phase 4 Validation
- [ ] Marketplace shows only approved skills
- [ ] Publishing triggers approval workflow when required
- [ ] Admin can approve/reject with notes
- [ ] Install/uninstall works across scopes
- [ ] Rating updates reflect in marketplace cards
- [ ] Export/import round-trips correctly

---

### Phase 5: Testing & Polish [Days 28-32]

##### 5.1 Functional Tests
- **Estimated Time:** 12 hours
- Cover: CRUD, execution, chat interception, marketplace, approval, rate limiting

##### 5.2 Documentation
- **Estimated Time:** 4 hours
- Feature doc at `docs/explanation/features/SKILLS_BUILDER.md`

##### 5.3 Version Bump & Deployment
- **Estimated Time:** 4 hours
- Bump version, build, deploy, verify in Azure

#### Final Validation
- [ ] All functional tests pass
- [ ] Feature documentation complete
- [ ] Admin settings fully functional
- [ ] Chat skill invocation works end-to-end
- [ ] Marketplace browsing and installation works
- [ ] No regressions in existing functionality

---

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `functions_skills.py` | Skill CRUD, validation, scope queries | New |
| `functions_skill_execution.py` | Execution engine, logging, triggers | New |
| `route_backend_skills.py` | REST API endpoints | New |
| Skills builder template + JS | Visual skill creator UI | New |
| Skills marketplace template + JS | Marketplace browsing UI | New |
| `config.py` | New Cosmos containers | Modified |
| `route_backend_chats.py` | Chat command interception | Modified |
| `workspace.html` | Skills tab in workspace | Modified |
| `admin_settings.html` + JS | Skills admin settings tab | Modified |
| `functions_settings.py` | Settings defaults | Modified |
| `app.py` | Route registration | Modified |

---

## Archon Tasks

1. **Skills Builder - Phase 1: Foundation** (4 days)
2. **Skills Builder - Phase 2: Execution Engine** (6 days)
3. **Skills Builder - Phase 3: Builder UI** (10 days)
4. **Skills Builder - Phase 4: Marketplace** (7 days)
5. **Skills Builder - Phase 5: Testing & Polish** (5 days)

---

## Success Criteria

- [ ] Users can create skills via visual builder (zero code)
- [ ] Skills invocable from chat via `/skill-name`
- [ ] Skills shareable across workspaces via marketplace
- [ ] Admin approval workflow for global publication
- [ ] All features toggleable via admin settings
- [ ] No regressions when features disabled
