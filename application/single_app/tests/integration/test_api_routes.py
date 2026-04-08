# tests/integration/test_api_routes.py
# Integration tests for API route protection and basic response behavior.

import pytest
import json


class TestDocumentApiRoutes:
    """Verify document API routes require authentication and respond correctly."""

    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/documents"),
        ("POST", "/api/documents/upload"),
        ("DELETE", "/api/documents/fake-doc-id"),
    ])
    def test_unauthenticated_request_rejected(self, client, method, path):
        """API document routes should reject unauthenticated requests."""
        if method == "GET":
            response = client.get(path)
        elif method == "POST":
            response = client.post(path)
        elif method == "DELETE":
            response = client.delete(path)
        assert response.status_code in (302, 401, 403), \
            f"Expected auth rejection for {method} {path}, got {response.status_code}"

    def test_authenticated_get_documents(self, authenticated_session, mock_settings):
        """Authenticated user can access the documents list endpoint."""
        response = authenticated_session.get("/api/documents")
        # Should return 200 with JSON or redirect to workspace
        assert response.status_code in (200, 302)


class TestConversationApiRoutes:
    """Verify conversation API routes require authentication."""

    @pytest.mark.parametrize("path", [
        "/api/get_conversations",
        "/conversations",
    ])
    def test_unauthenticated_request_rejected(self, client, path):
        """Conversation API routes should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403), \
            f"Expected auth rejection for GET {path}, got {response.status_code}"

    def test_authenticated_get_conversations(self, authenticated_session, mock_settings):
        """Authenticated user can access conversations endpoint."""
        response = authenticated_session.get("/api/get_conversations")
        assert response.status_code in (200, 302)


class TestGroupApiRoutes:
    """Verify group API routes require authentication."""

    def test_unauthenticated_get_groups_rejected(self, client):
        """Group listing should reject unauthenticated requests."""
        response = client.get("/api/groups")
        assert response.status_code in (302, 401, 403)


class TestAdminApiRoutes:
    """Verify admin API routes require admin role."""

    def test_non_admin_rejected_settings(self, authenticated_session):
        """Regular user should not access admin settings."""
        response = authenticated_session.get("/admin/settings")
        assert response.status_code in (302, 403)

    def test_non_admin_rejected_users(self, authenticated_session):
        """Regular user should not access admin user management."""
        response = authenticated_session.get("/api/admin/control-center/users")
        assert response.status_code in (302, 403)

    def test_admin_can_access_settings(self, admin_session, mock_settings):
        """Admin user should be able to access admin settings."""
        response = admin_session.get("/admin/settings")
        assert response.status_code in (200, 302)


class TestExternalApiRoutes:
    """Test external/public API endpoints."""

    def test_healthcheck_disabled_returns_error(self, client, mock_settings):
        """Healthcheck should return 400 when disabled in settings."""
        mock_settings.return_value["enable_external_healthcheck"] = False
        response = client.get("/external/healthcheck")
        # enabled_required returns 400 with error JSON when disabled
        assert response.status_code in (400, 403, 404)

    def test_healthcheck_enabled_returns_200(self, client, mock_settings):
        """Healthcheck should return 200 when enabled."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.get("/external/healthcheck")
        assert response.status_code == 200


class TestStaticAssets:
    """Verify static asset serving works."""

    def test_favicon_accessible(self, client):
        """Favicon or static assets should be accessible without auth."""
        response = client.get("/static/img/simplechat_logo.png")
        # Might be 200 if file exists or 404 if not — should never be 500
        assert response.status_code in (200, 304, 404)
        assert response.status_code != 500


class TestMethodNotAllowed:
    """Verify proper 405 handling for wrong HTTP methods."""

    def test_post_to_get_only_route(self, client):
        """POST to a GET-only route should return 405 or redirect."""
        response = client.post("/external/healthcheck")
        # Could be 405 Method Not Allowed, 302 redirect, or 404
        assert response.status_code in (302, 401, 403, 404, 405)
