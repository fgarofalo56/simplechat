#!/usr/bin/env python3
"""
Functional test for Phase 3: MCP Client Support.
Version: 0.239.002
Implemented in: 0.239.003

Tests MCP plugin factory, SSRF prevention, SK loader integration,
admin settings, and MCP connection testing.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


def test_mcp_url_validation():
    """Test MCP URL validation and SSRF prevention."""
    print("Testing Task 3.6: MCP URL validation / SSRF prevention...")
    try:
        from semantic_kernel_plugins.mcp_plugin_factory import validate_mcp_url

        # Valid public URLs (must resolve)
        validate_mcp_url("https://example.com/api", {})

        # Private IPs blocked
        for url in ["http://127.0.0.1:8080", "http://10.0.0.1/mcp", "http://192.168.1.1/api"]:
            try:
                validate_mcp_url(url, {})
                print(f"  FAIL: Should have blocked {url}")
                return False
            except ValueError:
                pass

        # Allowlist enforcement
        settings = {"mcp_server_url_allowlist": ["example.com"]}
        validate_mcp_url("https://example.com/api", settings)

        try:
            validate_mcp_url("https://untrusted.evil.com/api", settings)
            print("  FAIL: Should have blocked URL not in allowlist")
            return False
        except ValueError:
            pass

        print("  PASS: MCP URL validation working correctly")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_plugin_factory_exists():
    """Test that MCP plugin factory file has required functions."""
    print("Testing Task 3.2: MCP plugin factory...")
    try:
        factory_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'semantic_kernel_plugins', 'mcp_plugin_factory.py'
        )
        with open(factory_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'async def create_mcp_plugin' in source, "Missing create_mcp_plugin function"
        assert 'async def test_mcp_connection' in source, "Missing test_mcp_connection function"
        assert 'def validate_mcp_url' in source, "Missing validate_mcp_url function"
        assert 'MCPStreamableHttpPlugin' in source, "Missing StreamableHTTP transport support"
        assert 'MCPSsePlugin' in source, "Missing SSE transport support"
        assert 'mcp_plugin_connected' in source, "Missing connection logging"

        print("  PASS: MCP plugin factory has all required functions")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sk_loader_mcp_integration():
    """Test that SK loader handles MCP server type."""
    print("Testing Task 3.3: SK loader MCP integration...")
    try:
        loader_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'semantic_kernel_loader.py'
        )
        with open(loader_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert "mcp_server" in source, "Missing mcp_server type handling"
        assert "create_mcp_plugin" in source, "Missing create_mcp_plugin import"
        assert "enable_mcp_servers" in source, "Missing feature gate check"

        print("  PASS: SK loader has MCP type handling")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_requirements_mcp_extra():
    """Test that semantic-kernel[mcp] is in requirements."""
    print("Testing Task 3.1: SK MCP dependency...")
    try:
        req_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'requirements.txt'
        )
        with open(req_path, 'r') as f:
            source = f.read()

        assert 'semantic-kernel[mcp]>=1.39.4' in source, "Missing semantic-kernel[mcp] extra"

        print("  PASS: semantic-kernel[mcp] dependency configured")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_settings_defaults():
    """Test MCP settings defaults."""
    print("Testing Task 3.8: MCP settings defaults...")
    try:
        settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_settings.py'
        )
        with open(settings_path, 'r') as f:
            source = f.read()

        required = [
            "'enable_mcp_servers': False",
            "'mcp_server_url_allowlist': []",
            "'mcp_default_timeout': 30",
        ]

        for setting in required:
            assert setting in source, f"Missing: {setting}"

        print("  PASS: MCP settings defaults present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcp_admin_ui():
    """Test MCP Servers tab in admin settings."""
    print("Testing Task 3.8: MCP admin UI...")
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'templates', 'admin_settings.html'
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'id="mcp-servers-tab"' in source, "Missing MCP Servers tab button"
        assert 'id="mcp-servers"' in source, "Missing MCP Servers tab pane"
        assert 'name="enable_mcp_servers"' in source, "Missing enable_mcp_servers toggle"
        assert 'name="mcp_default_timeout"' in source, "Missing mcp_default_timeout input"

        print("  PASS: MCP Servers tab and fields present in admin UI")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []
    results.append(test_mcp_url_validation())
    results.append(test_mcp_plugin_factory_exists())
    results.append(test_sk_loader_mcp_integration())
    results.append(test_requirements_mcp_extra())
    results.append(test_mcp_settings_defaults())
    results.append(test_mcp_admin_ui())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All Phase 3 tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
