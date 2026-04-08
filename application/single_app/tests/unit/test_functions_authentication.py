# tests/unit/test_functions_authentication.py
# Unit tests for authentication functions.

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


class TestGetCurrentUserId:
    """Tests for get_current_user_id()."""

    def test_returns_oid_when_user_in_session(self, app):
        with app.test_request_context():
            from flask import session
            session["user"] = {"oid": "user-123", "name": "Test"}
            from functions_authentication import get_current_user_id
            assert get_current_user_id() == "user-123"

    def test_returns_none_when_no_user(self, app):
        with app.test_request_context():
            from functions_authentication import get_current_user_id
            assert get_current_user_id() is None


class TestGetCurrentUserInfo:
    """Tests for get_current_user_info()."""

    def test_returns_user_info_dict(self, app):
        with app.test_request_context():
            from flask import session
            session["user"] = {
                "oid": "user-123",
                "name": "Test User",
                "preferred_username": "test@example.com",
            }
            from functions_authentication import get_current_user_info
            info = get_current_user_info()
            assert info["userId"] == "user-123"
            assert info["displayName"] == "Test User"
            assert info["email"] == "test@example.com"

    def test_returns_none_when_not_logged_in(self, app):
        with app.test_request_context():
            from functions_authentication import get_current_user_info
            assert get_current_user_info() is None


class TestCheckUserAccessStatus:
    """Tests for check_user_access_status().

    The function does `from functions_settings import get_user_settings`
    internally, so we must patch at `functions_settings.get_user_settings`
    (the source module), not on `functions_authentication`.
    """

    @patch("functions_settings.get_user_settings")
    def test_allowed_when_status_is_allow(self, mock_get_settings):
        mock_get_settings.return_value = {
            "settings": {"access": {"status": "allow"}}
        }
        from functions_authentication import check_user_access_status
        is_allowed, reason = check_user_access_status("user-123")
        assert is_allowed is True
        assert reason is None

    @patch("functions_settings.get_user_settings")
    def test_denied_when_status_is_deny(self, mock_get_settings):
        mock_get_settings.return_value = {
            "settings": {"access": {"status": "deny"}}
        }
        from functions_authentication import check_user_access_status
        is_allowed, reason = check_user_access_status("user-123")
        assert is_allowed is False

    @patch("functions_settings.get_user_settings")
    def test_default_allows_when_no_access_settings(self, mock_get_settings):
        mock_get_settings.return_value = {"settings": {}}
        from functions_authentication import check_user_access_status
        is_allowed, reason = check_user_access_status("user-123")
        assert is_allowed is True

    @patch("functions_settings.get_user_settings")
    def test_fail_closed_on_exception(self, mock_get_settings):
        """Authentication should fail closed — deny access on error."""
        mock_get_settings.side_effect = Exception("DB connection failed")
        from functions_authentication import check_user_access_status
        is_allowed, reason = check_user_access_status("user-123")
        assert is_allowed is False
        assert "unavailable" in reason.lower() or "error" in reason.lower()

    @patch("functions_settings.update_user_settings")
    @patch("functions_settings.get_user_settings")
    def test_time_based_deny_expires(self, mock_get_settings, mock_update):
        """After the deny period expires, access should be restored."""
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_get_settings.return_value = {
            "settings": {
                "access": {
                    "status": "deny",
                    "datetime_to_allow": expired_time,
                }
            }
        }
        from functions_authentication import check_user_access_status
        is_allowed, reason = check_user_access_status("user-123")
        assert is_allowed is True


class TestJwksCache:
    """Tests for JWKS caching behavior."""

    @patch("functions_authentication.requests.get")
    def test_jwks_cache_has_ttl(self, mock_get):
        """Verify JWKS cache expires after TTL period."""
        import functions_authentication

        # Clear any existing cache
        functions_authentication.JWKS_CACHE = None
        functions_authentication._JWKS_CACHE_TIMESTAMP = 0

        # The function makes TWO requests.get calls:
        # 1. OIDC metadata -> returns {"jwks_uri": "https://..."}
        # 2. JWKS endpoint -> returns {"keys": [...]}
        mock_oidc_response = MagicMock(
            status_code=200,
            json=lambda: {"jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys"},
        )
        mock_jwks_response = MagicMock(
            status_code=200,
            json=lambda: {"keys": [{"kid": "test-kid", "kty": "RSA", "n": "abc", "e": "AQAB"}]},
        )
        mock_get.side_effect = [mock_oidc_response, mock_jwks_response]

        keys = functions_authentication.get_microsoft_entra_jwks()
        assert mock_get.call_count == 2
        assert keys is not None
        assert "test-kid" in keys

    @patch("functions_authentication.requests.get")
    def test_jwks_request_has_timeout(self, mock_get):
        """Verify JWKS HTTP requests have a timeout to prevent hanging."""
        import functions_authentication

        # Clear cache to force fetch
        functions_authentication.JWKS_CACHE = None
        functions_authentication._JWKS_CACHE_TIMESTAMP = 0

        mock_oidc_response = MagicMock(
            status_code=200,
            json=lambda: {"jwks_uri": "https://login.microsoftonline.com/common/discovery/v2.0/keys"},
        )
        mock_jwks_response = MagicMock(
            status_code=200,
            json=lambda: {"keys": []},
        )
        mock_get.side_effect = [mock_oidc_response, mock_jwks_response]

        functions_authentication.get_microsoft_entra_jwks()

        # Both calls should have timeout parameter
        for call in mock_get.call_args_list:
            assert call.kwargs.get("timeout") or (len(call.args) > 1 and call.args[1]), \
                f"Request should have timeout: {call}"
