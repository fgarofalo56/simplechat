# admin_workspaces.py

from config import *
from functions_authentication import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from functions_approvals import *
from functions_documents import update_document, delete_document, delete_document_chunks
from services.admin_metrics_service import enhance_public_workspace_with_activity
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print


def register_admin_workspace_routes(app):
    # Public Workspaces API
    @app.route('/api/admin/control-center/public-workspaces', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_control_center_public_workspaces():
        """
        Get paginated list of public workspaces with activity data for control center management.
        Similar to groups endpoint but for public workspaces.
        """
        try:
            # Parse request parameters
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), 100)  # Max 100 per page
            search_term = request.args.get('search', '').strip()
            status_filter = request.args.get('status_filter', 'all')
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            export_all = request.args.get('all', 'false').lower() == 'true'  # For CSV export
            
            # Calculate offset (only needed if not exporting all)
            offset = (page - 1) * per_page if not export_all else 0
            
            # Base query for public workspaces
            if search_term:
                # Search in workspace name and description
                query = """
                    SELECT * FROM c 
                    WHERE CONTAINS(LOWER(c.name), @search_term) 
                    OR CONTAINS(LOWER(c.description), @search_term)
                    ORDER BY c.name
                """
                parameters = [{"name": "@search_term", "value": search_term.lower()}]
            else:
                # Get all workspaces
                query = "SELECT * FROM c ORDER BY c.name"
                parameters = []
            
            # Execute query to get all matching workspaces
            all_workspaces = list(cosmos_public_workspaces_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Apply status filter if specified
            if status_filter != 'all':
                # For now, we'll treat all workspaces as 'active'
                # This can be enhanced later with actual status logic
                if status_filter != 'active':
                    all_workspaces = []
            
            # Calculate pagination
            total_count = len(all_workspaces)
            total_pages = math.ceil(total_count / per_page) if per_page > 0 else 0
            
            # Get the workspaces for current page or all for export
            if export_all:
                workspaces_page = all_workspaces  # Get all workspaces for CSV export
            else:
                workspaces_page = all_workspaces[offset:offset + per_page]
            
            # Enhance each workspace with activity data
            enhanced_workspaces = []
            for workspace in workspaces_page:
                try:
                    enhanced_workspace = enhance_public_workspace_with_activity(workspace, force_refresh=force_refresh)
                    enhanced_workspaces.append(enhanced_workspace)
                except Exception as enhance_e:
                    debug_print(f"Error enhancing workspace {workspace.get('id', 'unknown')}: {enhance_e}")
                    # Include the original workspace if enhancement fails
                    enhanced_workspaces.append(workspace)
            
            # Return response (paginated or all for export)
            if export_all:
                return jsonify({
                    'success': True,
                    'workspaces': enhanced_workspaces,
                    'total_count': total_count,
                    'filters': {
                        'search': search_term,
                        'status_filter': status_filter,
                        'force_refresh': force_refresh
                    }
                })
            else:
                return jsonify({
                    'workspaces': enhanced_workspaces,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_count': total_count,
                        'total_pages': total_pages,
                        'has_next': page < total_pages,
                        'has_prev': page > 1
                    },
                    'filters': {
                        'search': search_term,
                        'status_filter': status_filter,
                        'force_refresh': force_refresh
                    }
                })
            
        except Exception as e:
            debug_print(f"Error getting public workspaces for control center: {e}")
            return jsonify({'error': 'Failed to retrieve public workspaces'}), 500

    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/status', methods=['PUT'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_update_public_workspace_status(workspace_id):
        """
        Update public workspace status (active, locked, upload_disabled, inactive)
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
                
            # Get the workspace
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Public workspace not found'}), 404
            
            # Get admin user info
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid', 'unknown')
            admin_email = admin_user.get('preferred_username', 'unknown')
            
            # Get old status for logging
            old_status = workspace.get('status', 'active')  # Default to 'active' if not set
            
            # Only update and log if status actually changed
            if old_status != new_status:
                # Update workspace status
                workspace['status'] = new_status
                workspace['modifiedDate'] = datetime.utcnow().isoformat()
                
                # Add status change metadata
                if 'statusHistory' not in workspace:
                    workspace['statusHistory'] = []
                
                workspace['statusHistory'].append({
                    'old_status': old_status,
                    'new_status': new_status,
                    'changed_by_user_id': admin_user_id,
                    'changed_by_email': admin_email,
                    'changed_at': datetime.utcnow().isoformat(),
                    'reason': reason
                })
                
                # Update in database
                cosmos_public_workspaces_container.upsert_item(workspace)
                
                # Log to activity_logs container for audit trail
                from functions_activity_logging import log_public_workspace_status_change
                log_public_workspace_status_change(
                    workspace_id=workspace_id,
                    workspace_name=workspace.get('name', 'Unknown'),
                    old_status=old_status,
                    new_status=new_status,
                    changed_by_user_id=admin_user_id,
                    changed_by_email=admin_email,
                    reason=reason
                )
                
                # Log admin action (legacy logging)
                log_event("[ControlCenter] Public Workspace Status Update", {
                    "admin_user": admin_email,
                    "admin_user_id": admin_user_id,
                    "workspace_id": workspace_id,
                    "workspace_name": workspace.get('name'),
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason
                })
                
                return jsonify({
                    'message': 'Public workspace status updated successfully',
                    'old_status': old_status,
                    'new_status': new_status
                }), 200
            else:
                return jsonify({
                    'message': 'Status unchanged',
                    'status': new_status
                }), 200
                
        except Exception as e:
            debug_print(f"Error updating public workspace status: {e}")
            return jsonify({'error': 'Failed to update public workspace status'}), 500

    @app.route('/api/admin/control-center/public-workspaces/bulk-action', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_bulk_public_workspace_action():
        """
        Perform bulk actions on multiple public workspaces.
        Actions: lock, unlock, disable_uploads, enable_uploads, delete_documents
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
                
            workspace_ids = data.get('workspace_ids', [])
            action = data.get('action')
            reason = data.get('reason')  # Optional reason
            
            if not workspace_ids or not isinstance(workspace_ids, list):
                return jsonify({'error': 'workspace_ids must be a non-empty array'}), 400
                
            if not action:
                return jsonify({'error': 'Action is required'}), 400
            
            # Validate action
            valid_actions = ['lock', 'unlock', 'disable_uploads', 'enable_uploads', 'delete_documents']
            if action not in valid_actions:
                return jsonify({'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'}), 400
            
            # Get admin user info
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid', 'unknown')
            admin_email = admin_user.get('preferred_username', 'unknown')
            
            # Map actions to status values
            action_to_status = {
                'lock': 'locked',
                'unlock': 'active',
                'disable_uploads': 'upload_disabled',
                'enable_uploads': 'active'
            }
            
            successful = []
            failed = []
            
            for workspace_id in workspace_ids:
                try:
                    # Get the workspace
                    workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
                    
                    if action == 'delete_documents':
                        # Delete all documents for this workspace
                        # Query all documents
                        doc_query = "SELECT c.id FROM c WHERE c.public_workspace_id = @workspace_id"
                        doc_params = [{"name": "@workspace_id", "value": workspace_id}]
                        
                        docs_to_delete = list(cosmos_public_documents_container.query_items(
                            query=doc_query,
                            parameters=doc_params,
                            enable_cross_partition_query=True
                        ))
                        
                        deleted_count = 0
                        for doc in docs_to_delete:
                            try:
                                delete_document_chunks(doc['id'])
                                delete_document(doc['id'])
                                deleted_count += 1
                            except Exception as del_e:
                                debug_print(f"Error deleting document {doc['id']}: {del_e}")
                        
                        successful.append({
                            'workspace_id': workspace_id,
                            'workspace_name': workspace.get('name', 'Unknown'),
                            'action': action,
                            'documents_deleted': deleted_count
                        })
                        
                        # Log the action
                        log_event("[ControlCenter] Bulk Public Workspace Documents Deleted", {
                            "admin_user": admin_email,
                            "admin_user_id": admin_user_id,
                            "workspace_id": workspace_id,
                            "workspace_name": workspace.get('name'),
                            "documents_deleted": deleted_count,
                            "reason": reason
                        })
                        
                    else:
                        # Status change action
                        new_status = action_to_status[action]
                        old_status = workspace.get('status', 'active')
                        
                        if old_status != new_status:
                            workspace['status'] = new_status
                            workspace['modifiedDate'] = datetime.utcnow().isoformat()
                            
                            # Add status history
                            if 'statusHistory' not in workspace:
                                workspace['statusHistory'] = []
                            
                            workspace['statusHistory'].append({
                                'old_status': old_status,
                                'new_status': new_status,
                                'changed_by_user_id': admin_user_id,
                                'changed_by_email': admin_email,
                                'changed_at': datetime.utcnow().isoformat(),
                                'reason': reason,
                                'bulk_action': True
                            })
                            
                            cosmos_public_workspaces_container.upsert_item(workspace)
                            
                            # Log activity
                            from functions_activity_logging import log_public_workspace_status_change
                            log_public_workspace_status_change(
                                workspace_id=workspace_id,
                                workspace_name=workspace.get('name', 'Unknown'),
                                old_status=old_status,
                                new_status=new_status,
                                changed_by_user_id=admin_user_id,
                                changed_by_email=admin_email,
                                reason=f"Bulk action: {reason}" if reason else "Bulk action"
                            )
                        
                        successful.append({
                            'workspace_id': workspace_id,
                            'workspace_name': workspace.get('name', 'Unknown'),
                            'action': action,
                            'old_status': old_status,
                            'new_status': new_status
                        })
                    
                except Exception as e:
                    failed.append({
                        'workspace_id': workspace_id,
                        'error': str(e)
                    })
                    debug_print(f"Error processing workspace {workspace_id}: {e}")
            
            return jsonify({
                'message': 'Bulk action completed',
                'successful': successful,
                'failed': failed,
                'summary': {
                    'total': len(workspace_ids),
                    'success': len(successful),
                    'failed': len(failed)
                }
            }), 200
            
        except Exception as e:
            debug_print(f"Error performing bulk public workspace action: {e}")
            return jsonify({'error': 'Failed to perform bulk action'}), 500

    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_public_workspace_details(workspace_id):
        """
        Get detailed information about a specific public workspace.
        """
        try:
            # Get the workspace
            workspace = cosmos_public_workspaces_container.read_item(
                item=workspace_id,
                partition_key=workspace_id
            )
            
            # Enhance with activity information
            enhanced_workspace = enhance_public_workspace_with_activity(workspace)
            
            return jsonify(enhanced_workspace), 200
            
        except Exception as e:
            debug_print(f"Error getting public workspace details: {e}")
            return jsonify({'error': 'Failed to retrieve workspace details'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/members', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_public_workspace_members(workspace_id):
        """
        Get all members of a specific public workspace with their roles.
        Returns admins, document managers, and owner information.
        """
        try:
            # Get the workspace
            workspace = cosmos_public_workspaces_container.read_item(
                item=workspace_id,
                partition_key=workspace_id
            )
            
            # Create members list with roles
            members = []
            
            # Add owner - owner is an object with userId, email, displayName
            owner = workspace.get('owner')
            if owner:
                members.append({
                    'userId': owner.get('userId', ''),
                    'email': owner.get('email', ''),
                    'displayName': owner.get('displayName', owner.get('email', 'Unknown')),
                    'role': 'owner'
                })
            
            # Add admins - admins is an array of objects with userId, email, displayName
            admins = workspace.get('admins', [])
            for admin in admins:
                # Handle both object format and string format (for backward compatibility)
                if isinstance(admin, dict):
                    members.append({
                        'userId': admin.get('userId', ''),
                        'email': admin.get('email', ''),
                        'displayName': admin.get('displayName', admin.get('email', 'Unknown')),
                        'role': 'admin'
                    })
                else:
                    # Legacy format where admin is just a userId string
                    try:
                        user = cosmos_user_settings_container.read_item(
                            item=admin,
                            partition_key=admin
                        )
                        members.append({
                            'userId': admin,
                            'email': user.get('email', ''),
                            'displayName': user.get('display_name', user.get('email', '')),
                            'role': 'admin'
                        })
                    except:
                        pass
            
            # Add document managers - documentManagers is an array of objects with userId, email, displayName
            doc_managers = workspace.get('documentManagers', [])
            for dm in doc_managers:
                # Handle both object format and string format (for backward compatibility)
                if isinstance(dm, dict):
                    members.append({
                        'userId': dm.get('userId', ''),
                        'email': dm.get('email', ''),
                        'displayName': dm.get('displayName', dm.get('email', 'Unknown')),
                        'role': 'documentManager'
                    })
                else:
                    # Legacy format where documentManager is just a userId string
                    try:
                        user = cosmos_user_settings_container.read_item(
                            item=dm,
                            partition_key=dm
                        )
                        members.append({
                            'userId': dm,
                            'email': user.get('email', ''),
                            'displayName': user.get('display_name', user.get('email', '')),
                            'role': 'documentManager'
                        })
                    except:
                        pass
            
            return jsonify({
                'success': True,
                'members': members,
                'workspace_name': workspace.get('name', 'Unknown')
            }), 200
            
        except Exception as e:
            debug_print(f"Error getting workspace members: {e}")
            return jsonify({'error': 'Failed to retrieve workspace members'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/add-member', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_add_workspace_member(workspace_id):
        """
        Admin adds a member to a public workspace (used by both single add and CSV bulk upload)
        """
        try:
            data = request.get_json()
            user_id = data.get('userId')
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
            
            # Get the workspace
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Public workspace not found'}), 404
            
            # Check if user already exists
            owner = workspace.get('owner', {})
            owner_id = owner.get('userId') if isinstance(owner, dict) else owner
            admins = workspace.get('admins', [])
            doc_managers = workspace.get('documentManagers', [])
            
            # Extract user IDs from arrays (handle both object and string formats)
            admin_ids = [a.get('userId') if isinstance(a, dict) else a for a in admins]
            doc_manager_ids = [dm.get('userId') if isinstance(dm, dict) else dm for dm in doc_managers]
            
            if user_id == owner_id or user_id in admin_ids or user_id in doc_manager_ids:
                return jsonify({
                    'message': f'User {email} already exists in workspace',
                    'skipped': True
                }), 200
            
            # Create full user object
            user_obj = {
                'userId': user_id,
                'displayName': name,
                'email': email
            }
            
            # Add to appropriate role array with full user object
            if role == 'admin':
                workspace.setdefault('admins', []).append(user_obj)
            elif role == 'document_manager':
                workspace.setdefault('documentManagers', []).append(user_obj)
            # Note: 'user' role doesn't have a separate array in public workspaces
            # They are implicit members through document access
            
            # Update modification timestamp
            workspace['modifiedDate'] = datetime.utcnow().isoformat()
            
            # Save workspace
            cosmos_public_workspaces_container.upsert_item(workspace)
            
            # Determine the action source
            source = data.get('source', 'csv')
            action_type = 'add_workspace_member_directly' if source == 'single' else 'admin_add_workspace_member_csv'
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'activity_type': activity_type,
                'timestamp': datetime.utcnow().isoformat(),
                'admin_user_id': admin_user.get('oid') or admin_user.get('sub'),
                'admin_email': admin_email,
                'workspace_id': workspace_id,
                'workspace_name': workspace.get('name', 'Unknown'),
                'member_user_id': user_id,
                'member_email': email,
                'member_name': name,
                'member_role': role,
                'source': source,
                'description': f"Admin {admin_email} added member {name} ({email}) to workspace {workspace.get('name', workspace_id)} as {role}",
                'workspace_context': {
                    'public_workspace_id': workspace_id
                }
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            # Log to Application Insights
            log_event("[ControlCenter] Admin Add Workspace Member", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
                "member_email": email,
                "member_role": role
            })
            
            return jsonify({
                'message': f'Member {email} added successfully',
                'skipped': False
            }), 200
            
        except Exception as e:
            debug_print(f"Error adding workspace member: {e}")
            return jsonify({'error': 'Failed to add workspace member'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/add-member-single', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_add_workspace_member_single(workspace_id):
        """
        Admin adds a single member to a public workspace via the Add Member modal
        """
        try:
            data = request.get_json()
            user_id = data.get('userId')
            display_name = data.get('displayName')
            email = data.get('email')
            role = data.get('role', 'document_manager').lower()
            
            if not user_id or not display_name or not email:
                return jsonify({'error': 'Missing required fields: userId, displayName, email'}), 400
            
            # Validate role - workspaces only support admin and document_manager
            valid_roles = ['admin', 'document_manager']
            if role not in valid_roles:
                return jsonify({'error': f'Invalid role. Must be: {", ".join(valid_roles)}'}), 400
            
            admin_user = session.get('user', {})
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            
            # Get the workspace
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Public workspace not found'}), 404
            
            # Check if user already exists
            owner = workspace.get('owner', {})
            owner_id = owner.get('userId') if isinstance(owner, dict) else owner
            admins = workspace.get('admins', [])
            doc_managers = workspace.get('documentManagers', [])
            
            # Extract user IDs from arrays (handle both object and string formats)
            admin_ids = [a.get('userId') if isinstance(a, dict) else a for a in admins]
            doc_manager_ids = [dm.get('userId') if isinstance(dm, dict) else dm for dm in doc_managers]
            
            if user_id == owner_id or user_id in admin_ids or user_id in doc_manager_ids:
                return jsonify({
                    'error': f'User {email} already exists in workspace'
                }), 400
            
            # Add to appropriate role array with full user info
            user_obj = {
                'userId': user_id,
                'displayName': display_name,
                'email': email
            }
            
            if role == 'admin':
                workspace.setdefault('admins', []).append(user_obj)
            elif role == 'document_manager':
                workspace.setdefault('documentManagers', []).append(user_obj)
            
            # Update modification timestamp
            workspace['modifiedDate'] = datetime.utcnow().isoformat()
            
            # Save workspace
            cosmos_public_workspaces_container.upsert_item(workspace)
            
            # Log to activity logs
            activity_record = {
                'id': str(uuid.uuid4()),
                'activity_type': 'add_workspace_member_directly',
                'timestamp': datetime.utcnow().isoformat(),
                'admin_user_id': admin_user.get('oid') or admin_user.get('sub'),
                'admin_email': admin_email,
                'workspace_id': workspace_id,
                'workspace_name': workspace.get('name', 'Unknown'),
                'member_user_id': user_id,
                'member_email': email,
                'member_name': display_name,
                'member_role': role,
                'source': 'single',
                'description': f"Admin {admin_email} added member {display_name} ({email}) to workspace {workspace.get('name', workspace_id)} as {role}",
                'workspace_context': {
                    'public_workspace_id': workspace_id
                }
            }
            cosmos_activity_logs_container.create_item(body=activity_record)
            
            # Log to Application Insights
            log_event("[ControlCenter] Admin Add Workspace Member (Single)", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
                "member_email": email,
                "member_role": role
            })
            
            return jsonify({
                'message': f'Successfully added {display_name} as {role}',
                'success': True
            }), 200
            
        except Exception as e:
            debug_print(f"Error adding workspace member: {e}")
            return jsonify({'error': 'Failed to add workspace member'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/activity', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_public_workspace_activity(workspace_id):
        """
        Get activity timeline for a specific public workspace from activity logs
        Returns document creation/deletion, member changes, status changes, and conversations
        """
        try:
            # Get time range filter (default: last 30 days)
            days = request.args.get('days', '30')
            export = request.args.get('export', 'false').lower() == 'true'
            
            # Calculate date filter
            cutoff_date = None
            if days != 'all':
                try:
                    days_int = int(days)
                    cutoff_date = (datetime.utcnow() - timedelta(days=days_int)).isoformat()
                except ValueError:
                    pass
            
            # Query: All activities for public workspaces (no activity type filter to show everything)
            # Use SELECT * to get complete raw documents for modal display
            if cutoff_date:
                query = """
                    SELECT *
                    FROM c
                    WHERE c.workspace_context.public_workspace_id = @workspace_id
                    AND c.timestamp >= @cutoff_date
                    ORDER BY c.timestamp DESC
                """
            else:
                query = """
                    SELECT *
                    FROM c
                    WHERE c.workspace_context.public_workspace_id = @workspace_id
                    ORDER BY c.timestamp DESC
                """
            
            # Log the query for debugging
            debug_print(f"[Workspace Activity] Querying for workspace: {workspace_id}, days: {days}")
            debug_print(f"[Workspace Activity] Query: {query}")
            
            parameters = [
                {"name": "@workspace_id", "value": workspace_id}
            ]
            
            if cutoff_date:
                parameters.append({"name": "@cutoff_date", "value": cutoff_date})
            
            debug_print(f"[Workspace Activity] Parameters: {parameters}")
            
            # Execute query
            activities = list(cosmos_activity_logs_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"[Workspace Activity] Query returned {len(activities)} activities")
            
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
                
                elif activity_type == 'public_workspace_status_change':
                    status_change = activity.get('status_change', {})
                    formatted['status_change'] = {
                        'from_status': status_change.get('old_status'),
                        'to_status': status_change.get('new_status'),
                        'changed_by': activity.get('changed_by')
                    }
                    formatted['icon'] = 'shield-check'
                    formatted['color'] = 'warning'
                
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
                    if activity.get('workspace_context'):
                        formatted['workspace_context'] = activity.get('workspace_context')
                
                formatted_activities.append(formatted)
            
            if export:
                # Return CSV for export
                import io
                import csv
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(['Timestamp', 'Type', 'User ID', 'Description', 'Details'])
                for activity in formatted_activities:
                    details = ''
                    if activity.get('document'):
                        doc = activity['document']
                        details = f"{doc.get('file_name', '')} - {doc.get('file_type', '')}"
                    elif activity.get('status_change'):
                        sc = activity['status_change']
                        details = f"{sc.get('from_status', '')} -> {sc.get('to_status', '')}"
                    
                    writer.writerow([
                        activity['timestamp'],
                        activity['type'],
                        activity['user_id'],
                        activity['description'],
                        details
                    ])
                
                csv_content = output.getvalue()
                output.close()
                
                from flask import make_response
                response = make_response(csv_content)
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename="workspace_{workspace_id}_activity.csv"'
                return response
            
            return jsonify({
                'success': True,
                'activities': formatted_activities,
                'raw_activities': activities  # Include raw activities for modal display
            }), 200
            
        except Exception as e:
            debug_print(f"Error getting workspace activity: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Failed to retrieve workspace activity'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/take-ownership', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_admin_take_workspace_ownership(workspace_id):
        """
        Create an approval request for admin to take ownership of a public workspace.
        Requires approval from workspace owner or another admin.
        
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
            
            # Validate workspace exists
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Workspace not found'}), 404
            
            # Get old owner info
            old_owner = workspace.get('owner', {})
            if isinstance(old_owner, dict):
                old_owner_id = old_owner.get('userId')
                old_owner_email = old_owner.get('email')
            else:
                old_owner_id = old_owner
                old_owner_email = 'unknown'
            
            # Create approval request (use group_id parameter as partition key for workspace)
            approval = create_approval_request(
                request_type=TYPE_TAKE_OWNERSHIP,
                group_id=workspace_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'old_owner_id': old_owner_id,
                    'old_owner_email': old_owner_email,
                    'entity_type': 'workspace'
                }
            )
            
            # Log event
            log_event("[ControlCenter] Take Workspace Ownership Request Created", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Ownership transfer request created and pending approval',
                'approval_id': approval['id'],
                'requires_approval': True,
                'status': 'pending'
            }), 201
            
        except Exception as e:
            debug_print(f"Error creating take workspace ownership request: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/ownership', methods=['PUT'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_update_public_workspace_ownership(workspace_id):
        """
        Create an approval request to transfer public workspace ownership to another member.
        Requires approval from workspace owner or another admin.
        
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
            
            # Get the workspace
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Workspace not found'}), 404
            
            # Get new owner user details
            try:
                new_owner_user = cosmos_user_settings_container.read_item(
                    item=new_owner_user_id,
                    partition_key=new_owner_user_id
                )
                new_owner_email = new_owner_user.get('email', 'unknown')
                new_owner_name = new_owner_user.get('display_name', new_owner_email)
            except:
                return jsonify({'error': 'New owner user not found'}), 404
            
            # Check if new owner is a member of the workspace
            is_member = False
            current_owner = workspace.get('owner', {})
            if isinstance(current_owner, dict):
                if current_owner.get('userId') == new_owner_user_id:
                    is_member = True
            elif current_owner == new_owner_user_id:
                is_member = True
            
            # Check admins
            for admin in workspace.get('admins', []):
                admin_id = admin.get('userId') if isinstance(admin, dict) else admin
                if admin_id == new_owner_user_id:
                    is_member = True
                    break
            
            # Check documentManagers
            if not is_member:
                for dm in workspace.get('documentManagers', []):
                    dm_id = dm.get('userId') if isinstance(dm, dict) else dm
                    if dm_id == new_owner_user_id:
                        is_member = True
                        break
            
            if not is_member:
                return jsonify({'error': 'Selected user is not a member of this workspace'}), 400
            
            # Get old owner info
            old_owner_id = None
            old_owner_email = None
            if isinstance(current_owner, dict):
                old_owner_id = current_owner.get('userId')
                old_owner_email = current_owner.get('email')
            else:
                old_owner_id = current_owner
            
            # Create approval request (use group_id parameter as partition key for workspace)
            approval = create_approval_request(
                request_type=TYPE_TRANSFER_OWNERSHIP,
                group_id=workspace_id,
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'new_owner_id': new_owner_user_id,
                    'new_owner_email': new_owner_email,
                    'new_owner_name': new_owner_name,
                    'old_owner_id': old_owner_id,
                    'old_owner_email': old_owner_email,
                    'entity_type': 'workspace'
                }
            )
            
            # Log event
            log_event("[ControlCenter] Transfer Workspace Ownership Request Created", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
                "new_owner": new_owner_email,
                "old_owner_id": old_owner_id,
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'message': 'Ownership transfer approval request created',
                'approval_id': approval['id'],
                'requires_approval': True
            }), 201
            
        except Exception as e:
            debug_print(f"Error creating workspace ownership transfer request: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Failed to create ownership transfer request'}), 500


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>/documents', methods=['DELETE'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_delete_public_workspace_documents_admin(workspace_id):
        """
        Create an approval request to delete all documents in a public workspace.
        Requires approval from workspace owner or another admin.
        
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
            
            # Validate workspace exists
            try:
                workspace = cosmos_public_workspaces_container.read_item(item=workspace_id, partition_key=workspace_id)
            except:
                return jsonify({'error': 'Public workspace not found'}), 404
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_DELETE_DOCUMENTS,
                group_id=workspace_id,  # Use workspace_id as group_id for approval system
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'workspace_name': workspace.get('name'),
                    'entity_type': 'workspace'
                }
            )
            
            # Log event
            log_event("[ControlCenter] Delete Public Workspace Documents Request Created", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
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


    @app.route('/api/admin/control-center/public-workspaces/<workspace_id>', methods=['DELETE'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_delete_public_workspace_admin(workspace_id):
        """
        Create an approval request to delete an entire public workspace.
        Requires approval from workspace owner or another admin.
        
        Body:
            reason (str): Explanation for deleting the workspace (required)
        """
        try:
            data = request.get_json() or {}
            reason = data.get('reason', '').strip()
            
            if not reason:
                return jsonify({'error': 'Reason is required for workspace deletion'}), 400
            
            admin_user = session.get('user', {})
            admin_user_id = admin_user.get('oid') or admin_user.get('sub')
            admin_email = admin_user.get('preferred_username', admin_user.get('email', 'unknown'))
            admin_display_name = admin_user.get('name', admin_email)
            
            # Validate workspace exists
            try:
                workspace = cosmos_public_workspaces_container.read_item(
                    item=workspace_id,
                    partition_key=workspace_id
                )
            except:
                return jsonify({'error': 'Public workspace not found'}), 404
            
            # Create approval request
            approval = create_approval_request(
                request_type=TYPE_DELETE_GROUP,  # Reuse TYPE_DELETE_GROUP for workspace deletion
                group_id=workspace_id,  # Use workspace_id as group_id for approval system
                requester_id=admin_user_id,
                requester_email=admin_email,
                requester_name=admin_display_name,
                reason=reason,
                metadata={
                    'workspace_name': workspace.get('name'),
                    'entity_type': 'workspace'
                }
            )
            
            # Log event
            log_event("[ControlCenter] Delete Public Workspace Request Created", {
                "admin_user": admin_email,
                "workspace_id": workspace_id,
                "workspace_name": workspace.get('name'),
                "approval_id": approval['id'],
                "reason": reason
            })
            
            return jsonify({
                'success': True,
                'message': 'Workspace deletion request created and pending approval',
                'approval_id': approval['id'],
                'status': 'pending'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating workspace deletion request: {e}")
            return jsonify({'error': str(e)}), 500

