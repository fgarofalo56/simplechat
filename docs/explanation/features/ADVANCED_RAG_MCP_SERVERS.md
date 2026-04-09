# Advanced RAG - MCP Client Support

## Overview
MCP (Model Context Protocol) Client Support enables SimpleChat to connect to external MCP servers as Semantic Kernel plugins. This allows the AI assistant to invoke tools provided by external services (databases, APIs, custom tooling) through standardized MCP server connections. Connections are configured via admin settings and loaded dynamically at runtime.

**Version Implemented:** 0.239.002
**Phase:** Advanced RAG Phase 3

## Dependencies
- Semantic Kernel (plugin architecture)
- MCP SDK (`semantic-kernel-mcp` or equivalent transport)
- Azure OpenAI (tool-calling via GPT)

## Architecture Overview

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| MCP Plugin Factory | `semantic_kernel_plugins/mcp_plugin_factory.py` | 249 | Create SK plugins from MCP server connections |
| SK Loader Integration | `semantic_kernel_loader.py` | — | MCP plugin loading during kernel initialization |
| Admin Settings | `admin_settings.html` | — | MCP server configuration UI |

### Key Functions

#### `create_mcp_plugin(manifest, settings)` (async)
Creates a Semantic Kernel plugin from an MCP server action manifest. Connects to the MCP server, discovers available tools, and wraps them as SK functions that can be invoked during chat.

**Manifest Structure:**
```json
{
    "name": "my-mcp-server",
    "type": "mcp_server",
    "mcp_url": "https://mcp.example.com",
    "transport": "sse|streamable_http",
    "auth_type": "none|api_key|bearer",
    "auth_header": "Authorization",
    "auth_value": "Bearer xxx",
    "timeout": 30
}
```

#### `test_mcp_connection(mcp_url, transport, auth_type, auth_header, auth_value, timeout, settings)` (async)
Tests connectivity to an MCP server and lists available tools. Used by the admin UI to verify server configuration before saving.

#### `validate_mcp_url(url, settings)`
Security validation for MCP server URLs:
- SSRF prevention (blocks private IP ranges)
- Protocol validation (HTTPS required in production)
- Domain allowlisting (optional)

### Integration with Semantic Kernel

```
Admin configures MCP server in Settings
    ↓
Server config saved as action manifest in Cosmos DB
    ↓
SK Loader initializes kernel for chat session
    ↓
MCP plugin factory creates SK plugin from manifest
    ↓
Plugin registered with kernel (tools available to GPT)
    ↓
GPT tool-calls invoke MCP server tools via SK
    ↓
Results returned to chat conversation
```

### Security

- **URL Validation**: SSRF prevention blocks connections to private IP ranges
- **Authentication**: Supports API key, bearer token, and no-auth modes
- **HTTPS Enforcement**: Required for production deployments
- **Timeout Configuration**: Configurable connection and request timeouts
- **Logging**: All MCP connections and tool invocations logged to Application Insights

## Admin Settings

Located in **Admin Settings > MCP Servers** tab:

- **Enable MCP Servers**: Master toggle for MCP client functionality
- **MCP Server Configuration**: Table of configured servers with:
  - Server Name
  - Server URL (endpoint)
  - Transport type (SSE or Streamable HTTP)
  - Authentication method and credentials
  - Connection timeout
  - Test Connection button

## Configuration Keys

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `enable_mcp_servers` | bool | false | Enable MCP client support |

MCP server configurations are stored as action manifests in the existing actions/plugins system.

## Testing

### Functional Tests
- `functional_tests/test_mcp_support.py` — URL validation, connection testing, plugin creation

## Files Modified/Added

| File | Changes |
|------|---------|
| `semantic_kernel_plugins/mcp_plugin_factory.py` (249 lines) | New file: MCP plugin creation, connection testing |
| `semantic_kernel_loader.py` | MCP plugin type handling in SK initialization |
| `admin_settings.html` | MCP Servers tab |
| `_sidebar_nav.html` | MCP Servers sidebar navigation entry |
| `functions_settings.py` | MCP-related configuration keys |
| `config.py` | Default settings values |

(Ref: Advanced RAG Phase 3, MCP Client, Model Context Protocol, Semantic Kernel Plugins)
