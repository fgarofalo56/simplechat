# functions_mcp_catalog.py
"""
MCP Catalog management functions.

Provides CRUD operations for the MCP catalog — a browsable directory of
MCP server templates that users can install as actions. Catalog entries are
templates with pre-configured manifests and user-fillable config fields.
Installing a catalog entry creates an action in the existing actions system.
"""

import uuid
import traceback
from datetime import datetime, timezone
from config import cosmos_mcp_catalog_container
from functions_debug import debug_print


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def get_catalog_entries(category=None, search=None, active_only=True):
    """
    List catalog entries with optional filtering.

    Args:
        category: Filter by category slug (e.g. 'data-analytics')
        search: Free-text search against name, description, tags
        active_only: Only return active entries (default True)

    Returns:
        list: List of catalog entry dicts sorted by sort_order
    """
    try:
        conditions = []
        params = []

        if active_only:
            conditions.append("c.is_active = true")

        if category:
            conditions.append("c.category = @category")
            params.append({"name": "@category", "value": category})

        if search:
            conditions.append(
                "(CONTAINS(LOWER(c.name), LOWER(@search)) "
                "OR CONTAINS(LOWER(c.description), LOWER(@search)) "
                "OR ARRAY_CONTAINS(c.tags, @search_tag))"
            )
            params.append({"name": "@search", "value": search})
            params.append({"name": "@search_tag", "value": search.lower()})

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where} ORDER BY c.sort_order ASC"

        entries = list(cosmos_mcp_catalog_container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        return entries

    except Exception as e:
        debug_print(f"Error listing catalog entries: {e}")
        traceback.print_exc()
        return []


def get_catalog_entry(entry_id):
    """
    Get a single catalog entry by ID.

    Args:
        entry_id: The catalog entry UUID

    Returns:
        dict or None
    """
    try:
        entry = cosmos_mcp_catalog_container.read_item(
            item=entry_id,
            partition_key=entry_id
        )
        return entry
    except Exception as e:
        debug_print(f"Error getting catalog entry {entry_id}: {e}")
        return None


def save_catalog_entry(data):
    """
    Create or update a catalog entry (admin operation).

    Args:
        data: Catalog entry dict

    Returns:
        dict or None
    """
    try:
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())

        now = datetime.now(timezone.utc).isoformat()
        data.setdefault('created_at', now)
        data['updated_at'] = now
        data.setdefault('is_active', True)
        data.setdefault('sort_order', 50)
        data.setdefault('tags', [])
        data.setdefault('config_fields', [])
        data.setdefault('tools_preview', [])
        data.setdefault('requires_settings', [])

        result = cosmos_mcp_catalog_container.upsert_item(body=data)
        debug_print(f"Saved catalog entry: {result['id']} ({data.get('name', 'Unknown')})")
        return result

    except Exception as e:
        debug_print(f"Error saving catalog entry: {e}")
        traceback.print_exc()
        return None


def delete_catalog_entry(entry_id):
    """
    Delete a catalog entry (admin operation).

    Args:
        entry_id: The catalog entry UUID

    Returns:
        bool
    """
    try:
        cosmos_mcp_catalog_container.delete_item(
            item=entry_id,
            partition_key=entry_id
        )
        debug_print(f"Deleted catalog entry: {entry_id}")
        return True
    except Exception as e:
        debug_print(f"Error deleting catalog entry {entry_id}: {e}")
        traceback.print_exc()
        return False


def install_catalog_entry(entry_id, config_values, scope="personal",
                          user_id=None, group_id=None):
    """
    Install a catalog entry by creating an action from its template.

    Args:
        entry_id: Catalog entry UUID
        config_values: Dict of user-provided values for config_fields
        scope: 'personal', 'group', or 'global'
        user_id: Required for personal scope
        group_id: Required for group scope

    Returns:
        dict with 'action_id' on success, or None on failure
    """
    entry = get_catalog_entry(entry_id)
    if not entry:
        debug_print(f"Catalog entry not found: {entry_id}")
        return None

    try:
        # Build the action manifest from the template
        manifest = dict(entry.get('default_manifest', {}))
        manifest['id'] = str(uuid.uuid4())

        # Apply user config values to the URL template
        url_template = entry.get('mcp_url_template', '')
        if url_template and config_values:
            try:
                mcp_url = url_template.format(**config_values)
                manifest['mcp_url'] = mcp_url
            except KeyError as ke:
                debug_print(f"Missing config value for URL template: {ke}")
                return None

        # Apply auth values from config
        for field in entry.get('config_fields', []):
            field_name = field.get('name', '')
            if field_name in config_values:
                value = config_values[field_name]
                if field.get('type') == 'secret':
                    # Map to auth header/value for secret fields
                    if field_name in ('access_token', 'api_key', 'token'):
                        auth_prefix = manifest.get('mcp_auth_prefix', 'Bearer')
                        manifest['mcp_auth_value'] = f"{auth_prefix} {value}"
                    elif field_name == 'connection_string':
                        manifest['mcp_auth_value'] = value
                    else:
                        manifest[field_name] = value
                else:
                    manifest[field_name] = value

        # Set metadata
        manifest['catalog_entry_id'] = entry_id
        manifest['catalog_entry_name'] = entry.get('name', '')
        manifest['installed_at'] = datetime.now(timezone.utc).isoformat()
        manifest.setdefault('type', 'mcp_server')
        manifest.setdefault('name', entry.get('name', 'MCP Server'))
        manifest.setdefault('description', entry.get('description', ''))

        # Save via the appropriate scope
        if scope == 'global':
            from functions_global_actions import save_global_action
            result = save_global_action(manifest)
            if result:
                return {'action_id': result['id'], 'scope': 'global'}

        elif scope == 'group' and group_id:
            from functions_group_actions import save_group_action
            manifest['group_id'] = group_id
            result = save_group_action(manifest, group_id)
            if result:
                return {'action_id': result['id'], 'scope': 'group'}

        else:
            # Personal scope
            from functions_personal_actions import save_personal_action
            if user_id:
                manifest['user_id'] = user_id
            result = save_personal_action(manifest, user_id)
            if result:
                return {'action_id': result['id'], 'scope': 'personal'}

        debug_print(f"Failed to save action for catalog entry {entry_id}")
        return None

    except Exception as e:
        debug_print(f"Error installing catalog entry {entry_id}: {e}")
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# Pre-configured catalog entries
# ---------------------------------------------------------------------------

_DEFAULT_CATALOG_ENTRIES = [
    {
        "id": "mcp-azure-databricks",
        "name": "Azure Databricks",
        "slug": "azure-databricks",
        "description": "Connect to Databricks for SQL queries, Unity Catalog exploration, Genie natural-language analytics, and Vector Search. Uses the official Databricks managed MCP server.",
        "category": "data-analytics",
        "provider": "Databricks / Microsoft",
        "icon": "bi-lightning-charge",
        "transport": "streamable_http",
        "auth_type": "api_key",
        "mcp_url_template": "https://{workspace_url}/api/mcp/v1",
        "config_fields": [
            {"name": "workspace_url", "label": "Databricks Workspace URL", "type": "text", "required": True, "placeholder": "adb-xxxxx.azuredatabricks.net", "help": "Your Azure Databricks workspace hostname"},
            {"name": "access_token", "label": "Personal Access Token", "type": "secret", "required": True, "help": "Generate from Databricks > User Settings > Access Tokens"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Azure Databricks",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "api_key",
            "mcp_auth_header": "Authorization",
            "mcp_auth_prefix": "Bearer",
            "mcp_timeout": 60,
            "description": "Databricks MCP: SQL queries, Unity Catalog, Genie, Vector Search"
        },
        "tools_preview": ["execute_sql", "list_catalogs", "list_schemas", "list_tables", "describe_table", "genie_start_conversation", "genie_query", "vector_search"],
        "documentation_url": "https://docs.databricks.com/en/mcp/index.html",
        "tags": ["databricks", "sql", "analytics", "azure", "unity-catalog", "genie"],
        "is_active": True,
        "sort_order": 10
    },
    {
        "id": "mcp-azure-management",
        "name": "Azure Management (Azure MCP Server)",
        "slug": "azure-management",
        "description": "Manage Azure resources across 40+ services including Cosmos DB, Storage, App Service, Container Apps, and more. Uses the official Azure MCP Server from Microsoft. Note: This server uses stdio transport — requires an MCP-to-HTTP proxy for remote access.",
        "category": "azure-management",
        "provider": "Microsoft",
        "icon": "bi-cloud",
        "transport": "streamable_http",
        "auth_type": "azure_identity",
        "mcp_url_template": "{mcp_proxy_url}",
        "config_fields": [
            {"name": "mcp_proxy_url", "label": "MCP Proxy URL", "type": "text", "required": True, "placeholder": "https://your-mcp-proxy.azurewebsites.net", "help": "URL of an MCP-to-HTTP proxy hosting the Azure MCP Server. See docs for proxy setup."},
            {"name": "subscription_id", "label": "Azure Subscription ID", "type": "text", "required": False, "placeholder": "00000000-0000-0000-0000-000000000000"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Azure Management",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "azure_identity",
            "mcp_timeout": 60,
            "description": "Azure MCP Server: manage Cosmos DB, Storage, App Service, AKS, and 40+ Azure services"
        },
        "tools_preview": ["cosmos_db_query", "storage_list_containers", "storage_upload_blob", "app_service_list", "container_apps_list", "resource_group_list"],
        "documentation_url": "https://github.com/Azure/azure-mcp",
        "tags": ["azure", "management", "cosmos-db", "storage", "app-service", "infrastructure"],
        "is_active": True,
        "sort_order": 20
    },
    {
        "id": "mcp-sql-server",
        "name": "SQL Server / Azure SQL",
        "slug": "sql-server-azure-sql",
        "description": "Execute SQL queries against Microsoft SQL Server or Azure SQL Database. List databases, tables, schemas, and run read/write queries. Uses a community MSSQL MCP server.",
        "category": "data-analytics",
        "provider": "Community",
        "icon": "bi-database",
        "transport": "streamable_http",
        "auth_type": "api_key",
        "mcp_url_template": "{mcp_server_url}",
        "config_fields": [
            {"name": "mcp_server_url", "label": "MCP Server URL", "type": "text", "required": True, "placeholder": "https://your-mssql-mcp.azurewebsites.net", "help": "URL of the MSSQL MCP server deployment"},
            {"name": "connection_string", "label": "SQL Connection String", "type": "secret", "required": True, "placeholder": "Server=myserver.database.windows.net;Database=mydb;...", "help": "ADO.NET connection string for your SQL database"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "SQL Server",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "api_key",
            "mcp_auth_header": "X-Connection-String",
            "mcp_timeout": 60,
            "description": "SQL Server MCP: execute queries, explore schemas, list tables"
        },
        "tools_preview": ["execute_query", "list_databases", "list_tables", "describe_table", "get_table_schema"],
        "documentation_url": "https://github.com/executeautomation/mcp-mssql",
        "tags": ["sql-server", "azure-sql", "database", "queries", "analytics"],
        "is_active": True,
        "sort_order": 30
    },
    {
        "id": "mcp-postgresql",
        "name": "PostgreSQL",
        "slug": "postgresql",
        "description": "Execute SQL queries against PostgreSQL databases including Azure Database for PostgreSQL. The official MCP reference implementation for PostgreSQL.",
        "category": "data-analytics",
        "provider": "MCP Official",
        "icon": "bi-database-fill",
        "transport": "streamable_http",
        "auth_type": "api_key",
        "mcp_url_template": "{mcp_server_url}",
        "config_fields": [
            {"name": "mcp_server_url", "label": "MCP Server URL", "type": "text", "required": True, "placeholder": "https://your-postgres-mcp.azurewebsites.net", "help": "URL of the PostgreSQL MCP server deployment"},
            {"name": "connection_string", "label": "PostgreSQL Connection URI", "type": "secret", "required": True, "placeholder": "postgresql://user:pass@host:5432/dbname", "help": "PostgreSQL connection URI"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "PostgreSQL",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "api_key",
            "mcp_auth_header": "X-Connection-String",
            "mcp_timeout": 60,
            "description": "PostgreSQL MCP: execute queries, explore schemas, list tables"
        },
        "tools_preview": ["query", "list_tables", "describe_table", "list_schemas"],
        "documentation_url": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        "tags": ["postgresql", "postgres", "database", "queries", "azure"],
        "is_active": True,
        "sort_order": 40
    },
    {
        "id": "mcp-azure-synapse",
        "name": "Azure Synapse Analytics",
        "slug": "azure-synapse",
        "description": "Query Azure Synapse Analytics SQL pools using a SQL MCP server connected to your Synapse SQL endpoint. Supports dedicated and serverless SQL pools.",
        "category": "data-analytics",
        "provider": "Community",
        "icon": "bi-diagram-3",
        "transport": "streamable_http",
        "auth_type": "api_key",
        "mcp_url_template": "{mcp_server_url}",
        "config_fields": [
            {"name": "mcp_server_url", "label": "MCP Server URL", "type": "text", "required": True, "placeholder": "https://your-synapse-mcp.azurewebsites.net", "help": "URL of a SQL MCP server configured for Synapse"},
            {"name": "connection_string", "label": "Synapse SQL Connection String", "type": "secret", "required": True, "placeholder": "Server=myworkspace-ondemand.sql.azuresynapse.net;Database=mydb;...", "help": "Connection string for your Synapse SQL pool (dedicated or serverless)"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Azure Synapse",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "api_key",
            "mcp_auth_header": "X-Connection-String",
            "mcp_timeout": 120,
            "description": "Azure Synapse MCP: query SQL pools, explore data warehouse schemas"
        },
        "tools_preview": ["execute_query", "list_databases", "list_tables", "describe_table", "list_schemas"],
        "documentation_url": "https://learn.microsoft.com/en-us/azure/synapse-analytics/",
        "tags": ["synapse", "data-warehouse", "sql", "analytics", "azure"],
        "is_active": True,
        "sort_order": 50
    },
    {
        "id": "mcp-power-bi-fabric",
        "name": "Power BI / Microsoft Fabric",
        "slug": "power-bi-fabric",
        "description": "Explore Microsoft Fabric workspaces including Power BI semantic models, lakehouses, and data pipelines. Browse item metadata, schemas, and documentation. Note: Uses stdio transport — requires an MCP-to-HTTP proxy.",
        "category": "data-analytics",
        "provider": "Microsoft (Community)",
        "icon": "bi-bar-chart-line",
        "transport": "streamable_http",
        "auth_type": "azure_identity",
        "mcp_url_template": "{mcp_proxy_url}",
        "config_fields": [
            {"name": "mcp_proxy_url", "label": "MCP Proxy URL", "type": "text", "required": True, "placeholder": "https://your-fabric-mcp-proxy.azurewebsites.net", "help": "URL of an MCP-to-HTTP proxy hosting the Fabric MCP Server"},
            {"name": "workspace_id", "label": "Fabric Workspace ID", "type": "text", "required": False, "placeholder": "00000000-0000-0000-0000-000000000000", "help": "Optional: specific Fabric workspace to connect to"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Power BI / Fabric",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "azure_identity",
            "mcp_timeout": 60,
            "description": "Microsoft Fabric MCP: explore semantic models, lakehouses, Power BI items"
        },
        "tools_preview": ["list_workspaces", "list_items", "get_semantic_model", "get_lakehouse", "list_tables"],
        "documentation_url": "https://github.com/microsoft/fabric-mcp",
        "tags": ["power-bi", "fabric", "semantic-model", "lakehouse", "analytics", "azure"],
        "is_active": True,
        "sort_order": 60
    },
    {
        "id": "mcp-azure-cosmos-db",
        "name": "Azure Cosmos DB",
        "slug": "azure-cosmos-db",
        "description": "Query and manage Azure Cosmos DB databases and containers. List items, run SQL queries, and explore container schemas. Part of the Azure MCP Server ecosystem.",
        "category": "data-analytics",
        "provider": "Microsoft",
        "icon": "bi-globe",
        "transport": "streamable_http",
        "auth_type": "azure_identity",
        "mcp_url_template": "{mcp_proxy_url}",
        "config_fields": [
            {"name": "mcp_proxy_url", "label": "MCP Proxy URL", "type": "text", "required": True, "placeholder": "https://your-azure-mcp-proxy.azurewebsites.net", "help": "URL of an MCP-to-HTTP proxy hosting the Azure MCP Server with Cosmos DB tools"},
            {"name": "cosmos_account", "label": "Cosmos DB Account Name", "type": "text", "required": False, "placeholder": "my-cosmos-account"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Azure Cosmos DB",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "azure_identity",
            "mcp_timeout": 60,
            "description": "Cosmos DB MCP: query containers, explore databases, manage items"
        },
        "tools_preview": ["cosmos_db_query", "cosmos_db_list_databases", "cosmos_db_list_containers", "cosmos_db_get_item"],
        "documentation_url": "https://github.com/Azure/azure-mcp",
        "tags": ["cosmos-db", "nosql", "database", "azure"],
        "is_active": True,
        "sort_order": 70
    },
    {
        "id": "mcp-azure-ai-search",
        "name": "Azure AI Search",
        "slug": "azure-ai-search",
        "description": "Search and manage Azure AI Search indexes. Run full-text and vector queries, list indexes, and explore index schemas. Part of the Azure MCP Server ecosystem.",
        "category": "ai-services",
        "provider": "Microsoft",
        "icon": "bi-search",
        "transport": "streamable_http",
        "auth_type": "api_key",
        "mcp_url_template": "{mcp_proxy_url}",
        "config_fields": [
            {"name": "mcp_proxy_url", "label": "MCP Proxy URL", "type": "text", "required": True, "placeholder": "https://your-azure-mcp-proxy.azurewebsites.net", "help": "URL of an MCP-to-HTTP proxy hosting the Azure MCP Server with AI Search tools"},
            {"name": "search_endpoint", "label": "AI Search Endpoint", "type": "text", "required": False, "placeholder": "https://my-search.search.windows.net"},
            {"name": "api_key", "label": "AI Search API Key", "type": "secret", "required": False, "help": "Admin or query key for your AI Search service"}
        ],
        "default_manifest": {
            "type": "mcp_server",
            "name": "Azure AI Search",
            "mcp_transport": "streamable_http",
            "mcp_auth_type": "api_key",
            "mcp_auth_header": "api-key",
            "mcp_timeout": 30,
            "description": "Azure AI Search MCP: search indexes, run vector queries, explore schemas"
        },
        "tools_preview": ["search_query", "list_indexes", "get_index_schema", "vector_search"],
        "documentation_url": "https://github.com/Azure/azure-mcp",
        "tags": ["ai-search", "search", "vector", "azure", "cognitive-search"],
        "is_active": True,
        "sort_order": 80
    }
]


def seed_default_catalog(force=False):
    """
    Seed the MCP catalog with pre-configured entries.

    Args:
        force: If True, overwrite existing entries. If False, only insert
               entries whose IDs don't already exist.

    Returns:
        int: Number of entries seeded
    """
    seeded = 0
    for entry_data in _DEFAULT_CATALOG_ENTRIES:
        try:
            if not force:
                existing = get_catalog_entry(entry_data['id'])
                if existing:
                    continue

            now = datetime.now(timezone.utc).isoformat()
            entry_data['created_at'] = now
            entry_data['updated_at'] = now

            cosmos_mcp_catalog_container.upsert_item(body=entry_data)
            seeded += 1
            debug_print(f"Seeded catalog entry: {entry_data['name']}")

        except Exception as e:
            debug_print(f"Error seeding catalog entry {entry_data.get('name', '?')}: {e}")
            traceback.print_exc()

    debug_print(f"MCP catalog seeding complete: {seeded} entries added")
    return seeded


def get_catalog_categories():
    """
    Get distinct categories from active catalog entries.

    Returns:
        list: Sorted list of category strings
    """
    try:
        results = list(cosmos_mcp_catalog_container.query_items(
            query="SELECT DISTINCT VALUE c.category FROM c WHERE c.is_active = true",
            enable_cross_partition_query=True
        ))
        return sorted(results)
    except Exception as e:
        debug_print(f"Error getting catalog categories: {e}")
        return []
