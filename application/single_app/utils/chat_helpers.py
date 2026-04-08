# chat_helpers.py
# Chat utility functions for JSON parsing, result inspection, and message reload detection.
# Extracted from route_backend_chats.py — Phase 4 God File Decomposition.

import json
import logging
from typing import Any, Dict, List

from functions_logging import log_event


def parse_json_string(candidate: str) -> Any:
    """Parse JSON content when strings look like serialized structures."""
    trimmed = candidate.strip()
    if not trimmed or trimmed[0] not in ('{', '['):
        return None
    try:
        return json.loads(trimmed)
    except Exception as exc:
        log_event(
            f"[result_requires_message_reload] Failed to parse JSON: {str(exc)} | candidate: {trimmed[:200]}",
            level=logging.DEBUG
        )
        return None


def dict_requires_reload(payload: Dict[str, Any]) -> bool:
    """Inspect dictionary payloads for any signal that messages were persisted."""
    if payload.get('reload_messages') or payload.get('requires_message_reload'):
        return True

    metadata = payload.get('metadata')
    if isinstance(metadata, dict) and metadata.get('requires_message_reload'):
        return True

    image_url = payload.get('image_url')
    if isinstance(image_url, dict) and image_url.get('url'):
        return True
    if isinstance(image_url, str) and image_url.strip():
        return True

    result_type = payload.get('type')
    if isinstance(result_type, str) and result_type.lower() == 'image_url':
        return True

    mime = payload.get('mime')
    if isinstance(mime, str) and mime.startswith('image/'):
        return True

    for value in payload.values():
        if result_requires_message_reload(value):
            return True
    return False


def list_requires_reload(items: List[Any]) -> bool:
    """Evaluate list items for reload requirements."""
    return any(result_requires_message_reload(item) for item in items)


def result_requires_message_reload(result: Any) -> bool:
    """Heuristically detect plugin outputs that inject new Cosmos messages (e.g., chart images)."""
    if result is None:
        return False
    if isinstance(result, str):
        parsed = parse_json_string(result)
        return result_requires_message_reload(parsed) if parsed is not None else False
    if isinstance(result, list):
        return list_requires_reload(result)
    if isinstance(result, dict):
        return dict_requires_reload(result)
    return False
