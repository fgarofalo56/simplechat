# Implementation Plan: Advanced RAG Features for SimpleChat

**PRD Reference:** PRPs/prds/advanced-rag-features.prd.md
**Created:** 2026-03-25
**Author:** Claude Code (AI-assisted)
**Status:** Draft
**Estimated Effort:** 51.5 engineering days (~10-13 weeks)
**Current Version:** 0.239.002

---

## Overview

This plan transforms SimpleChat from a file-upload RAG application into a comprehensive knowledge intelligence platform. Five independently toggleable features are implemented across five phases:

1. **Search Quality Foundation** — Reranking, lost-in-the-middle reordering, token counting
2. **Web & GitHub Crawling** — URL ingestion, sitemap crawling, GitHub repo import
3. **MCP Client Support** — External tool servers for Semantic Kernel agents
4. **Graph RAG** — Entity extraction, knowledge graph traversal, community detection
5. **Context Optimization** — Token budgeting, conversation summarization, query expansion

Each feature is admin-toggleable via existing settings infrastructure. No feature is required for the others to work — they enhance each other when enabled together but degrade gracefully in isolation.

---

## Prerequisites

### Before Starting
- [ ] PRD approved and open questions resolved (especially #4: Crawl4AI in Phase 1? and #5: LazyGraphRAG evaluation)
- [ ] Cohere Rerank v4 Fast deployed as serverless endpoint on Azure AI Foundry
- [ ] Development environment running with Cosmos DB, Azure AI Search, and Azure OpenAI access
- [ ] Current `main` branch clean, all tests passing

### Required Knowledge
- Azure AI Search SDK (hybrid search, semantic ranking, index schema updates)
- Azure OpenAI SDK (embeddings, chat completions, JSON mode)
- Cosmos DB NoSQL SDK (containers, partitioning, queries)
- Semantic Kernel plugin architecture (existing in `semantic_kernel_loader.py`)
- Flask-Executor background tasks (already used for document processing)
- SimpleChat settings system (`functions_settings.py` → `get_settings()` / `sanitize_settings_for_user()`)

### Dependencies
| Dependency | Status | Notes |
|------------|--------|-------|
| Azure AI Search indexes (user/group/public) | Available | Existing infrastructure |
| Azure OpenAI (embeddings + chat) | Available | Existing infrastructure |
| Cosmos DB (SimpleChat database) | Available | Need 3 new containers for Graph RAG |
| Cohere Rerank v4 Fast (Azure AI Foundry) | **Needs setup** | Deploy as serverless endpoint before Phase 1 |
| `semantic-kernel>=1.39.4` | Available | Already in requirements.txt (line 44) |
| `beautifulsoup4`, `html2text` | Available | Already in requirements.txt (lines 38, 53) |
| `flask-executor` | Available | Already configured with max 30 workers |

---

## Implementation Phases

### Phase 1: Search Quality Foundation [Days 1-8]

**Objective:** Improve search relevance with reranking, attention optimization, and token infrastructure. This phase lays the groundwork that Phases 4 and 5 build upon.

**Why first:** Highest user-visible impact with lowest risk. Reranking alone delivers 20-35% accuracy improvement. Token counting infrastructure is needed by Phase 5.

#### Tasks

##### 1.1 Capture Semantic Ranker Scores and Captions
- **Description:** Modify `extract_search_results()` in `functions_search.py` to capture `@search.rerankerScore` (0-4 range) and `@search.captions` from Azure AI Search semantic ranking. These are already returned by the API but not captured.
- **Files:** `application/single_app/functions_search.py` (line 566-589)
- **Estimated Time:** 4 hours
- **Dependencies:** None
- **Implementation Notes:**
  ```python
  # In extract_search_results(), add to the extracted dict:
  "reranker_score": r.get("@search.rerankerScore"),
  "captions": r.get("@search.captions"),
  ```
  Also update `hybrid_search()` to include `@search.rerankerScore` and `@search.captions` in the `select` parameter of each search call.
- **Validation:**
  - [ ] Search results include `reranker_score` field (0-4 float or None)
  - [ ] Search results include `captions` field (list of extracted captions or None)
  - [ ] Existing search behavior unchanged when fields are absent

##### 1.2 Add tiktoken Token Counting Utility
- **Description:** Create `functions_context_optimization.py` with `count_tokens()` function using tiktoken. This will be the shared token counting utility for all phases.
- **Files:** New: `application/single_app/functions_context_optimization.py`
- **Estimated Time:** 4 hours
- **Dependencies:** `tiktoken>=0.7.0` (add to requirements.txt)
- **Implementation Notes:**
  ```python
  # functions_context_optimization.py
  import tiktoken

  def count_tokens(text: str, model: str = "gpt-4o") -> int:
      """Count tokens for a given text and model."""
      try:
          enc = tiktoken.encoding_for_model(model)
      except KeyError:
          enc = tiktoken.get_encoding("cl100k_base")
      return len(enc.encode(text))

  def count_messages_tokens(messages: list, model: str = "gpt-4o") -> int:
      """Count tokens for a list of chat messages."""
      total = 0
      for msg in messages:
          total += 4  # message overhead
          total += count_tokens(msg.get("content", ""), model)
          total += count_tokens(msg.get("role", ""), model)
      total += 2  # reply priming
      return total
  ```
- **Validation:**
  - [ ] `count_tokens("hello world", "gpt-4o")` returns correct token count
  - [ ] Handles unknown model names gracefully (falls back to cl100k_base)

##### 1.3 Implement Lost-in-the-Middle Reordering
- **Description:** Create `functions_reranking.py` with attention-optimized document reordering. LLMs attend most to the beginning and end of context, so place most relevant docs at start and end.
- **Files:** New: `application/single_app/functions_reranking.py`
- **Estimated Time:** 4 hours
- **Dependencies:** None (pure Python)
- **Implementation Notes:**
  ```python
  # functions_reranking.py
  def reorder_for_attention(documents: list) -> list:
      """Place highest-relevance docs at start and end of context.
      LLMs attend most to beginning and end, less to the middle."""
      if len(documents) <= 2:
          return documents
      top_half = documents[::2]     # Even indices (0, 2, 4, ...)
      bottom_half = documents[1::2] # Odd indices (1, 3, 5, ...)
      return top_half + list(reversed(bottom_half))
  ```
- **Validation:**
  - [ ] Documents reordered with highest-scoring at start and end
  - [ ] Empty/single/double document lists handled correctly
  - [ ] Unit test with known input/output

##### 1.4 Deploy Cohere Rerank v4 on Azure AI Foundry
- **Description:** Deploy `Cohere-rerank-v4.0-fast` as a serverless (pay-per-use) endpoint via Azure AI Foundry. Document the endpoint URL and API key in deployment notes.
- **Files:** Azure Portal (no code changes)
- **Estimated Time:** 4 hours
- **Dependencies:** Azure AI Foundry access, subscription with Cohere model access
- **Validation:**
  - [ ] Endpoint URL responds to health check
  - [ ] Test rerank API call with sample query + 5 documents returns ranked results
  - [ ] API key stored in Key Vault or admin settings

##### 1.5 Implement Cohere Reranking Integration
- **Description:** Add `rerank_with_cohere()` to `functions_reranking.py`. Integrate into the search pipeline in `functions_search.py` as a post-retrieval hook, guarded by `enable_cohere_rerank` setting.
- **Files:** `application/single_app/functions_reranking.py`, `application/single_app/functions_search.py`
- **Estimated Time:** 12 hours (1.5 days)
- **Dependencies:** Task 1.4 (Cohere deployment), `cohere>=5.0.0` (add to requirements.txt)
- **Implementation Notes:**
  ```python
  # In functions_reranking.py
  import cohere

  def rerank_with_cohere(query: str, documents: list, settings: dict, top_n: int = 10) -> list:
      """Rerank search results using Cohere Rerank v4 on Azure AI Foundry."""
      client = cohere.ClientV2(
          api_key=settings.get("cohere_rerank_api_key"),
          base_url=settings.get("cohere_rerank_endpoint"),
      )
      doc_texts = [doc["chunk_text"] for doc in documents]
      results = client.rerank(
          model="model",
          documents=doc_texts,
          query=query,
          top_n=top_n,
      )
      reranked = []
      for result in results.results:
          doc = documents[result.index].copy()
          doc["rerank_score"] = result.relevance_score
          reranked.append(doc)
      return reranked
  ```
  In `functions_search.py` → `hybrid_search()`, add a post-processing step after the existing merge/sort:
  ```python
  if settings.get("enable_cohere_rerank", False):
      from functions_reranking import rerank_with_cohere
      combined_results = rerank_with_cohere(query, combined_results, settings,
                                             top_n=settings.get("cohere_rerank_top_n", 10))
  ```
- **Validation:**
  - [ ] With `enable_cohere_rerank=True`: results reranked, `rerank_score` present
  - [ ] With `enable_cohere_rerank=False`: no API call made, behavior unchanged
  - [ ] Graceful error handling if Cohere endpoint is unavailable
  - [ ] Performance: < 500ms added latency for 30 documents

##### 1.6 Add Retrieval Quality Metrics Logging
- **Description:** Log retrieval metrics (result count, score distribution, rerank displacement, source diversity) using existing `log_event()` from `functions_appinsights.py`.
- **Files:** `application/single_app/functions_search.py`, `application/single_app/functions_reranking.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Tasks 1.1, 1.5
- **Implementation Notes:**
  ```python
  # Log after search + optional reranking
  log_event("search_quality_metrics", level=logging.INFO,
      query_length=len(query),
      result_count=len(results),
      avg_score=avg_score,
      reranked=was_reranked,
      rerank_displacement=avg_displacement,  # avg position change
      source_diversity=unique_docs / total_chunks,
      top_score=results[0]["score"] if results else 0,
  )
  ```
- **Validation:**
  - [ ] Metrics appear in Application Insights after search queries
  - [ ] Metrics include before/after reranking comparison when reranking is enabled

##### 1.7 Admin Settings UI for Search Quality
- **Description:** Add search quality settings to the admin settings panel. Settings: `enable_cohere_rerank`, `cohere_rerank_endpoint`, `cohere_rerank_api_key`, `cohere_rerank_top_n`, `enable_attention_reorder`.
- **Files:** `application/single_app/functions_settings.py` (add defaults), `application/single_app/route_frontend_admin_settings.py`, `application/single_app/static/js/admin/admin_settings.js`
- **Estimated Time:** 12 hours (1.5 days)
- **Dependencies:** None (settings are independent)
- **Implementation Notes:**
  Add to `default_settings` in `functions_settings.py`:
  ```python
  'enable_cohere_rerank': False,
  'cohere_rerank_endpoint': '',
  'cohere_rerank_api_key': '',
  'cohere_rerank_top_n': 10,
  'enable_attention_reorder': True,  # Default ON (low cost, high value)
  ```
  Add `cohere_rerank_api_key` and `cohere_rerank_endpoint` to the sanitization list in `sanitize_settings_for_user()`.
- **Validation:**
  - [ ] Settings appear in admin panel under "Search Quality" section
  - [ ] API key is sanitized (hidden from non-admin views)
  - [ ] Toggle enable/disable works and persists to Cosmos DB
  - [ ] Default values applied for new installations

#### Phase 1 Validation
```bash
# Verify search results include reranker scores
# Verify reranking toggle works via admin settings
# Verify attention reordering produces correct document order
# Verify token counting returns accurate results
# Check Application Insights for search quality metrics
```

---

### Phase 2: Web & GitHub Crawling [Days 9-20]

**Objective:** Enable users to add web content to their RAG workspaces by pasting URLs, crawling sitemaps, or importing GitHub repos.

**Why second:** Addresses the #1 user friction point (manual download-upload workflow) and is mostly additive (new files, new routes) with minimal risk to existing code.

#### Tasks

##### 2.1 Single URL Ingestion Engine
- **Description:** Create `functions_web_ingestion.py` with `ingest_url()` function using Trafilatura (primary) with BeautifulSoup + html2text fallback. Extract content, metadata, and convert to markdown.
- **Files:** New: `application/single_app/functions_web_ingestion.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** `trafilatura>=2.0.0` (add to requirements.txt)
- **Implementation Notes:**
  ```python
  # functions_web_ingestion.py
  import trafilatura
  from bs4 import BeautifulSoup
  import html2text

  def ingest_url(url: str, settings: dict) -> dict:
      """Fetch and extract content from a URL.
      Returns: {title, content_markdown, author, date, description, source_url, content_hash}
      """
      # 1. Validate URL (SSRF prevention: block private IPs)
      validate_url(url, settings)

      # 2. Try Trafilatura first (better metadata, cleaner extraction)
      downloaded = trafilatura.fetch_url(url)
      if downloaded:
          content = trafilatura.extract(downloaded, include_comments=False,
                                         include_tables=True, output_format="markdown")
          metadata = trafilatura.extract_metadata(downloaded)
          if content:
              return build_result(content, metadata, url)

      # 3. Fallback: BeautifulSoup + html2text
      ...
  ```
  Key patterns:
  - `robots.txt` check before crawling
  - Rate limiting (1.5-3.5s random delay)
  - SimHash deduplication fingerprint stored per URL
  - Content hash (SHA-256) for re-crawl change detection
  - Integration with existing `save_chunks()` pipeline
- **Validation:**
  - [ ] Successfully extracts content from static HTML pages
  - [ ] Metadata (title, author, date) extracted when available
  - [ ] Markdown output suitable for existing chunking pipeline
  - [ ] SSRF prevention blocks private IP ranges

##### 2.2 API Routes for URL Ingestion
- **Description:** Create `route_backend_web_ingestion.py` with endpoints for URL ingestion, crawl status, and re-crawl. Uses existing auth decorators and background task pattern.
- **Files:** New: `application/single_app/route_backend_web_ingestion.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 2.1
- **Implementation Notes:**
  New endpoints:
  ```python
  POST /api/workspace/documents/url          # Single URL ingestion
  POST /api/workspace/documents/crawl        # Sitemap crawl
  POST /api/workspace/documents/github       # GitHub repo import
  GET  /api/workspace/documents/crawl/status/<job_id>  # Crawl status
  POST /api/workspace/documents/url/<doc_id>/recrawl    # Re-crawl
  ```
  Each route follows existing patterns:
  - `@app.route(...)` + `@swagger_route(security=get_auth_security())` + `@login_required` + `@user_required`
  - `@enabled_required("enable_web_ingestion")` feature gate
  - Background execution via `flask_executor.submit()`
  - Store crawl job status in Cosmos DB for progress tracking
- **Validation:**
  - [ ] All routes require authentication and feature flag
  - [ ] Background task executes without blocking request
  - [ ] Crawl status returns progress (pages processed/total)

##### 2.3 Azure AI Search Index Schema Additions
- **Description:** Add `source_url`, `source_type`, and `content_hash` fields to all three search indexes (user, group, public). These are additive, non-breaking changes.
- **Files:** Index update script (new), `application/single_app/functions_documents.py` (update `save_chunks()`)
- **Estimated Time:** 4 hours
- **Dependencies:** None
- **Implementation Notes:**
  New index fields:
  ```python
  SimpleField(name="source_url", type=SearchFieldDataType.String, filterable=True),
  SimpleField(name="source_type", type=SearchFieldDataType.String, filterable=True, facetable=True),
  SimpleField(name="content_hash", type=SearchFieldDataType.String),
  ```
  Update `save_chunks()` to include these fields in chunk documents (default `source_type="file"` for existing uploads, `"web"` or `"github"` for new ingestion).
- **Validation:**
  - [ ] Existing documents unaffected (fields are optional/additive)
  - [ ] New fields queryable and filterable
  - [ ] Existing file uploads set `source_type="file"`

##### 2.4 UI: "Import from URL" Tab
- **Description:** Add an "Import from URL" tab alongside the existing file upload area in workspace document management. Tab contains: URL text field, type dropdown (Single Page / Sitemap / GitHub), options section, submit button, progress indicator.
- **Files:** Templates in `application/single_app/templates/`, JS in `application/single_app/static/js/workspace/`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Task 2.2 (API endpoints)
- **Implementation Notes:**
  - Bootstrap 5 tab component alongside existing file upload
  - URL validation client-side before submission
  - Progress polling via `GET /api/workspace/documents/crawl/status/{job_id}`
  - Document list icons: globe for web, GitHub logo for repos, file icon for uploads
  - Re-crawl button on web-sourced documents
  - Show `source_url` as clickable link in document details
- **Validation:**
  - [ ] URL tab visible when `enable_web_ingestion` is true
  - [ ] Hidden when feature is disabled
  - [ ] Form submission calls correct API endpoint based on type
  - [ ] Progress indicator updates during crawl

##### 2.5 Sitemap-Based Crawling
- **Description:** Add sitemap parsing and multi-page crawling to `functions_web_ingestion.py`. Parse sitemap XML to extract URLs, then crawl each with rate limiting and deduplication.
- **Files:** `application/single_app/functions_web_ingestion.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Tasks 2.1, `ultimate-sitemap-parser>=1.5.0`, `simhash>=2.1.0`
- **Implementation Notes:**
  ```python
  def crawl_sitemap(sitemap_url: str, settings: dict, max_depth: int = 2,
                    max_pages: int = 100, job_id: str = None) -> dict:
      """Crawl all URLs from a sitemap with depth and page limits."""
      # 1. Parse sitemap (handle nested sitemaps)
      # 2. Filter by allowed_domains setting
      # 3. Queue URLs up to max_pages
      # 4. Process each URL via ingest_url() with rate limiting
      # 5. Update job status in Cosmos DB after each page
      # 6. Deduplication via SimHash fingerprinting
  ```
- **Validation:**
  - [ ] Parses standard sitemap.xml format
  - [ ] Respects `max_depth` and `max_pages` limits
  - [ ] Rate limiting enforced (1.5-3.5s between requests)
  - [ ] Deduplication skips near-identical pages
  - [ ] Job status updates reflect progress

##### 2.6 GitHub Repository Import
- **Description:** Add GitHub repo import to `functions_web_ingestion.py` using PyGithub. Fetch README, docs, and optionally source code files. Language-aware chunking for code files.
- **Files:** `application/single_app/functions_web_ingestion.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** `PyGithub>=2.0.0`
- **Implementation Notes:**
  ```python
  def import_github_repo(repo_url: str, settings: dict, branch: str = "main",
                         include_code: bool = False, job_id: str = None) -> dict:
      """Import a GitHub repository's documentation and optionally code."""
      # 1. Parse repo URL -> owner/repo
      # 2. Authenticate via GitHub token (from settings) or anonymous
      # 3. Fetch file tree, filter by extension
      # 4. Process .md/.rst/.txt with markdown splitter
      # 5. Process code files with language-aware splitter (if include_code)
      # 6. Skip: binary, lock files, node_modules, files > 100KB
  ```
  File type handling per PRD section 4.3.
- **Validation:**
  - [ ] Imports README and docs/ directory by default
  - [ ] Code files only imported when `include_code=True`
  - [ ] Skips binary files, lock files, and oversized files
  - [ ] Language-aware chunking for code files
  - [ ] Handles private repos with GitHub token

##### 2.7 Crawl Progress/Status Tracking
- **Description:** Implement crawl job status tracking in Cosmos DB. Background tasks update job status as pages are processed. API endpoint returns current progress.
- **Files:** `application/single_app/functions_web_ingestion.py`, `application/single_app/route_backend_web_ingestion.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Tasks 2.2, 2.5, 2.6
- **Implementation Notes:**
  Store crawl jobs in existing Cosmos DB with schema:
  ```json
  {
    "id": "crawl_job_xxx",
    "type": "crawl_job",
    "user_id": "...",
    "status": "in_progress",  // queued, in_progress, completed, failed
    "total_pages": 50,
    "processed_pages": 12,
    "failed_pages": 1,
    "errors": [...],
    "created_at": "...",
    "completed_at": null
  }
  ```
- **Validation:**
  - [ ] Job status updates in real-time during crawl
  - [ ] Status endpoint returns correct progress
  - [ ] Failed pages tracked with error details

##### 2.8 Admin Settings for Web Crawling
- **Description:** Add web crawling settings to admin panel: `enable_web_ingestion`, `web_crawl_max_depth`, `web_crawl_max_pages`, `web_crawl_allowed_domains`, `enable_github_ingestion`, `github_include_code`.
- **Files:** `application/single_app/functions_settings.py`, admin UI files
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Implementation Notes:**
  Add to `default_settings`:
  ```python
  'enable_web_ingestion': False,
  'web_crawl_max_depth': 2,
  'web_crawl_max_pages': 100,
  'web_crawl_allowed_domains': [],
  'enable_github_ingestion': False,
  'github_include_code': False,
  'github_token': '',  # Add to sanitization list
  ```
- **Validation:**
  - [ ] Settings visible in admin panel
  - [ ] Feature gates work correctly
  - [ ] GitHub token sanitized from non-admin views

#### Phase 2 Validation
```bash
# Test single URL ingestion end-to-end
# Test sitemap crawl with depth/page limits
# Test GitHub import (public repo, with/without code)
# Verify web documents appear in search results with correct source_type
# Verify citations show source_url for web documents
# Test feature gates (all disabled by default)
```

---

### Phase 3: MCP Client Support [Days 21-27]

**Objective:** Enable Semantic Kernel agents to connect to external MCP servers for unlimited tool extensibility.

**Why third:** Lowest implementation effort (7 days) with high extensibility value. SK already has native MCP support — this is mostly configuration plumbing.

#### Tasks

##### 3.1 Update semantic-kernel Dependency
- **Description:** Change `semantic-kernel>=1.39.4` to `semantic-kernel[mcp]>=1.39.4` in requirements.txt. This installs the MCP SDK as a transitive dependency.
- **Files:** `application/single_app/requirements.txt` (line 44)
- **Estimated Time:** 2 hours (including testing that existing SK functionality still works)
- **Dependencies:** None
- **Validation:**
  - [ ] `pip install` succeeds with `[mcp]` extra
  - [ ] Existing SK agents still function correctly
  - [ ] MCP-related imports available: `from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin`

##### 3.2 Create MCP Plugin Factory
- **Description:** Create `mcp_plugin_factory.py` that creates MCP plugins from action manifests. Supports Streamable HTTP and SSE transports.
- **Files:** New: `application/single_app/semantic_kernel_plugins/mcp_plugin_factory.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 3.1
- **Implementation Notes:**
  ```python
  # semantic_kernel_plugins/mcp_plugin_factory.py
  from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin, MCPSsePlugin

  async def create_mcp_plugin(manifest: dict):
      """Create an MCP plugin from an action manifest."""
      transport = manifest.get("mcp_transport", "streamable_http")
      PluginClass = (MCPStreamableHttpPlugin if transport == "streamable_http"
                     else MCPSsePlugin)
      plugin = PluginClass(
          name=manifest["name"],
          description=manifest.get("description", ""),
          url=manifest["mcp_url"],
          load_tools=True,
          load_prompts=manifest.get("mcp_load_prompts", False),
          request_timeout=manifest.get("mcp_timeout", 30),
      )
      await plugin.connect()
      return plugin
  ```
  - Per-request connection lifecycle (connect at request start, close at end)
  - Tool allowlist filtering if `mcp_allowed_tools` is set
  - SSRF prevention: validate MCP URLs against allowlist + block private IPs
- **Validation:**
  - [ ] Plugin connects to a test MCP server
  - [ ] Tools from MCP server available in Semantic Kernel
  - [ ] Plugin disconnects cleanly after request

##### 3.3 Integrate MCP Type in SK Loader
- **Description:** Add `mcp_server` as a recognized action type in `load_agent_specific_plugins()` alongside the existing `openapi` type. When a plugin manifest has `type: "mcp_server"`, use the MCP factory.
- **Files:** `application/single_app/semantic_kernel_loader.py` (around line 566+)
- **Estimated Time:** 8 hours
- **Dependencies:** Task 3.2
- **Implementation Notes:**
  In the plugin loading loop within `load_agent_specific_plugins()`, add:
  ```python
  if manifest.get("type") == "mcp_server":
      if settings.get("enable_mcp_servers", False):
          plugin = await create_mcp_plugin(manifest)
          kernel.add_plugin(plugin)
  ```
  Ensure proper async handling (SK loader may need async context).
- **Validation:**
  - [ ] Agent with MCP action type loads MCP tools
  - [ ] Agent without MCP actions unaffected
  - [ ] Feature gate `enable_mcp_servers` respected

##### 3.4 Admin UI: MCP Server Action Type
- **Description:** Add MCP server as a new action type option in the agent configuration UI (the "stepper" for creating/editing agents). Fields: URL, transport type, auth type, auth header/value, timeout, tool allowlist.
- **Files:** Admin templates and JS for agent configuration
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Task 3.3
- **Implementation Notes:**
  - Add "MCP Server" option to action type dropdown
  - Show MCP-specific fields when selected: URL, transport (Streamable HTTP / SSE), auth type (None / API Key / Azure Identity), auth header, auth value, timeout, allowed tools
  - MCP manifest schema saved to Cosmos DB actions container
  - UI matches existing OpenAPI plugin configuration pattern
- **Validation:**
  - [ ] MCP server action type appears in agent configuration
  - [ ] All MCP-specific fields render and save correctly
  - [ ] Saved manifest matches expected schema

##### 3.5 MCP Connection Test Endpoint
- **Description:** Add a test endpoint that validates MCP server connectivity and lists available tools. Used by admin UI to verify configuration before saving.
- **Files:** `application/single_app/route_backend_plugins.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 3.2
- **Implementation Notes:**
  ```python
  POST /api/admin/plugins/mcp/test
  Body: { "mcp_url": "...", "mcp_transport": "streamable_http", "mcp_auth_type": "api_key", ... }
  Response: { "connected": true, "tools": [{"name": "...", "description": "..."}], "latency_ms": 250 }
  ```
- **Validation:**
  - [ ] Returns tool list for valid MCP servers
  - [ ] Returns error message for invalid URLs or timeouts
  - [ ] Respects URL allowlist setting

##### 3.6 Security: URL Allowlist and SSRF Prevention
- **Description:** Implement URL validation for MCP server connections. Block private IP ranges, enforce HTTPS in production, validate against `mcp_server_url_allowlist` setting.
- **Files:** `application/single_app/semantic_kernel_plugins/mcp_plugin_factory.py`
- **Estimated Time:** 8 hours
- **Dependencies:** None (can be done in parallel with other tasks)
- **Implementation Notes:**
  ```python
  import ipaddress, urllib.parse

  def validate_mcp_url(url: str, settings: dict):
      """Validate MCP server URL for security."""
      parsed = urllib.parse.urlparse(url)

      # Block private IPs (SSRF prevention)
      # Enforce HTTPS
      # Check against allowlist if configured
      ...
  ```
- **Validation:**
  - [ ] Private IPs (10.x, 172.16.x, 192.168.x, 127.x) blocked
  - [ ] Non-HTTPS URLs rejected in production
  - [ ] URL allowlist filtering works when configured

##### 3.7 MCP Tool Invocation Logging
- **Description:** Log MCP tool invocations using the existing `plugin_invocation_logger` pattern. Include tool name, server URL, duration, success/failure.
- **Files:** `application/single_app/semantic_kernel_plugins/mcp_plugin_factory.py`
- **Estimated Time:** 4 hours
- **Dependencies:** Task 3.2
- **Validation:**
  - [ ] MCP tool calls appear in Application Insights
  - [ ] Duration, tool name, and server URL logged

##### 3.8 Admin Settings for MCP
- **Description:** Add MCP settings: `enable_mcp_servers`, `mcp_server_url_allowlist`, `mcp_default_timeout`.
- **Files:** `application/single_app/functions_settings.py`, admin UI files
- **Estimated Time:** 4 hours
- **Dependencies:** None
- **Validation:**
  - [ ] Settings visible in admin panel
  - [ ] URL allowlist enforced when populated

#### Phase 3 Validation
```bash
# Deploy a test MCP server (e.g., Fetch MCP server)
# Create an agent with MCP server action
# Verify MCP tools appear in agent's available tools
# Test MCP tool invocation during chat
# Verify logging captures tool invocations
# Test security: blocked private IPs, HTTPS enforcement
```

---

### Phase 4: Graph RAG [Days 28-43]

**Objective:** Build a knowledge graph from uploaded documents enabling multi-hop reasoning, relationship discovery, and thematic summarization.

**Why fourth:** Most complex feature (15.5 days). Benefits from Phase 1's token counting infrastructure and is independently valuable even without other features.

#### Tasks

##### 4.1 Create Cosmos DB Containers for Graph Data
- **Description:** Add 3 new containers to the existing SimpleChat Cosmos DB database: `graph_entities`, `graph_relationships`, `graph_communities`. Configure partition keys and throughput.
- **Files:** `application/single_app/config.py`
- **Estimated Time:** 4 hours
- **Dependencies:** None
- **Implementation Notes:**
  Add container initialization in `config.py` following existing pattern:
  ```python
  cosmos_graph_entities_container = cosmos_database.get_container_client("graph_entities")
  cosmos_graph_relationships_container = cosmos_database.get_container_client("graph_relationships")
  cosmos_graph_communities_container = cosmos_database.get_container_client("graph_communities")
  ```
  Containers must be created in Azure Portal or via script with:
  - `graph_entities`: partition key `/workspace_id`, 1000 RU/s autoscale
  - `graph_relationships`: partition key `/workspace_id`, 1000 RU/s autoscale
  - `graph_communities`: partition key `/workspace_id`, 400 RU/s autoscale
- **Validation:**
  - [ ] Containers created in Cosmos DB
  - [ ] Container clients accessible from `config.py`
  - [ ] Read/write operations succeed

##### 4.2 Entity Extraction via GPT (JSON Mode)
- **Description:** Create `functions_graph_entities.py` with entity extraction using Azure OpenAI GPT in JSON mode. For each chunk, extract entities (name, type, description) and relationships (source, target, type, description).
- **Files:** New: `application/single_app/functions_graph_entities.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Task 4.1
- **Implementation Notes:**
  ```python
  # functions_graph_entities.py

  ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured knowledge from text.
  Given a text passage, extract all entities and relationships.

  For each ENTITY: entity_name, entity_type (person/organization/location/concept/technology/document/event), description
  For each RELATIONSHIP: source, target, relationship_type (WORKS_AT/MENTIONS/REPORTS_TO/USES/DEPENDS_ON/LOCATED_IN/etc.), description

  Return JSON: {"entities": [...], "relationships": [...]}"""

  def extract_entities_from_chunk(chunk_text: str, settings: dict) -> dict:
      """Extract entities and relationships from a single chunk."""
      model = settings.get("graph_rag_extraction_model", "gpt-4o-mini")
      entity_types = settings.get("graph_rag_entity_types",
          ["person", "organization", "location", "concept", "technology", "document"])

      response = gpt_client.chat.completions.create(
          model=model,
          response_format={"type": "json_object"},
          messages=[
              {"role": "system", "content": ENTITY_EXTRACTION_PROMPT},
              {"role": "user", "content": f"Entity types to extract: {entity_types}\n\nText:\n{chunk_text}"}
          ],
          max_tokens=2000,
          temperature=0,
      )
      return json.loads(response.choices[0].message.content)
  ```
- **Validation:**
  - [ ] Extracts entities with correct types from sample text
  - [ ] Extracts relationships between entities
  - [ ] JSON output parses correctly
  - [ ] Respects configurable entity types

##### 4.3 Entity Resolution and Deduplication
- **Description:** Implement two-stage entity deduplication: (1) exact match on normalized names, (2) semantic match using embedding cosine similarity > 0.85. Merges duplicate entities by combining source references.
- **Files:** `application/single_app/functions_graph_entities.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Task 4.2
- **Implementation Notes:**
  ```python
  def resolve_entity(entity: dict, workspace_id: str, settings: dict) -> str:
      """Resolve entity against existing graph. Returns entity_id (existing or new)."""
      normalized_name = normalize_entity_name(entity["entity_name"])

      # Stage 1: Exact match
      existing = query_entities_by_normalized_name(normalized_name, workspace_id)
      if existing:
          merge_entity_sources(existing["id"], entity)
          return existing["id"]

      # Stage 2: Semantic match (same type, embedding similarity > 0.85)
      embedding = generate_embedding(entity["entity_name"] + " " + entity["description"])
      similar = find_similar_entities(embedding, entity["entity_type"], workspace_id, threshold=0.85)
      if similar:
          merge_entity_sources(similar[0]["id"], entity)
          return similar[0]["id"]

      # New entity
      return create_entity(entity, embedding, workspace_id)
  ```
- **Validation:**
  - [ ] "John Smith" and "john smith" resolve to same entity
  - [ ] "JS" and "JavaScript" resolve correctly via semantic similarity
  - [ ] Source document references accumulate on merged entities
  - [ ] Different entity types with same name stay separate

##### 4.4 Hook Graph Extraction into Document Upload Pipeline
- **Description:** Add graph entity extraction as an async background step in `process_document_upload_background()`. Runs after chunking/indexing completes. Non-blocking — document is available for search immediately.
- **Files:** `application/single_app/functions_documents.py` (line 5472+)
- **Estimated Time:** 8 hours
- **Dependencies:** Tasks 4.2, 4.3
- **Implementation Notes:**
  At the end of `process_document_upload_background()`, add:
  ```python
  # After all chunks are saved to Azure AI Search
  if settings.get("enable_graph_rag", False):
      try:
          from functions_graph_entities import extract_and_store_entities
          executor.submit(extract_and_store_entities,
                         document_id, user_id, group_id, public_workspace_id, settings)
      except Exception as e:
          log_event(f"Graph extraction failed for {document_id}: {e}",
                   level=logging.WARNING)
  ```
  Entity extraction runs as a separate background task to avoid slowing down uploads.
- **Validation:**
  - [ ] Document upload completes without waiting for graph extraction
  - [ ] Graph entities appear in Cosmos DB after extraction completes
  - [ ] Extraction failure doesn't affect document availability
  - [ ] Feature gate `enable_graph_rag` respected

##### 4.5 Graph Traversal and Context Building
- **Description:** Create `functions_graph_rag.py` with graph-enhanced search. Detect entities in user query, traverse 1-2 hop neighborhood, format graph context for LLM.
- **Files:** New: `application/single_app/functions_graph_rag.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Tasks 4.1-4.3
- **Implementation Notes:**
  ```python
  # functions_graph_rag.py

  def graph_enhanced_search(query: str, vector_results: list,
                            workspace_id: str, settings: dict) -> tuple:
      """Augment vector search results with graph context.
      Returns: (vector_results, graph_context_text)"""

      # 1. Detect entities mentioned in query
      query_entities = detect_query_entities(query, workspace_id)
      if not query_entities:
          return vector_results, ""

      # 2. Get graph neighborhood (1-2 hops)
      max_depth = settings.get("graph_rag_max_depth", 2)
      graph_context = []
      for entity in query_entities[:5]:
          neighbors, relationships = get_entity_neighborhood(
              entity["id"], workspace_id, depth=max_depth)
          graph_context.extend(format_graph_context(entity, neighbors, relationships))

      # 3. Get relevant community summaries
      community_ids = {e.get("community_id") for e in query_entities if e.get("community_id")}
      for comm_id in list(community_ids)[:3]:
          summary = get_community_summary(comm_id, workspace_id)
          if summary:
              graph_context.append(f"Topic Cluster: {summary['title']}\n{summary['summary']}")

      return vector_results, "\n\n---\n\n".join(graph_context)
  ```
- **Validation:**
  - [ ] Query "How are X and Y related?" returns relationship paths
  - [ ] Graph traversal respects max_depth setting
  - [ ] Graph context formatted clearly for LLM consumption
  - [ ] Returns empty context when no entities detected

##### 4.6 Integrate Graph Context into Chat Pipeline
- **Description:** Modify `route_backend_chats.py` to inject graph context alongside vector search results when Graph RAG is enabled. Graph context is added as a separate section in the system prompt.
- **Files:** `application/single_app/route_backend_chats.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Task 4.5
- **Implementation Notes:**
  In the chat streaming handler (after hybrid search results are gathered):
  ```python
  graph_context = ""
  if settings.get("enable_graph_rag", False) and hybrid_search_enabled:
      from functions_graph_rag import graph_enhanced_search
      search_results, graph_context = graph_enhanced_search(
          message, search_results, workspace_id, settings)

  # Add graph context to system prompt
  if graph_context:
      system_messages.append({
          "role": "system",
          "content": f"Knowledge Graph Context:\n{graph_context}"
      })
  ```
- **Validation:**
  - [ ] Graph context injected into LLM prompt when entities found
  - [ ] Chat responses reference graph-discovered relationships
  - [ ] No graph context when feature disabled or no entities detected
  - [ ] Latency increase < 300ms for graph queries

##### 4.7 Query Routing (Vector-Only vs Graph-Enhanced)
- **Description:** Implement query classification to route between vector-only search, graph-enhanced search, and community search based on query patterns.
- **Files:** `application/single_app/functions_graph_rag.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 4.5
- **Implementation Notes:**
  ```python
  def route_query(query: str, workspace_id: str, settings: dict) -> str:
      """Route to appropriate retrieval method."""
      relationship_patterns = [
          r"how are .* related", r"connection between", r"depends on",
          r"who works", r"compare", r"summarize all",
          r"overview of", r"themes in", r"difference between"
      ]
      is_graph_query = any(re.search(p, query, re.IGNORECASE) for p in relationship_patterns)
      detected_entities = detect_entities_in_query(query, workspace_id)

      if is_graph_query and detected_entities:
          return "graph_first"       # Graph traversal + vector search
      elif is_graph_query:
          return "community_search"  # Search community summaries
      else:
          return "vector_only"       # Standard hybrid search
  ```
- **Validation:**
  - [ ] "How are Azure and Cosmos DB related?" routes to `graph_first`
  - [ ] "What are the main themes?" routes to `community_search`
  - [ ] "What is the pricing model?" routes to `vector_only`

##### 4.8 Community Detection (Leiden Algorithm)
- **Description:** Create `functions_graph_communities.py` implementing community detection using networkx and graspologic's Leiden algorithm. Partition the entity graph into topic clusters.
- **Files:** New: `application/single_app/functions_graph_communities.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Tasks 4.1-4.3, `networkx>=3.0`, `graspologic>=3.4`
- **Implementation Notes:**
  ```python
  # functions_graph_communities.py
  import networkx as nx
  from graspologic.partition import leiden

  def detect_communities(workspace_id: str, settings: dict) -> list:
      """Run Leiden community detection on workspace graph."""
      # 1. Load all entities and relationships from Cosmos DB
      # 2. Build networkx graph
      # 3. Run Leiden algorithm
      # 4. Store community assignments back to entities
      # 5. Return community membership list
  ```
  This is a batch operation, not per-query. Should be triggered:
  - After significant new documents are uploaded (e.g., 10+ new entities)
  - On-demand via admin action
  - Optionally on a schedule
- **Validation:**
  - [ ] Communities detected from graph with 20+ entities
  - [ ] Each entity assigned a community_id
  - [ ] Community sizes reasonable (not all in one cluster)

##### 4.9 Community Summary Generation
- **Description:** Generate LLM summaries for each detected community. Summaries describe the theme/topic of the entity cluster for use in thematic queries.
- **Files:** `application/single_app/functions_graph_communities.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 4.8
- **Implementation Notes:**
  ```python
  def generate_community_summary(community_id: str, workspace_id: str, settings: dict) -> dict:
      """Generate a thematic summary for a community of entities."""
      entities = get_community_entities(community_id, workspace_id)
      relationships = get_community_relationships(community_id, workspace_id)

      prompt = f"Summarize the main theme of this group of related entities:\n\n"
      prompt += "\n".join([f"- {e['entity_name']} ({e['entity_type']}): {e['description']}"
                           for e in entities[:20]])
      ...
  ```
- **Validation:**
  - [ ] Summaries accurately describe community themes
  - [ ] Summaries stored in `graph_communities` container
  - [ ] Summaries used by community_search query routing

##### 4.10 Admin Settings for Graph RAG
- **Description:** Add Graph RAG settings to admin panel: `enable_graph_rag`, `graph_rag_entity_types`, `graph_rag_extraction_model`, `graph_rag_max_depth`, `enable_community_detection`.
- **Files:** `application/single_app/functions_settings.py`, admin UI files
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Validation:**
  - [ ] Settings visible in admin panel
  - [ ] Entity types configurable as a list
  - [ ] Extraction model selectable (gpt-4o / gpt-4o-mini)

##### 4.11 Chat UI: Graph-Enhanced Search Indicator
- **Description:** Show a visual indicator in the chat interface when graph context was used in a response. Similar to existing `augmented` indicator for hybrid search.
- **Files:** Chat templates + JS
- **Estimated Time:** 8 hours
- **Dependencies:** Task 4.6
- **Implementation Notes:**
  Add `graph_enhanced: true/false` to the final SSE message. Frontend shows a small graph icon when graph context was used.
- **Validation:**
  - [ ] Graph icon appears when graph context was injected
  - [ ] No icon when graph is disabled or no entities found

#### Phase 4 Validation
```bash
# Upload several related documents
# Verify entities extracted and stored in Cosmos DB
# Verify entity resolution (deduplication works)
# Ask "How are X and Y related?" - verify graph traversal
# Ask factual question - verify vector-only routing
# Run community detection on test graph
# Verify community summaries generated
```

---

### Phase 5: Context Optimization & Advanced Search [Days 44-53]

**Objective:** Intelligent context management with token budgeting, progressive summarization, and advanced query enhancement (multi-query, HyDE, MMR, contextual compression).

**Why last:** Builds on all previous phases. Token counting from Phase 1, graph context from Phase 4. These are optimization layers that improve quality incrementally.

#### Tasks

##### 5.1 Progressive Conversation Summarization
- **Description:** Implement `summarize_conversation()` that progressively summarizes older conversation turns to free up context space while preserving key facts and decisions.
- **Files:** `application/single_app/functions_context_optimization.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Phase 1 Task 1.2 (tiktoken)
- **Implementation Notes:**
  ```python
  def summarize_conversation(messages: list, max_tokens: int, model: str) -> str:
      """Summarize older conversation turns, preserving key facts and decisions."""
      text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
      response = gpt_client.chat.completions.create(
          model=model,
          messages=[{
              "role": "user",
              "content": f"Summarize this conversation history, preserving key facts, "
                         f"decisions, and context needed to continue:\n\n{text[:3000]}"
          }],
          max_tokens=min(max_tokens, 500),
          temperature=0,
      )
      return response.choices[0].message.content.strip()
  ```
- **Validation:**
  - [ ] Summary captures key facts from conversation
  - [ ] Summary fits within token budget
  - [ ] 10-turn conversation summarized to ~200 tokens

##### 5.2 Token Budget Allocation in Chat Pipeline
- **Description:** Implement `build_optimized_context()` that allocates token budget across search results (50%), recent history (35%), and conversation summary (15%). Integrate into chat pipeline.
- **Files:** `application/single_app/functions_context_optimization.py`, `application/single_app/route_backend_chats.py`
- **Estimated Time:** 16 hours (2 days)
- **Dependencies:** Tasks 1.2, 5.1
- **Implementation Notes:**
  ```python
  def build_optimized_context(system_prompt, conversation_history, search_results,
                              user_message, max_context_tokens=12000, model="gpt-4o"):
      system_tokens = count_tokens(system_prompt, model)
      user_tokens = count_tokens(user_message, model)
      response_reserve = 2000
      available = max_context_tokens - system_tokens - user_tokens - response_reserve

      search_budget = int(available * 0.50)
      recent_budget = int(available * 0.35)
      summary_budget = int(available * 0.15)

      search_context = fit_within_budget(search_results, search_budget, model)
      recent_msgs = sliding_window(conversation_history, recent_budget, model)
      older_msgs = conversation_history[:len(conversation_history) - len(recent_msgs)]
      summary = summarize_conversation(older_msgs, summary_budget, model) if older_msgs else None

      return {"summary": summary, "recent_messages": recent_msgs,
              "search_context": search_context, "token_breakdown": {...}}
  ```
  Integration in `route_backend_chats.py`:
  ```python
  if settings.get("enable_context_optimization", False):
      from functions_context_optimization import build_optimized_context
      context = build_optimized_context(system_prompt, conversation_history,
                                        search_results, message, budget, model)
      # Use context.search_context instead of raw search_results
      # Use context.recent_messages instead of full conversation_history
      # Prepend context.summary to system prompt if present
  ```
- **Validation:**
  - [ ] Total context stays within configured token budget
  - [ ] Search results get priority allocation
  - [ ] Recent messages preserved, older ones summarized
  - [ ] Token breakdown logged for monitoring

##### 5.3 Map-Reduce for Large Document Sets
- **Description:** When search returns more results than fit in the context budget, use map-reduce summarization: summarize batches of 5 documents, then synthesize batch summaries.
- **Files:** `application/single_app/functions_context_optimization.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Task 5.2
- **Implementation Notes:**
  ```python
  def map_reduce_summarize(query: str, documents: list, batch_size: int = 5) -> str:
      """Map: summarize each batch. Reduce: synthesize batch summaries."""
      batches = [documents[i:i+batch_size] for i in range(0, len(documents), batch_size)]

      # Map: summarize each batch in context of the query
      batch_summaries = []
      for batch in batches:
          summary = summarize_batch(query, batch)
          batch_summaries.append(summary)

      # Reduce: synthesize all batch summaries
      return synthesize_summaries(query, batch_summaries)
  ```
  Only triggered when search results exceed context budget (not on every query).
- **Validation:**
  - [ ] 30 search results condensed to fit within budget
  - [ ] Key information preserved across map-reduce
  - [ ] Only triggered when results exceed budget

##### 5.4 Multi-Query Retrieval
- **Description:** Implement `generate_query_variations()` that produces 3 query variations for broader retrieval. Each variation searches independently, results are merged and deduplicated.
- **Files:** New: `application/single_app/functions_query_expansion.py`
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Implementation Notes:**
  ```python
  # functions_query_expansion.py

  def generate_query_variations(query: str, gpt_client, gpt_model: str, n: int = 3) -> list:
      """Generate N query variations for broader retrieval."""
      response = gpt_client.chat.completions.create(
          model=gpt_model,
          messages=[{
              "role": "user",
              "content": f"Generate {n} different versions of this question, each "
                         f"approaching it from a different angle:\n\n{query}\n\n"
                         f"Return only the questions, one per line."
          }],
          max_tokens=200,
          temperature=0.7,
      )
      queries = [query]
      for line in response.choices[0].message.content.strip().split("\n"):
          cleaned = line.strip().lstrip("0123456789.)- ")
          if cleaned:
              queries.append(cleaned)
      return queries[:n + 1]
  ```
  Integration in search pipeline: run `hybrid_search()` for each query variation, merge results by document ID, keep highest score per chunk.
- **Validation:**
  - [ ] 3 query variations generated from original query
  - [ ] Results merged and deduplicated
  - [ ] Broader recall (more unique documents found)

##### 5.5 HyDE (Hypothetical Document Embeddings)
- **Description:** Implement `hyde_generate()` that generates a hypothetical answer document, embeds it, and uses that embedding for search (instead of or alongside the query embedding).
- **Files:** `application/single_app/functions_query_expansion.py`
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Implementation Notes:**
  ```python
  def hyde_generate(query: str, gpt_client, gpt_model: str) -> str:
      """Generate a hypothetical answer document for embedding."""
      response = gpt_client.chat.completions.create(
          model=gpt_model,
          messages=[{
              "role": "user",
              "content": f"Write a detailed paragraph that would perfectly answer "
                         f"this question, as if from an expert document:\n\n{query}"
          }],
          max_tokens=200,
          temperature=0.7,
      )
      return response.choices[0].message.content.strip()
  ```
  The hypothetical document is embedded and used as an additional vector query alongside the original query embedding.
- **Validation:**
  - [ ] Hypothetical document is relevant to query
  - [ ] HyDE embedding finds documents that raw query misses
  - [ ] Feature toggleable via `enable_hyde` setting

##### 5.6 MMR (Maximal Marginal Relevance) Diversity Filtering
- **Description:** Implement MMR to select diverse documents, reducing redundancy in search results. Requires document embeddings in search results.
- **Files:** `application/single_app/functions_reranking.py`
- **Estimated Time:** 8 hours
- **Dependencies:** Phase 1 Task 1.3
- **Implementation Notes:**
  ```python
  import numpy as np

  def mmr_filter(query_embedding: list, documents: list,
                 lambda_param: float = 0.7, k: int = 10) -> list:
      """Select diverse documents using Maximal Marginal Relevance.
      lambda=0.7 = 70% relevance, 30% diversity."""
      if not documents:
          return []

      selected = []
      remaining = list(range(len(documents)))

      for _ in range(min(k, len(documents))):
          best_idx = None
          best_score = float('-inf')
          for idx in remaining:
              relevance = cosine_similarity(query_embedding, documents[idx]["embedding"])
              diversity = max(cosine_similarity(documents[idx]["embedding"],
                             documents[s]["embedding"]) for s in selected) if selected else 0
              mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity
              if mmr_score > best_score:
                  best_score = mmr_score
                  best_idx = idx
          selected.append(best_idx)
          remaining.remove(best_idx)

      return [documents[i] for i in selected]
  ```
  **Important:** When MMR is enabled, add `"embedding"` to the Azure AI Search `select` parameter to retrieve document embeddings.
- **Validation:**
  - [ ] Results more diverse (fewer near-duplicate chunks)
  - [ ] `lambda_param` configurable via `mmr_lambda` setting
  - [ ] Embedding retrieved from search when MMR enabled

##### 5.7 Contextual Compression
- **Description:** Extract only the sentences from each chunk that are directly relevant to the user's query, reducing context size while preserving relevance.
- **Files:** `application/single_app/functions_reranking.py`
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Implementation Notes:**
  ```python
  def compress_chunk(query: str, chunk_text: str, gpt_client, gpt_model: str) -> str:
      """Extract only query-relevant sentences from a chunk."""
      response = gpt_client.chat.completions.create(
          model=gpt_model,
          messages=[{
              "role": "user",
              "content": f"Extract only the sentences from the following text that are "
                         f"directly relevant to answering: {query}\n\nText:\n{chunk_text}\n\n"
                         f"Return only the relevant sentences, nothing else."
          }],
          max_tokens=500,
          temperature=0,
      )
      return response.choices[0].message.content.strip()
  ```
  **Cost note:** This makes one GPT call per chunk. Only apply to top-N chunks after reranking (e.g., top 10).
- **Validation:**
  - [ ] Compressed chunks contain only relevant sentences
  - [ ] Irrelevant filler text removed
  - [ ] Applied only to top-N chunks to control cost

##### 5.8 Admin Settings for Context Optimization
- **Description:** Add context optimization settings: `enable_context_optimization`, `context_token_budget`, `search_token_budget_pct`, `enable_conversation_summarization`, `enable_multi_query`, `enable_hyde`, `enable_mmr`, `mmr_lambda`, `enable_contextual_compression`.
- **Files:** `application/single_app/functions_settings.py`, admin UI files
- **Estimated Time:** 8 hours
- **Dependencies:** None
- **Implementation Notes:**
  Add to `default_settings`:
  ```python
  'enable_context_optimization': False,
  'context_token_budget': 12000,
  'search_token_budget_pct': 0.50,
  'enable_conversation_summarization': False,
  'enable_multi_query': False,
  'enable_hyde': False,
  'enable_mmr': False,
  'mmr_lambda': 0.7,
  'enable_contextual_compression': False,
  ```
- **Validation:**
  - [ ] All settings visible in admin panel
  - [ ] Each feature independently toggleable
  - [ ] Default values applied for new installations

#### Phase 5 Validation
```bash
# Test conversation summarization with 20+ turn conversation
# Verify token budget respected (check token_breakdown logging)
# Test multi-query retrieval (compare recall vs single query)
# Test HyDE (compare relevance on ambiguous queries)
# Test MMR (verify result diversity)
# Test contextual compression (verify shorter, more relevant chunks)
# Test all features disabled (no regressions)
# Performance benchmark: all features enabled vs baseline
```

---

## Technical Design

### Data Models

#### Cosmos DB: Crawl Job
```json
{
  "id": "crawl_job_xxx",
  "type": "crawl_job",
  "user_id": "user_123",
  "workspace_type": "user|group|public",
  "workspace_id": "...",
  "source_type": "url|sitemap|github",
  "source_url": "https://...",
  "status": "queued|in_progress|completed|failed",
  "total_pages": 50,
  "processed_pages": 12,
  "failed_pages": 1,
  "errors": [],
  "created_at": "2026-03-25T10:00:00Z",
  "completed_at": null
}
```

#### Cosmos DB: Graph Entity
```json
{
  "id": "entity_abc123",
  "type": "graph_entity",
  "entity_type": "person",
  "entity_name": "John Smith",
  "entity_name_normalized": "john_smith",
  "description": "CFO mentioned in Q3 financial report",
  "source_document_ids": ["doc_001", "doc_002"],
  "source_chunk_ids": ["doc_001_3", "doc_002_7"],
  "workspace_type": "user",
  "workspace_id": "user_xyz",
  "embedding": [0.012, -0.034, ...],
  "community_id": "comm_42",
  "properties": {"role": "CFO", "organization": "Contoso"},
  "created_at": "2026-03-25T10:00:00Z"
}
```

#### Cosmos DB: Graph Relationship
```json
{
  "id": "rel_def456",
  "type": "graph_relationship",
  "relationship_type": "WORKS_AT",
  "source_entity_id": "entity_abc123",
  "target_entity_id": "entity_ghi789",
  "description": "John Smith works at Contoso as CFO",
  "weight": 0.95,
  "source_document_ids": ["doc_001"],
  "workspace_type": "user",
  "workspace_id": "user_xyz"
}
```

#### Cosmos DB: Community Summary
```json
{
  "id": "comm_42",
  "type": "graph_community",
  "title": "Executive Leadership at Contoso",
  "summary": "A cluster of entities related to...",
  "entity_ids": ["entity_abc123", "entity_ghi789", ...],
  "workspace_type": "user",
  "workspace_id": "user_xyz",
  "created_at": "2026-03-25T10:00:00Z"
}
```

### Architecture

```
User Query
    |
    v
[Query Enhancement Layer]
    |-- classify_query() -> simple | complex | relationship
    |-- multi_query_retrieval() (if enabled)
    |-- hyde_search() (if enabled)
    |
    v
[Retrieval Layer]
    |-- Azure AI Search (BM25 + Vector + Semantic)
    |-- Graph Traversal (if graph query detected)
    |-- Community Search (if thematic query)
    |
    v
[Post-Retrieval Layer]
    |-- Cohere Rerank v4 (if enabled)
    |-- MMR Diversity (if enabled)
    |-- Contextual Compression (if enabled)
    |-- Attention Reordering (if enabled)
    |
    v
[Context Assembly Layer]
    |-- Token Budget Manager
    |-- Search context (50% budget)
    |-- Recent history (35% budget)
    |-- Conversation summary (15% budget)
    |-- Graph context (injected separately)
    |
    v
[Generation Layer]
    |-- Azure OpenAI GPT
    |-- MCP Tools (if agent with MCP actions)
    |
    v
[Response + Citations]
```

### Key Files

| File | Purpose | Status |
|------|---------|--------|
| `functions_reranking.py` | Cohere rerank, MMR, attention reorder | New (Phase 1) |
| `functions_context_optimization.py` | Token counting, budget, summarization | New (Phase 1) |
| `functions_web_ingestion.py` | URL/sitemap/GitHub crawling | New (Phase 2) |
| `route_backend_web_ingestion.py` | Web ingestion API routes | New (Phase 2) |
| `semantic_kernel_plugins/mcp_plugin_factory.py` | MCP plugin creation | New (Phase 3) |
| `functions_graph_rag.py` | Graph-enhanced search, query routing | New (Phase 4) |
| `functions_graph_entities.py` | Entity extraction, resolution, CRUD | New (Phase 4) |
| `functions_graph_communities.py` | Community detection, summarization | New (Phase 4) |
| `functions_query_expansion.py` | HyDE, multi-query, decomposition | New (Phase 5) |
| `functions_search.py` | Reranker scores, reranking hooks | Modified (Phase 1) |
| `functions_documents.py` | Graph extraction hook, web docs | Modified (Phase 2/4) |
| `route_backend_chats.py` | Query expansion, graph context, budget | Modified (Phase 4/5) |
| `semantic_kernel_loader.py` | MCP action type support | Modified (Phase 3) |
| `config.py` | New Cosmos DB containers | Modified (Phase 4) |
| `functions_settings.py` | New setting defaults + sanitization | Modified (All phases) |
| `requirements.txt` | New dependencies | Modified (All phases) |

---

## Codebase Context

### Patterns to Follow
- **Settings pattern:** `functions_settings.py` line 10 — `default_settings` dict with all defaults. Add new settings here. Sanitize secrets in `sanitize_settings_for_user()`.
- **Background tasks:** `functions_documents.py` line 5472 — `process_document_upload_background()` uses `flask_executor.submit()` for async processing. Follow this for graph extraction and web crawling.
- **Search pattern:** `functions_search.py` — `hybrid_search()` with score normalization, cross-index merging. Insert reranking/MMR as post-processing steps after merge.
- **Route pattern:** All routes use `@app.route() + @swagger_route(security=get_auth_security()) + @login_required + @user_required`. Feature-gated routes add `@enabled_required("setting_name")`.
- **Logging pattern:** `log_event()` from `functions_appinsights.py` for all Application Insights logging.
- **Plugin loading:** `semantic_kernel_loader.py` line 498 — `load_agent_specific_plugins()` iterates plugin manifests and loads by type. Add MCP type handling here.

### Integration Points
- **Chat pipeline:** `route_backend_chats.py` line 2702+ — The `/api/chat/stream` endpoint is the main integration point for query expansion, graph context, and token budgeting.
- **Document pipeline:** `functions_documents.py` line 5472 — `process_document_upload_background()` is the hook point for graph extraction.
- **Search pipeline:** `functions_search.py` — `hybrid_search()` is the integration point for reranking and post-retrieval enhancements.
- **SK agents:** `semantic_kernel_loader.py` — Plugin loading is the integration point for MCP servers.
- **Admin settings:** `functions_settings.py` + `route_frontend_admin_settings.py` + `static/js/admin/admin_settings.js` for all new settings.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Entity extraction adds latency to uploads | Medium | Run as async background task (non-blocking); document available for search immediately |
| Cohere Rerank adds query latency (+200-500ms) | Low | Cache reranked results in existing search cache; make toggleable; measure before/after |
| Crawl4AI requires Playwright (large dependency) | Medium | **Decision needed:** Use Trafilatura only in Phase 2 (no Playwright needed); add Crawl4AI later only if JS rendering required |
| MCP server connections can hang | Low | Enforce timeouts (30s default); per-request lifecycle with cleanup |
| Graph entity quality varies by domain | Medium | Configurable entity types; few-shot prompting option; GPT-4o option for higher quality |
| Token budget management complexity | Low | Sensible defaults (12000 tokens, 50/35/15 split); graceful fallback without optimization |
| All features enabled = complex pipeline | Medium | Every enhancement independently toggleable; feature flags for everything |
| Breaking changes to search results schema | Low | All schema changes are additive (new fields); existing code uses `.get()` with defaults |
| Cost escalation with all features | Medium | Per-query cost estimates documented; admin controls for each feature; monitor via Application Insights |

---

## Validation Checklist

### Pre-Implementation
- [ ] PRD approved and open questions resolved
- [ ] Cohere Rerank v4 deployed on Azure AI Foundry
- [ ] Cosmos DB graph containers created (Phase 4 prerequisite)
- [ ] Development environment has all new dependencies installed
- [ ] Existing tests passing on main branch

### During Implementation (Per Phase)
- [ ] Each task's validation criteria passes
- [ ] Code follows project conventions (filename comments, log_event, swagger_route)
- [ ] Settings added to `default_settings` and sanitized appropriately
- [ ] Feature gates work (feature disabled = no behavior change)
- [ ] No regressions in existing functionality

### Post-Implementation
- [ ] All P0 requirements complete (per PRD user stories)
- [ ] All new settings configurable via admin panel
- [ ] All new API endpoints follow auth pattern (login_required + user_required + swagger_route)
- [ ] Application Insights logging for all new features
- [ ] Performance benchmarked: baseline vs each feature vs all features
- [ ] Documentation updated (feature docs in `docs/explanation/features/`)
- [ ] Version bumped in `config.py`

---

## Archon Tasks

Tasks to be created in Archon for tracking:

1. **Advanced RAG - Phase 1: Search Quality Foundation**
   - Description: Reranker score capture, tiktoken, attention reordering, Cohere rerank, metrics logging, admin settings
   - Estimated: 7.5 days

2. **Advanced RAG - Phase 2: Web & GitHub Crawling**
   - Description: URL ingestion, sitemap crawling, GitHub import, search index additions, UI, progress tracking
   - Estimated: 11.5 days

3. **Advanced RAG - Phase 3: MCP Client Support**
   - Description: SK MCP dependency, plugin factory, SK loader integration, admin UI, security, logging
   - Estimated: 7 days

4. **Advanced RAG - Phase 4: Graph RAG**
   - Description: Cosmos containers, entity extraction, resolution, graph traversal, chat integration, communities
   - Estimated: 15.5 days

5. **Advanced RAG - Phase 5: Context Optimization & Advanced Search**
   - Description: Summarization, token budgeting, map-reduce, multi-query, HyDE, MMR, compression
   - Estimated: 10 days

---

## Success Criteria

From PRD, implementation is successful when:
- [ ] Search relevance (user feedback thumbs-up rate) improves by +20%
- [ ] Web content ingestion completes in < 30 seconds per URL
- [ ] Multi-hop question accuracy improves from ~30% to > 70%
- [ ] Context window utilization stays < 85% of budget
- [ ] Agent tool diversity increases from 7 built-in to 7 + N MCP tools
- [ ] Query latency (P50) stays < 2x baseline with all enhancements enabled
- [ ] All features independently toggleable via admin settings
- [ ] Zero regressions in existing functionality when all features disabled

---

## Dependencies Between Phases

```
Phase 1 (Search Quality)
    |
    +---> Phase 2 (Web Crawling)  [independent, can overlap]
    |
    +---> Phase 3 (MCP Support)   [independent, can overlap]
    |
    +---> Phase 4 (Graph RAG)     [uses token counting from Phase 1]
    |
    +---> Phase 5 (Context Opt)   [uses token counting from Phase 1, graph context from Phase 4]
```

**Parallelization opportunities:**
- Phase 2 and Phase 3 can run concurrently after Phase 1
- Phase 4 can start during Phase 2/3 if Phase 1 is complete
- Phase 5 should start after Phase 4 (needs graph context integration)

---

## New Dependencies Summary (requirements.txt additions)

```
# Phase 1: Search Quality
cohere>=5.0.0
tiktoken>=0.7.0

# Phase 2: Web Crawling
trafilatura>=2.0.0
ultimate-sitemap-parser>=1.5.0
PyGithub>=2.0.0
simhash>=2.1.0

# Phase 3: MCP Support (modify existing line)
# semantic-kernel>=1.39.4  ->  semantic-kernel[mcp]>=1.39.4

# Phase 4: Graph RAG
networkx>=3.0
graspologic>=3.4

# Phase 2 (deferred): JS-rendered pages
# crawl4ai>=0.8.0  (only if JS rendering needed, requires Playwright)
```
