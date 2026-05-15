# Migrated Archon v1 Tasks - SimpleChat

> Frozen export 2026-05-14 during the de-Archon-v1 migration.
> **Archon project ID**: `0ff42a4e-466c-499f-92e9-c78686d82785`
> **Total tasks captured**: 29

Archon v1 was archived 2026-04. Going forward use TodoWrite (in-session) +
GitHub Issues on fgarofalo56/simplechat (cross-session).

## status: done (29)

### CRITICAL: Allowlist frontend settings instead of blocklist sanitization
_order: 113 . feature: Security . id: `00a924ab-da8a-4c58-bafb-431a12c075ba`_

COMPLETED: Created FRONTEND_SETTINGS_ALLOWLIST frozenset in functions_settings.py with ~45 explicitly safe keys. Added get_frontend_settings() function. Updated base.html to use {{ frontend_settings|tojson|safe }} instead of dumping raw settings. Updated inject_settings() in app.py to provide frontend_settings context variable.

### Advanced RAG - Phase 1: Search Quality Foundation
_order: 112 . feature: advanced-rag . id: `e6853701-5ae0-4d61-86ab-2f31744d9aa0`_

DUPLICATE - Phase 1 already completed. See task 549134f6. All code implemented in functions_reranking.py, functions_context_optimization.py, functions_search.py. All 9 functional tests pass. Deployed to Azure.

### CRITICAL: Fix broken stream cancellation in chat-streaming.js
_order: 111 . feature: Chat . id: `6966ea4b-e5ae-40e6-b69b-3dd485ca65c5`_

COMPLETED: Added AbortController + ReadableStream reader cancellation to chat-streaming.js. Added currentAbortController and currentStreamReader module-level variables. Updated sendMessageWithStreaming() to create AbortController, pass signal to fetch, store reader reference. Rewrote cancelStreaming() to properly abort fetch, cancel reader, close EventSource, remove cursor, hide loading. Added AbortError suppression.

### CRITICAL: Fix OData injection vulnerability in search filter construction
_order: 109 . feature: Security . id: `88d5b6bd-6f7b-4411-852b-8cd1178447fd`_

COMPLETED: Created sanitize_odata_value() function in functions_search.py that escapes single quotes and strips dangerous characters. Applied to ALL OData filter interpolations in functions_search.py (~30+ locations) and functions_documents.py (2 locations). Also added int() casting for version filters.

### HIGH: Add rate limiting to all API endpoints (flask-limiter)
_order: 106 . feature: Security . id: `533ead2c-ee03-4f46-acd7-da75d01d0f12`_

COMPLETED: Added flask-limiter==3.12 to requirements.txt. Configured Limiter in app.py with user-based rate limiting (300 req/min default). Uses get_user_identifier() that tries user ID first, falls back to IP. Health check endpoints exempted.

### HIGH: Add Content Security Policy headers (flask-talisman)
_order: 104 . feature: Security . id: `8769030e-0f35-43de-9b59-7e1bffc5f0ee`_

SKIPPED - Already implemented. CSP headers already exist in config.py at lines 102-122 with a comprehensive Content-Security-Policy including default-src, script-src, style-src, img-src, connect-src, etc. No additional work needed.

### HIGH: Pin all dependencies and generate lockfile
_order: 102 . feature: Infrastructure . id: `fdd46dd9-c0cc-4fcb-83c8-9462acbd9875`_

COMPLETED: All 66 dependencies pinned to exact versions in requirements.txt. Header comment added noting the update date and instructions for upgrading.

### Advanced RAG - Phase 1: Search Quality Foundation
_order: 100 . feature: Advanced RAG . id: `549134f6-584f-48cf-97f2-96a4e14f7ffd`_

Phase 1 COMPLETE. All 7 tasks implemented, tested, deployed to Azure.\n\nTasks completed:\n1.1 Capture reranker scores/captions in extract_search_results()\n1.2 tiktoken token counting utility (functions_context_optimization.py)\n1.3 Lost-in-the-middle attention reordering (functions_reranking.py)\n1.4 Cohere Rerank v4 Fast deployed on Azure AI Foundry (deployment: cohere-rerank-v4-fast)\n1.5 Cohere reranking integration in hybrid_search() pipeline\n1.6 Search quality metrics logging to Application Insights\n1.7 Admin settings UI with Search Quality tab\n\nAll 9 functional tests pass. Deployed to Azure Container Apps and verified.

### Skills Builder - Phase 1: Foundation (Cosmos, CRUD, Settings)
_order: 100 . feature: Skills Builder . id: `8a08a7f5-5cf6-4745-a8ab-7a32ab02083d`_

Create skills/skill_executions Cosmos containers, functions_skills.py CRUD, route_backend_skills.py REST API, admin settings. 4 tasks.

### HIGH: Add lint + smoke tests to CI/CD pipeline
_order: 100 . feature: Infrastructure . id: `25466116-af97-42dc-bb8d-e3b7102a5d75`_

COMPLETED: Added test job to .github/workflows/docker_image_publish.yml that runs before build (needs: test). Test job includes: Python 3.12 setup, pip install dependencies + flake8, py_compile syntax check on all .py files, flake8 lint for critical errors (E9, F63, F7, F82). Updated actions/checkout from v3 to v4.

### Advanced RAG - Phase 2: Web & GitHub Crawling
_order: 98 . feature: advanced-rag . id: `bc3b4de6-399b-415a-9f35-4a3119263046`_

DUPLICATE - Phase 2 already completed. See task 136411b4. All code implemented in functions_web_ingestion.py (529 lines), route_backend_web_ingestion.py (529 lines). Dependencies added. Settings configured. Functional tests created.

### Skills Builder - Phase 3: Builder UI + Marketplace
_order: 95 . feature: Skills Builder . id: `20b5b2dc-53d6-46ad-91f2-cb931e8861c4`_

Visual skill creator page, workspace skills tab, marketplace page, test panel, approval modal. Combines plan phases 3-4.

### HIGH: Extract group_workspaces.html inline JS to modular files
_order: 92 . feature: Frontend . id: `484fd4f2-92ed-48b1-aa3a-d245a57a9eab`_

COMPLETED: Extracted ~3,600 lines of inline JS from group_workspaces.html into 7 modular files:
- group-navigation.js (442 lines, 8 functions: state mgmt, navigation, role display)
- group-documents.js (1,318 lines, 26 functions: document CRUD, filtering, pagination, selection)
- group-upload.js (336 lines, 12 functions: file upload with progress, drag-drop)
- group-prompts.js (343 lines, 7 functions: prompt management, pagination)
- group-grid-view.js (680 lines, 18 functions: grid/folder view, tag helpers, sort)
- group-tags.js (267 lines, 10 functions: tag management modal, CRUD)
- group-init.js (237 lines: modals, editors, filter toggles, DOMContentLoaded init)

Template reduced from 4,908 to 1,312 lines. All 3 Jinja2 variables moved to window.* config block. No Jinja2 syntax in any external JS file.

### Advanced RAG - Phase 2: Web & GitHub Crawling
_order: 90 . feature: Advanced RAG . id: `136411b4-e0fc-4d09-903f-99396d3b2ed3`_

URL ingestion, sitemap crawling, GitHub import, search index additions, UI, progress tracking, admin settings. 8 tasks.

### HIGH: Replace alert()/confirm() with Bootstrap notifications + reduce globals
_order: 90 . feature: Frontend . id: `26dcfbd7-08e2-444d-85f7-da57d1fd5829`_

COMPLETED: Replaced ALL native alert() and confirm() calls across the entire JS codebase with Bootstrap showGlobalToast() and showGlobalConfirm() utilities. Created global-toast.js with IIFE pattern providing window.showGlobalToast(message, variant, duration) and window.showGlobalConfirm(message, title) returning Promise<boolean>. Converted 23+ JS files across admin/, chat/, group/, public/, and workspace/ directories. Zero remaining active alert/confirm calls (only commented-out and third-party library code excluded). Also removed duplicate global-toast.js script tag from base.html. VERSION bumped to 0.239.008.

### Advanced RAG - Phase 3: MCP Client Support
_order: 85 . feature: advanced-rag . id: `1a828091-dfe2-454d-8cfc-494ace0ceaa8`_

DUPLICATE - Phase 3 already completed. See task a730cc8a. All code implemented in mcp_plugin_factory.py (249 lines). SK integration done. Security, logging, settings all configured. Functional tests created.

### STRATEGIC: Refactor config.py god-file into App Factory pattern
_order: 85 . feature: Architecture . id: `a5d549aa-fc1e-4ad1-8219-45a5c48c4690`_

config.py is ~800 lines with 96 imports. It initializes Cosmos DB clients at module import time, registers all Flask routes via star-imports, and holds app configuration + database init + route registration + middleware setup in one file. Makes isolated unit testing nearly impossible.

Impact: Testability, reliability, startup robustness
Fix: Split into app_factory.py (create_app pattern), database.py, routes/__init__.py. Enables proper testing, multi-worker compatibility, and clean startup.

Files: config.py → app_factory.py, database.py, routes/__init__.py
Effort: 2-3 days
Priority: STRATEGIC REWRITE — unlocks testability and multi-worker deployment

### Advanced RAG - Phase 3: MCP Client Support
_order: 80 . feature: Advanced RAG . id: `a730cc8a-d7d0-4986-a617-dd131bec7cdf`_

SK MCP dependency, plugin factory, SK loader integration, admin UI, connection test, security, logging, settings. 8 tasks.

### MEDIUM: Migrate Cosmos DB partition keys from /id to logical keys
_order: 79 . feature: Database . id: `4e417dfe-f416-4b5a-9bac-5eeb11147661`_

Most Cosmos DB containers use /id as partition key, causing cross-partition fan-out on every query that doesn't filter by id. Read-heavy patterns (list all documents in workspace) are expensive. As data grows, RU consumption scales poorly.

Impact: Performance, cost at scale
Fix: Migrate to logical partition keys (/workspace_id, /user_id) during a planned maintenance window.

Files: Cosmos DB container definitions, functions_documents.py, functions_group.py, etc.
Effort: 1-2 days + data migration window
Priority: MEDIUM — Plan for when scaling becomes an issue

### MEDIUM: Add malware scanning on document upload
_order: 77 . feature: Security . id: `400ee588-e1e4-4b1e-991c-df52d33a793c`_

Documents are uploaded and chunked without any content scanning. Users can upload malicious files that get indexed into Azure AI Search and potentially served to other users.

Impact: Security — malware propagation vector
Fix: Integrate Azure Defender for Storage or ClamAV scanning before document indexing.

Files: functions_documents.py (upload handlers), route_backend_documents.py
Effort: 4-6 hours
Priority: MEDIUM

### MEDIUM: Implement distributed MSAL token cache for multi-worker
_order: 75 . feature: Authentication . id: `bf30e466-2e9d-420f-97c3-5370951aad08`_

COMPLETED: Added documentation to _load_cache() in functions_authentication.py explaining that the MSAL token cache is already distributed when Redis sessions are enabled. The Flask session is backed by Redis when enable_redis_cache=True, making session["token_cache"] automatically distributed across all instances. No code change needed — only documentation added.

### Advanced RAG - Phase 4: Graph RAG
_order: 73 . feature: advanced-rag . id: `cb88a752-d49f-4f78-a9f2-57d0f139efc8`_

DUPLICATE - Phase 4 already completed. See task ba4cd64f. All code implemented: functions_graph_entities.py (287 lines), functions_graph_rag.py (278 lines), functions_graph_communities.py (206 lines). Cosmos containers configured. Functional tests created.

### MEDIUM: Fix uncanceled setInterval polling causing memory leaks
_order: 73 . feature: Frontend . id: `bf9735c3-bffb-47ff-91d6-4b8d259b9461`_

COMPLETED: Added Page Visibility API optimization to all 3 document polling implementations. When tab is hidden, all setInterval polls are paused. When tab becomes visible, polls are resumed. Added activePollIntervals Map to track interval IDs for proper cleanup. Fixed the 'Ideally clear interval' TODO in group_workspaces.html delete handler. Files modified: workspace-documents.js, public_workspace.js, group_workspaces.html.

### Advanced RAG - Phase 4: Graph RAG
_order: 70 . feature: Advanced RAG . id: `ba4cd64f-0adb-45c3-9a5a-08f611aba2bd`_

Cosmos containers, entity extraction, resolution, graph traversal, chat integration, communities, query routing, admin settings, UI. 11 tasks.

### Advanced RAG - Phase 5: Context Optimization & Advanced Search
_order: 61 . feature: advanced-rag . id: `4732c3f6-6817-4e97-9aa1-4fb2904a742b`_

DUPLICATE - Phase 5 already completed. See task 51b415bb. All code implemented: functions_context_optimization.py (290 lines), functions_query_expansion.py (132 lines). Token budgeting, summarization, multi-query, HyDE, MMR, compression all implemented. Functional tests created.

### Advanced RAG - Phase 5: Context Optimization & Advanced Search
_order: 60 . feature: Advanced RAG . id: `51b415bb-092a-4d24-afc2-6539eaf012c9`_

Summarization, token budgeting, map-reduce, multi-query, HyDE, MMR, contextual compression, admin settings. 8 tasks.

### LOW: Remove dead weight — unused imports, commented code, duplicate utils, print() calls
_order: 60 . feature: Code Quality . id: `bb19d4b3-9bbf-4b6e-abc0-f64da550c36a`_

COMPLETED: Converted 441+ print() calls to debug_print() across 45+ Python files. Added debug_print import to all route and function files that needed it. Removed emoji debug markers (🔥🤖🔍). Excluded infrastructure files (functions_appinsights.py, functions_debug.py, config.py, app.py) which have intentional print() calls. All 125 Python files pass syntax check. VERSION bumped to 0.239.007.

### Fix SQL injection vulnerabilities in route_frontend_chats.py
_order: 0 . feature: security . id: `9e07bbea-80d2-4097-8992-3701a5b06a6d`_

Convert all f-string interpolated Cosmos DB queries to use parameterized queries to prevent SQL injection attacks. Fixed 4 instances of vulnerable queries involving conversation_id parameter.

### Fix SQL injection vulnerabilities in route_backend_control_center.py
_order: 0 . id: `5bcd11c9-3b3d-447c-b6cf-e185e487a876`_

Convert f-string interpolated Cosmos DB queries to parameterized queries:
- CSV export queries (lines 2084, 2463)
- Count queries (lines 2110, 2489, 5535) 
- Paginated queries (lines 2123, 2502, 5548)
- Activity queries (lines 3111, 3120, 4029)
- Validate pagination parameters
