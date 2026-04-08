# tests/integration/test_speech_model_routes.py
# Integration tests for speech/TTS, model selection, and conversation export API routes.

import pytest


class TestSpeechRoutes:
    """Verify speech/TTS endpoints require authentication."""

    def test_unauthenticated_speech_transcribe_rejected(self, client):
        """POST /api/speech/transcribe-chat should reject unauthenticated."""
        response = client.post("/api/speech/transcribe-chat")
        assert response.status_code in (302, 401, 403)


class TestModelRoutes:
    """Verify model selection endpoints require authentication."""

    def test_unauthenticated_gpt_models_rejected(self, client):
        """GET /api/models/gpt should reject unauthenticated requests."""
        response = client.get("/api/models/gpt")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_embedding_models_rejected(self, client):
        """GET /api/models/embedding should reject unauthenticated."""
        response = client.get("/api/models/embedding")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_get_gpt_models(self, authenticated_session, mock_settings):
        """Authenticated user should be able to list GPT models."""
        response = authenticated_session.get("/api/models/gpt")
        # Should return 200 or error — not 500 or auth error
        assert response.status_code != 500
        assert response.status_code not in (401, 403)


class TestConversationExportRoutes:
    """Verify conversation export endpoints require authentication."""

    def test_unauthenticated_export_rejected(self, client):
        """POST /api/conversations/export should reject unauthenticated."""
        response = client.post("/api/conversations/export")
        assert response.status_code in (302, 401, 403)
