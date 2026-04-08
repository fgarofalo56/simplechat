# tests/integration/test_prompt_routes.py
# Integration tests for prompt-related API routes — personal, group, and public.

import pytest


class TestPersonalPromptRoutes:
    """Verify personal prompt routes require authentication."""

    def test_unauthenticated_prompts_rejected(self, client):
        """GET /api/prompts should reject unauthenticated requests."""
        response = client.get("/api/prompts")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_get_prompts(self, authenticated_session, mock_settings):
        """Authenticated user should be able to list prompts."""
        response = authenticated_session.get("/api/prompts")
        assert response.status_code in (200, 302)
        assert response.status_code != 500


class TestGroupPromptRoutes:
    """Verify group prompt routes require authentication."""

    def test_unauthenticated_group_prompts_rejected(self, client):
        """GET /api/group_prompts should reject unauthenticated requests."""
        response = client.get("/api/group_prompts")
        assert response.status_code in (302, 401, 403)


class TestPublicPromptRoutes:
    """Verify public prompt routes require authentication."""

    def test_unauthenticated_public_prompts_rejected(self, client):
        """GET /api/public_prompts should reject unauthenticated requests."""
        response = client.get("/api/public_prompts")
        assert response.status_code in (302, 401, 403)
