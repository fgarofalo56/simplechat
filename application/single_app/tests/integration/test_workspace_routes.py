# tests/integration/test_workspace_routes.py
# Integration tests for workspace-related routes — personal, group, and public.

import pytest


class TestPersonalWorkspaceRoutes:
    """Verify personal workspace routes require authentication."""

    @pytest.mark.parametrize("path", [
        "/workspace",
    ])
    def test_unauthenticated_workspace_rejected(self, client, path):
        """Personal workspace pages should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403)

    def test_authenticated_workspace_accessible(self, authenticated_session, mock_settings):
        """Authenticated user should be able to access workspace."""
        response = authenticated_session.get("/workspace")
        assert response.status_code in (200, 302)
        # If redirected, should not be to login
        if response.status_code == 302:
            location = response.headers.get("Location", "")
            assert "login" not in location.lower()


class TestGroupWorkspaceRoutes:
    """Verify group workspace routes require authentication."""

    def test_unauthenticated_groups_page_rejected(self, client):
        """Group workspaces page should reject unauthenticated requests."""
        response = client.get("/my_groups")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_api_groups_rejected(self, client):
        """GET /api/groups should reject unauthenticated requests."""
        response = client.get("/api/groups")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_create_group_rejected(self, client):
        """POST /api/groups should reject unauthenticated requests."""
        response = client.post("/api/groups")
        assert response.status_code in (302, 401, 403)


class TestPublicWorkspaceRoutes:
    """Verify public workspace routes require authentication."""

    def test_unauthenticated_public_workspaces_rejected(self, client):
        """Public workspaces page should reject unauthenticated requests."""
        response = client.get("/public_workspaces")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_api_public_workspaces_rejected(self, client):
        """GET /api/public_workspaces should reject unauthenticated requests."""
        response = client.get("/api/public_workspaces")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_public_workspaces(self, authenticated_session, mock_settings):
        """Authenticated user should see public workspaces page or redirect."""
        mock_settings.return_value["enable_public_workspaces"] = True
        response = authenticated_session.get("/public_workspaces")
        assert response.status_code in (200, 302)


class TestGroupDocumentRoutes:
    """Verify group document API routes require authentication."""

    @pytest.mark.parametrize("path", [
        "/api/group/fake-group-id/documents",
        "/api/group/fake-group-id/documents/upload",
    ])
    def test_unauthenticated_group_docs_rejected(self, client, path):
        """Group document routes should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403, 404, 405), \
            f"Expected auth rejection for {path}, got {response.status_code}"


class TestPublicDocumentRoutes:
    """Verify public document API routes require authentication."""

    @pytest.mark.parametrize("path", [
        "/api/public-workspaces/fake-ws-id/documents",
    ])
    def test_unauthenticated_public_docs_rejected(self, client, path):
        """Public document routes should reject unauthenticated requests."""
        response = client.get(path)
        assert response.status_code in (302, 401, 403, 404), \
            f"Expected auth rejection for {path}, got {response.status_code}"
