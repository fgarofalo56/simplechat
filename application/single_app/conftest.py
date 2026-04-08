# conftest.py
# Root conftest for SimpleChat test suite.
# Provides Flask app fixture, test client, and common mocks.

import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock

# Ensure the application directory is on the Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


def _mock_missing_module(module_path):
    """Register a MagicMock for a module if it isn't installed.

    This lets tests run in lightweight environments that don't have every
    Azure SDK package installed.  The mock is only inserted when the real
    module is absent, so it never masks a real installation.
    """
    parts = module_path.split(".")
    for i in range(len(parts)):
        partial = ".".join(parts[: i + 1])
        if partial not in sys.modules:
            try:
                __import__(partial)
            except (ImportError, ModuleNotFoundError):
                sys.modules[partial] = MagicMock()


# Modules that may be missing in dev/CI environments but are imported at
# module-level through the config_constants -> config import chain.
_OPTIONAL_AZURE_MODULES = [
    "azure.ai.formrecognizer",
    "azure.mgmt",
    "azure.mgmt.cognitiveservices",
    "azure.mgmt.cognitiveservices.models",
    "azure.ai.documentintelligence",
    "azure.ai.documentintelligence.models",
    "azure.ai.contentsafety",
    "azure.ai.contentsafety.models",
    "azure.storage.blob",
    "azure.search.documents",
    "azure.search.documents.models",
    "azure.search.documents.indexes",
    "azure.search.documents.indexes.models",
    "azure.cosmos",
    "azure.cosmos.exceptions",
    "azure.identity",
    "azure.monitor",
    "azure.monitor.opentelemetry",
    "semantic_kernel",
    "semantic_kernel.contents",
    "semantic_kernel.contents.chat_message_content",
    "ffmpeg_binaries",
    "ffmpeg",
    "fitz",
    "docx",
    "openpyxl",
    "xlrd",
    "pandas",
    "opentelemetry",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.flask",
    "opentelemetry.sdk",
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.resources",
    "pydub",
    "flask_limiter",
    "flask_limiter.util",
]

# flask_limiter needs a structured mock because limiter.exempt is used as a decorator
# and swagger_wrapper reads func.__name__ on the decorated function.
if "flask_limiter" not in sys.modules:
    import types as _types
    _mock_fl = _types.ModuleType("flask_limiter")
    _mock_fl_util = _types.ModuleType("flask_limiter.util")
    _mock_fl_util.get_remote_address = lambda: "127.0.0.1"

    class _FakeLimiter:
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            pass

        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator

        def exempt(self, f):
            return f

        def shared_limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator

        def request_filter(self, f):
            return f

    _mock_fl.Limiter = _FakeLimiter
    _mock_fl.util = _mock_fl_util
    sys.modules["flask_limiter"] = _mock_fl
    sys.modules["flask_limiter.util"] = _mock_fl_util

# flask_wtf needs a more structured mock because CSRFProtect inspects module attributes
if "flask_wtf" not in sys.modules:
    import types
    _mock_flask_wtf = types.ModuleType("flask_wtf")
    _mock_flask_wtf_csrf = types.ModuleType("flask_wtf.csrf")

    class _FakeCSRFProtect:
        def __init__(self, app=None):
            if app is not None:
                self.init_app(app)

        def init_app(self, app):
            # Register csrf_token() as a Jinja2 global so templates can use it
            app.jinja_env.globals["csrf_token"] = lambda: "test-csrf-token"

        def exempt(self, view):
            return view

    _mock_flask_wtf_csrf.CSRFProtect = _FakeCSRFProtect
    _mock_flask_wtf.csrf = _mock_flask_wtf_csrf
    sys.modules["flask_wtf"] = _mock_flask_wtf
    sys.modules["flask_wtf.csrf"] = _mock_flask_wtf_csrf

for _mod in _OPTIONAL_AZURE_MODULES:
    _mock_missing_module(_mod)

# Flask 3.x removed before_first_request; patch it back for compatibility
import flask
if not hasattr(flask.Flask, 'before_first_request'):
    def _before_first_request(self, f):
        """Compatibility shim: register func to run before the first request."""
        self.before_request_funcs.setdefault(None, [])

        def _wrapper():
            if not getattr(self, '_first_request_done', False):
                f()
                self._first_request_done = True

        self.before_request_funcs[None].insert(0, _wrapper)
        return f

    flask.Flask.before_first_request = _before_first_request

# Break the circular import between functions_debug <-> app_settings_cache
# and functions_debug <-> functions_settings by pre-loading stubs.
if "app_settings_cache" not in sys.modules:
    _mock_cache = MagicMock()
    _mock_cache.get_settings_cache.return_value = {"enable_debug_logging": False}
    sys.modules["app_settings_cache"] = _mock_cache

# Pre-load a minimal functions_debug stub to break circular imports.
# The real module will replace this once it finishes loading.
if "functions_debug" not in sys.modules:
    import types
    _debug_stub = types.ModuleType("functions_debug")
    _debug_stub.debug_print = lambda *args, **kwargs: None
    sys.modules["functions_debug"] = _debug_stub

# Mock the CosmosClient to prevent actual database connections at import time.
# The real azure.cosmos module may be installed but we don't want it calling
# out to a real (or missing) endpoint during tests.
_mock_cosmos_client_instance = MagicMock()
_mock_cosmos_db = MagicMock()
_mock_cosmos_container = MagicMock()
_mock_cosmos_container.query_items.return_value = iter([])
_mock_cosmos_container.upsert_item.return_value = {"id": "mock"}
_mock_cosmos_container.read_item.return_value = {"id": "mock"}
_mock_cosmos_db.create_container_if_not_exists.return_value = _mock_cosmos_container
_mock_cosmos_client_instance.create_database_if_not_exists.return_value = _mock_cosmos_db

# Patch CosmosClient before config_database is imported
import importlib
if "azure.cosmos" in sys.modules and hasattr(sys.modules["azure.cosmos"], "CosmosClient"):
    _real_cosmos = sys.modules["azure.cosmos"]
    if isinstance(_real_cosmos, MagicMock):
        # Already mocked — CosmosClient returns our instance
        _real_cosmos.CosmosClient.return_value = _mock_cosmos_client_instance
    else:
        # Real module installed — monkey-patch to avoid network calls
        _original_cosmos_init = _real_cosmos.CosmosClient
        _real_cosmos.CosmosClient = lambda *args, **kwargs: _mock_cosmos_client_instance


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """Set minimal environment variables required for app import.

    These prevent RuntimeError on missing SECRET_KEY and provide
    dummy values for Azure AD config used at module import time.
    """
    defaults = {
        "SECRET_KEY": "test-secret-key-do-not-use-in-production-1234567890abcdef",
        "CLIENT_ID": "00000000-0000-0000-0000-000000000000",
        "TENANT_ID": "00000000-0000-0000-0000-000000000000",
        "MICROSOFT_PROVIDER_AUTHENTICATION_SECRET": "test-secret",
        "LOGIN_REDIRECT_URL": "http://localhost:5000/callback",
        "HOME_REDIRECT_URL": "http://localhost:5000",
        "FLASK_ENV": "testing",
        "TESTING": "true",
        # Cosmos DB - dummy values to prevent import-time crash
        "AZURE_COSMOS_ENDPOINT": "https://localhost:8081",
        "AZURE_COSMOS_KEY": "dGVzdGtleQ==",  # base64 "testkey"
        "AZURE_COSMOS_AUTHENTICATION_TYPE": "key",
    }
    original = {}
    for key, value in defaults.items():
        original[key] = os.environ.get(key)
        if original[key] is None:
            os.environ[key] = value

    yield

    # Restore original values
    for key, orig_value in original.items():
        if orig_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig_value


@pytest.fixture(scope="session")
def app(set_test_env):
    """Create a Flask application instance for testing.

    Uses the real app module but configures it for testing with
    filesystem-based sessions in a temp directory.
    """
    # Import app after env vars are set
    from app import app as flask_app

    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for test convenience
        "SESSION_TYPE": "filesystem",
        "SESSION_FILE_DIR": tempfile.mkdtemp(prefix="simplechat_test_"),
        "SERVER_NAME": "localhost",
    })

    yield flask_app


@pytest.fixture
def client(app):
    """Create a Flask test client for making HTTP requests."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Push an application context for tests that need it."""
    with app.app_context() as ctx:
        yield ctx


@pytest.fixture
def request_context(app):
    """Push a request context for tests that need g, request, etc."""
    with app.test_request_context():
        yield


@pytest.fixture
def mock_cosmos_container(mocker):
    """Mock a Cosmos DB container for database tests.

    Returns a MagicMock that intercepts query_items, upsert_item,
    read_item, and delete_item calls.
    """
    mock_container = mocker.MagicMock()
    mock_container.query_items.return_value = iter([])
    mock_container.upsert_item.return_value = {"id": "test-id"}
    mock_container.read_item.return_value = {"id": "test-id"}
    mock_container.delete_item.return_value = None
    return mock_container


@pytest.fixture
def mock_settings(mocker):
    """Mock get_settings to return a default test configuration."""
    test_settings = {
        "id": "test-settings",
        "app_title": "SimpleChat Test",
        "enable_user_workspace": True,
        "enable_group_workspaces": True,
        "enable_public_workspaces": True,
        "enable_video_indexer": False,
        "enable_audio_transcription": False,
        "enable_semantic_kernel": False,
        "enable_content_safety": False,
        "enable_malware_scanning": False,
        "enable_redis_cache": False,
        "classification_banner_enabled": False,
        "enable_user_agreement": False,
        "openai_endpoint": "https://test.openai.azure.com",
        "openai_api_key": "test-api-key",
        "embedding_model": "text-embedding-ada-002",
        "chat_model": "gpt-4",
        "malware_scan_on_failure": "block",
    }
    mock = mocker.patch("functions_settings.get_settings", return_value=test_settings)
    return mock


@pytest.fixture
def authenticated_session(client):
    """Create a session with a mock authenticated user."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "oid": "test-user-id-12345",
            "name": "Test User",
            "preferred_username": "testuser@example.com",
            "roles": ["User"],
        }
        sess["token_cache"] = {}
    return client


@pytest.fixture
def admin_session(client):
    """Create a session with a mock admin user."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "oid": "admin-user-id-12345",
            "name": "Admin User",
            "preferred_username": "admin@example.com",
            "roles": ["User", "Admin"],
        }
        sess["token_cache"] = {}
    return client
