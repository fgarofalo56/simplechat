# config_database.py
# Cosmos DB client initialization and container definitions.
# Extracted from config.py for modularity.

import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential

from config_constants import AZURE_ENVIRONMENT

# Initialize Azure Cosmos DB client
cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
cosmos_key = os.getenv("AZURE_COSMOS_KEY")
cosmos_authentication_type = os.getenv("AZURE_COSMOS_AUTHENTICATION_TYPE", "key") #key or managed_identity

if cosmos_authentication_type == "managed_identity":
    cosmos_client = CosmosClient(cosmos_endpoint, credential=DefaultAzureCredential(), consistency_level="Session")
else:
    cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key, consistency_level="Session")

cosmos_database_name = "SimpleChat"
cosmos_database = cosmos_client.create_database_if_not_exists(cosmos_database_name)

# --- Container Definitions ---
# NOTE: Partition key changes only take effect on NEW deployments.
# For existing deployments, Cosmos DB uses the partition key that was set when the
# container was originally created. Use scripts/migrate_cosmos_partition_keys.py
# to migrate existing containers to new partition keys during a maintenance window.

cosmos_conversations_container_name = "conversations"
cosmos_conversations_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_conversations_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_messages_container_name = "messages"
cosmos_messages_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_messages_container_name,
    partition_key=PartitionKey(path="/conversation_id")
)

cosmos_group_conversations_container_name = "group_conversations"
cosmos_group_conversations_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_conversations_container_name,
    partition_key=PartitionKey(path="/group_id")
)

cosmos_group_messages_container_name = "group_messages"
cosmos_group_messages_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_messages_container_name,
    partition_key=PartitionKey(path="/conversation_id")
)

cosmos_settings_container_name = "settings"
cosmos_settings_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_settings_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_groups_container_name = "groups"
cosmos_groups_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_groups_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_public_workspaces_container_name = "public_workspaces"
cosmos_public_workspaces_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_public_workspaces_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_user_documents_container_name = "documents"
cosmos_user_documents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_user_documents_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_group_documents_container_name = "group_documents"
cosmos_group_documents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_documents_container_name,
    partition_key=PartitionKey(path="/group_id")
)

cosmos_public_documents_container_name = "public_documents"
cosmos_public_documents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_public_documents_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

cosmos_user_settings_container_name = "user_settings"
cosmos_user_settings_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_user_settings_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_safety_container_name = "safety"
cosmos_safety_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_safety_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_feedback_container_name = "feedback"
cosmos_feedback_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_feedback_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_archived_conversations_container_name = "archived_conversations"
cosmos_archived_conversations_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_archived_conversations_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_archived_messages_container_name = "archived_messages"
cosmos_archived_messages_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_archived_messages_container_name,
    partition_key=PartitionKey(path="/conversation_id")
)

cosmos_user_prompts_container_name = "prompts"
cosmos_user_prompts_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_user_prompts_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_group_prompts_container_name = "group_prompts"
cosmos_group_prompts_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_prompts_container_name,
    partition_key=PartitionKey(path="/group_id")
)

cosmos_public_prompts_container_name = "public_prompts"
cosmos_public_prompts_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_public_prompts_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

cosmos_file_processing_container_name = "file_processing"
cosmos_file_processing_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_file_processing_container_name,
    partition_key=PartitionKey(path="/document_id")
)

cosmos_personal_agents_container_name = "personal_agents"
cosmos_personal_agents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_personal_agents_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_personal_actions_container_name = "personal_actions"
cosmos_personal_actions_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_personal_actions_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_group_agents_container_name = "group_agents"
cosmos_group_agents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_agents_container_name,
    partition_key=PartitionKey(path="/group_id")
)

cosmos_group_actions_container_name = "group_actions"
cosmos_group_actions_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_group_actions_container_name,
    partition_key=PartitionKey(path="/group_id")
)

cosmos_global_agents_container_name = "global_agents"
cosmos_global_agents_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_global_agents_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_global_actions_container_name = "global_actions"
cosmos_global_actions_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_global_actions_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_agent_templates_container_name = "agent_templates"
cosmos_agent_templates_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_agent_templates_container_name,
    partition_key=PartitionKey(path="/id")
)

cosmos_agent_facts_container_name = "agent_facts"
cosmos_agent_facts_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_agent_facts_container_name,
    partition_key=PartitionKey(path="/scope_id")
)

cosmos_search_cache_container_name = "search_cache"
cosmos_search_cache_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_search_cache_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_activity_logs_container_name = "activity_logs"
cosmos_activity_logs_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_activity_logs_container_name,
    partition_key=PartitionKey(path="/user_id")
)

cosmos_notifications_container_name = "notifications"
cosmos_notifications_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_notifications_container_name,
    partition_key=PartitionKey(path="/user_id"),
    default_ttl=-1  # TTL disabled by default, enabled per-document
)

cosmos_approvals_container_name = "approvals"
cosmos_approvals_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_approvals_container_name,
    partition_key=PartitionKey(path="/group_id"),
    default_ttl=-1  # TTL disabled by default, enabled per-document for auto-cleanup
)

# Skills Builder containers (Phase A: Enterprise Platform)
cosmos_skills_container_name = "skills"
cosmos_skills_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_skills_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

cosmos_skill_executions_container_name = "skill_executions"
cosmos_skill_executions_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_skill_executions_container_name,
    partition_key=PartitionKey(path="/user_id")
)

# Graph RAG containers (Phase 4: Advanced RAG)
cosmos_graph_entities_container_name = "graph_entities"
cosmos_graph_entities_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_graph_entities_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

cosmos_graph_relationships_container_name = "graph_relationships"
cosmos_graph_relationships_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_graph_relationships_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

cosmos_graph_communities_container_name = "graph_communities"
cosmos_graph_communities_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_graph_communities_container_name,
    partition_key=PartitionKey(path="/workspace_id")
)

# MCP Catalog container (browsable directory of MCP server templates)
cosmos_mcp_catalog_container_name = "mcp_catalog"
cosmos_mcp_catalog_container = cosmos_database.create_container_if_not_exists(
    id=cosmos_mcp_catalog_container_name,
    partition_key=PartitionKey(path="/id")
)
