# test_admin_metrics_service.py
# Unit tests for services/admin_metrics_service.py — admin dashboard metrics.

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone


@pytest.mark.usefixtures('set_test_env')
class TestEnhanceUserWithActivity:
    """Tests for enhance_user_with_activity() — enriches user data with computed fields and activity metrics."""

    def _make_user(self, **overrides):
        """Helper to create a user dict with reasonable defaults."""
        base = {
            'id': 'user-123',
            'email': 'test@example.com',
            'display_name': 'Test User',
            'settings': {},
            'lastUpdated': '2024-01-01T00:00:00Z'
        }
        base.update(overrides)
        return base

    def test_basic_user_structure(self):
        """Test that enhance_user_with_activity returns expected structure with defaults."""
        user = self._make_user()

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            # Check basic structure
            assert result['id'] == 'user-123'
            assert result['email'] == 'test@example.com'
            assert result['display_name'] == 'Test User'
            assert result['access_status'] == 'allow'
            assert result['file_upload_status'] == 'allow'
            assert result['profile_image'] is None

            # Check activity structure with defaults
            assert 'activity' in result
            assert result['activity']['login_metrics']['total_logins'] == 0
            assert result['activity']['login_metrics']['last_login'] is None
            assert result['activity']['chat_metrics']['total_conversations'] == 0
            assert result['activity']['chat_metrics']['total_messages'] == 0
            assert result['activity']['chat_metrics']['total_content_size'] == 0
            assert result['activity']['document_metrics']['total_documents'] == 0
            assert result['activity']['document_metrics']['ai_search_size'] == 0
            assert result['activity']['document_metrics']['storage_account_size'] == 0
            assert result['activity']['document_metrics']['personal_workspace_enabled'] is False

    def test_access_status_deny_permanent(self):
        """Test user with permanent deny access status shows 'deny'."""
        user = self._make_user(settings={
            'access': {
                'status': 'deny'
                # No datetime_to_allow means permanent deny
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == 'deny'

    def test_access_status_deny_with_expired_datetime(self):
        """Test user with expired deny datetime shows 'allow'."""
        # Set datetime to 1 hour ago (expired)
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        user = self._make_user(settings={
            'access': {
                'status': 'deny',
                'datetime_to_allow': expired_time
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == 'allow'

    def test_access_status_deny_with_future_datetime(self):
        """Test user with future deny datetime shows 'deny_until_...'."""
        # Set datetime to 1 hour in the future
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        user = self._make_user(settings={
            'access': {
                'status': 'deny',
                'datetime_to_allow': future_time
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == f"deny_until_{future_time}"

    def test_access_status_deny_with_invalid_datetime(self):
        """Test user with invalid datetime string falls back to 'deny'."""
        user = self._make_user(settings={
            'access': {
                'status': 'deny',
                'datetime_to_allow': 'invalid-date-string'
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == 'deny'

    def test_file_upload_status_deny_permanent(self):
        """Test user with permanent file upload deny shows 'deny'."""
        user = self._make_user(settings={
            'file_uploads': {
                'status': 'deny'
                # No datetime_to_allow means permanent deny
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['file_upload_status'] == 'deny'

    def test_file_upload_status_deny_with_future_datetime(self):
        """Test user with future file upload deny shows 'deny_until_...'."""
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        user = self._make_user(settings={
            'file_uploads': {
                'status': 'deny',
                'datetime_to_allow': future_time
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['file_upload_status'] == f"deny_until_{future_time}"

    def test_profile_image_extracted(self):
        """Test that profile image is extracted from settings."""
        user = self._make_user(settings={
            'profileImage': 'https://example.com/user-avatar.jpg'
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['profile_image'] == 'https://example.com/user-avatar.jpg'

    def test_personal_workspace_enabled_extracted(self):
        """Test that personal workspace enabled flag is extracted from settings."""
        user = self._make_user(settings={
            'enable_personal_workspace': True
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['activity']['document_metrics']['personal_workspace_enabled'] is True

    def test_empty_settings_dict_handled(self):
        """Test that empty settings dict is handled gracefully."""
        user = self._make_user(settings={})

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == 'allow'
            assert result['file_upload_status'] == 'allow'
            assert result['profile_image'] is None
            assert result['activity']['document_metrics']['personal_workspace_enabled'] is False

    def test_missing_settings_key_handled(self):
        """Test that missing settings key is handled gracefully."""
        user = self._make_user()
        # Remove the settings key entirely
        del user['settings']

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['settings'] == {}
            assert result['access_status'] == 'allow'
            assert result['file_upload_status'] == 'allow'
            assert result['profile_image'] is None

    def test_exception_in_activity_queries_doesnt_crash(self):
        """Test that exceptions in activity queries don't crash function, returns default zeros."""
        user = self._make_user()

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make queries raise exceptions
            mock_activity.query_items.side_effect = Exception("Database error")
            mock_convos.query_items.side_effect = Exception("Database error")
            mock_messages.query_items.side_effect = Exception("Database error")
            mock_docs.query_items.side_effect = Exception("Database error")

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            # Function should return user data with default activity values
            assert result['id'] == 'user-123'
            assert result['activity']['login_metrics']['total_logins'] == 0
            assert result['activity']['chat_metrics']['total_conversations'] == 0
            assert result['activity']['document_metrics']['total_documents'] == 0

    def test_cached_metrics_used_when_not_forcing_refresh(self):
        """Test that cached metrics are used when force_refresh=False."""
        cached_metrics = {
            'calculated_at': '2024-01-01T12:00:00Z',
            'login_metrics': {
                'total_logins': 5,
                'last_login': '2024-01-01T10:00:00Z'
            },
            'chat_metrics': {
                'last_day_conversation': '01/01/2024',
                'total_conversations': 3,
                'total_messages': 15,
                'total_content_size': 1500
            },
            'document_metrics': {
                'total_documents': 2,
                'ai_search_size': 160000,
                'storage_account_size': 500000
            }
        }

        user = self._make_user(settings={
            'metrics': cached_metrics
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.debug_print'):

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=False)

            # Should use cached values
            assert result['activity']['login_metrics']['total_logins'] == 5
            assert result['activity']['chat_metrics']['total_conversations'] == 3
            assert result['activity']['document_metrics']['total_documents'] == 2

    def test_defaults_returned_when_no_cached_metrics_and_not_forcing(self):
        """Test that default values are returned when no cache and force_refresh=False."""
        user = self._make_user()

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.debug_print'):

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=False)

            # Should return defaults without querying Cosmos
            assert result['activity']['login_metrics']['total_logins'] == 0
            assert result['activity']['chat_metrics']['total_conversations'] == 0
            assert result['activity']['document_metrics']['total_documents'] == 0

    def test_function_resilient_to_database_errors(self):
        """Test that database query exceptions don't crash function - it returns enhanced structure with default values."""
        user = self._make_user()

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all database operations fail
            mock_activity.query_items.side_effect = Exception("Database connection error")
            mock_convos.query_items.side_effect = Exception("Database connection error")
            mock_messages.query_items.side_effect = Exception("Database connection error")
            mock_docs.query_items.side_effect = Exception("Database connection error")

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            # Function should return enhanced data with default activity values rather than crashing
            assert result['id'] == 'user-123'
            assert result['access_status'] == 'allow'
            assert result['file_upload_status'] == 'allow'
            assert result['activity']['login_metrics']['total_logins'] == 0
            assert result['activity']['chat_metrics']['total_conversations'] == 0
            assert result['activity']['document_metrics']['total_documents'] == 0

    def test_datetime_with_z_suffix_parsed_correctly(self):
        """Test that datetime strings with Z suffix are parsed correctly."""
        future_time_z = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        user = self._make_user(settings={
            'access': {
                'status': 'deny',
                'datetime_to_allow': future_time_z
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == f"deny_until_{future_time_z}"

    def test_allow_status_default_for_non_deny(self):
        """Test that access and file upload status default to 'allow' for non-deny values."""
        user = self._make_user(settings={
            'access': {
                'status': 'pending'  # Not 'deny', should default to 'allow'
            },
            'file_uploads': {
                'status': 'review'  # Not 'deny', should default to 'allow'
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Make all queries return empty results
            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['access_status'] == 'allow'
            assert result['file_upload_status'] == 'allow'

    def test_file_upload_status_deny_with_expired_datetime(self):
        """Test user with expired file upload deny shows 'allow'."""
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        user = self._make_user(settings={
            'file_uploads': {
                'status': 'deny',
                'datetime_to_allow': expired_time
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['file_upload_status'] == 'allow'

    def test_file_upload_status_deny_with_invalid_datetime(self):
        """Test user with invalid file upload deny datetime falls back to 'deny'."""
        user = self._make_user(settings={
            'file_uploads': {
                'status': 'deny',
                'datetime_to_allow': 'not-a-date'
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            mock_activity.query_items.return_value = iter([])
            mock_convos.query_items.return_value = iter([])
            mock_messages.query_items.return_value = iter([])
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['file_upload_status'] == 'deny'

    def test_force_refresh_with_conversations(self):
        """Test force_refresh computes chat metrics from Cosmos queries."""
        user = self._make_user()

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.cosmos_activity_logs_container', create=True) as mock_activity, \
             patch('services.admin_metrics_service.cosmos_conversations_container', create=True) as mock_convos, \
             patch('services.admin_metrics_service.cosmos_messages_container', create=True) as mock_messages, \
             patch('services.admin_metrics_service.cosmos_user_documents_container', create=True) as mock_docs, \
             patch('services.admin_metrics_service.debug_print'):

            # Return 2 conversations
            mock_convos.query_items.return_value = iter([
                {'id': 'conv-1', 'last_updated': '2024-06-15T10:00:00Z'},
                {'id': 'conv-2', 'last_updated': '2024-06-10T08:00:00Z'},
            ])

            # Message counts and sizes
            mock_messages.query_items.side_effect = [
                iter([5]),    # count for batch
                iter([2500]), # size for batch
            ]

            # Login metrics
            mock_activity.query_items.side_effect = [
                iter([10]),       # total logins
                iter([{'timestamp': '2024-06-15T10:00:00Z'}]),  # last login
            ]

            # Document metrics
            mock_docs.query_items.return_value = iter([])

            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=True)

            assert result['activity']['chat_metrics']['total_conversations'] == 2
            assert result['activity']['chat_metrics']['total_messages'] == 5

    def test_cached_metrics_personal_workspace_flag_overridden(self):
        """Cached doc metrics get personal_workspace_enabled from live settings, not cache."""
        user = self._make_user(settings={
            'enable_personal_workspace': True,
            'metrics': {
                'calculated_at': '2024-01-01T12:00:00Z',
                'login_metrics': {'total_logins': 5, 'last_login': None},
                'chat_metrics': {'total_conversations': 0, 'total_messages': 0, 'total_content_size': 0},
                'document_metrics': {
                    'total_documents': 0,
                    'ai_search_size': 0,
                    'storage_account_size': 0,
                    'personal_workspace_enabled': False,  # cached as False
                },
            }
        })

        with patch('services.admin_metrics_service.get_settings', return_value={}), \
             patch('services.admin_metrics_service.debug_print'):
            from services.admin_metrics_service import enhance_user_with_activity
            result = enhance_user_with_activity(user, force_refresh=False)
            # Should use live settings value (True), not cached (False)
            assert result['activity']['document_metrics']['personal_workspace_enabled'] is True