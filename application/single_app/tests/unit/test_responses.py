# tests/unit/test_responses.py
# Unit tests for utils/responses.py — standardized API response helpers.

import pytest
import sys
import os
import json

APP_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
if APP_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(APP_DIR))


@pytest.fixture
def flask_app():
    """Minimal Flask app for testing response helpers."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestApiSuccess:

    def test_default_success(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_success
            response, status = api_success()
            data = json.loads(response.get_data(as_text=True))
            assert status == 200
            assert data["success"] is True

    def test_success_with_data(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_success
            response, status = api_success(data={"id": "123"})
            data = json.loads(response.get_data(as_text=True))
            assert data["data"]["id"] == "123"

    def test_success_with_message(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_success
            response, status = api_success(message="Created")
            data = json.loads(response.get_data(as_text=True))
            assert data["message"] == "Created"

    def test_success_custom_status(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_success
            _, status = api_success(status_code=201)
            assert status == 201


class TestApiError:

    def test_default_error(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_error
            response, status = api_error("Something went wrong")
            data = json.loads(response.get_data(as_text=True))
            assert status == 400
            assert data["success"] is False
            assert data["error"] == "Something went wrong"

    def test_error_with_details(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_error
            response, status = api_error("Validation failed", details={"field": "name"})
            data = json.loads(response.get_data(as_text=True))
            assert data["details"]["field"] == "name"

    def test_error_custom_status(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_error
            _, status = api_error("Server error", status_code=500)
            assert status == 500


class TestApiNotFound:

    def test_not_found_default(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_not_found
            response, status = api_not_found()
            data = json.loads(response.get_data(as_text=True))
            assert status == 404
            assert "not found" in data["error"].lower()

    def test_not_found_custom_resource(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_not_found
            response, status = api_not_found("Document")
            data = json.loads(response.get_data(as_text=True))
            assert "Document" in data["error"]


class TestApiForbidden:

    def test_forbidden(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_forbidden
            _, status = api_forbidden()
            assert status == 403


class TestApiUnauthorized:

    def test_unauthorized(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_unauthorized
            _, status = api_unauthorized()
            assert status == 401


class TestApiPaginated:

    def test_paginated_response(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_paginated
            items = [{"id": "1"}, {"id": "2"}]
            response, status = api_paginated(items, total=50, page=1, per_page=10)
            data = json.loads(response.get_data(as_text=True))
            assert status == 200
            assert data["success"] is True
            assert len(data["data"]) == 2
            assert data["pagination"]["total"] == 50
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["per_page"] == 10
            assert data["pagination"]["total_pages"] == 5

    def test_paginated_total_pages_calculation(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_paginated
            response, _ = api_paginated([], total=11, page=1, per_page=5)
            data = json.loads(response.get_data(as_text=True))
            assert data["pagination"]["total_pages"] == 3  # ceil(11/5) = 3

    def test_paginated_zero_items(self, flask_app):
        with flask_app.app_context():
            from utils.responses import api_paginated
            response, _ = api_paginated([], total=0, page=1, per_page=10)
            data = json.loads(response.get_data(as_text=True))
            assert data["pagination"]["total_pages"] == 0
