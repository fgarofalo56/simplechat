# PRD: Enterprise Platform Features — Skills Builder, Workflow Engine & Data Analytics

**Created:** 2026-03-27
**Author:** Claude Code (AI-assisted)
**Status:** Draft
**Version:** 1.0
**Current App Version:** 0.239.003

---

## Executive Summary

Transform SimpleChat from a document-centric RAG chat application into a full enterprise intelligence platform by adding three major capabilities: (A) a visual Skills Builder that lets users create reusable AI skills without code, (B) a Workflow Engine with Azure Logic Apps integration for multi-step automation, and (C) a Data Analytics Platform that connects to all major Azure data services. These features leverage SimpleChat's existing Semantic Kernel plugin architecture, extending it from 15 built-in plugins to an unlimited, user-composable toolkit.

---

## 1. Goal

### Primary Objective
Enable non-developer users to build custom AI skills, orchestrate multi-step workflows, and query enterprise data services — all through the SimpleChat chat interface and admin UI — without writing code.

### Success Metrics
- [ ] Users can create and share custom skills via visual builder (zero code required)
- [ ] Workflows can chain 2+ skills/actions with conditional logic and scheduling
- [ ] At least 8 Azure data services queryable through chat (Synapse, Databricks, SQL, Cosmos, Data Lake, Log Analytics, Power BI, Fabric)
- [ ] Skills marketplace with 50+ community-contributed skills within 3 months of launch
- [ ] 80%+ of enterprise data queries answerable without leaving SimpleChat
- [ ] Workflow execution success rate > 95%
- [ ] Admin can manage all features via existing admin settings panel

---

## 2. Why

### Business Value
- **Democratize AI**: Non-developers can build AI capabilities without IT involvement
- **Reduce tool sprawl**: Consolidate data querying, automation, and AI chat into one platform
- **Accelerate time-to-insight**: Direct data service access from chat eliminates context switching
- **Enterprise stickiness**: Deep Azure integration makes SimpleChat the hub for AI-powered work

### User Value
- **Skills Builder**: "I want to create a reusable skill that summarizes Jira tickets and don't want to write Python"
- **Workflows**: "I want to automatically extract data from uploaded documents, enrich it with Databricks, and email a report every Monday"
- **Data Analytics**: "I want to ask questions about our Synapse data warehouse in natural language"

### Problems Solved
- **Skill creation is code-only**: Currently requires Python + JSON manifest. Builder makes it visual.
- **No automation**: Users can chat but can't chain actions. Workflows fix this.
- **Data is siloed**: Databricks, Synapse, SQL data requires separate tools. Analytics platform unifies access.
- **No Logic Apps integration**: Azure Logic Apps is the enterprise standard for automation but isn't connected.

### Risks of Not Implementing
- Users adopt competing platforms (Copilot Studio, Power Platform) for automation
- Data teams maintain separate tooling, reducing SimpleChat adoption
- Custom skill creation remains developer-bottlenecked

---

## 3. What

### User-Visible Behavior

**Before:**
- Users chat with AI using uploaded documents
- Plugins require Python code + JSON manifests to create
- No workflow automation — every action is manual
- Data queries limited to pre-configured SQL/Databricks plugins
- No dashboards or visualizations

**After:**
- Users create AI skills visually (prompt templates, tool chains, triggers)
- Skills shared across workspaces via marketplace
- Multi-step workflows with conditional logic, scheduling, and Logic Apps integration
- Natural language queries against Synapse, Databricks, SQL, Cosmos, Data Lake
- Inline charts, tables, and dashboards from query results
- Workflow history and monitoring dashboard

---

### Functional Requirements

#### Phase A: Skills Builder [P0]

##### A.1 Visual Skill Creator
- [ ] Drag-and-drop skill builder UI in workspace settings
- [ ] Skill components: System Prompt, Input Schema, Output Schema, Tools (existing plugins), Model Selection
- [ ] Live preview/test panel to try the skill before saving
- [ ] Skill versioning (major.minor) with rollback
- [ ] Skill types: Prompt Skill (system prompt + model), Tool Skill (system prompt + plugins), Chain Skill (sequence of skills)

##### A.2 Skill Execution Engine
- [ ] Skills invocable from chat via `/skill-name` or natural language trigger phrases
- [ ] Skills can accept structured input (form) or freeform text
- [ ] Skill execution logs viewable by creator and admin
- [ ] Skill output can be: text response, structured data (JSON/table), file download, or trigger another skill
- [ ] Rate limiting per skill (configurable by admin)

##### A.3 Skill Sharing & Marketplace
- [ ] Skills shareable at: personal (private), group, public workspace, and global (admin) scopes
- [ ] Skill marketplace page listing all available skills with search/filter
- [ ] Skill cards showing: name, description, author, usage count, rating
- [ ] One-click "Add to My Workspace" for marketplace skills
- [ ] Admin approval workflow for global skill publication (reuse existing agent template gallery pattern)
- [ ] Skill import/export as JSON for cross-instance sharing

##### A.4 Skill Admin Settings
- [ ] `enable_skills_builder`: Master toggle
- [ ] `allow_user_skills`: Users can create personal skills
- [ ] `allow_group_skills`: Group members can create group skills
- [ ] `skills_require_approval`: Skills need admin approval before global publication
- [ ] `max_skills_per_user`: Limit per user (default: 50)

#### Phase B: Workflow Engine & Logic Apps [P0]

##### B.1 Workflow Designer
- [ ] Visual workflow builder with node-based canvas (steps connected by edges)
- [ ] Step types: Skill Execution, HTTP Request, Data Query, Condition (if/else), Loop, Delay, Logic App Trigger
- [ ] Each step configurable with input mapping from previous steps
- [ ] Workflow validation before save (check all connections, required inputs)
- [ ] Workflow versioning with diff view

##### B.2 Workflow Execution Runtime
- [ ] Synchronous execution for short workflows (< 30 seconds)
- [ ] Asynchronous execution with progress tracking for long workflows
- [ ] Step-by-step execution log with timing, input/output per step
- [ ] Error handling: retry policy (configurable), skip-on-error, fail-fast
- [ ] Workflow execution history with search/filter

##### B.3 Workflow Triggers
- [ ] Manual trigger (button click or chat command)
- [ ] Scheduled trigger (cron-like: daily, weekly, monthly, custom)
- [ ] Event trigger: new document uploaded, chat message matching pattern, webhook
- [ ] Logic Apps trigger: receive events from Azure Logic Apps via webhook

##### B.4 Azure Logic Apps Integration
- [ ] Browse and trigger existing Logic Apps from SimpleChat
- [ ] Create new Logic Apps from workflow templates (using Azure Logic Apps REST API)
- [ ] Monitor Logic Apps run status and history
- [ ] Bidirectional: Logic Apps can trigger SimpleChat workflows via webhook endpoint
- [ ] Authentication: Managed Identity for Logic Apps management, webhook auth for inbound

##### B.5 Workflow Templates
- [ ] Pre-built workflow templates: Document Processing Pipeline, Weekly Report, Data ETL, Approval Chain
- [ ] Template marketplace (same pattern as skill marketplace)
- [ ] Template parameterization (variables replaced at instantiation)

##### B.6 Workflow Admin Settings
- [ ] `enable_workflows`: Master toggle
- [ ] `enable_workflow_scheduling`: Allow scheduled workflows
- [ ] `enable_logic_apps_integration`: Azure Logic Apps connectivity
- [ ] `logic_apps_subscription_id`, `logic_apps_resource_group`: Azure resource targeting
- [ ] `max_workflow_steps`: Maximum steps per workflow (default: 20)
- [ ] `max_concurrent_workflows`: Per-user concurrency limit (default: 5)
- [ ] `workflow_execution_timeout`: Maximum runtime in seconds (default: 300)

#### Phase C: Data Analytics Platform [P0]

##### C.1 Data Connection Manager
- [ ] Admin UI to configure data source connections (connection string, Managed Identity, or service principal)
- [ ] Supported data sources:
  - Azure Synapse Analytics (SQL pools, Spark pools, serverless SQL)
  - Azure Databricks (SQL warehouses, clusters)
  - Azure SQL Database (all flavors: SQL Server, PostgreSQL, MySQL)
  - Azure Cosmos DB (SQL API analytics queries)
  - Azure Data Lake Storage Gen2 (file browsing, Parquet/CSV querying)
  - Azure Log Analytics (KQL queries — already implemented)
  - Power BI (embedded reports and datasets)
  - Microsoft Fabric (lakehouses, warehouses)
- [ ] Connection health check and test query
- [ ] Connections shareable at personal, group, global scopes

##### C.2 Natural Language Data Query
- [ ] Chat-based data querying: "Show me top 10 customers by revenue from the Synapse warehouse"
- [ ] AI generates SQL/KQL query from natural language, shows it to user for approval before execution
- [ ] Schema-aware: agent knows table/column names via schema discovery plugins
- [ ] Multi-database support: user selects data source or AI auto-routes based on question
- [ ] Query history with re-run capability

##### C.3 Query Result Visualization
- [ ] Inline table rendering for query results (sortable, filterable, paginated)
- [ ] Chart generation from query results: bar, line, pie, area, scatter
- [ ] Chart type auto-suggestion based on data shape
- [ ] Export results as CSV, JSON, or Excel
- [ ] Pin results to a personal/group dashboard

##### C.4 Dashboard Builder
- [ ] Personal and group dashboards with pinned query results and charts
- [ ] Dashboard layout: grid-based with drag-and-drop positioning
- [ ] Auto-refresh on configurable interval (5m, 15m, 1h, manual)
- [ ] Dashboard sharing: personal, group, public
- [ ] Dashboard templates for common patterns (KPI overview, cost analysis, data quality)

##### C.5 Azure Synapse Integration
- [ ] Connect to Synapse workspaces via Managed Identity or service principal
- [ ] Query serverless SQL pools and dedicated SQL pools
- [ ] Browse Synapse pipelines and trigger execution
- [ ] Monitor pipeline run status and history
- [ ] Access Spark pool for complex analytics (submit PySpark jobs)
- [ ] SDK: `azure-synapse-artifacts`, `azure-synapse-spark`, `azure-synapse-managedprivateendpoints`

##### C.6 Azure Databricks Integration (Enhanced)
- [ ] Extend existing `databricks_table_plugin.py` with:
  - Workspace browser (list clusters, warehouses, notebooks)
  - Execute notebook as a job and retrieve results
  - Unity Catalog integration (browse catalogs, schemas, tables)
  - Auto-generate table description from column statistics
- [ ] SDK: Databricks REST API v2.0, `databricks-sdk`

##### C.7 Azure Data Lake Storage Gen2 Integration
- [ ] Browse ADLS containers, directories, and files
- [ ] Preview file contents (Parquet, CSV, JSON — first 100 rows)
- [ ] Query Parquet/CSV files via Synapse serverless SQL (auto-generate OPENROWSET queries)
- [ ] File metadata display (size, modified date, format)
- [ ] SDK: `azure-storage-file-datalake`

##### C.8 Cosmos DB Analytics (Enhanced)
- [ ] Extend existing Cosmos DB integration with:
  - Cross-partition analytical queries
  - Container-level statistics (document count, storage, RU consumption)
  - Data sampling for schema discovery
  - Export query results to Data Lake
- [ ] SDK: `azure-cosmos` (already installed)

##### C.9 Power BI Embedded
- [ ] Embed Power BI reports and dashboards inline in SimpleChat
- [ ] List available reports from a Power BI workspace
- [ ] Row-level security (RLS) mapping from SimpleChat user identity
- [ ] Interactive report filtering from chat context
- [ ] SDK: `azure-identity`, Power BI REST API v1.0

##### C.10 Data Analytics Admin Settings
- [ ] `enable_data_analytics`: Master toggle
- [ ] `enable_synapse_integration`: Synapse connectivity
- [ ] `enable_databricks_enhanced`: Extended Databricks features
- [ ] `enable_datalake_browser`: ADLS Gen2 browsing
- [ ] `enable_cosmos_analytics`: Cosmos analytical queries
- [ ] `enable_powerbi_embedding`: Power BI report embedding
- [ ] `enable_query_visualization`: Chart generation from results
- [ ] `enable_dashboards`: Dashboard builder
- [ ] `data_query_max_rows`: Maximum rows returned per query (default: 10000)
- [ ] `data_query_timeout`: Query execution timeout seconds (default: 120)
- [ ] Per-connection settings: connection string, auth type, resource identifiers

### Non-Functional Requirements
- **Performance**: Skill execution < 5s for prompt skills, < 30s for tool chains. Data queries < 30s for interactive, < 5m for batch.
- **Security**: All connections use Managed Identity where possible. Secrets in Key Vault. Query approval before execution. RBAC at connection level.
- **Scalability**: Workflow engine uses Flask-Executor (existing 30 worker threads). Data queries use connection pooling.
- **Accessibility**: All UI components follow existing Bootstrap 5 + WCAG 2.1 AA patterns.

---

## 4. Context

### Codebase Context

| Area | Existing Code | Leverage Strategy |
|------|--------------|-------------------|
| Plugin architecture | `BasePlugin`, manifest schema, CRUD API | Skills Builder generates plugin manifests visually |
| Agent system | Agent templates, gallery, approval workflow | Skills marketplace reuses gallery pattern |
| SQL integration | `sql_plugin_factory.py`, 5 database types | Data connections extend SQL factory pattern |
| Databricks | `databricks_table_plugin.py` | Enhanced with workspace browsing, notebooks |
| Log Analytics | `log_analytics_plugin.py` | Already complete — model for other services |
| Secret storage | Key Vault integration with `__Secret` fields | All connection credentials use existing KV pattern |
| Background tasks | Flask-Executor (30 workers) | Workflow execution reuses executor pattern |
| Admin settings | `functions_settings.py` + admin UI tabs | New settings follow established Phase 1-5 pattern |
| Cosmos DB | 26+ containers, partitioned by user/group | New containers for skills, workflows, dashboards |

### Dependencies

| Dependency | Type | Notes |
|-----------|------|-------|
| `azure-mgmt-logic` | New | Logic Apps management SDK |
| `azure-synapse-artifacts` | New | Synapse pipeline management |
| `azure-synapse-spark` | New | Synapse Spark job submission |
| `azure-storage-file-datalake` | New | ADLS Gen2 browsing |
| `databricks-sdk` | New | Enhanced Databricks integration |
| `plotly` or `chart.js` | New | Client-side chart rendering |
| `azure-mgmt-resource` | New | Resource discovery for Logic Apps |
| `databricks-sql-connector` | New | Databricks SQL warehouse DB API 2.0 queries |
| Existing: `azure-cosmos`, `azure-identity`, `azure-storage-blob`, `azure-keyvault-secrets`, `pyodbc`, `psycopg2-binary`, `PyMySQL`, `msal` | Installed | Already in requirements.txt |

**Authentication Patterns (from research):**
- **Synapse**: Managed Identity via `DefaultAzureCredential` + `pyodbc` with `Authentication=ActiveDirectoryMsi`
- **Databricks**: PAT, Service Principal, or Azure AD via `databricks-sdk` unified auth
- **Logic Apps**: Managed Identity via `azure-mgmt-logic` (ARM scope: `https://management.azure.com/.default`)
- **PostgreSQL MI**: Token from `DefaultAzureCredential` with scope `https://ossrdbms-aad.database.windows.net/.default` as password
- **Power BI**: Service principal via `msal` + REST API (scope: `https://analysis.windows.net/powerbi/api/.default`)
- **ADLS Gen2**: Managed Identity via `azure-storage-file-datalake`

### Constraints
- **Frontend**: Bootstrap 5 + vanilla JavaScript (no React/Vue). Workflow designer must work within this constraint.
- **Backend**: Flask single-process with Flask-Executor threading. No Celery or distributed task queue.
- **Auth**: Azure AD / Entra ID via MSAL. All data connections inherit user or Managed Identity auth.
- **Cosmos DB**: 400 RU/s default per container. New containers must be efficient.

---

## 5. User Stories

### Primary User: Knowledge Worker (Non-Developer)

**Story 1: Create a Skill**
As a knowledge worker, I want to create a reusable AI skill that summarizes meeting transcripts in a specific format, so that my team can use it consistently without knowing prompt engineering.

**Acceptance Criteria:**
- [ ] I can open a Skills Builder from my workspace settings
- [ ] I can define: name, description, system prompt, input type, model
- [ ] I can test the skill with sample input and see the output
- [ ] I can save and invoke the skill from chat with `/summarize-meeting`
- [ ] My team can find and add the skill from the marketplace

**Story 2: Build a Workflow**
As a team lead, I want to create a workflow that runs every Monday: queries our Synapse warehouse for weekly KPIs, formats them into a summary, and sends the result to our Teams channel via Logic Apps.

**Acceptance Criteria:**
- [ ] I can create a workflow with: Data Query step -> Skill step -> Logic Apps step
- [ ] I can schedule it to run weekly on Mondays at 9 AM
- [ ] I can see execution history and status
- [ ] Failed steps show error details and support retry

**Story 3: Query Enterprise Data**
As a data analyst, I want to ask questions about our Azure Synapse data warehouse in natural language from the SimpleChat chat interface, and see results as tables and charts.

**Acceptance Criteria:**
- [ ] I can select a data connection from the chat toolbar
- [ ] I type "show revenue by region for Q4" and the AI generates SQL
- [ ] I approve the generated SQL before it executes
- [ ] Results display as a sortable table with a chart option
- [ ] I can pin the chart to my personal dashboard

### Secondary User: Admin

**Story 4: Manage Data Connections**
As an admin, I want to configure Azure data service connections that are available to all users, with proper access controls and secret management.

**Acceptance Criteria:**
- [ ] I can add connections for Synapse, Databricks, SQL, ADLS, Cosmos, Power BI
- [ ] Each connection uses Managed Identity or Key Vault-stored credentials
- [ ] I can test each connection before saving
- [ ] I can scope connections to global, group, or require specific roles

---

## 6. Technical Considerations

### Architecture Impact

```
SimpleChat Platform Architecture (Post-Implementation)
======================================================

[Chat UI] ─── [Skills Engine] ─── [Skill Marketplace]
    |               |                      |
    |          [Workflow Engine] ──── [Scheduler]
    |               |                      |
    |          [Data Query Layer] ── [Visualization]
    |               |                      |
    v               v                      v
[Semantic Kernel] ─── [Plugin Registry] ─── [Connection Manager]
    |                       |                       |
    v                       v                       v
[Azure OpenAI]    [15+ Built-in Plugins]    [Azure Data Services]
                  [User-Created Skills]      - Synapse
                  [MCP Servers]              - Databricks
                  [Logic Apps Actions]       - SQL (all)
                                             - Cosmos DB
                                             - Data Lake Gen2
                                             - Power BI
                                             - Log Analytics
```

### New Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `skills` | `/workspace_id` | Skill definitions and metadata |
| `skill_executions` | `/user_id` | Skill execution logs |
| `workflows` | `/workspace_id` | Workflow definitions |
| `workflow_executions` | `/user_id` | Workflow execution history |
| `workflow_schedules` | `/id` | Scheduled workflow triggers |
| `data_connections` | `/workspace_id` | Data source connection configs |
| `dashboards` | `/workspace_id` | Dashboard definitions and layouts |
| `query_history` | `/user_id` | Saved queries and results |

### New API Endpoints

**Skills Builder:**
```
POST   /api/skills                         Create skill
GET    /api/skills                         List skills (with scope filter)
GET    /api/skills/<id>                    Get skill details
PUT    /api/skills/<id>                    Update skill
DELETE /api/skills/<id>                    Delete skill
POST   /api/skills/<id>/execute            Execute skill
GET    /api/skills/<id>/executions         Execution history
POST   /api/skills/<id>/publish            Publish to marketplace
GET    /api/skills/marketplace             Browse marketplace
POST   /api/skills/<id>/install            Install skill to workspace
```

**Workflow Engine:**
```
POST   /api/workflows                      Create workflow
GET    /api/workflows                      List workflows
GET    /api/workflows/<id>                 Get workflow details
PUT    /api/workflows/<id>                 Update workflow
DELETE /api/workflows/<id>                 Delete workflow
POST   /api/workflows/<id>/execute         Execute workflow
GET    /api/workflows/<id>/executions      Execution history
GET    /api/workflows/<id>/executions/<eid> Execution details
POST   /api/workflows/<id>/schedule        Set schedule
DELETE /api/workflows/<id>/schedule        Remove schedule
POST   /api/webhooks/workflow/<id>         Webhook trigger
```

**Logic Apps:**
```
GET    /api/logicapps                      List Logic Apps
GET    /api/logicapps/<id>                 Get Logic App details
POST   /api/logicapps/<id>/trigger         Trigger Logic App run
GET    /api/logicapps/<id>/runs            Get run history
POST   /api/logicapps/create               Create Logic App from template
```

**Data Analytics:**
```
POST   /api/data/connections               Create connection
GET    /api/data/connections               List connections
PUT    /api/data/connections/<id>           Update connection
DELETE /api/data/connections/<id>           Delete connection
POST   /api/data/connections/<id>/test      Test connection
POST   /api/data/query                     Execute query
GET    /api/data/query/history              Query history
GET    /api/data/schema/<connection_id>     Get schema/tables
POST   /api/data/visualize                 Generate chart from data
POST   /api/dashboards                     Create dashboard
GET    /api/dashboards                     List dashboards
PUT    /api/dashboards/<id>                Update dashboard
GET    /api/data/datalake/browse            Browse ADLS files
GET    /api/data/synapse/pipelines          List Synapse pipelines
POST   /api/data/synapse/pipelines/<id>/run Trigger pipeline
GET    /api/data/powerbi/reports            List Power BI reports
```

### Security Considerations
- **Query Approval**: AI-generated SQL/KQL must be shown to user before execution (prevents injection)
- **Read-Only Default**: All data connections default to read-only mode. Write access requires explicit admin opt-in.
- **Row-Level Security**: Data connections respect Azure RBAC and RLS when using user delegation
- **Secret Isolation**: All credentials in Key Vault, never in Cosmos DB or frontend
- **Webhook Auth**: Inbound webhook endpoints require HMAC signature or shared secret
- **Execution Sandboxing**: Workflow steps run in isolated contexts; one step's failure doesn't leak data to another
- **Rate Limiting**: Per-user rate limits on skill execution, data queries, and workflow runs

---

## 7. Out of Scope

Explicitly NOT included in this PRD:
- **Custom Python code execution**: Skills are prompt-based + existing plugins, not arbitrary code
- **Real-time data streaming**: No Kafka/Event Hub real-time streaming (batch queries only)
- **Full ETL pipeline builder**: Workflows can trigger Synapse/Databricks pipelines but don't replace ADF
- **Power BI report creation**: Only embedding existing reports, not building new ones
- **Cross-instance federation**: Skills/workflows don't sync across SimpleChat deployments
- **Mobile-optimized workflow designer**: Workflow builder is desktop-focused
- **GPU/ML model training**: Data analytics is query + visualization, not model training

---

## 8. Open Questions

1. **Workflow designer library**: **RESOLVED** — Use Sequential Workflow Designer (Tier 1, zero deps, vanilla JS, MIT, CDN) for step-based workflows. Add Drawflow.js (Tier 2) later for full DAG support. React Flow and n8n embed are not viable for our vanilla JS frontend. Logic Apps designer (LogicAppsUX) is a full React monorepo — too complex to embed; use form-based JSON builder instead.
2. **Logic Apps authentication**: **RESOLVED** — Use Managed Identity via `DefaultAzureCredential` (ARM scope). `azure-mgmt-logic` SDK supports full CRUD, trigger, and monitoring. Support both Consumption (multi-tenant via SDK) and Standard (single-tenant via REST artifacts API).
3. **Chart library**: **RESOLVED** — Chart.js for inline charts (200KB, Canvas-based, Bootstrap-compatible). Power BI embedding via `powerbi-client` JS SDK for advanced dashboards.
4. **Synapse vs Fabric**: **RESOLVED** — Synapse first (Phase C). Fabric as Phase D. Note: Azure Synapse Link for Cosmos DB is deprecated for new projects — use Cosmos DB Mirroring for Fabric when targeting Phase D.
5. **Skill execution model**: **RESOLVED** — Both: Prompt Skills (simple system prompt + model) and Agent Skills (system prompt + SK plugins). Skills stored in Cosmos DB as plugin manifests; `UserSkillPlugin` wraps them as `BasePlugin` subclass for dynamic SK registration.
6. **Data connection scoping**: **RESOLVED** — Global + group connections admin-managed. Personal connections behind `allow_user_data_connections` feature flag. All secrets in Key Vault via existing `__Secret` field pattern.

---

## 9. Implementation Phases

| Phase | Duration | Features | Priority |
|-------|----------|----------|----------|
| **Phase A: Skills Builder** | 6-8 weeks | Skill creator, execution engine, marketplace, admin settings | P0 |
| **Phase B: Workflow Engine** | 8-10 weeks | Designer, runtime, triggers, scheduling, Logic Apps integration | P0 |
| **Phase C: Data Analytics** | 10-12 weeks | Connection manager, NL query, visualization, dashboards, all Azure services | P0 |
| **Phase D: Enhanced Integrations** | 4-6 weeks | Power BI embedding, Fabric, advanced Synapse, Spark jobs | P1 |

### Phase A Breakdown (Skills Builder)

| Task | Days | Description |
|------|------|-------------|
| A.1 Cosmos containers + data model | 2 | `skills`, `skill_executions` containers |
| A.2 Skill CRUD API | 3 | REST endpoints for skill management |
| A.3 Skill execution engine | 5 | Invoke skills via SK, log results, handle errors |
| A.4 Skills Builder UI | 8 | Visual builder with prompt editor, tool selector, test panel |
| A.5 Skill marketplace | 5 | Browse, search, install, publish, approval workflow |
| A.6 Chat integration | 3 | `/skill-name` invocation, natural language triggers |
| A.7 Admin settings + UI | 3 | Settings defaults, admin tab, feature gates |
| A.8 Functional tests | 3 | Comprehensive test coverage |
| **Total** | **32 days** | ~6-7 weeks |

### Phase B Breakdown (Workflow Engine)

| Task | Days | Description |
|------|------|-------------|
| B.1 Cosmos containers + data model | 2 | `workflows`, `workflow_executions`, `workflow_schedules` |
| B.2 Workflow CRUD API | 3 | REST endpoints for workflow management |
| B.3 Workflow execution runtime | 8 | Step-by-step execution, error handling, async support |
| B.4 Workflow designer UI | 10 | Visual node-based canvas with Drawflow.js |
| B.5 Scheduling engine | 5 | Cron-based scheduler with Flask background tasks |
| B.6 Logic Apps integration | 8 | Browse, trigger, create, monitor via Azure SDK |
| B.7 Webhook endpoint | 3 | Inbound webhook for Logic Apps and external triggers |
| B.8 Workflow templates | 3 | Pre-built templates + template marketplace |
| B.9 Admin settings + UI | 3 | Settings, admin tab, monitoring dashboard |
| B.10 Functional tests | 5 | Comprehensive test coverage |
| **Total** | **50 days** | ~10-12 weeks |

### Phase C Breakdown (Data Analytics)

| Task | Days | Description |
|------|------|-------------|
| C.1 Data connection manager | 5 | Connection CRUD, test, Key Vault integration |
| C.2 Connection admin UI | 5 | Admin panel for managing data connections |
| C.3 Synapse Analytics plugin | 8 | SQL pools, pipeline triggers, schema discovery |
| C.4 Enhanced Databricks plugin | 5 | Workspace browser, Unity Catalog, notebooks |
| C.5 ADLS Gen2 browser plugin | 5 | File browsing, Parquet/CSV preview |
| C.6 Enhanced Cosmos analytics | 3 | Cross-partition queries, container stats |
| C.7 Natural language query UI | 5 | Chat-based query with SQL approval flow |
| C.8 Query result visualization | 8 | Chart.js integration, auto-chart suggestion |
| C.9 Dashboard builder | 10 | Grid layout, pinned charts, auto-refresh |
| C.10 Power BI embedding | 5 | Report listing, embedding, RLS |
| C.11 Admin settings + UI | 3 | Settings, admin tabs, connection scoping |
| C.12 Functional tests | 5 | Comprehensive test coverage |
| **Total** | **67 days** | ~13-15 weeks |

**Grand Total: ~149 engineering days (~30-35 weeks)**

---

## 10. Approval

| Role | Name | Status | Date |
|------|------|--------|------|
| Product Owner | | Pending | |
| Tech Lead | | Pending | |
| Security | | Pending | |

---

## Appendix

### A. Existing Plugin Architecture (Leverage Points)

SimpleChat already has a mature plugin system that these features build upon:

```
BasePlugin (abstract)
  |-- metadata property (name, type, description, methods)
  |-- @kernel_function decorator for exposed functions
  |-- Manifest-driven configuration (JSON)
  |-- Key Vault secret storage (__Secret fields)
  |-- Health checking + invocation logging
  |
  |-- SQLQueryPlugin (5 DB types)
  |-- DatabricksTablePlugin (REST API)
  |-- LogAnalyticsPlugin (KQL)
  |-- OpenApiPlugin (any REST API)
  |-- MCPPlugin (external tool servers)
  |-- BlobStoragePlugin, QueueStoragePlugin
  |-- MSGraphPlugin
  |-- MathPlugin, TextPlugin, EmbeddingPlugin
  |-- FactMemoryPlugin
```

**Key insight**: Skills are essentially user-created plugins with a visual manifest builder. The entire plugin loading, execution, and logging infrastructure is reused.

### B. Azure SDK Reference

| Service | SDK Package | Auth Methods |
|---------|------------|-------------|
| Logic Apps | `azure-mgmt-logic` | Managed Identity, Service Principal |
| Synapse Analytics | `azure-synapse-artifacts`, `azure-synapse-spark` | Managed Identity |
| Databricks | `databricks-sdk` | PAT, Service Principal, Azure AD |
| Data Lake Gen2 | `azure-storage-file-datalake` | Managed Identity, Key |
| Cosmos DB | `azure-cosmos` (installed) | Managed Identity, Key |
| SQL Database | `pyodbc` (installed) | Connection string, MI |
| Power BI | REST API v1.0 | Azure AD token |
| Log Analytics | `azure-monitor-query` (installed) | Managed Identity |
| Key Vault | `azure-keyvault-secrets` (installed) | Managed Identity |

### C. Frontend Library Options

| Feature | Library | Size | Notes |
|---------|---------|------|-------|
| Workflow Designer | Sequential Workflow Designer | 30KB | Vanilla JS/TS, zero deps, MIT, CDN-loadable, step-based |
| Workflow Designer (DAG) | Drawflow.js | 15KB | Vanilla JS, zero deps, MIT, full DAG support (Tier 2) |
| Charts | Chart.js | 200KB | Canvas-based, Bootstrap compatible |
| Dashboard Grid | Gridstack.js | 30KB | Drag-and-drop grid layout |
| Code Editor (SQL) | CodeMirror 6 | 150KB | Syntax highlighting for SQL/KQL |
| Table Rendering | Simple-DataTables | 20KB | Sortable, filterable, paginated |
| Power BI Embedding | powerbi-client | 100KB | Official Microsoft JS SDK, CDN |

**Workflow Designer Recommendation (from research):**
- **Tier 1: Sequential Workflow Designer** — zero external deps, pure TypeScript/SVG, CDN-loadable, step-based flows covering 80% of use cases. Best fit for Bootstrap 5 + vanilla JS constraint.
- **Tier 2: Drawflow.js** — add later for full DAG/branching support if needed.
- **NOT recommended**: React Flow (requires React), n8n embed (requires n8n server), Logic Apps designer (React monorepo, too complex to embed).

**Logic Apps Designer Note:** The LogicAppsUX open-source React monorepo cannot be practically embedded in our vanilla JS frontend. Instead, build a form-based workflow definition editor that generates Logic Apps Workflow Definition Language JSON via the `azure-mgmt-logic` SDK.

### D. Data Model: Skill Definition

```json
{
  "id": "skill_uuid",
  "name": "summarize-meeting",
  "display_name": "Summarize Meeting Transcript",
  "description": "Creates a structured summary from meeting transcripts",
  "version": "1.0",
  "type": "prompt_skill",
  "author_id": "user_uuid",
  "workspace_id": "workspace_uuid",
  "scope": "group",
  "status": "published",
  "config": {
    "system_prompt": "You are an expert meeting summarizer...",
    "model": "gpt-4o",
    "max_tokens": 2000,
    "temperature": 0.3,
    "input_schema": {
      "type": "object",
      "properties": {
        "transcript": {"type": "string", "description": "Meeting transcript text"}
      },
      "required": ["transcript"]
    },
    "output_format": "markdown",
    "tools": [],
    "trigger_phrases": ["summarize meeting", "meeting summary"]
  },
  "usage_count": 142,
  "rating": 4.7,
  "created_at": "2026-03-27T00:00:00Z",
  "updated_at": "2026-03-27T00:00:00Z"
}
```

### E. Data Model: Workflow Definition

```json
{
  "id": "workflow_uuid",
  "name": "weekly-kpi-report",
  "display_name": "Weekly KPI Report",
  "description": "Queries Synapse for KPIs, formats report, sends via Logic App",
  "version": "1.0",
  "author_id": "user_uuid",
  "workspace_id": "workspace_uuid",
  "status": "active",
  "steps": [
    {
      "id": "step_1",
      "type": "data_query",
      "name": "Query KPIs",
      "config": {
        "connection_id": "synapse_conn_uuid",
        "query": "SELECT region, SUM(revenue) FROM sales GROUP BY region",
        "output_variable": "kpi_data"
      },
      "position": {"x": 100, "y": 100},
      "next": ["step_2"]
    },
    {
      "id": "step_2",
      "type": "skill_execution",
      "name": "Format Report",
      "config": {
        "skill_id": "format-report-skill",
        "input": {"data": "{{step_1.output}}"}
      },
      "position": {"x": 300, "y": 100},
      "next": ["step_3"]
    },
    {
      "id": "step_3",
      "type": "logic_app_trigger",
      "name": "Send to Teams",
      "config": {
        "logic_app_id": "/subscriptions/.../Microsoft.Logic/workflows/send-teams-message",
        "body": {"message": "{{step_2.output}}"}
      },
      "position": {"x": 500, "y": 100},
      "next": []
    }
  ],
  "schedule": {
    "enabled": true,
    "cron": "0 9 * * 1",
    "timezone": "America/New_York"
  },
  "error_policy": {
    "retry_count": 2,
    "retry_delay_seconds": 30,
    "on_failure": "fail_fast"
  },
  "created_at": "2026-03-27T00:00:00Z"
}
```

### F. Data Model: Data Connection

```json
{
  "id": "connection_uuid",
  "name": "production-synapse",
  "display_name": "Production Synapse Warehouse",
  "type": "synapse",
  "scope": "global",
  "auth": {
    "type": "managed_identity",
    "endpoint": "https://myworkspace.sql.azuresynapse.net",
    "database": "dedicated_pool_1"
  },
  "metadata": {
    "tables_discovered": 142,
    "last_schema_sync": "2026-03-27T00:00:00Z"
  },
  "read_only": true,
  "max_rows": 10000,
  "timeout": 120,
  "created_by": "admin_user_id",
  "created_at": "2026-03-27T00:00:00Z"
}
```
