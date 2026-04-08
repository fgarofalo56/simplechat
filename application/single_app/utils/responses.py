# utils/responses.py
# Standardized API response helpers for consistent JSON responses.

from flask import jsonify
from typing import Any, Optional


def api_success(data: Any = None, message: str = None, status_code: int = 200):
    """Create a standardized success response.

    Args:
        data: The response payload.
        message: Optional success message.
        status_code: HTTP status code (default 200).

    Returns:
        Flask Response with JSON body.
    """
    body = {"success": True}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return jsonify(body), status_code


def api_error(message: str, status_code: int = 400, details: Any = None):
    """Create a standardized error response.

    Args:
        message: Error message for the client.
        status_code: HTTP status code (default 400).
        details: Optional additional error details.

    Returns:
        Flask Response with JSON body.
    """
    body = {"success": False, "error": message}
    if details is not None:
        body["details"] = details
    return jsonify(body), status_code


def api_not_found(resource: str = "Resource"):
    """Create a 404 Not Found response.

    Args:
        resource: Name of the resource (e.g., 'Document', 'Conversation').
    """
    return api_error(f"{resource} not found", status_code=404)


def api_forbidden(message: str = "Access denied"):
    """Create a 403 Forbidden response."""
    return api_error(message, status_code=403)


def api_unauthorized(message: str = "Authentication required"):
    """Create a 401 Unauthorized response."""
    return api_error(message, status_code=401)


def api_paginated(items: list, total: int, page: int, per_page: int, **extra):
    """Create a paginated response.

    Args:
        items: List of items for the current page.
        total: Total number of items across all pages.
        page: Current page number (1-based).
        per_page: Number of items per page.
        **extra: Additional fields to include in the response.

    Returns:
        Flask Response with pagination metadata.
    """
    body = {
        "success": True,
        "data": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
        },
    }
    body.update(extra)
    return jsonify(body), 200
