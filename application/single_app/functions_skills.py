# functions_skills.py

import logging
import re
import uuid
from datetime import datetime, timezone

from config import cosmos_skills_container, cosmos_skill_executions_container

logger = logging.getLogger(__name__)

# Status constants
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

VALID_TYPES = {"prompt_skill", "tool_skill", "chain_skill"}
VALID_CATEGORIES = {"productivity", "data", "integration", "analysis", "other"}
VALID_SCOPES = {"personal", "group", "global"}


def _log_event(message, level=logging.INFO, extra=None):
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_skill_payload(payload: dict, partial: bool = False):
    """Validate skill creation/update payload. Raises ValueError on invalid."""
    if not partial:
        required = ["name", "display_name", "description", "type"]
        for field in required:
            if not payload.get(field):
                raise ValueError(f"Missing required field: {field}")

    if "name" in payload:
        name = payload["name"]
        if not re.match(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$', name):
            raise ValueError("Skill name must be 3-50 chars, lowercase alphanumeric and hyphens, start/end with alphanumeric")

    if "type" in payload and payload["type"] not in VALID_TYPES:
        raise ValueError(f"Invalid skill type. Must be one of: {VALID_TYPES}")

    if "category" in payload and payload["category"] not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category. Must be one of: {VALID_CATEGORIES}")

    if "scope" in payload and payload["scope"] not in VALID_SCOPES:
        raise ValueError(f"Invalid scope. Must be one of: {VALID_SCOPES}")

    if "display_name" in payload and len(payload["display_name"]) > 100:
        raise ValueError("Display name must be 100 characters or less")

    if "description" in payload and len(payload["description"]) > 500:
        raise ValueError("Description must be 500 characters or less")


def _build_command(name: str) -> str:
    """Build the /command from skill name."""
    return f"/{name}"


# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

def create_skill(user_id: str, user_name: str, payload: dict) -> dict:
    """Create a new skill."""
    validate_skill_payload(payload)

    now = datetime.now(timezone.utc).isoformat()
    workspace_id = payload.get("workspace_id", user_id)

    skill = {
        "id": str(uuid.uuid4()),
        "name": payload["name"],
        "display_name": payload["display_name"],
        "description": payload["description"],
        "version": payload.get("version", "1.0"),
        "type": payload["type"],
        "category": payload.get("category", "other"),
        "author_id": user_id,
        "author_name": user_name,
        "workspace_id": workspace_id,
        "scope": payload.get("scope", "personal"),
        "status": STATUS_DRAFT,
        "config": payload.get("config", {
            "system_prompt": "",
            "model": "gpt-4o",
            "max_tokens": 2000,
            "temperature": 0.3,
            "input_schema": {"type": "object", "properties": {}},
            "output_format": "markdown",
            "tools": [],
            "trigger_phrases": [],
        }),
        "commands": [_build_command(payload["name"])],
        "usage_count": 0,
        "rating_sum": 0,
        "rating_count": 0,
        "installed_by": [],
        "created_at": now,
        "updated_at": now,
    }

    cosmos_skills_container.create_item(body=skill)

    _log_event("skill_created", extra={"skill_id": skill["id"], "name": skill["name"],
                                        "type": skill["type"], "scope": skill["scope"]})
    return skill


def get_skill(skill_id: str, workspace_id: str) -> dict:
    """Get a skill by ID."""
    try:
        return cosmos_skills_container.read_item(item=skill_id, partition_key=workspace_id)
    except Exception as e:
        logger.warning(f"Failed to read skill {skill_id} in workspace {workspace_id}: {e}")
        return None


def get_skill_by_command(command: str, user_id: str, group_id: str = None) -> dict:
    """Find a skill by its /command. Searches personal -> group -> global scopes."""
    command = command.lower().strip()

    # Search personal scope
    query = "SELECT * FROM c WHERE ARRAY_CONTAINS(c.commands, @cmd) AND c.workspace_id = @ws"
    results = list(cosmos_skills_container.query_items(
        query=query,
        parameters=[{"name": "@cmd", "value": command}, {"name": "@ws", "value": user_id}],
        partition_key=user_id
    ))
    if results:
        return results[0]

    # Search group scope
    if group_id:
        results = list(cosmos_skills_container.query_items(
            query=query,
            parameters=[{"name": "@cmd", "value": command}, {"name": "@ws", "value": group_id}],
            partition_key=group_id
        ))
        if results:
            return results[0]

    # Search global scope (approved only)
    query_global = (
        "SELECT * FROM c WHERE ARRAY_CONTAINS(c.commands, @cmd) "
        "AND c.scope = 'global' AND c.status = 'approved'"
    )
    # Global skills use 'global' as workspace_id
    results = list(cosmos_skills_container.query_items(
        query=query_global,
        parameters=[{"name": "@cmd", "value": command}],
        enable_cross_partition_query=True
    ))
    if results:
        return results[0]

    return None


def update_skill(skill_id: str, workspace_id: str, updates: dict) -> dict:
    """Update a skill."""
    validate_skill_payload(updates, partial=True)

    skill = get_skill(skill_id, workspace_id)
    if not skill:
        raise ValueError("Skill not found")

    now = datetime.now(timezone.utc).isoformat()
    for key, value in updates.items():
        if key not in ("id", "author_id", "created_at", "workspace_id"):
            skill[key] = value

    if "name" in updates:
        skill["commands"] = [_build_command(updates["name"])]

    skill["updated_at"] = now
    cosmos_skills_container.upsert_item(skill)
    return skill


def delete_skill(skill_id: str, workspace_id: str) -> bool:
    """Delete a skill."""
    try:
        cosmos_skills_container.delete_item(item=skill_id, partition_key=workspace_id)
        _log_event("skill_deleted", extra={"skill_id": skill_id})
        return True
    except Exception as e:
        logger.error(f"Failed to delete skill {skill_id}: {e}")
        return False


# ---------------------------------------------------------------------------
# Listing & Search
# ---------------------------------------------------------------------------

def list_skills(workspace_id: str, scope: str = None, status: str = None) -> list:
    """List skills for a workspace, optionally filtered by scope/status."""
    conditions = ["c.workspace_id = @ws"]
    params = [{"name": "@ws", "value": workspace_id}]

    if scope:
        conditions.append("c.scope = @scope")
        params.append({"name": "@scope", "value": scope})
    if status:
        conditions.append("c.status = @status")
        params.append({"name": "@status", "value": status})

    query = f"SELECT * FROM c WHERE {' AND '.join(conditions)} ORDER BY c.updated_at DESC"
    return list(cosmos_skills_container.query_items(
        query=query, parameters=params, partition_key=workspace_id
    ))


def list_marketplace_skills(category: str = None, search: str = None,
                            sort_by: str = "usage_count") -> list:
    """List approved skills for the marketplace."""
    conditions = ["c.status = 'approved'", "c.scope = 'global'"]
    params = []

    if category and category != "all":
        conditions.append("c.category = @cat")
        params.append({"name": "@cat", "value": category})

    if search:
        conditions.append("(CONTAINS(LOWER(c.display_name), @search) OR CONTAINS(LOWER(c.description), @search))")
        params.append({"name": "@search", "value": search.lower()})

    order = "c.usage_count DESC" if sort_by == "usage_count" else "c.created_at DESC"
    query = f"SELECT * FROM c WHERE {' AND '.join(conditions)} ORDER BY {order}"

    return list(cosmos_skills_container.query_items(
        query=query, parameters=params, enable_cross_partition_query=True
    ))


def list_pending_skills() -> list:
    """List skills pending admin approval."""
    query = "SELECT * FROM c WHERE c.status = 'pending_approval' ORDER BY c.created_at ASC"
    return list(cosmos_skills_container.query_items(
        query=query, parameters=[], enable_cross_partition_query=True
    ))


# ---------------------------------------------------------------------------
# Publishing & Approval
# ---------------------------------------------------------------------------

def publish_skill(skill_id: str, workspace_id: str, require_approval: bool = True) -> dict:
    """Publish a skill to the marketplace."""
    skill = get_skill(skill_id, workspace_id)
    if not skill:
        raise ValueError("Skill not found")

    now = datetime.now(timezone.utc).isoformat()

    if require_approval:
        skill["status"] = STATUS_PENDING
    else:
        skill["status"] = STATUS_APPROVED
        skill["scope"] = "global"
        skill["workspace_id"] = "global"

    skill["updated_at"] = now
    cosmos_skills_container.upsert_item(skill)

    # If moving to global scope, create a copy in global partition
    if not require_approval:
        skill["workspace_id"] = "global"
        try:
            cosmos_skills_container.create_item(body=skill)
        except Exception as e:
            logger.warning(f"Global skill copy already exists for {skill_id}, upserting instead: {e}")
            cosmos_skills_container.upsert_item(skill)

    _log_event("skill_published", extra={"skill_id": skill_id,
               "require_approval": require_approval})
    return skill


def approve_skill(skill_id: str, admin_user_id: str, notes: str = "") -> dict:
    """Approve a pending skill for marketplace."""
    # Find across partitions
    query = "SELECT * FROM c WHERE c.id = @id AND c.status = 'pending_approval'"
    results = list(cosmos_skills_container.query_items(
        query=query, parameters=[{"name": "@id", "value": skill_id}],
        enable_cross_partition_query=True
    ))
    if not results:
        raise ValueError("Pending skill not found")

    skill = results[0]
    now = datetime.now(timezone.utc).isoformat()

    # Update original
    skill["status"] = STATUS_APPROVED
    skill["approved_by"] = admin_user_id
    skill["approved_at"] = now
    skill["review_notes"] = notes
    skill["updated_at"] = now
    cosmos_skills_container.upsert_item(skill)

    # Create global copy
    global_skill = dict(skill)
    global_skill["scope"] = "global"
    global_skill["workspace_id"] = "global"
    try:
        cosmos_skills_container.create_item(body=global_skill)
    except Exception as e:
        logger.warning(f"Global skill copy already exists for {skill_id}, upserting instead: {e}")
        cosmos_skills_container.upsert_item(global_skill)

    _log_event("skill_approved", extra={"skill_id": skill_id, "approved_by": admin_user_id})
    return skill


def reject_skill(skill_id: str, admin_user_id: str, reason: str = "") -> dict:
    """Reject a pending skill."""
    query = "SELECT * FROM c WHERE c.id = @id AND c.status = 'pending_approval'"
    results = list(cosmos_skills_container.query_items(
        query=query, parameters=[{"name": "@id", "value": skill_id}],
        enable_cross_partition_query=True
    ))
    if not results:
        raise ValueError("Pending skill not found")

    skill = results[0]
    now = datetime.now(timezone.utc).isoformat()
    skill["status"] = STATUS_REJECTED
    skill["rejected_by"] = admin_user_id
    skill["rejected_at"] = now
    skill["rejection_reason"] = reason
    skill["updated_at"] = now
    cosmos_skills_container.upsert_item(skill)

    _log_event("skill_rejected", extra={"skill_id": skill_id, "rejected_by": admin_user_id})
    return skill


# ---------------------------------------------------------------------------
# Installation & Rating
# ---------------------------------------------------------------------------

def install_skill(skill_id: str, user_id: str) -> bool:
    """Install a marketplace skill for a user."""
    # Find the global skill
    skill = get_skill(skill_id, "global")
    if not skill or skill.get("status") != STATUS_APPROVED:
        raise ValueError("Skill not available for installation")

    if user_id not in skill.get("installed_by", []):
        skill.setdefault("installed_by", []).append(user_id)
        skill["usage_count"] = skill.get("usage_count", 0) + 1
        cosmos_skills_container.upsert_item(skill)

    return True


def rate_skill(skill_id: str, user_id: str, rating: int) -> dict:
    """Rate a skill (1-5)."""
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5")

    skill = get_skill(skill_id, "global")
    if not skill:
        raise ValueError("Skill not found")

    skill["rating_sum"] = skill.get("rating_sum", 0) + rating
    skill["rating_count"] = skill.get("rating_count", 0) + 1
    skill["updated_at"] = datetime.now(timezone.utc).isoformat()
    cosmos_skills_container.upsert_item(skill)
    return skill


# ---------------------------------------------------------------------------
# Execution Logging
# ---------------------------------------------------------------------------

def log_skill_execution(skill_id: str, skill_name: str, user_id: str,
                        input_text: str, output_text: str,
                        duration_ms: int, status: str = "success"):
    """Log a skill execution."""
    now = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "id": str(uuid.uuid4()),
        "skill_id": skill_id,
        "skill_name": skill_name,
        "user_id": user_id,
        "input_preview": input_text[:500] if input_text else "",
        "output_preview": output_text[:500] if output_text else "",
        "duration_ms": duration_ms,
        "status": status,
        "created_at": now,
    }

    try:
        cosmos_skill_executions_container.create_item(body=log_entry)
    except Exception as e:
        logger.error(f"Failed to log skill execution: {e}")


def get_skill_executions(skill_id: str, user_id: str, limit: int = 20) -> list:
    """Get execution history for a skill."""
    query = (
        "SELECT TOP @limit * FROM c WHERE c.skill_id = @sid AND c.user_id = @uid "
        "ORDER BY c.created_at DESC"
    )
    return list(cosmos_skill_executions_container.query_items(
        query=query,
        parameters=[
            {"name": "@limit", "value": limit},
            {"name": "@sid", "value": skill_id},
            {"name": "@uid", "value": user_id},
        ],
        partition_key=user_id
    ))
