# route_backend_mcp_catalog.py
"""Backend routes for MCP Catalog management.

Provides browse/search/install endpoints for users and CRUD endpoints
for admins to manage the MCP server catalog.
"""

from flask import Blueprint, jsonify, request, session
from swagger_wrapper import swagger_route, get_auth_security

from functions_authentication import (
    admin_required,
    login_required,
    get_current_user_info,
)
from functions_mcp_catalog import (
    get_catalog_entries,
    get_catalog_entry,
    get_catalog_categories,
    save_catalog_entry,
    delete_catalog_entry,
    install_catalog_entry,
    seed_default_catalog,
)
from functions_settings import get_settings
from functions_debug import debug_print

bp_mcp_catalog = Blueprint('mcp_catalog', __name__)


def _catalog_enabled():
    settings = get_settings()
    return settings.get('enable_mcp_catalog', False)


# ---------------------------------------------------------------------------
# User-facing endpoints
# ---------------------------------------------------------------------------

@bp_mcp_catalog.route('/api/mcp-catalog', methods=['GET'])
@swagger_route(security=get_auth_security())
@login_required
def list_catalog():
    """List all active MCP catalog entries with optional filtering."""
    if not _catalog_enabled():
        return jsonify({'entries': [], 'categories': []})

    category = request.args.get('category')
    search = request.args.get('search')

    entries = get_catalog_entries(category=category, search=search, active_only=True)
    categories = get_catalog_categories()

    return jsonify({
        'entries': entries,
        'categories': categories
    })


@bp_mcp_catalog.route('/api/mcp-catalog/<entry_id>', methods=['GET'])
@swagger_route(security=get_auth_security())
@login_required
def get_catalog_detail(entry_id):
    """Get a single catalog entry by ID."""
    if not _catalog_enabled():
        return jsonify({'error': 'MCP Catalog is disabled.'}), 403

    entry = get_catalog_entry(entry_id)
    if not entry:
        return jsonify({'error': 'Catalog entry not found.'}), 404

    return jsonify({'entry': entry})


@bp_mcp_catalog.route('/api/mcp-catalog/<entry_id>/install', methods=['POST'])
@swagger_route(security=get_auth_security())
@login_required
def install_from_catalog(entry_id):
    """Install an MCP server from the catalog as an action.

    Request body:
        config_values: dict of user-provided configuration values
        scope: 'personal' | 'group' | 'global' (default: 'personal')
        group_id: required if scope is 'group'
    """
    if not _catalog_enabled():
        return jsonify({'error': 'MCP Catalog is disabled.'}), 403

    settings = get_settings()
    if not settings.get('enable_mcp_servers', False):
        return jsonify({'error': 'MCP Servers are not enabled. Enable them in Admin Settings first.'}), 403

    data = request.get_json(silent=True) or {}
    config_values = data.get('config_values', {})
    scope = data.get('scope', 'personal')
    group_id = data.get('group_id')

    # Validate scope permissions
    user_info = get_current_user_info()
    user_id = user_info.get('oid') if user_info else None

    if scope == 'global':
        user = session.get('user') or {}
        if 'Admin' not in (user.get('roles') or []):
            return jsonify({'error': 'Only admins can install MCP servers globally.'}), 403

    if scope == 'group' and not group_id:
        return jsonify({'error': 'group_id is required for group scope.'}), 400

    # Validate required config fields
    entry = get_catalog_entry(entry_id)
    if not entry:
        return jsonify({'error': 'Catalog entry not found.'}), 404

    for field in entry.get('config_fields', []):
        if field.get('required') and field['name'] not in config_values:
            return jsonify({
                'error': f"Missing required field: {field.get('label', field['name'])}"
            }), 400

    result = install_catalog_entry(
        entry_id=entry_id,
        config_values=config_values,
        scope=scope,
        user_id=user_id,
        group_id=group_id
    )

    if not result:
        return jsonify({'error': 'Failed to install MCP server. Check logs for details.'}), 500

    return jsonify({
        'message': f"MCP server '{entry.get('name', '')}' installed successfully.",
        'action_id': result['action_id'],
        'scope': result['scope']
    }), 201


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@bp_mcp_catalog.route('/api/admin/mcp-catalog', methods=['GET'])
@swagger_route(security=get_auth_security())
@login_required
@admin_required
def admin_list_catalog():
    """List all catalog entries (including inactive) for admin management."""
    category = request.args.get('category')
    search = request.args.get('search')

    entries = get_catalog_entries(category=category, search=search, active_only=False)
    categories = get_catalog_categories()

    return jsonify({
        'entries': entries,
        'categories': categories
    })


@bp_mcp_catalog.route('/api/admin/mcp-catalog', methods=['POST'])
@swagger_route(security=get_auth_security())
@login_required
@admin_required
def admin_create_catalog_entry():
    """Create a new MCP catalog entry."""
    data = request.get_json(silent=True) or {}

    if not data.get('name'):
        return jsonify({'error': 'Catalog entry name is required.'}), 400

    data.setdefault('slug', data['name'].lower().replace(' ', '-'))

    result = save_catalog_entry(data)
    if not result:
        return jsonify({'error': 'Failed to create catalog entry.'}), 500

    return jsonify({'entry': result}), 201


@bp_mcp_catalog.route('/api/admin/mcp-catalog/<entry_id>', methods=['PATCH'])
@swagger_route(security=get_auth_security())
@login_required
@admin_required
def admin_update_catalog_entry(entry_id):
    """Update an existing MCP catalog entry."""
    existing = get_catalog_entry(entry_id)
    if not existing:
        return jsonify({'error': 'Catalog entry not found.'}), 404

    data = request.get_json(silent=True) or {}

    # Merge updates into existing entry
    for key, value in data.items():
        if key not in ('id', '_rid', '_self', '_etag', '_attachments', '_ts'):
            existing[key] = value

    result = save_catalog_entry(existing)
    if not result:
        return jsonify({'error': 'Failed to update catalog entry.'}), 500

    return jsonify({'entry': result})


@bp_mcp_catalog.route('/api/admin/mcp-catalog/<entry_id>', methods=['DELETE'])
@swagger_route(security=get_auth_security())
@login_required
@admin_required
def admin_delete_catalog_entry(entry_id):
    """Delete an MCP catalog entry."""
    deleted = delete_catalog_entry(entry_id)
    if not deleted:
        return jsonify({'error': 'Catalog entry not found or could not be deleted.'}), 404

    return jsonify({'success': True})


@bp_mcp_catalog.route('/api/admin/mcp-catalog/seed', methods=['POST'])
@swagger_route(security=get_auth_security())
@login_required
@admin_required
def admin_seed_catalog():
    """Re-seed the catalog with default MCP server entries.

    Request body:
        force: bool - If true, overwrite existing default entries (default: false)
    """
    data = request.get_json(silent=True) or {}
    force = data.get('force', False)

    count = seed_default_catalog(force=force)
    return jsonify({
        'message': f'Seeded {count} catalog entries.',
        'count': count
    })
