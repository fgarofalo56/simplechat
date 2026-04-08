# route_backend_control_center.py
# Backward-compatible facade — delegates to focused route modules under routes/.
#
# This file was decomposed into 5 route modules and 1 service module:
#   - routes/admin_users.py       — User management endpoints
#   - routes/admin_groups.py      — Group management endpoints
#   - routes/admin_workspaces.py  — Public workspace management endpoints
#   - routes/admin_activity.py    — Activity trends, refresh, migration, logs
#   - routes/admin_approvals.py   — Approval workflow endpoints (admin + non-admin)
#   - services/admin_metrics_service.py — enhance_* helpers, activity aggregation
#
# All existing imports like `from route_backend_control_center import *` continue to work.

# Original imports — kept for backward compatibility with callers.
from config import *
from functions_authentication import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from functions_approvals import *
from functions_documents import update_document, delete_document, delete_document_chunks
from functions_group import delete_group
from utils_cache import invalidate_group_search_cache
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print

# Re-export helpers from service module for backward compatibility.
from services.admin_metrics_service import (
    enhance_user_with_activity,
    enhance_public_workspace_with_activity,
    enhance_group_with_activity,
    get_activity_trends_data,
    get_raw_activity_trends_data,
)

# Import route registration functions from sub-modules.
from routes.admin_users import register_admin_user_routes
from routes.admin_groups import register_admin_group_routes
from routes.admin_workspaces import register_admin_workspace_routes
from routes.admin_activity import register_admin_activity_routes
from routes.admin_approvals import register_admin_approval_routes


def register_route_backend_control_center(app):
    """Register all control center routes by delegating to focused sub-modules."""
    register_admin_user_routes(app)
    register_admin_group_routes(app)
    register_admin_workspace_routes(app)
    register_admin_activity_routes(app)
    register_admin_approval_routes(app)
