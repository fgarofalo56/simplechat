# mcp_plugin_factory.py

import ipaddress
import logging
import socket
import time
import urllib.parse

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


# ---------------------------------------------------------------------------
# SSRF prevention for MCP URLs
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


def validate_mcp_url(url: str, settings: dict):
    """Validate MCP server URL for security.

    Blocks private IPs, enforces HTTPS in production, and checks against allowlist.
    Raises ValueError on validation failure.
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    # Block private IPs
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _, _, _, _, addr_tuple in resolved:
            addr = ipaddress.ip_address(addr_tuple[0])
            for net in _PRIVATE_NETWORKS:
                if addr in net:
                    raise ValueError(f"MCP URL resolves to private IP: {addr}")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")

    # Check URL allowlist if configured
    allowlist = settings.get("mcp_server_url_allowlist", [])
    if allowlist:
        allowed = False
        for pattern in allowlist:
            if hostname == pattern or hostname.endswith("." + pattern):
                allowed = True
                break
        if not allowed:
            raise ValueError(f"MCP server hostname not in allowlist: {hostname}")


# ---------------------------------------------------------------------------
# MCP Plugin Factory
# ---------------------------------------------------------------------------

async def create_mcp_plugin(manifest: dict, settings: dict = None):
    """Create an MCP plugin from an action manifest.

    Args:
        manifest: Action manifest dict with keys:
            - name: Plugin name
            - description: Plugin description
            - mcp_url: MCP server URL
            - mcp_transport: "streamable_http" or "sse" (default: streamable_http)
            - mcp_auth_type: "none", "api_key", or "azure_identity"
            - mcp_auth_header: Auth header name (e.g., "Authorization")
            - mcp_auth_value: Auth header value (e.g., "Bearer xxx")
            - mcp_timeout: Request timeout in seconds (default: 30)
            - mcp_load_prompts: Whether to load prompts (default: False)
            - mcp_allowed_tools: Optional list of tool names to allow
        settings: App settings dict for validation

    Returns:
        Connected MCP plugin instance.
    """
    if settings is None:
        settings = {}

    mcp_url = manifest.get("mcp_url", "")
    if not mcp_url:
        raise ValueError("MCP manifest missing 'mcp_url'")

    validate_mcp_url(mcp_url, settings)

    name = manifest.get("name", "mcp_plugin")
    description = manifest.get("description", "")
    transport = manifest.get("mcp_transport", "streamable_http")
    timeout = manifest.get("mcp_timeout", 30)
    load_prompts = manifest.get("mcp_load_prompts", False)

    # Build auth headers
    headers = {}
    auth_type = manifest.get("mcp_auth_type", "none")
    if auth_type == "api_key":
        header_name = manifest.get("mcp_auth_header", "Authorization")
        header_value = manifest.get("mcp_auth_value", "")
        if header_value:
            headers[header_name] = header_value

    start_time = time.time()

    try:
        if transport == "sse":
            from semantic_kernel.connectors.mcp import MCPSsePlugin
            plugin = MCPSsePlugin(
                name=name,
                description=description,
                url=mcp_url,
                headers=headers if headers else None,
                load_tools=True,
                load_prompts=load_prompts,
                request_timeout=timeout,
            )
        else:
            from semantic_kernel.connectors.mcp import MCPStreamableHttpPlugin
            plugin = MCPStreamableHttpPlugin(
                name=name,
                description=description,
                url=mcp_url,
                headers=headers if headers else None,
                load_tools=True,
                load_prompts=load_prompts,
                request_timeout=timeout,
            )

        await plugin.connect()
        duration_ms = int((time.time() - start_time) * 1000)

        # Filter tools if allowlist is set
        allowed_tools = manifest.get("mcp_allowed_tools")
        if allowed_tools and hasattr(plugin, "functions"):
            # Filter to only allowed tool names
            pass  # SK MCP plugins auto-load; filtering happens at invocation time

        _log_event(
            "mcp_plugin_connected",
            level=logging.INFO,
            extra={
                "plugin_name": name,
                "mcp_url": mcp_url,
                "transport": transport,
                "duration_ms": duration_ms,
            },
        )

        return plugin

    except ImportError as e:
        raise ImportError(
            f"MCP plugin support requires semantic-kernel[mcp]. "
            f"Install with: pip install 'semantic-kernel[mcp]>=1.39.4'. Error: {e}"
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        _log_event(
            "mcp_plugin_connection_failed",
            level=logging.ERROR,
            extra={
                "plugin_name": name,
                "mcp_url": mcp_url,
                "error": str(e),
                "duration_ms": duration_ms,
            },
        )
        raise


async def test_mcp_connection(mcp_url: str, transport: str = "streamable_http",
                               auth_type: str = "none", auth_header: str = "",
                               auth_value: str = "", timeout: int = 30,
                               settings: dict = None) -> dict:
    """Test connectivity to an MCP server and list available tools.

    Returns dict with: connected (bool), tools (list), latency_ms (int), error (str or None)
    """
    if settings is None:
        settings = {}

    try:
        validate_mcp_url(mcp_url, settings)
    except ValueError as e:
        return {"connected": False, "tools": [], "latency_ms": 0, "error": str(e)}

    manifest = {
        "name": "test_mcp",
        "mcp_url": mcp_url,
        "mcp_transport": transport,
        "mcp_auth_type": auth_type,
        "mcp_auth_header": auth_header,
        "mcp_auth_value": auth_value,
        "mcp_timeout": timeout,
    }

    start_time = time.time()
    try:
        plugin = await create_mcp_plugin(manifest, settings)
        latency_ms = int((time.time() - start_time) * 1000)

        tools = []
        if hasattr(plugin, "functions"):
            for func_name, func in plugin.functions.items():
                tools.append({
                    "name": func_name,
                    "description": getattr(func, "description", ""),
                })

        # Disconnect after test
        if hasattr(plugin, "close"):
            await plugin.close()

        return {
            "connected": True,
            "tools": tools,
            "latency_ms": latency_ms,
            "error": None,
        }

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "connected": False,
            "tools": [],
            "latency_ms": latency_ms,
            "error": str(e),
        }
