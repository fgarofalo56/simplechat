# admin_approvals.py
# Approval workflow endpoints (admin + non-admin paths).
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
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print


def register_admin_approval_routes(app):
    # ============================================================================
    # APPROVAL WORKFLOW ENDPOINTS
    # ============================================================================

    @app.route('/api/admin/control-center/approvals', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_get_approvals():
        """
        Get approval requests visible to the current user.
        
        Query Parameters:
            page (int): Page number (default: 1)
            page_size (int): Items per page (default: 20)
            status (str): Filter by status (pending, approved, denied, all)
            action_type (str): Filter by action type
            search (str): Search by group name or reason
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            
            # Get user roles from session
            user_roles = user.get('roles', [])
            
            # Get query parameters
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            status_filter = request.args.get('status', 'all')
            action_type_filter = request.args.get('action_type', 'all')
            search_query = request.args.get('search', '')
            
            # Determine include_completed based on status filter
            include_completed = (status_filter == 'all' or status_filter in ['approved', 'denied'])
            
            # Map action_type to request_type_filter
            request_type_filter = None if action_type_filter == 'all' else action_type_filter
            
            # Fetch approvals
            result = get_pending_approvals(
                user_id=user_id,
                user_roles=user_roles,
                page=page,
                per_page=page_size,
                include_completed=include_completed,
                request_type_filter=request_type_filter
            )
            
            # Add can_approve field to each approval
            approvals_with_permission = []
            for approval in result.get('approvals', []):
                approval_copy = dict(approval)
                # User can approve if they didn't create the request OR if they're the only admin
                approval_copy['can_approve'] = (approval.get('requester_id') != user_id)
                approvals_with_permission.append(approval_copy)
            
            # Rename fields to match frontend expectations
            return jsonify({
                'success': True,
                'approvals': approvals_with_permission,
                'total_count': result.get('total', 0),
                'page': result.get('page', 1),
                'page_size': result.get('per_page', page_size),
                'total_pages': result.get('total_pages', 0)
            }), 200
            
        except Exception as e:
            debug_print(f"Error fetching approvals: {e}")
            import traceback
            debug_print(traceback.format_exc())
            return jsonify({'error': 'Failed to fetch approvals', 'details': str(e)}), 500

    @app.route('/api/admin/control-center/approvals/<approval_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_get_approval_by_id(approval_id):
        """
        Get a single approval request by ID.
        
        Query Parameters:
            group_id (str): Group ID (partition key)
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            
            group_id = request.args.get('group_id')
            if not group_id:
                return jsonify({'error': 'group_id query parameter is required'}), 400
            
            # Get the approval
            approval = cosmos_approvals_container.read_item(
                item=approval_id,
                partition_key=group_id
            )
            
            # Add can_approve field
            approval['can_approve'] = (approval.get('requester_id') != user_id)
            
            return jsonify(approval), 200
            
        except Exception as e:
            debug_print(f"Error fetching approval {approval_id}: {e}")
            import traceback
            debug_print(traceback.format_exc())
            return jsonify({'error': 'Failed to fetch approval', 'details': str(e)}), 500

    @app.route('/api/admin/control-center/approvals/<approval_id>/approve', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_approve_request(approval_id):
        """
        Approve an approval request and execute the action.
        
        Body:
            group_id (str): Group ID (partition key)
            comment (str, optional): Approval comment
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            user_email = user.get('preferred_username', user.get('email', 'unknown'))
            user_name = user.get('name', user_email)
            
            data = request.get_json()
            group_id = data.get('group_id')
            comment = data.get('comment', '')
            
            if not group_id:
                return jsonify({'error': 'group_id is required'}), 400
            
            # Approve the request
            approval = approve_request(
                approval_id=approval_id,
                group_id=group_id,
                approver_id=user_id,
                approver_email=user_email,
                approver_name=user_name,
                comment=comment
            )
            
            # Execute the approved action
            execution_result = _execute_approved_action(approval, user_id, user_email, user_name)
            
            return jsonify({
                'success': True,
                'message': 'Request approved and executed',
                'approval': approval,
                'execution_result': execution_result
            }), 200
            
        except Exception as e:
            debug_print(f"Error approving request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/approvals/<approval_id>/deny', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_deny_request(approval_id):
        """
        Deny an approval request.
        
        Body:
            group_id (str): Group ID (partition key)
            comment (str): Reason for denial (required)
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            user_email = user.get('preferred_username', user.get('email', 'unknown'))
            user_name = user.get('name', user_email)
            
            data = request.get_json()
            group_id = data.get('group_id')
            comment = data.get('comment', '')
            
            if not group_id:
                return jsonify({'error': 'group_id is required'}), 400
            
            if not comment:
                return jsonify({'error': 'comment is required for denial'}), 400
            
            # Deny the request
            approval = deny_request(
                approval_id=approval_id,
                group_id=group_id,
                denier_id=user_id,
                denier_email=user_email,
                denier_name=user_name,
                comment=comment,
                auto_denied=False
            )
            
            return jsonify({
                'success': True,
                'message': 'Request denied',
                'approval': approval
            }), 200
            
        except Exception as e:
            debug_print(f"Error denying request: {e}")
            return jsonify({'error': str(e)}), 500
    
    # New standalone approvals API endpoints (accessible to all users with permissions)
    @app.route('/api/approvals', methods=['GET'])
    @login_required
    def api_get_approvals():
        """
        Get approval requests visible to the current user (admins, control center admins, and group owners).
        
        Query Parameters:
            page (int): Page number (default: 1)
            page_size (int): Items per page (default: 20)
            status (str): Filter by status (pending, approved, denied, all)
            action_type (str): Filter by action type
            search (str): Search by group name or reason
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            user_roles = user.get('roles', [])
            
            # Get query parameters
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            status_filter = request.args.get('status', 'pending')
            action_type_filter = request.args.get('action_type', 'all')
            search_query = request.args.get('search', '')
            
            debug_print(f"📋 [APPROVALS API] Fetching approvals - status_filter: {status_filter}, action_type: {action_type_filter}")
            
            # Determine include_completed based on status filter
            # 'all' means show everything, specific statuses mean show only those
            include_completed = (status_filter in ['all', 'approved', 'denied', 'executed'])
            
            debug_print(f"📋 [APPROVALS API] include_completed: {include_completed}")
            
            # Map action_type to request_type_filter
            request_type_filter = None if action_type_filter == 'all' else action_type_filter
            
            # Fetch approvals
            result = get_pending_approvals(
                user_id=user_id,
                user_roles=user_roles,
                page=page,
                per_page=page_size,
                include_completed=include_completed,
                request_type_filter=request_type_filter,
                status_filter=status_filter
            )
            
            # Add can_approve field to each approval
            approvals_with_permission = []
            for approval in result.get('approvals', []):
                approval_copy = dict(approval)
                # User can approve if they didn't create the request
                approval_copy['can_approve'] = (approval.get('requester_id') != user_id)
                approvals_with_permission.append(approval_copy)
            
            return jsonify({
                'success': True,
                'approvals': approvals_with_permission,
                'total_count': result.get('total', 0),
                'page': result.get('page', 1),
                'page_size': result.get('per_page', page_size),
                'total_pages': result.get('total_pages', 0)
            }), 200
            
        except Exception as e:
            debug_print(f"Error fetching approvals: {e}")
            import traceback
            debug_print(traceback.format_exc())
            return jsonify({'error': 'Failed to fetch approvals', 'details': str(e)}), 500

    @app.route('/api/approvals/<approval_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    def api_get_approval_by_id(approval_id):
        """
        Get a single approval request by ID.
        
        Query Parameters:
            group_id (str): Group ID (partition key)
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            
            group_id = request.args.get('group_id')
            if not group_id:
                return jsonify({'error': 'group_id query parameter is required'}), 400
            
            # Get the approval
            approval = cosmos_approvals_container.read_item(
                item=approval_id,
                partition_key=group_id
            )
            
            # Add can_approve field
            approval['can_approve'] = (approval.get('requester_id') != user_id)
            
            return jsonify(approval), 200
            
        except Exception as e:
            debug_print(f"Error fetching approval {approval_id}: {e}")
            import traceback
            debug_print(traceback.format_exc())
            return jsonify({'error': 'Failed to fetch approval', 'details': str(e)}), 500

    @app.route('/api/approvals/<approval_id>/approve', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    def api_approve_request(approval_id):
        """
        Approve an approval request and execute the action.
        
        Body:
            group_id (str): Group ID (partition key)
            comment (str, optional): Approval comment
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            user_email = user.get('preferred_username', user.get('email', 'unknown'))
            user_name = user.get('name', user_email)
            
            data = request.get_json()
            group_id = data.get('group_id')
            comment = data.get('comment', '')
            
            if not group_id:
                return jsonify({'error': 'group_id is required'}), 400
            
            # Approve the request
            approval = approve_request(
                approval_id=approval_id,
                group_id=group_id,
                approver_id=user_id,
                approver_email=user_email,
                approver_name=user_name,
                comment=comment
            )
            
            # Execute the approved action
            execution_result = _execute_approved_action(approval, user_id, user_email, user_name)
            
            return jsonify({
                'success': True,
                'message': 'Request approved and executed',
                'approval': approval,
                'execution_result': execution_result
            }), 200
            
        except Exception as e:
            debug_print(f"Error approving request: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/approvals/<approval_id>/deny', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    def api_deny_request(approval_id):
        """
        Deny an approval request.
        
        Body:
            group_id (str): Group ID (partition key)
            comment (str): Reason for denial (required)
        """
        try:
            user = session.get('user', {})
            user_id = user.get('oid') or user.get('sub')
            user_email = user.get('preferred_username', user.get('email', 'unknown'))
            user_name = user.get('name', user_email)
            
            data = request.get_json()
            group_id = data.get('group_id')
            comment = data.get('comment', '')
            
            if not group_id:
                return jsonify({'error': 'group_id is required'}), 400
            
            if not comment:
                return jsonify({'error': 'comment is required for denial'}), 400
            
            # Deny the request
            approval = deny_request(
                approval_id=approval_id,
                group_id=group_id,
                denier_id=user_id,
                denier_email=user_email,
                denier_name=user_name,
                comment=comment,
                auto_denied=False
            )
            
            return jsonify({
                'success': True,
                'message': 'Request denied',
                'approval': approval
            }), 200
            
        except Exception as e:
            debug_print(f"Error denying request: {e}")
            return jsonify({'error': str(e)}), 500

    def _execute_approved_action(approval, executor_id, executor_email, executor_name):
        """
        Execute the action specified in an approved request.
        
        Args:
            approval: Approved request document
            executor_id: User ID executing the action
            executor_email: Email of executor
            executor_name: Display name of executor
        
        Returns:
            Result dictionary with success status and message
        """
        try:
            request_type = approval['request_type']
            group_id = approval['group_id']
            
            if request_type == TYPE_TAKE_OWNERSHIP:
                # Execute take ownership
                # Check if this is for a public workspace or group
                if approval.get('metadata', {}).get('entity_type') == 'workspace':
                    result = _execute_take_workspace_ownership(approval, executor_id, executor_email, executor_name)
                else:
                    result = _execute_take_ownership(approval, executor_id, executor_email, executor_name)
            
            elif request_type == TYPE_TRANSFER_OWNERSHIP:
                # Execute transfer ownership
                # Check if this is for a public workspace or group
                if approval.get('metadata', {}).get('entity_type') == 'workspace':
                    result = _execute_transfer_workspace_ownership(approval, executor_id, executor_email, executor_name)
                else:
                    result = _execute_transfer_ownership(approval, executor_id, executor_email, executor_name)
            
            elif request_type == TYPE_DELETE_DOCUMENTS:
                # Check if this is for a public workspace or group
                if approval.get('metadata', {}).get('entity_type') == 'workspace':
                    result = _execute_delete_public_workspace_documents(approval, executor_id, executor_email, executor_name)
                else:
                    result = _execute_delete_documents(approval, executor_id, executor_email, executor_name)
            
            elif request_type == TYPE_DELETE_GROUP:
                # Check if this is for a public workspace or group
                if approval.get('metadata', {}).get('entity_type') == 'workspace':
                    result = _execute_delete_public_workspace(approval, executor_id, executor_email, executor_name)
                else:
                    result = _execute_delete_group(approval, executor_id, executor_email, executor_name)
            
            elif request_type == TYPE_DELETE_USER_DOCUMENTS:
                # Execute delete user documents
                result = _execute_delete_user_documents(approval, executor_id, executor_email, executor_name)
            
            else:
                result = {'success': False, 'message': f'Unknown request type: {request_type}'}
            
            # Mark approval as executed
            mark_approval_executed(
                approval_id=approval['id'],
                group_id=group_id,
                success=result['success'],
                result_message=result['message']
            )
            
            return result
            
        except Exception as e:
            # Mark as failed
            mark_approval_executed(
                approval_id=approval['id'],
                group_id=approval['group_id'],
                success=False,
                result_message=f"Execution error: {str(e)}"
            )
            raise

    def _execute_take_ownership(approval, executor_id, executor_email, executor_name):
        """Execute admin take ownership action."""
        try:
            group_id = approval['group_id']
            requester_id = approval['requester_id']
            requester_email = approval['requester_email']
            
            # Get the group
            group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            
            old_owner = group.get('owner', {})
            old_owner_id = old_owner.get('id')
            old_owner_email = old_owner.get('email', 'unknown')
            
            # Update owner to requester (the admin who requested)
            group['owner'] = {
                'id': requester_id,
                'email': requester_email,
                'displayName': approval['requester_name']
            }
            
            # Remove requester from special roles if present
            if requester_id in group.get('admins', []):
                group['admins'].remove(requester_id)
            if requester_id in group.get('documentManagers', []):
                group['documentManagers'].remove(requester_id)
            
            # Ensure requester is in users list
            requester_in_users = any(m.get('userId') == requester_id for m in group.get('users', []))
            if not requester_in_users:
                group.setdefault('users', []).append({
                    'userId': requester_id,
                    'email': requester_email,
                    'displayName': approval['requester_name']
                })
            
            # Demote old owner to regular member
            if old_owner_id:
                old_owner_in_users = any(m.get('userId') == old_owner_id for m in group.get('users', []))
                if not old_owner_in_users:
                    group.setdefault('users', []).append({
                        'userId': old_owner_id,
                        'email': old_owner_email,
                        'displayName': old_owner.get('displayName', old_owner_email)
                    })
                
                if old_owner_id in group.get('admins', []):
                    group['admins'].remove(old_owner_id)
                if old_owner_id in group.get('documentManagers', []):
                    group['documentManagers'].remove(old_owner_id)
            
            group['modifiedDate'] = datetime.utcnow().isoformat()
            cosmos_groups_container.upsert_item(group)
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'group_ownership_change',
                'activity_type': 'admin_take_ownership_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'admin_user_id': requester_id,
                'admin_email': requester_email,
                'approver_id': executor_id,
                'approver_email': executor_email,
                'group_id': group_id,
                'group_name': group.get('name', 'Unknown'),
                'old_owner_id': old_owner_id,
                'old_owner_email': old_owner_email,
                'new_owner_id': requester_id,
                'new_owner_email': requester_email,
                'approval_id': approval['id'],
                'description': f"Admin {requester_email} took ownership (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            return {
                'success': True,
                'message': f'Ownership transferred to {requester_email}'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to take ownership: {str(e)}'}

    def _execute_take_workspace_ownership(approval, executor_id, executor_email, executor_name):
        """Execute admin take workspace ownership action."""
        try:
            workspace_id = approval.get('workspace_id') or approval.get('group_id')
            requester_id = approval['requester_id']
            requester_email = approval['requester_email']
            requester_name = approval['requester_name']
            
            # Get the workspace
            workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            
            # Get old owner info
            old_owner = workspace.get('owner', {})
            if isinstance(old_owner, dict):
                old_owner_id = old_owner.get('userId')
                old_owner_email = old_owner.get('email')
                old_owner_name = old_owner.get('displayName')
            else:
                # Old format where owner is just a string
                old_owner_id = old_owner
                # Try to get user info
                try:
                    old_owner_user = cosmos_user_settings_container.read_item(
                        item=old_owner_id,
                        partition_key=old_owner_id
                    )
                    old_owner_email = old_owner_user.get('email', 'unknown')
                    old_owner_name = old_owner_user.get('display_name', old_owner_email)
                except:
                    old_owner_email = 'unknown'
                    old_owner_name = 'unknown'
            
            # Update owner to requester (the admin who requested) with full user object
            workspace['owner'] = {
                'userId': requester_id,
                'email': requester_email,
                'displayName': requester_name
            }
            
            # Remove requester from admins/documentManagers if present
            new_admins = []
            for admin in workspace.get('admins', []):
                admin_id = admin.get('userId') if isinstance(admin, dict) else admin
                if admin_id != requester_id:
                    # Ensure admin is full object
                    if isinstance(admin, dict):
                        new_admins.append(admin)
                    else:
                        # Convert string ID to object if needed
                        try:
                            admin_user = cosmos_user_settings_container.read_item(
                                item=admin,
                                partition_key=admin
                            )
                            new_admins.append({
                                'userId': admin,
                                'email': admin_user.get('email', 'unknown'),
                                'displayName': admin_user.get('display_name', 'unknown')
                            })
                        except:
                            pass
            workspace['admins'] = new_admins
            
            new_dms = []
            for dm in workspace.get('documentManagers', []):
                dm_id = dm.get('userId') if isinstance(dm, dict) else dm
                if dm_id != requester_id:
                    # Ensure dm is full object
                    if isinstance(dm, dict):
                        new_dms.append(dm)
                    else:
                        # Convert string ID to object if needed
                        try:
                            dm_user = cosmos_user_settings_container.read_item(
                                item=dm,
                                partition_key=dm
                            )
                            new_dms.append({
                                'userId': dm,
                                'email': dm_user.get('email', 'unknown'),
                                'displayName': dm_user.get('display_name', 'unknown')
                            })
                        except:
                            pass
            workspace['documentManagers'] = new_dms
            
            # Demote old owner to admin if not already there
            if old_owner_id and old_owner_id != requester_id:
                old_owner_in_admins = any(
                    (a.get('userId') if isinstance(a, dict) else a) == old_owner_id 
                    for a in workspace.get('admins', [])
                )
                old_owner_in_dms = any(
                    (dm.get('userId') if isinstance(dm, dict) else dm) == old_owner_id 
                    for dm in workspace.get('documentManagers', [])
                )
                
                if not old_owner_in_admins and not old_owner_in_dms:
                    # Add old owner as admin
                    workspace.setdefault('admins', []).append({
                        'userId': old_owner_id,
                        'email': old_owner_email,
                        'displayName': old_owner_name
                    })
            
            workspace['modifiedDate'] = datetime.utcnow().isoformat()
            cosmos_public_workspaces_container.upsert_item(workspace)
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'workspace_ownership_change',
                'activity_type': 'admin_take_ownership_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': requester_id,
                'requester_email': requester_email,
                'approver_id': executor_id,
                'approver_email': executor_email,
                'workspace_id': workspace_id,
                'workspace_name': workspace.get('name', 'Unknown'),
                'old_owner_id': old_owner_id,
                'old_owner_email': old_owner_email,
                'new_owner_id': requester_id,
                'new_owner_email': requester_email,
                'approval_id': approval['id'],
                'description': f"Admin {requester_email} took ownership (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            return {
                'success': True,
                'message': f"Ownership transferred to {requester_email}"
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to take workspace ownership: {str(e)}'}

    def _execute_transfer_ownership(approval, executor_id, executor_email, executor_name):
        """Execute transfer ownership action."""
        try:
            group_id = approval['group_id']
            new_owner_id = approval['metadata'].get('new_owner_id')
            
            if not new_owner_id:
                return {'success': False, 'message': 'new_owner_id not found in approval metadata'}
            
            # Get the group
            group = cosmos_groups_container.read_item(item=group_id, partition_key=group_id)
            
            # Find new owner in members
            new_owner_member = None
            for member in group.get('users', []):
                if member.get('userId') == new_owner_id:
                    new_owner_member = member
                    break
            
            if not new_owner_member:
                return {'success': False, 'message': 'New owner not found in group members'}
            
            old_owner = group.get('owner', {})
            old_owner_id = old_owner.get('id')
            
            # Update owner
            group['owner'] = {
                'id': new_owner_id,
                'email': new_owner_member.get('email'),
                'displayName': new_owner_member.get('displayName')
            }
            
            # Remove new owner from special roles
            if new_owner_id in group.get('admins', []):
                group['admins'].remove(new_owner_id)
            if new_owner_id in group.get('documentManagers', []):
                group['documentManagers'].remove(new_owner_id)
            
            # Demote old owner to member
            if old_owner_id:
                old_owner_in_users = any(m.get('userId') == old_owner_id for m in group.get('users', []))
                if not old_owner_in_users:
                    group.setdefault('users', []).append({
                        'userId': old_owner_id,
                        'email': old_owner.get('email'),
                        'displayName': old_owner.get('displayName')
                    })
                
                if old_owner_id in group.get('admins', []):
                    group['admins'].remove(old_owner_id)
                if old_owner_id in group.get('documentManagers', []):
                    group['documentManagers'].remove(old_owner_id)
            
            group['modifiedDate'] = datetime.utcnow().isoformat()
            cosmos_groups_container.upsert_item(group)
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'group_ownership_change',
                'activity_type': 'transfer_ownership_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'group_id': group_id,
                'group_name': group.get('name', 'Unknown'),
                'old_owner_id': old_owner_id,
                'old_owner_email': old_owner.get('email'),
                'new_owner_id': new_owner_id,
                'new_owner_email': new_owner_member.get('email'),
                'approval_id': approval['id'],
                'description': f"Ownership transferred to {new_owner_member.get('email')} (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            return {
                'success': True,
                'message': f"Ownership transferred to {new_owner_member.get('email')}"
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to transfer ownership: {str(e)}'}

    def _execute_transfer_workspace_ownership(approval, executor_id, executor_email, executor_name):
        """Execute transfer workspace ownership action."""
        try:
            workspace_id = approval.get('workspace_id') or approval.get('group_id')
            new_owner_id = approval['metadata'].get('new_owner_id')
            new_owner_email = approval['metadata'].get('new_owner_email')
            new_owner_name = approval['metadata'].get('new_owner_name')
            
            if not new_owner_id:
                return {'success': False, 'message': 'new_owner_id not found in approval metadata'}
            
            # Get the workspace
            workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            
            # Get old owner info
            old_owner = workspace.get('owner', {})
            if isinstance(old_owner, dict):
                old_owner_id = old_owner.get('userId')
                old_owner_email = old_owner.get('email')
                old_owner_name = old_owner.get('displayName')
            else:
                # Handle case where owner is just a string (old format)
                old_owner_id = old_owner
                # Try to get full user info
                try:
                    old_owner_user = cosmos_user_settings_container.read_item(
                        item=old_owner_id,
                        partition_key=old_owner_id
                    )
                    old_owner_email = old_owner_user.get('email', 'unknown')
                    old_owner_name = old_owner_user.get('display_name', old_owner_email)
                except:
                    old_owner_email = 'unknown'
                    old_owner_name = 'unknown'
            
            # Update owner with full user object
            workspace['owner'] = {
                'userId': new_owner_id,
                'email': new_owner_email,
                'displayName': new_owner_name
            }
            
            # Remove new owner from admins/documentManagers if present
            new_admins = []
            for admin in workspace.get('admins', []):
                admin_id = admin.get('userId') if isinstance(admin, dict) else admin
                if admin_id != new_owner_id:
                    # Ensure admin is full object
                    if isinstance(admin, dict):
                        new_admins.append(admin)
                    else:
                        # Convert string ID to object if needed
                        try:
                            admin_user = cosmos_user_settings_container.read_item(
                                item=admin,
                                partition_key=admin
                            )
                            new_admins.append({
                                'userId': admin,
                                'email': admin_user.get('email', 'unknown'),
                                'displayName': admin_user.get('display_name', 'unknown')
                            })
                        except:
                            pass
            workspace['admins'] = new_admins
            
            new_dms = []
            for dm in workspace.get('documentManagers', []):
                dm_id = dm.get('userId') if isinstance(dm, dict) else dm
                if dm_id != new_owner_id:
                    # Ensure dm is full object
                    if isinstance(dm, dict):
                        new_dms.append(dm)
                    else:
                        # Convert string ID to object if needed
                        try:
                            dm_user = cosmos_user_settings_container.read_item(
                                item=dm,
                                partition_key=dm
                            )
                            new_dms.append({
                                'userId': dm,
                                'email': dm_user.get('email', 'unknown'),
                                'displayName': dm_user.get('display_name', 'unknown')
                            })
                        except:
                            pass
            workspace['documentManagers'] = new_dms
            
            # Add old owner to admins if not already there
            if old_owner_id and old_owner_id != new_owner_id:
                old_owner_in_admins = any(
                    (a.get('userId') if isinstance(a, dict) else a) == old_owner_id 
                    for a in workspace.get('admins', [])
                )
                old_owner_in_dms = any(
                    (dm.get('userId') if isinstance(dm, dict) else dm) == old_owner_id 
                    for dm in workspace.get('documentManagers', [])
                )
                
                if not old_owner_in_admins and not old_owner_in_dms:
                    # Add old owner as admin
                    workspace.setdefault('admins', []).append({
                        'userId': old_owner_id,
                        'email': old_owner_email,
                        'displayName': old_owner_name
                    })
            
            workspace['modifiedDate'] = datetime.utcnow().isoformat()
            cosmos_public_workspaces_container.upsert_item(workspace)
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'workspace_ownership_change',
                'activity_type': 'transfer_ownership_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'workspace_id': workspace_id,
                'workspace_name': workspace.get('name', 'Unknown'),
                'old_owner_id': old_owner_id,
                'old_owner_email': old_owner_email,
                'new_owner_id': new_owner_id,
                'new_owner_email': new_owner_email,
                'approval_id': approval['id'],
                'description': f"Ownership transferred to {new_owner_email} (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            return {
                'success': True,
                'message': f"Ownership transferred to {new_owner_email}"
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to transfer workspace ownership: {str(e)}'}

    def _execute_delete_documents(approval, executor_id, executor_email, executor_name):
        """Execute delete all documents action."""
        try:
            group_id = approval['group_id']
            
            debug_print(f"🔍 [DELETE_GROUP_DOCS] Starting deletion for group_id: {group_id}")
            
            # Query all document metadata for this group
            query = "SELECT * FROM c WHERE c.group_id = @group_id AND c.type = 'document_metadata'"
            parameters = [{"name": "@group_id", "value": group_id}]
            
            debug_print(f"🔍 [DELETE_GROUP_DOCS] Query: {query}")
            debug_print(f"🔍 [DELETE_GROUP_DOCS] Parameters: {parameters}")
            debug_print(f"🔍 [DELETE_GROUP_DOCS] Using partition_key: {group_id}")
            
            # Query with partition key for better performance
            documents = list(cosmos_group_documents_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=group_id
            ))
            
            debug_print(f"📊 [DELETE_GROUP_DOCS] Found {len(documents)} documents with partition key query")
            
            # If no documents found with partition key, try cross-partition query
            if len(documents) == 0:
                debug_print(f"⚠️ [DELETE_GROUP_DOCS] No documents found with partition key, trying cross-partition query")
                documents = list(cosmos_group_documents_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                debug_print(f"📊 [DELETE_GROUP_DOCS] Cross-partition query found {len(documents)} documents")
                
                # Log sample document for debugging
                if len(documents) > 0:
                    sample_doc = documents[0]
                    debug_print(f"📄 [DELETE_GROUP_DOCS] Sample document structure: id={sample_doc.get('id')}, type={sample_doc.get('type')}, group_id={sample_doc.get('group_id')}")
            
            deleted_count = 0
            
            # Use proper deletion APIs for each document
            for doc in documents:
                try:
                    doc_id = doc['id']
                    debug_print(f"🗑️ [DELETE_GROUP_DOCS] Deleting document {doc_id}")
                    
                    # Use delete_document API which handles:
                    # - Blob storage deletion
                    # - AI Search index deletion
                    # - Cosmos DB metadata deletion
                    # Note: For group documents, we don't have a user_id, so we pass None
                    delete_result = delete_document(
                        user_id=None,
                        document_id=doc_id,
                        group_id=group_id
                    )
                    
                    # Check if delete_result is valid and successful
                    if delete_result and delete_result.get('success'):
                        # Delete document chunks using proper API
                        delete_document_chunks(
                            document_id=doc_id,
                            group_id=group_id
                        )
                        
                        deleted_count += 1
                        debug_print(f"✅ [DELETE_GROUP_DOCS] Successfully deleted document {doc_id}")
                    else:
                        error_msg = delete_result.get('message') if delete_result else 'delete_document returned None'
                        debug_print(f"❌ [DELETE_GROUP_DOCS] Failed to delete document {doc_id}: {error_msg}")
                    
                except Exception as doc_error:
                    debug_print(f"❌ [DELETE_GROUP_DOCS] Error deleting document {doc.get('id')}: {doc_error}")
            
            # Invalidate group search cache after deletion
            try:
                invalidate_group_search_cache(group_id)
                debug_print(f"🔄 [DELETE_GROUP_DOCS] Invalidated search cache for group {group_id}")
            except Exception as cache_error:
                debug_print(f"⚠️ [DELETE_GROUP_DOCS] Could not invalidate search cache: {cache_error}")
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'group_documents_deletion',
                'activity_type': 'delete_all_documents_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'group_id': group_id,
                'group_name': approval['group_name'],
                'documents_deleted': deleted_count,
                'approval_id': approval['id'],
                'description': f"All documents deleted from group (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            debug_print(f"[ControlCenter] Group Documents Deleted (Approved) -- group_id: {group_id}, documents_deleted: {deleted_count}")
            
            return {
                'success': True,
                'message': f'Deleted {deleted_count} documents'
            }
            
        except Exception as e:
            debug_print(f"[DELETE_GROUP_DOCS] Fatal error: {e}")
            return {'success': False, 'message': f'Failed to delete documents: {str(e)}'}

    def _execute_delete_public_workspace_documents(approval, executor_id, executor_email, executor_name):
        """Execute delete all documents in a public workspace."""
        try:
            workspace_id = approval['group_id']  # workspace_id is stored as group_id
            
            debug_print(f"🔍 [DELETE_WORKSPACE_DOCS] Starting deletion for workspace_id: {workspace_id}")
            
            # Query all documents for this workspace
            query = "SELECT c.id FROM c WHERE c.public_workspace_id = @workspace_id"
            parameters = [{"name": "@workspace_id", "value": workspace_id}]
            
            debug_print(f"🔍 [DELETE_WORKSPACE_DOCS] Query: {query}")
            debug_print(f"🔍 [DELETE_WORKSPACE_DOCS] Parameters: {parameters}")
            
            documents = list(cosmos_public_documents_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"📊 [DELETE_WORKSPACE_DOCS] Found {len(documents)} documents")
            
            deleted_count = 0
            for doc in documents:
                try:
                    doc_id = doc['id']
                    debug_print(f"🗑️ [DELETE_WORKSPACE_DOCS] Deleting document {doc_id}")
                    
                    # Delete document chunks and metadata using proper APIs
                    delete_document_chunks(
                        document_id=doc_id,
                        public_workspace_id=workspace_id
                    )
                    
                    delete_document(
                        user_id=None,
                        document_id=doc_id,
                        public_workspace_id=workspace_id
                    )
                    
                    deleted_count += 1
                    debug_print(f"✅ [DELETE_WORKSPACE_DOCS] Successfully deleted document {doc_id}")
                    
                except Exception as doc_error:
                    debug_print(f"❌ [DELETE_WORKSPACE_DOCS] Error deleting document {doc_id}: {doc_error}")
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'public_workspace_documents_deletion',
                'activity_type': 'delete_all_documents_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'workspace_id': workspace_id,
                'workspace_name': approval.get('metadata', {}).get('workspace_name', 'Unknown'),
                'documents_deleted': deleted_count,
                'approval_id': approval['id'],
                'description': f"All documents deleted from public workspace (approved by {executor_email})",
                'workspace_context': {
                    'public_workspace_id': workspace_id
                }
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            debug_print(f"[ControlCenter] Public Workspace Documents Deleted (Approved) -- workspace_id: {workspace_id}, documents_deleted: {deleted_count}")
            
            return {
                'success': True,
                'message': f'Deleted {deleted_count} documents from public workspace'
            }
            
        except Exception as e:
            debug_print(f"[DELETE_WORKSPACE_DOCS] Fatal error: {e}")
            return {'success': False, 'message': f'Failed to delete workspace documents: {str(e)}'}

    def _execute_delete_public_workspace(approval, executor_id, executor_email, executor_name):
        """Execute delete entire public workspace action."""
        try:
            workspace_id = approval['group_id']  # workspace_id is stored as group_id
            
            debug_print(f"🔍 [DELETE_WORKSPACE] Starting deletion for workspace_id: {workspace_id}")
            
            # First delete all documents
            doc_result = _execute_delete_public_workspace_documents(approval, executor_id, executor_email, executor_name)
            
            if not doc_result['success']:
                return doc_result
            
            # Delete the workspace itself
            try:
                cosmos_public_workspaces_container.delete_item(
                    item=workspace_id,
                    partition_key=workspace_id
                )
                debug_print(f"✅ [DELETE_WORKSPACE] Successfully deleted workspace {workspace_id}")
            except Exception as del_e:
                debug_print(f"❌ [DELETE_WORKSPACE] Error deleting workspace {workspace_id}: {del_e}")
                return {'success': False, 'message': f'Failed to delete workspace: {str(del_e)}'}
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'public_workspace_deletion',
                'activity_type': 'delete_workspace_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'workspace_id': workspace_id,
                'workspace_name': approval.get('metadata', {}).get('workspace_name', 'Unknown'),
                'approval_id': approval['id'],
                'description': f"Public workspace completely deleted (approved by {executor_email})",
                'workspace_context': {
                    'public_workspace_id': workspace_id
                }
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            debug_print(f"[ControlCenter] Public Workspace Deleted (Approved) -- workspace_id: {workspace_id}")
            
            return {
                'success': True,
                'message': 'Public workspace and all documents deleted successfully'
            }
            
        except Exception as e:
            debug_print(f"[DELETE_WORKSPACE] Fatal error: {e}")
            return {'success': False, 'message': f'Failed to delete workspace: {str(e)}'}

    def _execute_delete_group(approval, executor_id, executor_email, executor_name):
        """Execute delete entire group action."""
        try:
            group_id = approval['group_id']
            
            # First delete all documents
            doc_result = _execute_delete_documents(approval, executor_id, executor_email, executor_name)
            
            # Delete group conversations (optional - could keep for audit)
            try:
                query = "SELECT * FROM c WHERE c.group_id = @group_id"
                parameters = [{"name": "@group_id", "value": group_id}]
                
                conversations = list(cosmos_group_conversations_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                for conv in conversations:
                    cosmos_group_conversations_container.delete_item(
                        item=conv['id'],
                        partition_key=group_id
                    )
            except Exception as conv_error:
                debug_print(f"Error deleting conversations: {conv_error}")
            
            # Delete group messages (optional)
            try:
                messages = list(cosmos_group_messages_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                for msg in messages:
                    cosmos_group_messages_container.delete_item(
                        item=msg['id'],
                        partition_key=group_id
                    )
            except Exception as msg_error:
                debug_print(f"Error deleting messages: {msg_error}")
            
            # Finally, delete the group itself using proper API
            debug_print(f"🗑️ [DELETE GROUP] Deleting group document using delete_group() API")
            delete_group(group_id)
            debug_print(f"✅ [DELETE GROUP] Group {group_id} successfully deleted")
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'group_deletion',
                'activity_type': 'delete_group_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'group_id': group_id,
                'group_name': approval['group_name'],
                'approval_id': approval['id'],
                'description': f"Group completely deleted (approved by {executor_email})"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            return {
                'success': True,
                'message': 'Group completely deleted'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Failed to delete group: {str(e)}'}

    def _execute_delete_user_documents(approval, executor_id, executor_email, executor_name):
        """Execute delete all user documents action."""
        try:
            from functions_documents import delete_document, delete_document_chunks
            from utils_cache import invalidate_personal_search_cache
            
            user_id = approval['metadata'].get('user_id')
            user_email = approval['metadata'].get('user_email', 'unknown')
            user_name = approval['metadata'].get('user_name', user_email)
            
            if not user_id:
                return {'success': False, 'message': 'User ID not found in approval metadata'}
            
            # Query all personal documents for this user
            # Personal documents are stored in cosmos_user_documents_container with user_id as partition key
            query = "SELECT * FROM c WHERE c.user_id = @user_id"
            parameters = [{"name": "@user_id", "value": user_id}]
            
            debug_print(f"🔍 [DELETE_USER_DOCS] Querying for user_id: {user_id}")
            debug_print(f"🔍 [DELETE_USER_DOCS] Query: {query}")
            debug_print(f"🔍 [DELETE_USER_DOCS] Container: cosmos_user_documents_container")
            
            documents = list(cosmos_user_documents_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id  # Use partition key for efficient query
            ))
            
            debug_print(f"📊 [DELETE_USER_DOCS] Found {len(documents)} documents with partition key query")
            if len(documents) > 0:
                debug_print(f"📄 [DELETE_USER_DOCS] First document sample: id={documents[0].get('id', 'no-id')}, file_name={documents[0].get('file_name', 'no-filename')}, type={documents[0].get('type', 'no-type')}")
            else:
                # Try a cross-partition query to see if documents exist elsewhere
                debug_print(f"⚠️ [DELETE_USER_DOCS] No documents found with partition key, trying cross-partition query...")
                documents = list(cosmos_user_documents_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                debug_print(f"📊 [DELETE_USER_DOCS] Cross-partition query found {len(documents)} documents")
                if len(documents) > 0:
                    sample_doc = documents[0]
                    debug_print(f"📄 [DELETE_USER_DOCS] Sample doc fields: {list(sample_doc.keys())}")
                    debug_print(f"📄 [DELETE_USER_DOCS] Sample doc: id={sample_doc.get('id')}, type={sample_doc.get('type')}, user_id={sample_doc.get('user_id')}, file_name={sample_doc.get('file_name')}")
            
            deleted_count = 0
            
            # Use the existing delete_document function for proper cleanup
            for doc in documents:
                try:
                    document_id = doc['id']
                    debug_print(f"🗑️ [DELETE_USER_DOCS] Deleting document {document_id}: {doc.get('file_name', 'unknown')}")
                    
                    # Use the proper delete_document function which handles:
                    # - Blob storage deletion
                    # - AI Search index deletion
                    # - Cosmos DB document deletion
                    delete_document(user_id, document_id)
                    delete_document_chunks(document_id)
                    
                    deleted_count += 1
                    debug_print(f"✅ [DELETE_USER_DOCS] Successfully deleted document {document_id}")
                    
                except Exception as doc_error:
                    debug_print(f"❌ [DELETE_USER_DOCS] Error deleting document {doc.get('id')}: {doc_error}")
            
            # Invalidate search cache for this user
            try:
                invalidate_personal_search_cache(user_id)
                debug_print(f"🔄 [DELETE_USER_DOCS] Invalidated search cache for user {user_id}")
            except Exception as cache_error:
                debug_print(f"⚠️ [DELETE_USER_DOCS] Failed to invalidate search cache: {cache_error}")
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'type': 'user_documents_deletion',
                'activity_type': 'delete_all_user_documents_approved',
                'timestamp': datetime.utcnow().isoformat(),
                'requester_id': approval['requester_id'],
                'requester_email': approval['requester_email'],
                'approver_id': executor_id,
                'approver_email': executor_email,
                'target_user_id': user_id,
                'target_user_email': user_email,
                'target_user_name': user_name,
                'documents_deleted': deleted_count,
                'approval_id': approval['id'],
                'description': f"All documents deleted for user {user_name} ({user_email}) - approved by {executor_email}"
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            # Log to AppInsights
            log_event("[ControlCenter] User Documents Deleted (Approved)", {
                "executor": executor_email,
                "user_id": user_id,
                "user_email": user_email,
                "documents_deleted": deleted_count,
                "approval_id": approval['id']
            })
            
            return {
                'success': True,
                'message': f'Deleted {deleted_count} documents for user {user_name}'
            }
            
        except Exception as e:
            debug_print(f"Error deleting user documents: {e}")
            return {'success': False, 'message': f'Failed to delete user documents: {str(e)}'}

            return jsonify({'error': 'Failed to retrieve activity logs'}), 500