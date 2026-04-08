# tests/integration/test_admin_routes.py
# Integration tests for admin/control-center API routes — user management,
# settings, agents, and retention policies.

import pytest
import json


class TestAdminUserManagement:
    """Verify admin user management endpoints require admin role."""

    @pytest.mark.parametrize("path", [
        "/api/admin/control-center/users",
        "/api/admin/control-center/activity-trends",
    ])
    def test_unauthenticated_admin_rejected(self, client, path):
        """Admin endpoints should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403)

    @pytest.mark.parametrize("path", [
        "/api/admin/control-center/users",
    ])
    def test_non_admin_user_rejected(self, authenticated_session, path):
        """Regular user should be rejected from admin endpoints."""
        response = authenticated_session.get(path)
        assert response.status_code in (302, 403)

    def test_admin_can_list_users(self, admin_session, mock_settings):
        """Admin should be able to access user listing."""
        response = admin_session.get("/api/admin/control-center/users")
        # May return 200 or internal error with mock Cosmos — not 403
        assert response.status_code not in (401, 403)


class TestAdminSettingsRoutes:
    """Verify settings management routes via frontend paths."""

    def test_unauthenticated_admin_settings_page_rejected(self, client):
        """GET /admin/settings should reject unauthenticated requests."""
        response = client.get("/admin/settings")
        assert response.status_code in (302, 401, 403)

    def test_non_admin_settings_page_rejected(self, authenticated_session):
        """Regular user should not access admin settings page."""
        response = authenticated_session.get("/admin/settings")
        assert response.status_code in (302, 403)

    def test_admin_settings_page_accessible(self, admin_session, mock_settings):
        """Admin should be able to access admin settings page."""
        response = admin_session.get("/admin/settings")
        assert response.status_code in (200, 302)

    def test_admin_settings_test_connection(self, admin_session, mock_settings):
        """Admin can access test_connection endpoint."""
        response = admin_session.post(
            "/api/admin/settings/test_connection",
            data=json.dumps({"service": "openai"}),
            content_type="application/json",
        )
        # Should not get auth error
        assert response.status_code not in (401, 403)


class TestAdminAgentRoutes:
    """Verify agent management routes require authentication."""

    def test_unauthenticated_admin_agents_rejected(self, client):
        """GET /api/admin/agents should reject unauthenticated requests."""
        response = client.get("/api/admin/agents")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_agent_templates_rejected(self, client):
        """GET /api/admin/agent-templates should reject unauthenticated."""
        response = client.get("/api/admin/agent-templates")
        assert response.status_code in (302, 401, 403)

    def test_non_admin_agents_rejected(self, authenticated_session):
        """Regular user should not access admin agent management."""
        response = authenticated_session.get("/api/admin/agents")
        assert response.status_code in (302, 403)

    def test_admin_can_list_agents(self, admin_session, mock_settings):
        """Admin should be able to list agents."""
        response = admin_session.get("/api/admin/agents")
        assert response.status_code not in (401, 403)


class TestAdminRetentionPolicy:
    """Verify retention policy routes require authentication."""

    def test_unauthenticated_retention_defaults_rejected(self, client):
        """GET /api/retention-policy/defaults/<type> should reject unauth."""
        response = client.get("/api/retention-policy/defaults/user")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_retention_post_rejected(self, client):
        """POST /api/retention-policy/user should reject unauth."""
        response = client.post("/api/retention-policy/user")
        assert response.status_code in (302, 401, 403)


class TestUserPluginRoutes:
    """Verify user-level plugin routes require authentication."""

    def test_unauthenticated_user_plugins_rejected(self, client):
        """GET /api/user/plugins should reject unauthenticated requests."""
        response = client.get("/api/user/plugins")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_user_plugins(self, authenticated_session, mock_settings):
        """Authenticated user should be able to list their plugins."""
        response = authenticated_session.get("/api/user/plugins")
        assert response.status_code != 500
        assert response.status_code not in (401, 403)


class TestUserAgentRoutes:
    """Verify user-level agent routes require authentication."""

    def test_unauthenticated_user_agents_rejected(self, client):
        """GET /api/user/agents should reject unauthenticated requests."""
        response = client.get("/api/user/agents")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_user_agents(self, authenticated_session, mock_settings):
        """Authenticated user should be able to list their agents."""
        response = authenticated_session.get("/api/user/agents")
        assert response.status_code != 500
        assert response.status_code not in (401, 403)
