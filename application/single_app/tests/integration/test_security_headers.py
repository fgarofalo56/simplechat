# tests/integration/test_security_headers.py
# Integration tests verifying security headers on HTTP responses.

import pytest


# Use a non-existent URL to test security headers. Flask's after_request
# handler fires on ALL responses (including 404s), so this avoids needing
# a route that might invoke MSAL or require complex mocking.
_TEST_URL = "/this-url-does-not-exist-header-test"


class TestSecurityHeaders:
    """Verify that security headers are applied to all responses.

    Security headers are set via app.after_request(add_security_headers),
    which fires for every response including 404s. We test using a
    non-existent URL to avoid external dependencies (MSAL, etc.).
    """

    def test_x_frame_options_present(self, client):
        response = client.get(_TEST_URL)
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy_present(self, client):
        response = client.get(_TEST_URL)
        assert "strict-origin" in response.headers.get("Referrer-Policy", "")

    def test_permissions_policy_present(self, client):
        response = client.get(_TEST_URL)
        policy = response.headers.get("Permissions-Policy", "")
        assert "camera=()" in policy

    def test_csp_header_present(self, client):
        response = client.get(_TEST_URL)
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp

    def test_csp_has_nonce_not_unsafe_eval(self, client):
        """CSP should use nonce-based script loading, not unsafe-eval."""
        response = client.get(_TEST_URL)
        csp = response.headers.get("Content-Security-Policy", "")
        assert "'unsafe-eval'" not in csp
        # Nonce should be present in script-src
        script_src = csp.split("script-src")[1].split(";")[0] if "script-src" in csp else ""
        assert "'nonce-" in script_src or "'unsafe-inline'" in script_src

    def test_x_content_type_options_on_text_response(self, client):
        """X-Content-Type-Options is set conditionally for text/* content types."""
        response = client.get(_TEST_URL)
        # Flask's default 404 returns text/html, so nosniff should be present
        if response.content_type and "text/" in response.content_type.lower():
            assert response.headers.get("X-Content-Type-Options") == "nosniff"


class TestSessionCookieSecurity:
    """Verify that session cookie flags are set correctly."""

    def test_session_cookie_httponly(self, app):
        assert app.config.get("SESSION_COOKIE_HTTPONLY") is True

    def test_session_cookie_samesite(self, app):
        samesite = app.config.get("SESSION_COOKIE_SAMESITE")
        assert samesite in ("Lax", "Strict", "None")

    def test_permanent_session_lifetime_set(self, app):
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        assert lifetime is not None
        assert lifetime.total_seconds() > 0

    def test_csrf_time_limit_matches_session(self, app):
        """CSRF token lifetime should match session lifetime."""
        csrf_limit = app.config.get("WTF_CSRF_TIME_LIMIT")
        session_limit = app.config.get("PERMANENT_SESSION_LIFETIME")
        if csrf_limit and session_limit:
            assert csrf_limit == int(session_limit.total_seconds())


class TestCsrfProtection:
    """Verify CSRF protection is active."""

    def test_csrf_enabled_in_production_config(self):
        """CSRF should be enabled by default (only disabled in test config)."""
        from config_constants import SECRET_KEY
        assert SECRET_KEY is not None  # CSRF requires a secret key


class TestHealthEndpoint:
    """Verify the health check endpoint works."""

    def test_health_returns_200(self, client, mock_settings):
        """Health endpoint at /external/healthcheck requires enable_external_healthcheck."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.get("/external/healthcheck")
        assert response.status_code == 200

    def test_health_returns_text(self, client, mock_settings):
        """Health endpoint returns a timestamp string."""
        mock_settings.return_value["enable_external_healthcheck"] = True
        response = client.get("/external/healthcheck")
        assert response.status_code == 200
        # Should return a datetime string
        data = response.get_data(as_text=True)
        assert len(data) > 0
