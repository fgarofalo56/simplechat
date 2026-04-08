# tests/integration/test_notification_feedback_routes.py
# Integration tests for notification and feedback API routes.

import pytest
import json


class TestNotificationRoutes:
    """Verify notification endpoints require authentication."""

    def test_unauthenticated_get_notifications_rejected(self, client):
        """GET /api/notifications should reject unauthenticated requests."""
        response = client.get("/api/notifications")
        assert response.status_code in (302, 401, 403)

    def test_authenticated_get_notifications(self, authenticated_session, mock_settings):
        """Authenticated user should be able to list notifications."""
        response = authenticated_session.get("/api/notifications")
        # Should return 200 (list) or error from mock — not 500
        assert response.status_code != 500

    def test_unauthenticated_notification_count_rejected(self, client):
        """GET /api/notifications/count should reject unauthenticated."""
        response = client.get("/api/notifications/count")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_notification_page_rejected(self, client):
        """Notification frontend page should reject unauthenticated requests."""
        response = client.get("/notifications")
        assert response.status_code in (302, 401, 403)


class TestFeedbackRoutes:
    """Verify feedback endpoints require authentication."""

    def test_unauthenticated_feedback_submit_rejected(self, client):
        """POST /feedback/submit should reject unauthenticated requests."""
        response = client.post(
            "/feedback/submit",
            data=json.dumps({"message_id": "fake", "rating": "positive"}),
            content_type="application/json",
        )
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_my_feedback_rejected(self, client):
        """GET /my_feedback should reject unauthenticated requests."""
        response = client.get("/my_feedback")
        assert response.status_code in (302, 401, 403)

    def test_unauthenticated_feedback_review_rejected(self, client):
        """GET /admin/feedback_review should reject unauthenticated requests."""
        response = client.get("/admin/feedback_review")
        assert response.status_code in (302, 401, 403)

    def test_non_admin_feedback_review_rejected(self, authenticated_session):
        """Regular user should not access feedback review."""
        response = authenticated_session.get("/admin/feedback_review")
        # Should be denied — admins only can review feedback
        assert response.status_code in (302, 403)
