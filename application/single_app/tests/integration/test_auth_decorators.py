# tests/integration/test_auth_decorators.py
# Integration tests for authentication decorators — ensures unauthenticated
# requests are properly rejected.

import pytest


class TestUnauthenticatedAccess:
    """Verify that protected routes reject unauthenticated requests."""

    @pytest.mark.parametrize("path", [
        "/chats",
        "/workspace",
        "/my_groups",
        "/profile",
    ])
    def test_frontend_routes_redirect_to_login(self, client, path):
        """Frontend routes should redirect unauthenticated users to login."""
        response = client.get(path)
        # Should redirect (302) to login or return 401
        assert response.status_code in (302, 401, 403), \
            f"Expected redirect/deny for {path}, got {response.status_code}"

    @pytest.mark.parametrize("path", [
        "/api/documents",
    ])
    def test_api_routes_return_401_or_redirect(self, client, path):
        """API routes should return 401 or redirect for unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403), \
            f"Expected 401/redirect for {path}, got {response.status_code}"


class TestAuthenticatedAccess:
    """Verify that authenticated users can access protected routes."""

    def test_authenticated_user_can_access_chats(self, authenticated_session):
        response = authenticated_session.get("/chats")
        # Should not be redirected to login
        assert response.status_code in (200, 302)
        # If redirected, should not be to login
        if response.status_code == 302:
            location = response.headers.get("Location", "")
            assert "login" not in location.lower()


class TestAdminAccess:
    """Verify that admin routes require admin role."""

    def test_non_admin_cannot_access_admin_settings(self, authenticated_session):
        """Regular users should not access admin settings."""
        response = authenticated_session.get("/admin/settings")
        # Should be denied or redirected
        assert response.status_code in (302, 403)

    def test_admin_can_access_admin_settings(self, admin_session):
        """Admin users should be able to access admin settings."""
        response = admin_session.get("/admin/settings")
        # Should succeed or at least not get 403
        assert response.status_code in (200, 302)
