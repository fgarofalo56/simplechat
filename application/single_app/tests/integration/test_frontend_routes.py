# tests/integration/test_frontend_routes.py
# Integration tests for frontend page routes — ensuring they require auth
# and render without 500 errors.

import pytest


class TestFrontendPageAuth:
    """Verify that all frontend pages require authentication."""

    @pytest.mark.parametrize("path", [
        "/chats",
        "/workspace",
        "/my_groups",
        "/profile",
        "/public_workspaces",
        "/conversations",
        "/notifications",
        "/my_feedback",
    ])
    def test_unauthenticated_frontend_pages_redirect(self, client, path):
        """All frontend pages should redirect unauthenticated users."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403), \
            f"Expected auth redirect for {path}, got {response.status_code}"


class TestFrontendPageRendering:
    """Verify that authenticated frontend pages render without errors."""

    def test_chats_page_renders(self, authenticated_session, mock_settings):
        """Chat page should render for authenticated user."""
        response = authenticated_session.get("/chats")
        assert response.status_code in (200, 302)
        assert response.status_code != 500

    def test_workspace_page_renders(self, authenticated_session, mock_settings):
        """Workspace page should render for authenticated user."""
        response = authenticated_session.get("/workspace")
        assert response.status_code in (200, 302)
        assert response.status_code != 500

    def test_profile_page_renders(self, authenticated_session, mock_settings):
        """Profile page should render for authenticated user."""
        response = authenticated_session.get("/profile")
        assert response.status_code in (200, 302)
        assert response.status_code != 500

    def test_notifications_page_renders(self, authenticated_session, mock_settings):
        """Notifications page should render for authenticated user."""
        response = authenticated_session.get("/notifications")
        assert response.status_code in (200, 302)
        assert response.status_code != 500


class TestAdminFrontendPages:
    """Verify admin-only frontend pages."""

    @pytest.mark.parametrize("path", [
        "/admin/settings",
        "/admin/control-center",
    ])
    def test_unauthenticated_admin_pages_rejected(self, client, path):
        """Admin frontend pages should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403)

    @pytest.mark.parametrize("path", [
        "/admin/settings",
        "/admin/control-center",
    ])
    def test_non_admin_pages_rejected(self, authenticated_session, path):
        """Regular user should not access admin pages."""
        response = authenticated_session.get(path)
        assert response.status_code in (302, 403)

    def test_admin_settings_page_renders(self, admin_session, mock_settings):
        """Admin user should be able to access admin settings page."""
        response = admin_session.get("/admin/settings")
        assert response.status_code in (200, 302)
        assert response.status_code != 500

    def test_admin_control_center_page_renders(self, admin_session, mock_settings):
        """Admin user should be able to access control center page."""
        response = admin_session.get("/admin/control-center")
        assert response.status_code in (200, 302)
        assert response.status_code != 500


class TestSafetyPages:
    """Verify safety-related frontend pages."""

    def test_unauthenticated_safety_violations_rejected(self, client):
        """Safety violations page should reject unauthenticated requests."""
        response = client.get("/safety_violations")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_admin_safety_rejected(self, client):
        """Admin safety page should reject unauthenticated requests."""
        response = client.get("/admin/safety_violations")
        assert response.status_code in (302, 401, 403)
