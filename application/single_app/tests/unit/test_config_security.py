# tests/unit/test_config_security.py
# Unit tests for security configuration.
# Tests import from utils.security (lightweight, no Azure SDK dependencies)
# and verify the security constants independently.

import pytest
import sys
import os

# Ensure app dir is on path
APP_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
if APP_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(APP_DIR))

from utils.security import build_csp_header, generate_csp_nonce


class TestBuildCspHeader:
    """Tests for the CSP header builder function."""

    def test_with_nonce_includes_nonce(self):
        result = build_csp_header(nonce="abc123")
        assert "'nonce-abc123'" in result
        assert "'unsafe-inline'" not in result.split("script-src")[1].split(";")[0]

    def test_with_nonce_removes_unsafe_eval(self):
        result = build_csp_header(nonce="abc123")
        assert "'unsafe-eval'" not in result

    def test_without_nonce_uses_unsafe_inline(self):
        result = build_csp_header(nonce=None)
        assert "'unsafe-inline'" in result.split("script-src")[1].split(";")[0]

    def test_without_nonce_no_unsafe_eval(self):
        result = build_csp_header()
        assert "'unsafe-eval'" not in result

    def test_includes_all_required_directives(self):
        result = build_csp_header(nonce="test")
        required_directives = [
            "default-src 'self'",
            "script-src",
            "style-src 'self'",
            "img-src 'self'",
            "font-src 'self'",
            "connect-src 'self'",
            "media-src 'self'",
            "object-src 'none'",
            "frame-ancestors 'self'",
            "base-uri 'self'",
        ]
        for directive in required_directives:
            assert directive in result, f"Missing directive: {directive}"

    def test_style_src_keeps_unsafe_inline(self):
        """Inline styles are allowed since removing them is impractical."""
        result = build_csp_header(nonce="test")
        style_src = result.split("style-src")[1].split(";")[0]
        assert "'unsafe-inline'" in style_src

    def test_object_src_is_none(self):
        result = build_csp_header(nonce="test")
        assert "object-src 'none'" in result

    def test_connect_src_allows_websockets(self):
        result = build_csp_header(nonce="test")
        connect = result.split("connect-src")[1].split(";")[0]
        assert "wss:" in connect
        assert "ws:" in connect


class TestGenerateCspNonce:
    """Tests for nonce generation."""

    def test_returns_string(self):
        nonce = generate_csp_nonce()
        assert isinstance(nonce, str)

    def test_not_empty(self):
        nonce = generate_csp_nonce()
        assert len(nonce) > 0

    def test_unique_per_call(self):
        nonces = {generate_csp_nonce() for _ in range(100)}
        assert len(nonces) == 100, "Nonces should be unique"

    def test_url_safe_characters(self):
        """Nonce should only contain URL-safe base64 characters."""
        import re
        nonce = generate_csp_nonce()
        assert re.match(r'^[A-Za-z0-9_-]+$', nonce)
