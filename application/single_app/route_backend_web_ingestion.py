# route_backend_web_ingestion.py

import uuid
import logging
from datetime import datetime, timezone
from flask import request, jsonify, current_app
from functools import wraps

from swagger_wrapper import swagger_route, get_auth_security
from functions_authentication import login_required, user_required
from functions_settings import get_settings, enabled_required

logger = logging.getLogger(__name__)


def register_route_backend_web_ingestion(app):

    @app.route('/api/workspace/documents/url', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @user_required
    def api_ingest_url():
        """Ingest a single URL into the user's workspace."""
        from flask import session
        user_id = session.get("user", {}).get("oid")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_web_ingestion", False):
            return jsonify({"error": "Web ingestion is disabled"}), 400

        data = request.get_json()
        if not data or not data.get("url"):
            return jsonify({"error": "URL is required"}), 400

        url = data["url"].strip()
        group_id = data.get("group_id")
        public_workspace_id = data.get("public_workspace_id")

        # Validate GitHub ingestion feature flag
        if "github.com" in url:
            if not settings.get("enable_github_ingestion", False):
                return jsonify({"error": "GitHub ingestion is disabled"}), 400

        try:
            from functions_web_ingestion import validate_url
            validate_url(url, settings)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        # Create document metadata in Cosmos DB
        document_id = str(uuid.uuid4())
        try:
            from functions_documents import create_document, update_document
            title = data.get("title") or url
            create_document(
                document_id=document_id,
                file_name=title,
                user_id=user_id,
                status="Queued for processing",
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )
            update_document(
                document_id=document_id,
                user_id=user_id,
                percentage_complete=0,
                source_url=url,
                source_type="web",
                group_id=group_id,
                public_workspace_id=public_workspace_id,
            )
        except Exception as e:
            logger.error(f"Failed to create document for URL ingestion: {e}")
            return jsonify({"error": "Failed to create document record"}), 500

        # Submit background task
        try:
            from functions_web_ingestion import process_web_document
            executor = current_app.extensions.get("executor")
            if executor:
                executor.submit(
                    process_web_document,
                    document_id=document_id,
                    user_id=user_id,
                    url=url,
                    source_type="web",
                    settings=settings,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
            else:
                # Fallback: process synchronously
                process_web_document(
                    document_id=document_id,
                    user_id=user_id,
                    url=url,
                    source_type="web",
                    settings=settings,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
        except Exception as e:
            logger.error(f"Failed to submit web ingestion task: {e}")
            return jsonify({"error": "Failed to start processing"}), 500

        return jsonify({
            "message": "URL queued for ingestion",
            "document_id": document_id,
            "url": url,
        }), 200

    @app.route('/api/workspace/documents/crawl', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @user_required
    def api_crawl_sitemap():
        """Crawl a sitemap and ingest all discovered URLs."""
        from flask import session
        user_id = session.get("user", {}).get("oid")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_web_ingestion", False):
            return jsonify({"error": "Web ingestion is disabled"}), 400

        data = request.get_json()
        if not data or not data.get("url"):
            return jsonify({"error": "Sitemap URL is required"}), 400

        sitemap_url = data["url"].strip()
        group_id = data.get("group_id")
        public_workspace_id = data.get("public_workspace_id")
        max_pages = min(
            int(data.get("max_pages", settings.get("web_crawl_max_pages", 100))),
            settings.get("web_crawl_max_pages", 100),
        )
        max_depth = min(
            int(data.get("max_depth", settings.get("web_crawl_max_depth", 2))),
            settings.get("web_crawl_max_depth", 2),
        )

        # Create a crawl job record
        job_id = str(uuid.uuid4())
        crawl_job = {
            "id": job_id,
            "type": "crawl_job",
            "user_id": user_id,
            "workspace_type": "public" if public_workspace_id else ("group" if group_id else "user"),
            "workspace_id": public_workspace_id or group_id or user_id,
            "source_type": "sitemap",
            "source_url": sitemap_url,
            "status": "queued",
            "total_pages": 0,
            "processed_pages": 0,
            "failed_pages": 0,
            "document_ids": [],
            "errors": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }

        try:
            from config import cosmos_settings_container
            cosmos_settings_container.upsert_item(crawl_job)
        except Exception as e:
            logger.error(f"Failed to create crawl job: {e}")

        # Submit background crawl task
        try:
            executor = current_app.extensions.get("executor")
            if executor:
                executor.submit(
                    _process_sitemap_crawl,
                    job_id=job_id,
                    sitemap_url=sitemap_url,
                    user_id=user_id,
                    settings=settings,
                    max_pages=max_pages,
                    max_depth=max_depth,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
        except Exception as e:
            logger.error(f"Failed to submit crawl task: {e}")
            return jsonify({"error": "Failed to start crawl"}), 500

        return jsonify({
            "message": "Sitemap crawl queued",
            "job_id": job_id,
            "sitemap_url": sitemap_url,
            "max_pages": max_pages,
        }), 200

    @app.route('/api/workspace/documents/github', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @user_required
    def api_import_github():
        """Import a GitHub repository into the user's workspace."""
        from flask import session
        user_id = session.get("user", {}).get("oid")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_github_ingestion", False):
            return jsonify({"error": "GitHub ingestion is disabled"}), 400

        data = request.get_json()
        if not data or not data.get("url"):
            return jsonify({"error": "GitHub repository URL is required"}), 400

        repo_url = data["url"].strip()
        group_id = data.get("group_id")
        public_workspace_id = data.get("public_workspace_id")
        branch = data.get("branch", "main")
        include_code = data.get("include_code", settings.get("github_include_code", False))

        # Create a crawl job record
        job_id = str(uuid.uuid4())
        crawl_job = {
            "id": job_id,
            "type": "crawl_job",
            "user_id": user_id,
            "workspace_type": "public" if public_workspace_id else ("group" if group_id else "user"),
            "workspace_id": public_workspace_id or group_id or user_id,
            "source_type": "github",
            "source_url": repo_url,
            "status": "queued",
            "total_pages": 0,
            "processed_pages": 0,
            "failed_pages": 0,
            "document_ids": [],
            "errors": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }

        try:
            from config import cosmos_settings_container
            cosmos_settings_container.upsert_item(crawl_job)
        except Exception as e:
            logger.error(f"Failed to create crawl job: {e}")

        # Submit background task
        try:
            executor = current_app.extensions.get("executor")
            if executor:
                executor.submit(
                    _process_github_import,
                    job_id=job_id,
                    repo_url=repo_url,
                    user_id=user_id,
                    settings=settings,
                    branch=branch,
                    include_code=include_code,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
        except Exception as e:
            logger.error(f"Failed to submit GitHub import: {e}")
            return jsonify({"error": "Failed to start import"}), 500

        return jsonify({
            "message": "GitHub import queued",
            "job_id": job_id,
            "repo_url": repo_url,
        }), 200

    @app.route('/api/workspace/documents/crawl/status/<job_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @user_required
    def api_crawl_status(job_id):
        """Get the status of a crawl job."""
        from flask import session
        user_id = session.get("user", {}).get("oid")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        try:
            from config import cosmos_settings_container
            job = cosmos_settings_container.read_item(item=job_id, partition_key=job_id)
            if job.get("user_id") != user_id:
                return jsonify({"error": "Not authorized"}), 403

            return jsonify({
                "job_id": job["id"],
                "status": job.get("status", "unknown"),
                "source_type": job.get("source_type"),
                "source_url": job.get("source_url"),
                "total_pages": job.get("total_pages", 0),
                "processed_pages": job.get("processed_pages", 0),
                "failed_pages": job.get("failed_pages", 0),
                "document_ids": job.get("document_ids", []),
                "errors": job.get("errors", [])[:10],
                "created_at": job.get("created_at"),
                "completed_at": job.get("completed_at"),
            }), 200
        except Exception:
            return jsonify({"error": "Job not found"}), 404

    @app.route('/api/workspace/documents/url/<document_id>/recrawl', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @user_required
    def api_recrawl_url(document_id):
        """Re-crawl a web-sourced document to update its content."""
        from flask import session
        user_id = session.get("user", {}).get("oid")
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        settings = get_settings()
        if not settings.get("enable_web_ingestion", False):
            return jsonify({"error": "Web ingestion is disabled"}), 400

        try:
            from functions_documents import get_document_metadata
            metadata = get_document_metadata(document_id=document_id, user_id=user_id)
            if not metadata:
                return jsonify({"error": "Document not found"}), 404

            source_url = metadata.get("source_url")
            if not source_url:
                return jsonify({"error": "Document has no source URL"}), 400

            source_type = metadata.get("source_type", "web")

            # Submit background re-crawl
            from functions_web_ingestion import process_web_document
            executor = current_app.extensions.get("executor")
            if executor:
                executor.submit(
                    process_web_document,
                    document_id=document_id,
                    user_id=user_id,
                    url=source_url,
                    source_type=source_type,
                    settings=settings,
                )

            return jsonify({
                "message": "Re-crawl started",
                "document_id": document_id,
                "url": source_url,
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500


def _process_sitemap_crawl(job_id, sitemap_url, user_id, settings,
                           max_pages, max_depth, group_id=None,
                           public_workspace_id=None):
    """Background task: crawl sitemap and process each page."""
    from functions_web_ingestion import crawl_sitemap, process_web_document
    from functions_documents import create_document, update_document

    try:
        _update_crawl_job(job_id, status="in_progress")

        def status_callback(processed, total, errors):
            _update_crawl_job(job_id, processed_pages=processed,
                              total_pages=total, failed_pages=errors)

        result = crawl_sitemap(
            sitemap_url, settings, max_depth=max_depth,
            max_pages=max_pages, job_id=job_id,
            status_callback=status_callback,
        )

        document_ids = []
        for page in result["pages"]:
            try:
                doc_id = str(uuid.uuid4())
                create_document(
                    document_id=doc_id,
                    file_name=page.get("title", page["source_url"]),
                    user_id=user_id,
                    status="Processing...",
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                update_document(
                    document_id=doc_id, user_id=user_id,
                    source_url=page["source_url"],
                    source_type="web",
                    content_hash=page["content_hash"],
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                process_web_document(
                    document_id=doc_id, user_id=user_id,
                    url=page["source_url"], source_type="web",
                    settings=settings, group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                document_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Error processing crawled page: {e}")

        _update_crawl_job(
            job_id, status="completed",
            document_ids=document_ids,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"Sitemap crawl failed: {e}")
        _update_crawl_job(job_id, status="failed",
                          errors=[{"error": str(e)}])


def _process_github_import(job_id, repo_url, user_id, settings,
                           branch, include_code, group_id=None,
                           public_workspace_id=None):
    """Background task: import GitHub repo files."""
    from functions_web_ingestion import import_github_repo, process_web_document
    from functions_documents import create_document, update_document

    try:
        _update_crawl_job(job_id, status="in_progress")

        def status_callback(processed, total, errors):
            _update_crawl_job(job_id, processed_pages=processed,
                              total_pages=total, failed_pages=errors)

        result = import_github_repo(
            repo_url, settings, branch=branch,
            include_code=include_code, job_id=job_id,
            status_callback=status_callback,
        )

        document_ids = []
        for page in result["pages"]:
            try:
                doc_id = str(uuid.uuid4())
                create_document(
                    document_id=doc_id,
                    file_name=page.get("title", page["source_url"]),
                    user_id=user_id,
                    status="Processing...",
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                update_document(
                    document_id=doc_id, user_id=user_id,
                    source_url=page["source_url"],
                    source_type="github",
                    content_hash=page["content_hash"],
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                process_web_document(
                    document_id=doc_id, user_id=user_id,
                    url=page["source_url"], source_type="github",
                    settings=settings, group_id=group_id,
                    public_workspace_id=public_workspace_id,
                )
                document_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Error processing GitHub file: {e}")

        _update_crawl_job(
            job_id, status="completed",
            document_ids=document_ids,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as e:
        logger.error(f"GitHub import failed: {e}")
        _update_crawl_job(job_id, status="failed",
                          errors=[{"error": str(e)}])


def _update_crawl_job(job_id, **kwargs):
    """Update a crawl job record in Cosmos DB."""
    try:
        from config import cosmos_settings_container
        job = cosmos_settings_container.read_item(item=job_id, partition_key=job_id)
        for k, v in kwargs.items():
            job[k] = v
        cosmos_settings_container.upsert_item(job)
    except Exception as e:
        logger.error(f"Failed to update crawl job {job_id}: {e}")
