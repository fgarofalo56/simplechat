# services/workspace.py
# Workspace abstraction — eliminates repeated personal/group/public branching
# across route handlers and document functions.

from enum import Enum
from typing import Tuple


class WorkspaceType(Enum):
    """The three workspace types in SimpleChat."""
    PERSONAL = "personal"
    GROUP = "group"
    PUBLIC = "public"


def get_workspace_containers(workspace_type: WorkspaceType) -> dict:
    """Get the Cosmos DB containers for a given workspace type.

    Returns a dict with keys: 'documents', 'prompts', 'agents', 'actions'.
    Each value is the Cosmos container object for that workspace type.

    This centralizes the container selection logic that is currently
    duplicated across ~20 route/function files.

    Args:
        workspace_type: The workspace type to get containers for.

    Returns:
        dict: Container mapping for the workspace type.
    """
    from config_database import (
        cosmos_user_documents_container,
        cosmos_group_documents_container,
        cosmos_public_documents_container,
        cosmos_user_prompts_container,
        cosmos_group_prompts_container,
        cosmos_public_prompts_container,
        cosmos_personal_agents_container,
        cosmos_group_agents_container,
        cosmos_global_agents_container,
        cosmos_personal_actions_container,
        cosmos_group_actions_container,
        cosmos_global_actions_container,
    )

    containers = {
        WorkspaceType.PERSONAL: {
            "documents": cosmos_user_documents_container,
            "prompts": cosmos_user_prompts_container,
            "agents": cosmos_personal_agents_container,
            "actions": cosmos_personal_actions_container,
        },
        WorkspaceType.GROUP: {
            "documents": cosmos_group_documents_container,
            "prompts": cosmos_group_prompts_container,
            "agents": cosmos_group_agents_container,
            "actions": cosmos_group_actions_container,
        },
        WorkspaceType.PUBLIC: {
            "documents": cosmos_public_documents_container,
            "prompts": cosmos_public_prompts_container,
            "agents": cosmos_global_agents_container,
            "actions": cosmos_global_actions_container,
        },
    }
    return containers[workspace_type]


def get_storage_container_name(workspace_type: WorkspaceType) -> str:
    """Get the Azure Blob Storage container name for a workspace type.

    Args:
        workspace_type: The workspace type.

    Returns:
        str: The blob container name.
    """
    from config_constants import (
        storage_account_user_documents_container_name,
        storage_account_group_documents_container_name,
        storage_account_public_documents_container_name,
    )
    names = {
        WorkspaceType.PERSONAL: storage_account_user_documents_container_name,
        WorkspaceType.GROUP: storage_account_group_documents_container_name,
        WorkspaceType.PUBLIC: storage_account_public_documents_container_name,
    }
    return names[workspace_type]


def get_partition_key_field(workspace_type: WorkspaceType) -> str:
    """Get the partition key field name for documents in a workspace type.

    Args:
        workspace_type: The workspace type.

    Returns:
        str: The partition key field name (e.g., 'user_id', 'group_id', 'workspace_id').
    """
    fields = {
        WorkspaceType.PERSONAL: "user_id",
        WorkspaceType.GROUP: "group_id",
        WorkspaceType.PUBLIC: "workspace_id",
    }
    return fields[workspace_type]
