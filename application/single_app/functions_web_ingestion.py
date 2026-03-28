# functions_web_ingestion.py

import hashlib
import ipaddress
import logging
import re
import time
import urllib.parse
from datetime import datetime, timezone

import requests
import trafilatura
from bs4 import BeautifulSoup
import html2text

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


# ---------------------------------------------------------------------------
# URL validation / SSRF prevention
# ---------------------------------------------------------------------------

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str, settings: dict = None):
    """Validate URL for safety (SSRF prevention).

    Raises ValueError if the URL is invalid or targets a private network.
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    # Resolve hostname and check against private networks
    import socket
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr_tuple in resolved:
            addr = ipaddress.ip_address(addr_tuple[0])
            for net in _PRIVATE_NETWORKS:
                if addr in net:
                    raise ValueError(f"URL resolves to private IP: {addr}")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    # Check against allowed domains if configured
    if settings:
        allowed = settings.get("web_crawl_allowed_domains", [])
        if allowed and hostname not in allowed:
            raise ValueError(f"Domain not in allowed list: {hostname}")


def _content_hash(text: str) -> str:
    """Generate SHA-256 hash for content change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Single URL ingestion
# ---------------------------------------------------------------------------

def ingest_url(url: str, settings: dict) -> dict:
    """Fetch and extract content from a URL.

    Uses Trafilatura (primary) with BeautifulSoup + html2text fallback.

    Returns dict with keys: title, content_markdown, author, date,
    description, source_url, content_hash
    """
    validate_url(url, settings)

    # Check robots.txt
    _check_robots_txt(url)

    # Try Trafilatura first
    downloaded = trafilatura.fetch_url(url)
    if downloaded:
        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            output_format="txt",
        )
        metadata = trafilatura.extract_metadata(downloaded)
        if content and len(content.strip()) > 50:
            title = metadata.title if metadata and metadata.title else _extract_title_from_url(url)
            author = metadata.author if metadata and metadata.author else ""
            date = metadata.date if metadata and metadata.date else ""
            description = metadata.description if metadata and metadata.description else ""
            return {
                "title": title,
                "content_markdown": content,
                "author": author,
                "date": date,
                "description": description,
                "source_url": url,
                "content_hash": _content_hash(content),
            }

    # Fallback: BeautifulSoup + html2text
    resp = requests.get(url, timeout=30, headers={"User-Agent": "SimpleChat/1.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    h.body_width = 0
    content = h.handle(str(soup))

    title = soup.title.string.strip() if soup.title and soup.title.string else _extract_title_from_url(url)

    return {
        "title": title,
        "content_markdown": content,
        "author": "",
        "date": "",
        "description": "",
        "source_url": url,
        "content_hash": _content_hash(content),
    }


def _extract_title_from_url(url: str) -> str:
    """Extract a readable title from a URL path."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip("/")
    if path:
        last_segment = path.split("/")[-1]
        return urllib.parse.unquote(last_segment).replace("-", " ").replace("_", " ").title()
    return parsed.hostname or url


def _check_robots_txt(url: str):
    """Best-effort robots.txt check. Does not block on failure."""
    try:
        from urllib.robotparser import RobotFileParser
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        if not rp.can_fetch("SimpleChat/1.0", url):
            logger.warning(f"robots.txt disallows fetching: {url}")
    except Exception as e:
        logger.warning(f"robots.txt check failed for {url}: {e}")


# ---------------------------------------------------------------------------
# Sitemap-based crawling
# ---------------------------------------------------------------------------

def crawl_sitemap(sitemap_url: str, settings: dict, max_depth: int = 2,
                  max_pages: int = 100, job_id: str = None,
                  status_callback=None) -> dict:
    """Crawl all URLs from a sitemap with depth and page limits.

    Args:
        sitemap_url: URL of the sitemap.xml
        settings: App settings dict
        max_depth: Maximum sitemap nesting depth
        max_pages: Maximum pages to crawl
        job_id: Optional job ID for status tracking
        status_callback: Optional callback(processed, total, errors) for progress

    Returns dict with: pages (list of ingested dicts), errors (list), total, processed
    """
    validate_url(sitemap_url, settings)

    urls = _parse_sitemap(sitemap_url, max_depth=max_depth)
    urls = urls[:max_pages]

    results = {"pages": [], "errors": [], "total": len(urls), "processed": 0}

    for i, url in enumerate(urls):
        try:
            # Rate limiting: random delay between 1.5-3.5 seconds
            import random
            time.sleep(random.uniform(1.5, 3.5))

            page = ingest_url(url, settings)
            results["pages"].append(page)
            results["processed"] += 1

        except Exception as e:
            results["errors"].append({"url": url, "error": str(e)})
            results["processed"] += 1

        if status_callback:
            status_callback(results["processed"], results["total"], len(results["errors"]))

    return results


def _parse_sitemap(sitemap_url: str, max_depth: int = 2, current_depth: int = 0) -> list:
    """Parse a sitemap XML and return list of URLs. Handles nested sitemaps."""
    if current_depth >= max_depth:
        return []

    try:
        from usp.tree import sitemap_tree_for_homepage
        parsed = urllib.parse.urlparse(sitemap_url)
        homepage = f"{parsed.scheme}://{parsed.netloc}"
        tree = sitemap_tree_for_homepage(homepage)
        return [page.url for page in tree.all_pages()]
    except Exception as e:
        logger.warning(f"usp sitemap parsing failed for {sitemap_url}, falling back to XML parsing: {e}")
        # Fallback: basic XML parsing
        try:
            resp = requests.get(sitemap_url, timeout=30, headers={"User-Agent": "SimpleChat/1.0"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")

            urls = []
            # Check for sitemap index (nested sitemaps)
            for sitemap_tag in soup.find_all("sitemap"):
                loc = sitemap_tag.find("loc")
                if loc and current_depth + 1 < max_depth:
                    urls.extend(_parse_sitemap(loc.text.strip(), max_depth, current_depth + 1))

            # Extract page URLs
            for url_tag in soup.find_all("url"):
                loc = url_tag.find("loc")
                if loc:
                    urls.append(loc.text.strip())

            return urls
        except Exception as e:
            logger.error(f"Failed to parse sitemap {sitemap_url}: {e}")
            return []


# ---------------------------------------------------------------------------
# GitHub repository import
# ---------------------------------------------------------------------------

# File extensions to process by default (documentation)
_DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
# Code extensions (only if include_code=True)
_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cs", ".go",
    ".rs", ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".swift",
    ".kt", ".scala", ".sh", ".bash", ".yaml", ".yml", ".toml",
    ".json", ".xml", ".sql", ".r", ".m", ".lua",
}
# Files/dirs to skip
_SKIP_PATTERNS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".cache", "vendor",
}
_SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Pipfile.lock", "poetry.lock", "Cargo.lock",
    "go.sum", "composer.lock",
}


def import_github_repo(repo_url: str, settings: dict, branch: str = "main",
                       include_code: bool = False, job_id: str = None,
                       status_callback=None) -> dict:
    """Import a GitHub repository's documentation and optionally code.

    Args:
        repo_url: GitHub repository URL (https://github.com/owner/repo)
        settings: App settings dict
        branch: Branch name to import from
        include_code: Whether to include source code files
        job_id: Optional job ID for status tracking
        status_callback: Optional callback for progress

    Returns dict with: pages (list), errors (list), total, processed
    """
    from github import Github, GithubException

    # Parse owner/repo from URL
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    owner, repo_name = match.group(1), match.group(2)

    # Authenticate
    token = settings.get("github_token", "")
    g = Github(token) if token else Github()

    try:
        repo = g.get_repo(f"{owner}/{repo_name}")
    except GithubException as e:
        raise ValueError(f"Cannot access repository: {e}")

    # Determine which extensions to process
    allowed_extensions = set(_DOC_EXTENSIONS)
    if include_code:
        allowed_extensions |= _CODE_EXTENSIONS

    # Get file tree
    try:
        tree = repo.get_git_tree(branch, recursive=True)
    except GithubException:
        tree = repo.get_git_tree("main", recursive=True)

    files_to_process = []
    for item in tree.tree:
        if item.type != "blob":
            continue
        if item.size > 100 * 1024:  # Skip files > 100KB
            continue

        path = item.path
        # Skip directories
        if any(skip in path.split("/") for skip in _SKIP_PATTERNS):
            continue
        # Skip lock files
        filename = path.split("/")[-1]
        if filename in _SKIP_FILES:
            continue
        # Check extension
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in allowed_extensions:
            continue

        files_to_process.append(item)

    results = {"pages": [], "errors": [], "total": len(files_to_process), "processed": 0}

    for item in files_to_process:
        try:
            blob = repo.get_git_blob(item.sha)
            import base64
            content = base64.b64decode(blob.content).decode("utf-8", errors="replace")

            if len(content.strip()) < 10:
                results["processed"] += 1
                continue

            results["pages"].append({
                "title": item.path,
                "content_markdown": content,
                "author": "",
                "date": "",
                "description": f"File from {owner}/{repo_name}",
                "source_url": f"https://github.com/{owner}/{repo_name}/blob/{branch}/{item.path}",
                "content_hash": _content_hash(content),
            })
            results["processed"] += 1

        except Exception as e:
            results["errors"].append({"url": item.path, "error": str(e)})
            results["processed"] += 1

        if status_callback:
            status_callback(results["processed"], results["total"], len(results["errors"]))

    return results


# ---------------------------------------------------------------------------
# Document processing pipeline integration
# ---------------------------------------------------------------------------

def process_web_document(document_id: str, user_id: str, url: str,
                         source_type: str, settings: dict,
                         group_id: str = None, public_workspace_id: str = None):
    """Process a single URL into chunks and index in Azure AI Search.

    Follows the same pipeline as process_document_upload_background():
    1. Fetch content from URL
    2. Chunk the content
    3. Save chunks via save_chunks()
    4. Update document metadata

    Args:
        document_id: The Cosmos DB document ID
        user_id: Owner user ID
        url: URL to ingest
        source_type: "web" or "github"
        settings: App settings
        group_id: Optional group workspace ID
        public_workspace_id: Optional public workspace ID
    """
    from functions_documents import (
        save_chunks, update_document, get_document_metadata,
    )
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    try:
        # Update status
        update_document(
            document_id=document_id,
            user_id=user_id,
            status="Fetching content from URL...",
            group_id=group_id,
            public_workspace_id=public_workspace_id,
        )

        # Fetch content
        result = ingest_url(url, settings)
        content = result["content_markdown"]

        if not content or len(content.strip()) < 50:
            update_document(
                document_id=document_id,
                user_id=user_id,
                status="Error: No content extracted from URL",
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )
            return

        # Store source metadata on the document
        update_document(
            document_id=document_id,
            user_id=user_id,
            source_url=url,
            source_type=source_type,
            content_hash=result["content_hash"],
            group_id=group_id,
            public_workspace_id=public_workspace_id,
        )

        # Chunk content
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_text(content)

        total_chunks = len(chunks)
        total_tokens = 0

        update_document(
            document_id=document_id,
            user_id=user_id,
            status=f"Processing {total_chunks} chunks...",
            number_of_pages=total_chunks,
            group_id=group_id,
            public_workspace_id=public_workspace_id,
        )

        # Save each chunk
        for i, chunk_text in enumerate(chunks):
            token_usage = save_chunks(
                page_text_content=chunk_text,
                page_number=i + 1,
                file_name=result.get("title", url),
                user_id=user_id,
                document_id=document_id,
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )
            if token_usage and isinstance(token_usage, dict):
                total_tokens += token_usage.get("total_tokens", 0)

            # Update progress
            pct = int(((i + 1) / total_chunks) * 100)
            update_document(
                document_id=document_id,
                user_id=user_id,
                percentage_complete=pct,
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )

        # Complete
        update_document(
            document_id=document_id,
            user_id=user_id,
            status="Completed",
            percentage_complete=100,
            number_of_pages=total_chunks,
            group_id=group_id,
            public_workspace_id=public_workspace_id,
        )

        _log_event(
            "web_document_processed",
            level=logging.INFO,
            extra={
                "document_id": document_id,
                "url": url,
                "source_type": source_type,
                "chunks": total_chunks,
                "tokens": total_tokens,
            },
        )

    except Exception as e:
        logger.error(f"Error processing web document {document_id}: {e}")
        try:
            update_document(
                document_id=document_id,
                user_id=user_id,
                status=f"Error: {str(e)[:200]}",
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )
        except Exception as e2:
            logger.warning(f"Failed to update error status for document {document_id}: {e2}")
        raise
