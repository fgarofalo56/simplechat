# Advanced RAG - Web & GitHub Crawling

## Overview
Web & GitHub Crawling enables SimpleChat to ingest content from external web pages, sitemaps, and GitHub repositories directly into workspace document collections. Users can import documentation, knowledge bases, and code repositories for AI-powered search and chat without manual file uploads.

**Version Implemented:** 0.239.002
**Phase:** Advanced RAG Phase 2

## Dependencies
- `requests` (HTTP fetching)
- `beautifulsoup4` (HTML content extraction)
- Azure AI Search (document indexing)
- Azure Cosmos DB (crawl job tracking, document metadata)
- Azure OpenAI (embeddings for chunked content)

## Architecture Overview

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Web Ingestion Engine | `functions_web_ingestion.py` | 529 | URL fetching, content extraction, sitemap crawling, GitHub import |
| Web Ingestion API | `route_backend_web_ingestion.py` | 529 | REST endpoints for ingestion operations |

### Key Functions

#### URL Ingestion
- **`validate_url(url, settings)`**: SSRF prevention — validates URLs against blocklists (private IP ranges, internal hosts), enforces HTTPS, and checks allowed domains.
- **`ingest_url(url, settings)`**: Fetches a URL, extracts clean text content using BeautifulSoup, removes navigation/headers/footers, and returns structured content with metadata.
- **`process_web_document(document_id, user_id, url, ...)`**: End-to-end processing — fetches URL, chunks content, generates embeddings, and indexes in Azure AI Search.

#### Sitemap Crawling
- **`crawl_sitemap(sitemap_url, settings, max_depth, max_pages, ...)`**: Discovers and crawls all URLs from a sitemap XML with configurable depth and page limits. Supports nested sitemaps (sitemap index files).
- **`_parse_sitemap(sitemap_url, max_depth, current_depth)`**: Recursively parses sitemap XML including nested sitemap indexes.

#### GitHub Import
- **`import_github_repo(repo_url, settings, branch, include_code, ...)`**: Imports documentation files (and optionally code) from a GitHub repository. Uses the GitHub API to list repository contents and fetch file content.

#### Content Management
- **`_content_hash(text)`**: SHA-256 hashing for content change detection during re-crawl operations.
- **`_check_robots_txt(url)`**: Best-effort robots.txt compliance checking.

### API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/web/ingest` | Ingest a single URL |
| `POST` | `/api/web/crawl` | Crawl a sitemap |
| `POST` | `/api/web/github` | Import a GitHub repository |
| `GET` | `/api/web/crawl/<job_id>/status` | Check crawl job status |
| `POST` | `/api/web/recrawl/<document_id>` | Re-crawl a web-sourced document |

### Crawl Job Tracking

Crawl jobs are tracked in Cosmos DB with status updates:
- `pending` → `running` → `completed` / `failed`
- Progress tracking: pages processed, total discovered, errors encountered
- Status callback function updates job record in real-time

### Security

- **SSRF Prevention**: URLs validated against private IP ranges (10.x, 172.16-31.x, 192.168.x, 127.x, 169.254.x)
- **Domain Allowlisting**: Optional configured list of allowed domains
- **HTTPS Enforcement**: HTTP URLs rejected unless explicitly allowed
- **robots.txt Compliance**: Best-effort checking before crawling
- **Rate Limiting**: Configurable delay between requests during sitemap crawls

## Admin Settings

Located in **Admin Settings > Web Crawling** tab:

### Web URL Ingestion Section
- **Enable Web Ingestion**: Master toggle for URL ingestion
- **Max Pages per Crawl**: Limit for sitemap crawl operations
- **Allowed Domains**: Comma-separated list of permitted domains
- **Request Delay**: Delay (ms) between requests during crawls

### GitHub Import Section
- **Enable GitHub Import**: Toggle for GitHub repository import
- **GitHub Token**: Personal access token for private repositories
- **Include Code Files**: Whether to import source code files (not just docs)
- **Default Branch**: Branch to import from (default: `main`)

## Configuration Keys

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `enable_web_ingestion` | bool | false | Enable web URL ingestion |
| `web_ingestion_max_pages` | int | 100 | Max pages per sitemap crawl |
| `web_ingestion_allowed_domains` | string | "" | Allowed domains (comma-separated) |
| `web_ingestion_delay_ms` | int | 1000 | Delay between crawl requests |
| `enable_github_ingestion` | bool | false | Enable GitHub import |
| `github_token` | string | "" | GitHub personal access token |
| `github_include_code` | bool | false | Include code files in import |
| `github_default_branch` | string | "main" | Default branch for import |

## Testing

### Functional Tests
- `functional_tests/test_web_crawling.py` — Tests for URL validation, content extraction, sitemap parsing, GitHub import

## Files Modified/Added

| File | Changes |
|------|---------|
| `functions_web_ingestion.py` (529 lines) | New file: URL ingestion, sitemap crawling, GitHub import |
| `route_backend_web_ingestion.py` (529 lines) | New file: REST API endpoints |
| `admin_settings.html` | Web Crawling tab sections |
| `_sidebar_nav.html` | Web Crawling sidebar navigation entry |
| `admin_sidebar_nav.js` | Section scroll mappings |
| `app.py` | Route registration |
| `config.py` | Default settings values |
| `requirements.txt` | beautifulsoup4 dependency |

(Ref: Advanced RAG Phase 2, Web Crawling, GitHub Import, URL Ingestion)
