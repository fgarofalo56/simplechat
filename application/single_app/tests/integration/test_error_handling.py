# tests/integration/test_error_handling.py
# Integration tests for error handling, 404 pages, and edge cases.

import pytest


class TestNotFoundHandling:
    """Verify 404 handling returns appropriate responses."""

    def test_nonexistent_page_returns_404(self, client):
        """Non-existent pages should return 404."""
        response = client.get("/this-page-definitely-does-not-exist")
        assert response.status_code == 404

    def test_nonexistent_api_returns_error(self, client):
        """Non-existent API endpoints should return 404 or auth rejection."""
        response = client.get("/api/nonexistent-endpoint-xyz")
        assert response.status_code in (302, 401, 404)

    def test_404_includes_security_headers(self, client):
        """Even 404 responses should include security headers."""
        response = client.get("/this-page-definitely-does-not-exist")
        assert response.headers.get("X-Frame-Options") is not None
        assert response.headers.get("Content-Security-Policy") is not None


class TestAppConfiguration:
    """Verify critical app configuration values."""

    def test_secret_key_set(self, app):
        """Secret key must be set."""
        assert app.config.get("SECRET_KEY") is not None
        assert len(app.config["SECRET_KEY"]) > 10  # Not a trivially short key

    def test_session_type_configured(self, app):
        """Session type should be configured (not default cookie-based in production)."""
        session_type = app.config.get("SESSION_TYPE")
        assert session_type is not None

    def test_testing_mode_enabled(self, app):
        """App should be in testing mode during tests."""
        assert app.config.get("TESTING") is True


class TestCorsAndContentType:
    """Verify content type handling."""

    def test_json_content_type_on_api_response(self, authenticated_session, mock_settings):
        """API endpoints returning JSON should have correct content type."""
        response = authenticated_session.get("/api/get_conversations")
        if response.status_code == 200:
            assert "application/json" in response.content_type


class TestRateLimitingConfiguration:
    """Verify rate limiting doesn't break basic requests."""

    def test_request_not_rate_limited_on_first_call(self, client):
        """First request should never be rate limited."""
        response = client.get("/this-page-does-not-exist-rate-test")
        # Should get 404, not 429
        assert response.status_code == 404
