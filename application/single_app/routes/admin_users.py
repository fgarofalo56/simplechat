# admin_users.py
# User management admin endpoints.
# Extracted from route_backend_control_center.py - Phase 4 God File Decomposition.

from config import *
from functions_authentication import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from functions_approvals import *
from services.admin_metrics_service import enhance_user_with_activity
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print


def register_admin_user_routes(app):
    # User Management APIs
    @app.route('/api/admin/control-center/users', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_all_users():
        """
        Get all users with their settings, activity data, and access status.
        Supports pagination and filtering.
        """
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 per page
            search = request.args.get('search', '').strip()
            access_filter = request.args.get('access_filter', 'all')  # all, allow, deny
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            export_all = request.args.get('all', 'false').lower() == 'true'  # For CSV export
            
            # Build query with filters
            query_conditions = []
            parameters = []
            
            if search:
                query_conditions.append("(CONTAINS(LOWER(c.email), @search) OR CONTAINS(LOWER(c.display_name), @search))")
                parameters.append({"name": "@search", "value": search.lower()})
            
            if access_filter != 'all':
                query_conditions.append("c.settings.access.status = @access_status")
                parameters.append({"name": "@access_status", "value": access_filter})
            
            if export_all:
                # For CSV export, get all users without pagination
                if query_conditions:
                    users_query = f"""
                        SELECT c.id, c.email, c.display_name, c.lastUpdated, c.settings
                        FROM c
                        WHERE {" AND ".join(query_conditions)}
                        ORDER BY c.display_name
                    """
                else:
                    users_query = """
                        SELECT c.id, c.email, c.display_name, c.lastUpdated, c.settings
                        FROM c
                        ORDER BY c.display_name
                    """
                
                users = list(cosmos_user_settings_container.query_items(
                    query=users_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                # Enhance user data with activity information
                enhanced_users = []
                for user in users:
                    enhanced_user = enhance_user_with_activity(user, force_refresh=force_refresh)
                    enhanced_users.append(enhanced_user)
                
                return jsonify({
                    'success': True,
                    'users': enhanced_users,
                    'total_count': len(enhanced_users)
                }), 200

            # Get total count for pagination
            if query_conditions:
                count_query = "SELECT VALUE COUNT(1) FROM c WHERE " + " AND ".join(query_conditions)
            else:
                count_query = "SELECT VALUE COUNT(1) FROM c"
            total_items_result = list(cosmos_user_settings_container.query_items(
                query=count_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            total_items = total_items_result[0] if total_items_result and isinstance(total_items_result[0], int) else 0

            # Calculate pagination - validate pagination parameters to prevent injection
            try:
                offset = max(0, (int(page) - 1) * int(per_page))
                safe_per_page = min(int(per_page), 1000)  # Cap at reasonable limit
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid pagination parameters'}), 400
            total_pages = (total_items + safe_per_page - 1) // safe_per_page

            # Get paginated results
            if query_conditions:
                users_query = f"""
                    SELECT c.id, c.email, c.display_name, c.lastUpdated, c.settings
                    FROM c
                    WHERE {" AND ".join(query_conditions)}
                    ORDER BY c.display_name
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            else:
                users_query = f"""
                    SELECT c.id, c.email, c.display_name, c.lastUpdated, c.settings
                    FROM c
                    ORDER BY c.display_name
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            
            users = list(cosmos_user_settings_container.query_items(
                query=users_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Enhance user data with activity information
            enhanced_users = []
            for user in users:
                enhanced_user = enhance_user_with_activity(user, force_refresh=force_refresh)
                enhanced_users.append(enhanced_user)
            
            return jsonify({
                'users': enhanced_users,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_items': total_items,
                    'total_pages': total_pages,
                    'has_prev': page > 1,
                    'has_next': page < total_pages
                }
            }), 200
            
        except Exception as e:
            debug_print(f"Error getting users: {e}")
            return jsonify({'error': 'Failed to retrieve users'}), 500
    
    @app.route('/api/admin/control-center/users/<user_id>/access', methods=['PATCH'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_update_user_access(user_id):
        """
        Update user access permissions (allow/deny with optional time-based restriction).
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            status = data.get('status')
            datetime_to_allow = data.get('datetime_to_allow')
            
            if status not in ['allow', 'deny']:
                return jsonify({'error': 'Status must be "allow" or "deny"'}), 400
            
            # Validate datetime_to_allow if provided
            if datetime_to_allow:
                try:
                    # Validate ISO 8601 format
                    datetime.fromisoformat(datetime_to_allow.replace('Z', '+00:00') if 'Z' in datetime_to_allow else datetime_to_allow)
                except ValueError:
                    return jsonify({'error': 'Invalid datetime format. Use ISO 8601 format'}), 400
            
            # Update user access settings
            access_settings = {
                'access': {
                    'status': status,
                    'datetime_to_allow': datetime_to_allow
                }
            }
            
            success = update_user_settings(user_id, access_settings)
            
            if success:
                # Log admin action
                admin_user = session.get('user', {})
                log_event("[ControlCenter] User Access Updated", {
                    "admin_user": admin_user.get('preferred_username', 'unknown'),
                    "target_user_id": user_id,
                    "access_status": status,
                    "datetime_to_allow": datetime_to_allow
                })
                
                return jsonify({'message': 'User access updated successfully'}), 200
            else:
                return jsonify({'error': 'Failed to update user access'}), 500
            
        except Exception as e:
            debug_print(f"Error updating user access: {e}")
            return jsonify({'error': 'Failed to update user access'}), 500
    
    @app.route('/api/admin/control-center/users/<user_id>/file-uploads', methods=['PATCH'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_update_user_file_uploads(user_id):
        """
        Update user file upload permissions (allow/deny with optional time-based restriction).
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            status = data.get('status')
            datetime_to_allow = data.get('datetime_to_allow')
            
            if status not in ['allow', 'deny']:
                return jsonify({'error': 'Status must be "allow" or "deny"'}), 400
            
            # Validate datetime_to_allow if provided
            if datetime_to_allow:
                try:
                    # Validate ISO 8601 format
                    datetime.fromisoformat(datetime_to_allow.replace('Z', '+00:00') if 'Z' in datetime_to_allow else datetime_to_allow)
                except ValueError:
                    return jsonify({'error': 'Invalid datetime format. Use ISO 8601 format'}), 400
            
            # Update user file upload settings
            file_upload_settings = {
                'file_uploads': {
                    'status': status,
                    'datetime_to_allow': datetime_to_allow
                }
            }
            
            success = update_user_settings(user_id, file_upload_settings)
            
            if success:
                # Log admin action
                admin_user = session.get('user', {})
                log_event("[ControlCenter] User File Upload Updated", {
                    "admin_user": admin_user.get('preferred_username', 'unknown'),
                    "target_user_id": user_id,
                    "file_upload_status": status,
                    "datetime_to_allow": datetime_to_allow
                })
                
                return jsonify({'message': 'User file upload permissions updated successfully'}), 200
            else:
                return jsonify({'error': 'Failed to update user file upload permissions'}), 500
            
        except Exception as e:
            debug_print(f"Error updating user file uploads: {e}")
            return jsonify({'error': 'Failed to update user file upload permissions'}), 500
    
    @app.route('/api/admin/control-center/users/<user_id>/delete-documents', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_delete_user_documents_admin(user_id):
        """
        Create an approval request to delete all documents for a user.
        Requires approval from another admin.
        
        Body:
            reason (str): Explanation for deleting documents (required)
        """
        try:
            data = request.get_json() or {}
            reason = data.get('reason', '').strip()
            
            if not reason:
                return jsonify({'error': 'Reason is required for document deletion'}), 400
            
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid') or admin_user.get('sub')
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            admin_display_name = admin_user.get('name', admin_email)
            
            # Validate user exists by trying to get their data from Cosmos
            try:
                user_doc = cosmos_user_settings_container.read_item(
                    item=user_id,
                    partition_key=user_id
                )
                user_email = user_doc.get('email', 'unknown')
                user_name = user_doc.get('display_name', user_email)
            except Exception:
                return jsonify({'error': 'User not found'}), 404
            
            # Create approval request using user_id as both group_id (for partition) and storing user_id in metadata
            from functions_approvals import create_approval_request, TYPE_DELETE_USER_DOCUMENTS
            approval = create_approval_request(
                request_type=TYPE_DELETE_USER_DOCUMENTS,
                group_id=user_id,  # Using user_id as partition key for user-related approvals
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'user_id': user_id,
                    'user_name': user_name,
                    'user_email': user_email
                }
            )
            
            # Log event
            log_event("[ControlCenter] Delete User Documents Request Created", {
                "admin_user": admin_email,
                "user_id": user_id,
                "user_email": user_email,
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Document deletion request created successfully. Awaiting approval from another admin.',
                'approval_id': approval['id']
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating user document deletion request: {e}")
            log_event("[ControlCenter] Delete User Documents Request Failed", {
                "error": str(e),
                "user_id": user_id
            })
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/control-center/users/bulk-action', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_bulk_user_action():
        """
        Perform bulk actions on multiple users (access control, file upload control).
        """
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            user_ids = data.get('user_ids', [])
            action_type = data.get('action_type')  # 'access' or 'file_uploads'
            settings = data.get('settings', {})
            
            if not user_ids or not action_type or not settings:
                return jsonify({'error': 'Missing required fields: user_ids, action_type, settings'}), 400
            
            if action_type not in ['access', 'file_uploads']:
                return jsonify({'error': 'action_type must be "access" or "file_uploads"'}), 400
            
            status = settings.get('status')
            datetime_to_allow = settings.get('datetime_to_allow')
            
            if status not in ['allow', 'deny']:
                return jsonify({'error': 'Status must be "allow" or "deny"'}), 400
            
            # Validate datetime_to_allow if provided
            if datetime_to_allow:
                try:
                    datetime.fromisoformat(datetime_to_allow.replace('Z', '+00:00') if 'Z' in datetime_to_allow else datetime_to_allow)
                except ValueError:
                    return jsonify({'error': 'Invalid datetime format. Use ISO 8601 format'}), 400
            
            # Apply bulk action
            success_count = 0
            failed_users = []
            
            update_settings = {
                action_type: {
                    'status': status,
                    'datetime_to_allow': datetime_to_allow
                }
            }
            
            for user_id in user_ids:
                try:
                    success = update_user_settings(user_id, update_settings)
                    if success:
                        success_count += 1
                    else:
                        failed_users.append(user_id)
                except Exception as e:
                    debug_print(f"Error updating user {user_id}: {e}")
                    failed_users.append(user_id)
            
            # Log admin action
            admin_user = session.get('user', {})
            log_event("[ControlCenter] Bulk User Action", {
                "admin_user": admin_user.get('preferred_username', 'unknown'),
                "action_type": action_type,
                "user_count": len(user_ids),
                "success_count": success_count,
                "failed_count": len(failed_users),
                "settings": settings
            })
            
            result = {
                'message': f'Bulk action completed. {success_count} users updated successfully.',
                'success_count': success_count,
                'failed_count': len(failed_users)
            }
            
            if failed_users:
                result['failed_users'] = failed_users
            
            return jsonify(result), 200
            
        except Exception as e:
            debug_print(f"Error performing bulk user action: {e}")
            return jsonify({'error': 'Failed to perform bulk action'}), 500

