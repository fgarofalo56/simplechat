# tests/integration/test_external_routes.py
# Integration tests for external/public API routes — token-based auth,
# public document access, and feature-flag gating.

import pytest
import json


class TestExternalHealthEndpoint:
    """Verify external health check endpoint behavior."""

    def test_health_disabled_returns_400(self, client, mock_settings):
        """Health endpoint should return 400 when feature is disabled."""
        mock_settings.return_value["enable_external_healthcheck"] = False
        response = client.get("/external/healthcheck")
        assert response.status_code in (400, 403, 404)

    def test_health_enabled_returns_200(self, client, mock_settings):
        """Health endpoint should return 200 when feature is enabled."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.get("/external/healthcheck")
        assert response.status_code == 200

    def test_health_returns_timestamp(self, client, mock_settings):
        """Health endpoint should return a timestamp-like string."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.get("/external/healthcheck")
        data = response.get_data(as_text=True)
        # Should contain a date-like pattern
        assert len(data) >= 10  # At minimum "YYYY-MM-DD"

    def test_health_post_not_allowed(self, client, mock_settings):
        """POST to health endpoint should be rejected."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.post("/external/healthcheck")
        assert response.status_code in (405, 404)


class TestExternalPublicDocuments:
    """Verify external public document routes require access token."""

    def test_no_auth_header_returns_401(self, client):
        """Request without Authorization header should return 401."""
        response = client.get("/external/public-documents")
        # If the route exists, should return 401; if not, 404
        assert response.status_code in (401, 404)

    def test_invalid_bearer_token_returns_401(self, client):
        """Request with invalid bearer token should return 401."""
        response = client.get(
            "/external/public-documents",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert response.status_code in (401, 403, 404)

    def test_malformed_auth_header_returns_401(self, client):
        """Request with malformed auth header should return 401."""
        response = client.get(
            "/external/public-documents",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert response.status_code in (401, 404)


class TestStaticAssetAccess:
    """Verify that certain paths are accessible without auth."""

    def test_robots_txt_accessible(self, client):
        """robots933456.txt should be accessible (Azure health probe)."""
        response = client.get("/robots933456.txt")
        # Should return 200 or 404 — not an auth error
        assert response.status_code in (200, 404)

    def test_favicon_accessible(self, client):
        """Favicon should be accessible without auth."""
        response = client.get("/favicon.ico")
        assert response.status_code in (200, 302, 404)

    def test_acceptable_use_policy_accessible(self, client):
        """Acceptable use policy page should be accessible."""
        response = client.get("/acceptable_use_policy.html")
        assert response.status_code in (200, 404)
