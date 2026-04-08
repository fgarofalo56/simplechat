# admin_groups.py
# Group management admin endpoints.
# Extracted from route_backend_control_center.py - Phase 4 God File Decomposition.

from config import *
from functions_authentication import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from functions_approvals import *
from functions_documents import update_document, delete_document, delete_document_chunks
from functions_group import delete_group
from utils_cache import invalidate_group_search_cache
from services.admin_metrics_service import enhance_group_with_activity
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print


def register_admin_group_routes(app):
    # Group Management APIs
    @app.route('/api/admin/control-center/groups', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_all_groups():
        """
        Get all groups with their activity data and metrics.
        Supports pagination and filtering.
        """
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 per page
            search = request.args.get('search', '').strip()
            status_filter = request.args.get('status_filter', 'all')  # all, active, locked, etc.
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            export_all = request.args.get('all', 'false').lower() == 'true'  # For CSV export
            
            # Build query with filters
            query_conditions = []
            parameters = []
            
            if search:
                query_conditions.append("(CONTAINS(LOWER(c.name), @search) OR CONTAINS(LOWER(c.description), @search))")
                parameters.append({"name": "@search", "value": search.lower()})
            
            # Note: status filtering would need to be implemented based on business logic
            # For now, we'll get all groups and filter client-side if needed
            
            if export_all:
                # For CSV export, get all groups without pagination
                if query_conditions:
                    groups_query = f"""
                        SELECT *
                        FROM c
                        WHERE {" AND ".join(query_conditions)}
                        ORDER BY c.name
                    """
                else:
                    groups_query = """
                        SELECT *
                        FROM c
                        ORDER BY c.name
                    """
                
                groups = list(cosmos_groups_container.query_items(
                    query=groups_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                # Enhance group data with activity information
                enhanced_groups = []
                for group in groups:
                    enhanced_group = enhance_group_with_activity(group, force_refresh=force_refresh)
                    enhanced_groups.append(enhanced_group)
                
                return jsonify({
                    'success': True,
                    'groups': enhanced_groups,
                    'total_count': len(enhanced_groups)
                }), 200

            # Get total count for pagination
            if query_conditions:
                count_query = "SELECT VALUE COUNT(1) FROM c WHERE " + " AND ".join(query_conditions)
            else:
                count_query = "SELECT VALUE COUNT(1) FROM c"
            total_items_result = list(cosmos_groups_container.query_items(
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
                groups_query = f"""
                    SELECT *
                    FROM c
                    WHERE {" AND ".join(query_conditions)}
                    ORDER BY c.name
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            else:
                groups_query = f"""
                    SELECT *
                    FROM c
                    ORDER BY c.name
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            
            groups = list(cosmos_groups_container.query_items(
                query=groups_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Enhance group data with activity information
            enhanced_groups = []
            for group in groups:
                enhanced_group = enhance_group_with_activity(group, force_refresh=force_refresh)
                enhanced_groups.append(enhanced_group)
            
            return jsonify({
                'groups': enhanced_groups,
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
            debug_print(f"Error getting groups: {e}")
            return jsonify({'error': 'Failed to retrieve groups'}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/status', methods=['PUT'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_update_group_status(group_id):
        """
        Update group status (active, locked, upload_disabled, inactive)
        Tracks who made the change and when, logs to activity_logs
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            new_status = data.get('status')
            reason = data.get('reason')  # Optional reason for the status change
            
            if not new_status:
                return jsonify({'error': 'Status is required'}), 400
            
            # Validate status values
            valid_statuses = ['active', 'locked', 'upload_disabled', 'inactive']
            if new_status not in valid_statuses:
                return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
                
            # Get the group
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Get admin user info
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid', 'unknown')
            admin_email = admin_user.get('preferred_username', 'unknown')
            
            # Get old status for logging
            old_status = group.get('status', 'active')  # Default to 'active' if not set
            
            # Only update and log if status actually changed
            if old_status != new_status:
                # Update group status
                group['status'] = new_status
                group['modifiedDate'] = datetime.utcnow().isoformat()
                
                # Add status change metadata
                if 'statusHistory' not in group:
                    group['statusHistory'] = []
                
                group['statusHistory'].append({
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by_user_id': admin_user_id,
                    'changed_by_email': admin_email,
                    'changed_at': datetime.utcnow().isoformat(),
                    'reason': reason
                })
                
                # Update in database
                cosmos_groups_container.upsert_item(group)
                
                # Log to activity_logs container for audit trail
                from functions_activity_logging import log_group_status_change
                log_group_status_change(
                    group_id=group_id,
                    group_name=group.get('name', 'Unknown'),
                    old_status=old_status,
                    new_status=new_status,
                    changed_by_user_id=admin_user_id,
                    changed_by_email=admin_email,
                    reason=reason
                )
                
                # Log admin action (legacy logging)
                log_event("[ControlCenter] Group Status Update", {
                    "admin_user": admin_email,
                    "admin_user_id": admin_user_id,
                    "group_id": group_id,
                    "group_name": group.get('name'),
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason
                })
                
                return jsonify({
                    'message': 'Group status updated successfully',
                    'old_status': old_status,
                    'new_status': new_status
                }), 200
            else:
                return jsonify({
                    'message': 'Group status unchanged',
                    'status': new_status
                }), 200
            
        except Exception as e:
            debug_print(f"Error updating group status: {e}")
            return jsonify({'error': 'Failed to update group status'}), 500

    @app.route('/api/admin/control-center/groups/<group_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_group_details_admin(group_id):
        """
        Get detailed information about a specific group
        """
        try:
            # Get the group
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Enhance with activity data
            enhanced_group = enhance_group_with_activity(group)
            
            return jsonify(enhanced_group), 200
            
        except Exception as e:
            debug_print(f"Error getting group details: {e}")
            return jsonify({'error': 'Failed to retrieve group details'}), 500

    @app.route('/api/admin/control-center/groups/<group_id>', methods=['DELETE'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_delete_group_admin(group_id):
        """
        Create an approval request to delete a group and all its documents.
        Requires approval from group owner or another admin.
        
        Body:
            reason (str): Explanation for deleting the group (required)
        """
        try:
            data = request.get_json() or {}
            reason = data.get('reason', '').strip()
            
            if not reason:
                return jsonify({'error': 'Reason is required for group deletion'}), 400
            
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid') or admin_user.get('sub')
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            admin_display_name = admin_user.get('name', admin_email)
            
            # Validate group exists
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_DELETE_GROUP,
                group_id=group_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'group_name': group.get('name'),
                    'owner_id': group.get('owner', {}).get('id'),
                    'owner_email': group.get('owner', {}).get('email')
                }
            )
            
            # Log event
            log_event("[ControlCenter] Delete Group Request Created", {
                "admin_user": admin_email,
                "group_id": group_id,
                "group_name": group.get('name'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Group deletion request created and pending approval',
                'approval_id': approval['id'],
                'status': 'pending'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating group deletion request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/delete-documents', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_delete_group_documents_admin(group_id):
        """
        Create an approval request to delete all documents in a group.
        Requires approval from group owner or another admin.
        
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
            
            # Validate group exists
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_DELETE_DOCUMENTS,
                group_id=group_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'group_name': group.get('name')
                }
            )
            
            # Log event
            log_event("[ControlCenter] Delete Documents Request Created", {
                "admin_user": admin_email,
                "group_id": group_id,
                "group_name": group.get('name'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Document deletion request created and pending approval',
                'approval_id': approval['id'],
                'status': 'pending'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating document deletion request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/members', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_group_members_admin(group_id):
        """
        Get list of group members for ownership transfer selection
        """
        try:
            # Get the group
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Get member list with user details
            members = []
            for member in group.get('users', []):
                # Skip the current owner from the list
                if member.get('userId') == group.get('owner', {}).get('id'):
                    continue
                    
                members.append({
                    'userId': member.get('userId'),
                    'email': member.get('email', 'No email'),
                    'displayName': member.get('displayName', 'Unknown User')
                })
            
            return jsonify({'members': members}), 200
            
        except Exception as e:
            debug_print(f"Error getting group members: {e}")
            return jsonify({'error': 'Failed to retrieve group members'}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/take-ownership', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_take_group_ownership(group_id):
        """
        Create an approval request for admin to take ownership of a group.
        Requires approval from group owner or another admin.
        
        Body:
            reason (str): Explanation for taking ownership (required)
        """
        try:
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid') or admin_user.get('sub')
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            admin_display_name = admin_user.get('name', admin_email)
            
            if not admin_user_id:
                return jsonify({'error': 'Could not identify admin user'}), 400
            
            # Get request body
            data = request.get_json() or {}
            reason = data.get('reason', '').strip()
            
            if not reason:
                return jsonify({'error': 'Reason is required for ownership transfer'}), 400
            
            # Validate group exists
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_TAKE_OWNERSHIP,
                group_id=group_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'old_owner_id': group.get('owner', {}).get('id'),
                    'old_owner_email': group.get('owner', {}).get('email')
                }
            )
            
            # Log event
            log_event("[ControlCenter] Take Ownership Request Created", {
                "admin_user": admin_email,
                "group_id": group_id,
                "group_name": group.get('name'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Ownership transfer request created and pending approval',
                'approval_id': approval['id'],
                'status': 'pending'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating take ownership request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/transfer-ownership', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_transfer_group_ownership(group_id):
        """
        Create an approval request to transfer group ownership to another member.
        Requires approval from group owner or another admin.
        
        Body:
            newOwnerId (str): User ID of the new owner (required)
            reason (str): Explanation for ownership transfer (required)
        """
        try:
            data = request.get_json()
            new_owner_user_id = data.get('newOwnerId')
            reason = data.get('reason', '').strip()
            
            if not new_owner_user_id:
                return jsonify({'error': 'Missing newOwnerId'}), 400
            
            if not reason:
                return jsonify({'error': 'Reason is required for ownership transfer'}), 400
            
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid') or admin_user.get('sub')
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            admin_display_name = admin_user.get('name', admin_email)
            
            # Get the group
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Find the new owner in members list
            new_owner_member = None
            for member in group.get('users', []):
                if member.get('userId') == new_owner_user_id:
                    new_owner_member = member
                    break
            
            if not new_owner_member:
                return jsonify({'error': 'Selected user is not a member of this group'}), 400
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_TRANSFER_OWNERSHIP,
                group_id=group_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'new_owner_id': new_owner_user_id,
                    'new_owner_email': new_owner_member.get('email'),
                    'new_owner_name': new_owner_member.get('displayName'),
                    'old_owner_id': group.get('owner', {}).get('id'),
                    'old_owner_email': group.get('owner', {}).get('email')
                }
            )
            
            # Log event
            log_event("[ControlCenter] Transfer Ownership Request Created", {
                "admin_user": admin_email,
                "group_id": group_id,
                "group_name": group.get('name'),
                "new_owner": new_owner_member.get('email'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Ownership transfer request created and pending approval',
                'approval_id': approval['id'],
                'status': 'pending'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating transfer ownership request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/add-member', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_add_group_member(group_id):
        """
        Admin adds a member to a group (used by both single add and CSV bulk upload)
        """
        try:
            data = request.get_json()
            user_id = data.get('userId')
            # Support both 'name' (from CSV) and 'displayName' (from single add form)
            name = data.get('displayName') or data.get('name')
            email = data.get('email')
            role = data.get('role', 'user').lower()
            
            if not user_id or not name or not email:
                return jsonify({'error': 'Missing required fields: userId, name/displayName, email'}), 400
            
            # Validate role
            valid_roles = ['admin', 'document_manager', 'user']
            if role not in valid_roles:
                return jsonify({'error': f'Invalid role. Must be: {", ".join(valid_roles)}'}), 400
            
            admin_user = session.get('user', {})
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            
            # Get the group
            try:
                group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            except:
                return jsonify({'error': 'Group not found'}), 404
            
            # Check if user already exists (skip duplicate)
            existing_user = False
            for member in group.get('users', []):
                if member.get('userId') == user_id:
                    existing_user = True
                    break
            
            if existing_user:
                return jsonify({
                    'message': f'User {email} already exists in group',
                    'skipped': True
                }), 200
            
            # Add user to users array
            group.setdefault('users', []).append({
                'userId': user_id,
                'email': email,
                'displayName': name
            })
            
            # Add to appropriate role array
            if role == 'admin':
                if user_id not in group.get('admins', []):
                    group.setdefault('admins', []).append(user_id)
            elif role == 'document_manager':
                if user_id not in group.get('documentManagers', []):
                    group.setdefault('documentManagers', []).append(user_id)
            
            # Update modification timestamp
            group['modifiedDate'] = datetime.utcnow().isoformat()
            
            # Save group
            cosmos_groups_container.upsert_item(group)
            
            # Determine the action source (single add vs bulk CSV)
            source = data.get('source', 'csv')  # Default to 'csv' for backward compatibility
            action_type = 'add_member_directly' if source == 'single' else 'admin_add_member_csv'
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'activity_type': action_type,
                'timestamp': datetime.utcnow().isoformat(),
                'admin_user_id': admin_user.get('oid') or admin_user.get('sub'),
                'admin_email': admin_email,
                'group_id': group_id,
                'group_name': group.get('name', 'Unknown'),
                'member_user_id': user_id,
                'member_email': email,
                'member_name': name,
                'member_role': role,
                'source': source,
                'description': f"Admin {admin_email} added member {name} ({email}) to group {group.get('name', group_id)} as {role}"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            # Log to Application Insights
            log_event("[ControlCenter] Admin Add Group Member", {
                "admin_user": admin_email,
                "group_id": group_id,
                "group_name": group.get('name'),
                "member_email": email,
                "member_role": role
            })
            
            return jsonify({
                'message': f'Member {email} added successfully',
                'skipped': False
            }), 200
            
        except Exception as e:
            debug_print(f"Error adding group member: {e}")
            return jsonify({'error': 'Failed to add member'}), 500

    @app.route('/api/admin/control-center/groups/<group_id>/activity', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_get_group_activity(group_id):
        """
        Get activity timeline for a specific group from activity logs
        Returns document creation/deletion, member changes, status changes, and conversations
        """
        try:
            # Get time range filter (default: last 30 days)
            days = request.args.get('days', '30')
            
            # Calculate date filter
            cutoff_date = None
            if days != 'all':
                try:
                    days_int = int(days)
                    cutoff_date = (datetime.utcnow() - timedelta(days=days_int)).isoformat()
                except ValueError:
                    pass
            
            # Build queries - use two separate queries to avoid nested property access issues
            # Query 1: Activities with c.group.group_id (member/status changes)
            # Query 2: Activities with c.workspace_context.group_id (document operations)
            
            # Query 1: Member and status activities (all activity types with c.group.group_id)
            # Use SELECT * to get complete raw documents for modal display
            if cutoff_date:
                query1 = """
                    SELECT *
                    FROM c
                    WHERE c.group.group_id = @group_id
                    AND c.timestamp >= @cutoff_date
                """
            else:
                query1 = """
                    SELECT *
                    FROM c
                    WHERE c.group.group_id = @group_id
                """

            # Query 2: Document activities (all activity types with c.workspace_context.group_id)
            # Use SELECT * to get complete raw documents for modal display
            if cutoff_date:
                query2 = """
                    SELECT *
                    FROM c
                    WHERE c.workspace_context.group_id = @group_id
                    AND c.timestamp >= @cutoff_date
                """
            else:
                query2 = """
                    SELECT *
                    FROM c
                    WHERE c.workspace_context.group_id = @group_id
                """
            
            # Log the queries for debugging
            debug_print(f"[Group Activity] Querying for group: {group_id}, days: {days}")
            debug_print(f"[Group Activity] Query 1: {query1}")
            debug_print(f"[Group Activity] Query 2: {query2}")
            
            parameters = [
                {"name": "@group_id", "value": group_id}
            ]
            
            if cutoff_date:
                parameters.append({"name": "@cutoff_date", "value": cutoff_date})
            
            debug_print(f"[Group Activity] Parameters: {parameters}")
            
            # Execute both queries
            activities = []
            
            try:
                # Query 1: Member and status activities
                activities1 = list(cosmos_activity_logs_container.query_items(
                    query=query1,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                debug_print(f"[Group Activity] Query 1 returned {len(activities1)} activities")
                activities.extend(activities1)
            except Exception as e:
                debug_print(f"[Group Activity] Query 1 failed: {e}")
            
            try:
                # Query 2: Document activities
                activities2 = list(cosmos_activity_logs_container.query_items(
                    query=query2,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                debug_print(f"[Group Activity] Query 2 returned {len(activities2)} activities")
                activities.extend(activities2)
            except Exception as e:
                debug_print(f"[Group Activity] Query 2 failed: {e}")
            
            # Sort combined results by timestamp descending
            activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            # Format activities for timeline display
            formatted_activities = []
            for activity in activities:
                formatted = {
                    'id': activity.get('id'),
                    'type': activity.get('activity_type'),
                    'timestamp': activity.get('timestamp'),
                    'user_id': activity.get('user_id'),
                    'description': activity.get('description', '')
                }
                
                # Add type-specific details
                activity_type = activity.get('activity_type')
                
                if activity_type == 'document_creation':
                    doc = activity.get('document', {})
                    formatted['document'] = {
                        'file_name': doc.get('file_name'),
                        'file_type': doc.get('file_type'),
                        'file_size_bytes': doc.get('file_size_bytes'),
                        'page_count': doc.get('page_count')
                    }
                    formatted['icon'] = 'file-earmark-plus'
                    formatted['color'] = 'success'
                
                elif activity_type == 'document_deletion':
                    doc = activity.get('document', {})
                    formatted['document'] = {
                        'file_name': doc.get('file_name'),
                        'file_type': doc.get('file_type')
                    }
                    formatted['icon'] = 'file-earmark-minus'
                    formatted['color'] = 'danger'
                
                elif activity_type == 'document_metadata_update':
                    doc = activity.get('document', {})
                    formatted['document'] = {
                        'file_name': doc.get('file_name')
                    }
                    formatted['icon'] = 'pencil-square'
                    formatted['color'] = 'info'
                
                elif activity_type == 'group_member_added':
                    added_by = activity.get('added_by', {})
                    added_member = activity.get('added_member', {})
                    formatted['member'] = {
                        'name': added_member.get('name'),
                        'email': added_member.get('email'),
                        'role': added_member.get('role')
                    }
                    formatted['added_by'] = {
                        'email': added_by.get('email'),
                        'role': added_by.get('role')
                    }
                    formatted['icon'] = 'person-plus'
                    formatted['color'] = 'primary'
                
                elif activity_type == 'group_member_deleted':
                    removed_by = activity.get('removed_by', {})
                    removed_member = activity.get('removed_member', {})
                    formatted['member'] = {
                        'name': removed_member.get('name'),
                        'email': removed_member.get('email')
                    }
                    formatted['removed_by'] = {
                        'email': removed_by.get('email'),
                        'role': removed_by.get('role')
                    }
                    formatted['icon'] = 'person-dash'
                    formatted['color'] = 'warning'
                
                elif activity_type == 'group_status_change':
                    status_change = activity.get('status_change', {})
                    formatted['status_change'] = {
                        'from_status': status_change.get('old_status'),  # Use old_status from log
                        'to_status': status_change.get('new_status')    # Use new_status from log
                    }
                    formatted['icon'] = 'shield-lock'
                    formatted['color'] = 'secondary'
                
                elif activity_type == 'conversation_creation':
                    formatted['icon'] = 'chat-dots'
                    formatted['color'] = 'info'
                
                elif activity_type == 'token_usage':
                    usage = activity.get('usage', {})
                    formatted['token_usage'] = {
                        'total_tokens': usage.get('total_tokens'),
                        'prompt_tokens': usage.get('prompt_tokens'),
                        'completion_tokens': usage.get('completion_tokens'),
                        'model': usage.get('model'),
                        'token_type': activity.get('token_type')  # 'chat' or 'embedding'
                    }
                    # Add chat details if available
                    chat_details = activity.get('chat_details', {})
                    if chat_details:
                        formatted['token_usage']['conversation_id'] = chat_details.get('conversation_id')
                        formatted['token_usage']['message_id'] = chat_details.get('message_id')
                    # Add embedding details if available
                    embedding_details = activity.get('embedding_details', {})
                    if embedding_details:
                        formatted['token_usage']['document_id'] = embedding_details.get('document_id')
                        formatted['token_usage']['file_name'] = embedding_details.get('file_name')
                    formatted['icon'] = 'cpu'
                    formatted['color'] = 'info'
                
                else:
                    # Fallback for unknown activity types - still show them!
                    formatted['icon'] = 'circle'
                    formatted['color'] = 'secondary'
                    # Keep any additional data that might be in the activity
                    if activity.get('status_change'):
                        formatted['status_change'] = activity.get('status_change')
                    if activity.get('document'):
                        formatted['document'] = activity.get('document')
                    if activity.get('group'):
                        formatted['group'] = activity.get('group')
                
                formatted_activities.append(formatted)
            
            return jsonify({
                'group_id': group_id,
                'activities': formatted_activities,
                'raw_activities': activities,  # Include raw activities for modal display
                'count': len(formatted_activities),
                'time_range_days': days
            }), 200
            
        except Exception as e:
            debug_print(f"Error fetching group activity: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to fetch group activity: {str(e)}'}), 500

