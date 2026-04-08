# tests/integration/test_user_routes.py
# Integration tests for user management API routes — profile, settings, search.

import pytest
import json


class TestUserAuthProtection:
    """Verify user API endpoints require authentication."""

    @pytest.mark.parametrize("path", [
        "/api/userSearch",
        "/api/user/settings",
        "/api/user/info/fake-user-id",
        "/api/user/profile-image/fake-user-id",
    ])
    def test_unauthenticated_user_routes_rejected(self, client, path):
        """User API routes should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403), \
            f"Expected auth rejection for GET {path}, got {response.status_code}"


class TestUserSearch:
    """Verify user search endpoint behavior."""

    def test_authenticated_user_search_no_query(self, authenticated_session, mock_settings):
        """GET /api/userSearch without query should return empty or error."""
        response = authenticated_session.get("/api/userSearch")
        # Should not crash — 200 (empty results) or 400 (missing param)
        assert response.status_code in (200, 400)
        assert response.status_code != 500

    def test_authenticated_user_search_with_query(self, authenticated_session, mock_settings):
        """GET /api/userSearch with query should return results or empty list."""
        response = authenticated_session.get("/api/userSearch?q=test")
        assert response.status_code in (200, 400)
        assert response.status_code != 500


class TestUserSettings:
    """Verify user settings endpoint behavior."""

    def test_authenticated_get_user_settings(self, authenticated_session, mock_settings):
        """GET /api/user/settings should return settings or empty object."""
        response = authenticated_session.get("/api/user/settings")
        assert response.status_code in (200, 302)
        assert response.status_code != 500

    def test_authenticated_post_user_settings(self, authenticated_session, mock_settings):
        """POST /api/user/settings should accept settings update."""
        response = authenticated_session.post(
            "/api/user/settings",
            data=json.dumps({"theme": "dark"}),
            content_type="application/json",
        )
        # Should succeed or return validation error — not crash
        assert response.status_code in (200, 201, 400)
        assert response.status_code != 500


class TestUserProfile:
    """Verify user profile endpoints."""

    def test_authenticated_get_user_info(self, authenticated_session, mock_settings):
        """GET /api/user/info/<id> should return user info or error."""
        response = authenticated_session.get("/api/user/info/test-user-id-12345")
        # May return 200 (user found) or 404 (user not found in mock)
        assert response.status_code in (200, 404)
        assert response.status_code != 500

    def test_authenticated_get_profile_image(self, authenticated_session, mock_settings):
        """GET /api/user/profile-image/<id> should return image or default."""
        response = authenticated_session.get("/api/user/profile-image/test-user-id-12345")
        # Image endpoint — 200 or 404
        assert response.status_code in (200, 404)
        assert response.status_code != 500
