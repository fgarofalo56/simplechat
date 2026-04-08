# tag_service.py
# Tag management operations — normalization, validation, workspace tags, and propagation.

import re
from config import *
from functions_debug import debug_print


# ============= TAG MANAGEMENT FUNCTIONS =============

def normalize_tag(tag):
    """
    Normalize a tag by trimming whitespace and converting to lowercase.
    Returns normalized tag string.
    """
    if not isinstance(tag, str):
        return ""
    return tag.strip().lower()


def validate_tags(tags):
    """
    Validate an array of tags.
    Returns (is_valid, error_message, normalized_tags)

    Rules:
    - Max 50 characters per tag
    - Alphanumeric + hyphens/underscores only
    - No empty tags
    - Case-insensitive uniqueness
    """
    if not isinstance(tags, list):
        return False, "Tags must be an array", []

    normalized = []
    seen = set()

    for tag in tags:
        if not isinstance(tag, str):
            return False, "All tags must be strings", []

        normalized_tag = normalize_tag(tag)

        if not normalized_tag:
            continue  # Skip empty tags

        if len(normalized_tag) > 50:
            return False, f"Tag '{normalized_tag}' exceeds 50 characters", []

        # Check alphanumeric + hyphens/underscores
        import re
        if not re.match(r'^[a-z0-9_-]+$', normalized_tag):
            return False, f"Tag '{normalized_tag}' contains invalid characters (only alphanumeric, hyphens, and underscores allowed)", []

        # Check for duplicates
        if normalized_tag in seen:
            continue  # Skip duplicate

        seen.add(normalized_tag)
        normalized.append(normalized_tag)

    return True, None, normalized


def sanitize_tags_for_filter(raw_tags):
    """
    Sanitize and validate tags for use in filter/query operations.
    Silently skips invalid tags since they can never match stored tags.

    Args:
        raw_tags: Either a comma-separated string or a list of strings
    Returns:
        List of valid, normalized tag strings matching ^[a-z0-9_-]+$
    """
    import re

    if isinstance(raw_tags, str):
        candidates = [t.strip() for t in raw_tags.split(',') if t.strip()]
    elif isinstance(raw_tags, list):
        candidates = [t for t in raw_tags if isinstance(t, str)]
    else:
        return []

    valid_tags = []
    seen = set()

    for tag in candidates:
        normalized = normalize_tag(tag)
        if not normalized:
            continue
        if not re.match(r'^[a-z0-9_-]+$', normalized):
            continue
        if len(normalized) > 50:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        valid_tags.append(normalized)

    return valid_tags


def get_workspace_tags(user_id, group_id=None, public_workspace_id=None):
    """
    Get all unique tags used in a workspace with document counts.
    Returns: [{'name': 'tag1', 'count': 5, 'color': '#3b82f6'}, ...]
    """
    from functions_settings import get_user_settings

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct container
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
        partition_key = public_workspace_id
        workspace_type = 'public'
    elif is_group:
        cosmos_container = cosmos_group_documents_container
        partition_key = group_id
        workspace_type = 'group'
    else:
        cosmos_container = cosmos_user_documents_container
        partition_key = user_id
        workspace_type = 'personal'

    try:
        # Query all documents with tags
        if is_public_workspace:
            query = """
                SELECT c.tags
                FROM c
                WHERE c.public_workspace_id = @partition_key
                    AND IS_DEFINED(c.tags)
                    AND ARRAY_LENGTH(c.tags) > 0
            """
        elif is_group:
            query = """
                SELECT c.tags
                FROM c
                WHERE c.group_id = @partition_key
                    AND IS_DEFINED(c.tags)
                    AND ARRAY_LENGTH(c.tags) > 0
            """
        else:
            query = """
                SELECT c.tags
                FROM c
                WHERE c.user_id = @partition_key
                    AND IS_DEFINED(c.tags)
                    AND ARRAY_LENGTH(c.tags) > 0
            """

        parameters = [{"name": "@partition_key", "value": partition_key}]

        documents = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        # Count tag occurrences
        tag_counts = {}
        for doc in documents:
            for tag in doc.get('tags', []):
                normalized_tag = normalize_tag(tag)
                if normalized_tag:
                    tag_counts[normalized_tag] = tag_counts.get(normalized_tag, 0) + 1

        # Get tag definitions (colors) from the appropriate source
        if is_public_workspace:
            # Read from public workspace record (shared across all users)
            from functions_public_workspaces import find_public_workspace_by_id
            ws_doc = find_public_workspace_by_id(public_workspace_id)
            workspace_tag_defs = (ws_doc or {}).get('tag_definitions', {})
        elif is_group:
            # Read from group record (shared across all group members)
            from functions_group import find_group_by_id
            group_doc = find_group_by_id(group_id)
            workspace_tag_defs = (group_doc or {}).get('tag_definitions', {})
        else:
            # Personal: read from user settings
            user_settings = get_user_settings(user_id)
            settings_dict = user_settings.get('settings', {})
            tag_definitions = settings_dict.get('tag_definitions', {})
            workspace_tag_defs = tag_definitions.get('personal', {})

        # Build result with colors from used tags
        results = []
        for tag_name, count in tag_counts.items():
            tag_def = workspace_tag_defs.get(tag_name, {})
            results.append({
                'name': tag_name,
                'count': count,
                'color': tag_def.get('color', get_default_tag_color(tag_name))
            })

        # Add defined tags that haven't been used yet (count = 0)
        for tag_name, tag_def in workspace_tag_defs.items():
            if tag_name not in tag_counts:
                results.append({
                    'name': tag_name,
                    'count': 0,
                    'color': tag_def.get('color', get_default_tag_color(tag_name))
                })

        # Sort by count descending, then name ascending
        results.sort(key=lambda x: (-x['count'], x['name']))

        return results

    except Exception as e:
        debug_print(f"Error getting workspace tags: {e}")
        return []


def get_default_tag_color(tag_name):
    """
    Generate a consistent color for a tag based on its name.
    Uses a predefined color palette and hashes the tag name.
    """
    color_palette = [
        '#3b82f6',  # blue
        '#10b981',  # green
        '#f59e0b',  # amber
        '#ef4444',  # red
        '#8b5cf6',  # purple
        '#ec4899',  # pink
        '#06b6d4',  # cyan
        '#84cc16',  # lime
        '#f97316',  # orange
        '#6366f1',  # indigo
    ]

    # Simple hash function to pick color consistently
    hash_val = sum(ord(c) for c in tag_name)
    color_index = hash_val % len(color_palette)
    return color_palette[color_index]


def get_or_create_tag_definition(user_id, tag_name, workspace_type='personal', color=None, group_id=None, public_workspace_id=None):
    """
    Get or create a tag definition.
    For personal: stored in user settings.
    For group: stored on the group Cosmos record.
    For public: stored on the public workspace Cosmos record.

    Args:
        user_id: User ID
        tag_name: Normalized tag name
        workspace_type: 'personal', 'group', or 'public'
        color: Optional hex color code
        group_id: Group ID (required when workspace_type='group')
        public_workspace_id: Public workspace ID (required when workspace_type='public')

    Returns:
        Tag definition dict with color
    """
    from datetime import datetime, timezone

    if workspace_type == 'group' and group_id:
        from functions_group import find_group_by_id
        group_doc = find_group_by_id(group_id)
        if not group_doc:
            return {'color': color or get_default_tag_color(tag_name)}
        tag_defs = group_doc.get('tag_definitions', {})
        if tag_name not in tag_defs:
            tag_defs[tag_name] = {
                'color': color if color else get_default_tag_color(tag_name),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            group_doc['tag_definitions'] = tag_defs
            cosmos_groups_container.upsert_item(group_doc)
        return tag_defs[tag_name]
    elif workspace_type == 'public' and public_workspace_id:
        from functions_public_workspaces import find_public_workspace_by_id
        ws_doc = find_public_workspace_by_id(public_workspace_id)
        if not ws_doc:
            return {'color': color or get_default_tag_color(tag_name)}
        tag_defs = ws_doc.get('tag_definitions', {})
        if tag_name not in tag_defs:
            tag_defs[tag_name] = {
                'color': color if color else get_default_tag_color(tag_name),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            ws_doc['tag_definitions'] = tag_defs
            cosmos_public_workspaces_container.upsert_item(ws_doc)
        return tag_defs[tag_name]
    else:
        # Personal: store in user settings
        from functions_settings import get_user_settings, update_user_settings

        user_settings = get_user_settings(user_id)
        settings_dict = user_settings.get('settings', {})
        tag_definitions = settings_dict.get('tag_definitions', {})

        if 'personal' not in tag_definitions:
            tag_definitions['personal'] = {}

        workspace_tags = tag_definitions['personal']

        if tag_name not in workspace_tags:
            workspace_tags[tag_name] = {
                'color': color if color else get_default_tag_color(tag_name),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            update_user_settings(user_id, {'tag_definitions': tag_definitions})

        return workspace_tags[tag_name]


def propagate_tags_to_blob_metadata(document_id, tags, user_id, group_id=None, public_workspace_id=None):
    """
    Update blob metadata with document tags when enhanced citations is enabled.
    Tags are stored as a comma-separated string in blob metadata.

    Args:
        document_id: Document ID
        tags: Array of normalized tag names
        user_id: User ID
        group_id: Optional group ID
        public_workspace_id: Optional public workspace ID
    """
    try:
        settings = get_settings()
        if not settings.get('enable_enhanced_citations', False):
            return

        is_group = group_id is not None
        is_public_workspace = public_workspace_id is not None

        # Read document from Cosmos DB to get file_name
        if is_public_workspace:
            cosmos_container = cosmos_public_documents_container
        elif is_group:
            cosmos_container = cosmos_group_documents_container
        else:
            cosmos_container = cosmos_user_documents_container

        doc_item = cosmos_container.read_item(document_id, partition_key=document_id)
        file_name = doc_item.get('file_name')
        if not file_name:
            debug_print(f"Warning: No file_name found for document {document_id}, skipping blob metadata update")
            return

        # Determine container and blob path
        if is_public_workspace:
            storage_account_container_name = storage_account_public_documents_container_name
            blob_path = f"{public_workspace_id}/{file_name}"
        elif is_group:
            storage_account_container_name = storage_account_group_documents_container_name
            blob_path = f"{group_id}/{file_name}"
        else:
            storage_account_container_name = storage_account_user_documents_container_name
            blob_path = f"{user_id}/{file_name}"

        blob_service_client = CLIENTS.get("storage_account_office_docs_client")
        if not blob_service_client:
            debug_print(f"Warning: Blob service client not available, skipping blob metadata update")
            return

        blob_client = blob_service_client.get_blob_client(
            container=storage_account_container_name,
            blob=blob_path
        )

        if not blob_client.exists():
            debug_print(f"Warning: Blob not found at {blob_path}, skipping metadata update")
            return

        # Get existing metadata and update with tags
        properties = blob_client.get_blob_properties()
        existing_metadata = dict(properties.metadata) if properties.metadata else {}
        existing_metadata['document_tags'] = ','.join(tags) if tags else ''
        blob_client.set_blob_metadata(metadata=existing_metadata)

        debug_print(f"Successfully updated blob metadata tags for document {document_id} at {blob_path}")

    except Exception as e:
        debug_print(f"Warning: Failed to update blob metadata tags for document {document_id}: {e}")
        # Non-fatal — tag propagation to chunks is the primary operation


def propagate_tags_to_chunks(document_id, tags, user_id, group_id=None, public_workspace_id=None):
    """
    Update all chunks for a document with new tags.
    This is called immediately after tag updates.

    Args:
        document_id: Document ID
        tags: Array of normalized tag names
        user_id: User ID
        group_id: Optional group ID
        public_workspace_id: Optional public workspace ID
    """
    try:
        # Get all chunks for this document
        chunks = get_all_chunks(document_id, user_id, group_id, public_workspace_id)

        if not chunks:
            debug_print(f"No chunks found for document {document_id}")
            return

        # Update each chunk with new tags
        chunk_count = 0
        for chunk in chunks:
            try:
                update_chunk_metadata(
                    chunk_id=chunk['id'],
                    user_id=user_id,
                    group_id=group_id,
                    public_workspace_id=public_workspace_id,
                    document_id=document_id,
                    document_tags=tags
                )
                chunk_count += 1
            except Exception as chunk_error:
                debug_print(f"Error updating chunk {chunk['id']} with tags: {chunk_error}")
                # Continue with other chunks

        debug_print(f"Successfully propagated tags to {chunk_count} chunks for document {document_id}")

        # Also update blob metadata with tags if enhanced citations is enabled
        propagate_tags_to_blob_metadata(document_id, tags, user_id, group_id, public_workspace_id)

    except Exception as e:
        debug_print(f"Error propagating tags to chunks for document {document_id}: {e}")
        raise