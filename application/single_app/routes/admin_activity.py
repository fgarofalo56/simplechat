# admin_activity.py
# Activity trends, data refresh, migration, and activity log admin endpoints.
# Extracted from route_backend_control_center.py - Phase 4 God File Decomposition.

from config import *
from functions_authentication import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from services.admin_metrics_service import (
    enhance_user_with_activity,
    enhance_public_workspace_with_activity,
    enhance_group_with_activity,
    get_activity_trends_data,
    get_raw_activity_trends_data,
)
from swagger_wrapper import swagger_route, get_auth_security
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print


def register_admin_activity_routes(app):
    # Activity Trends API
    @app.route('/api/admin/control-center/activity-trends', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('dashboard')
    def api_get_activity_trends():
        """
        Get activity trends data for the control center dashboard.
        Returns aggregated activity data from various containers.
        """
        try:
            # Check if custom start_date and end_date are provided
            custom_start = request.args.get('start_date')
            custom_end = request.args.get('end_date')
            
            if custom_start and custom_end:
                # Use custom date range
                try:
                    start_date = datetime.fromisoformat(custom_start).replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = datetime.fromisoformat(custom_end).replace(hour=23, minute=59, second=59, microsecond=999999)
                    days = (end_date - start_date).days + 1
                    debug_print(f"🔍 [Activity Trends API] Custom date range: {start_date} to {end_date} ({days} days)")
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD format.'}), 400
            else:
                # Use days parameter (default behavior)
                days = int(request.args.get('days', 7))
                # Set end_date to end of current day to include all of today's records
                end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
                debug_print(f"🔍 [Activity Trends API] Request for {days} days: {start_date} to {end_date}")
            
            # Get activity data
            activity_data = get_activity_trends_data(start_date, end_date)
            
            debug_print(f"🔍 [Activity Trends API] Returning data: {activity_data}")
            
            return jsonify({
                'success': True,
                'activity_data': activity_data,
                'period': f"{days} days",
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            })
            
        except Exception as e:
            debug_print(f"Error getting activity trends: {e}")
            debug_print(f"❌ [Activity Trends API] Error: {e}")
            return jsonify({'error': 'Failed to retrieve activity trends'}), 500



    @app.route('/api/admin/control-center/activity-trends/export', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('dashboard')
    def api_export_activity_trends():
        """
        Export activity trends raw data as CSV file based on selected charts and date range.
        Returns detailed records with user information instead of aggregated counts.
        """
        try:
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Starting CSV export process")
            data = request.get_json()
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Request data: {data}")            # Parse request parameters
            charts = data.get('charts', ['logins', 'chats', 'documents'])  # Default to all charts
            time_window = data.get('time_window', '30')  # Default to 30 days
            start_date = data.get('start_date')  # For custom range
            end_date = data.get('end_date')  # For custom range
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Parsed params - charts: {charts}, time_window: {time_window}, start_date: {start_date}, end_date: {end_date}")            # Determine date range
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Determining date range")
            if time_window == 'custom' and start_date and end_date:
                try:
                    debug_print("🔍 [ACTIVITY TRENDS DEBUG] Processing custom dates: {start_date} to {end_date}")
                    start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00') if 'Z' in start_date else start_date)
                    end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00') if 'Z' in end_date else end_date)
                    end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                    debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Custom date objects created: {start_date_obj} to {end_date_obj}")
                except ValueError as ve:
                    debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Date parsing error: {ve}")
                    return jsonify({'error': 'Invalid date format'}), 400
            else:
                # Use predefined ranges
                days = int(time_window) if time_window.isdigit() else 30
                end_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                start_date_obj = end_date_obj - timedelta(days=days-1)
                debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Predefined range: {days} days, from {start_date_obj} to {end_date_obj}")
            
            # Get raw activity data using new function
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Calling get_raw_activity_trends_data")
            raw_data = get_raw_activity_trends_data(
                start_date_obj,
                end_date_obj,
                charts
            )
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Raw data retrieved: {len(raw_data) if raw_data else 0} chart types")
            
            # Generate CSV content with all data types
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write data for each chart type
            debug_print(f"🔍 [CSV DEBUG] Processing {len(charts)} chart types: {charts}")
            for chart_type in charts:
                debug_print(f"🔍 [CSV DEBUG] Processing chart type: {chart_type}")
                if chart_type in raw_data and raw_data[chart_type]:
                    debug_print(f"🔍 [CSV DEBUG] Found {len(raw_data[chart_type])} records for {chart_type}")
                    # Add section header
                    writer.writerow([])  # Empty row for separation
                    section_header = f"=== {chart_type.upper()} DATA ==="
                    debug_print(f"🔍 [CSV DEBUG] Writing section header: {section_header}")
                    writer.writerow([section_header])
                    
                    # Write headers and data based on chart type
                    if chart_type == 'logins':
                        debug_print(f"🔍 [CSV DEBUG] Writing login headers for {chart_type}")
                        writer.writerow(['Display Name', 'Email', 'User ID', 'Login Time'])
                        record_count = 0
                        for record in raw_data[chart_type]:
                            record_count += 1
                            if record_count <= 3:  # Debug first 3 records
                                debug_print(f"🔍 [CSV DEBUG] Login record {record_count} structure: {list(record.keys())}")
                                debug_print(f"🔍 [CSV DEBUG] Login record {record_count} data: {record}")
                            writer.writerow([
                                record.get('display_name', ''),
                                record.get('email', ''),
                                record.get('user_id', ''),
                                record.get('login_time', '')
                            ])
                        debug_print(f"🔍 [CSV DEBUG] Finished writing {record_count} login records")
                    
                    elif chart_type in ['documents', 'personal_documents', 'group_documents', 'public_documents']:
                        # Handle all document types with same structure
                        debug_print(f"🔍 [CSV DEBUG] Writing document headers for {chart_type}")
                        writer.writerow([
                            'Display Name', 'Email', 'User ID', 'Document ID', 'Document Filename', 
                            'Document Title', 'Document Page Count', 'Document Size in AI Search', 
                            'Document Size in Storage Account', 'Upload Date', 'Document Type'
                        ])
                        record_count = 0
                        for record in raw_data[chart_type]:
                            record_count += 1
                            if record_count <= 3:  # Log first 3 records for debugging
                                debug_print(f"🔍 [CSV DEBUG] Writing {chart_type} record {record_count}: {record.get('filename', 'No filename')}")
                            writer.writerow([
                                record.get('display_name', ''),
                                record.get('email', ''),
                                record.get('user_id', ''),
                                record.get('document_id', ''),
                                record.get('filename', ''),
                                record.get('title', ''),
                                record.get('page_count', ''),
                                record.get('ai_search_size', ''),
                                record.get('storage_account_size', ''),
                                record.get('upload_date', ''),
                                record.get('document_type', chart_type.replace('_documents', '').title())
                            ])
                        debug_print(f"🔍 [CSV DEBUG] Finished writing {record_count} records for {chart_type}")
                    
                    elif chart_type == 'chats':
                        debug_print(f"🔍 [CSV DEBUG] Writing chat headers for {chart_type}")
                        writer.writerow([
                            'Display Name', 'Email', 'User ID', 'Chat ID', 'Chat Title', 
                            'Number of Messages', 'Total Size (characters)', 'Created Date'
                        ])
                        record_count = 0
                        for record in raw_data[chart_type]:
                            record_count += 1
                            if record_count <= 3:  # Debug first 3 records
                                debug_print(f"🔍 [CSV DEBUG] Chat record {record_count} structure: {list(record.keys())}")
                                debug_print(f"🔍 [CSV DEBUG] Chat record {record_count} data: {record}")
                            writer.writerow([
                                record.get('display_name', ''),
                                record.get('email', ''),
                                record.get('user_id', ''),
                                record.get('chat_id', ''),
                                record.get('chat_title', ''),
                                record.get('message_count', ''),
                                record.get('total_size', ''),
                                record.get('created_date', '')
                            ])
                        debug_print(f"🔍 [CSV DEBUG] Finished writing {record_count} chat records")
                    
                    elif chart_type == 'tokens':
                        debug_print(f"🔍 [CSV DEBUG] Writing token usage headers for {chart_type}")
                        writer.writerow([
                            'Display Name', 'Email', 'User ID', 'Token Type', 'Model Name', 
                            'Prompt Tokens', 'Completion Tokens', 'Total Tokens', 'Timestamp'
                        ])
                        record_count = 0
                        for record in raw_data[chart_type]:
                            record_count += 1
                            if record_count <= 3:  # Debug first 3 records
                                debug_print(f"🔍 [CSV DEBUG] Token record {record_count} structure: {list(record.keys())}")
                                debug_print(f"🔍 [CSV DEBUG] Token record {record_count} data: {record}")
                            writer.writerow([
                                record.get('display_name', ''),
                                record.get('email', ''),
                                record.get('user_id', ''),
                                record.get('token_type', ''),
                                record.get('model_name', ''),
                                record.get('prompt_tokens', ''),
                                record.get('completion_tokens', ''),
                                record.get('total_tokens', ''),
                                record.get('timestamp', '')
                            ])
                        debug_print(f"🔍 [CSV DEBUG] Finished writing {record_count} token usage records")
                else:
                    debug_print(f"🔍 [CSV DEBUG] No data found for {chart_type} - available keys: {list(raw_data.keys()) if raw_data else 'None'}")
                    
            # Add final debug info
            debug_print(f"🔍 [CSV DEBUG] Finished processing all chart types. Raw data summary:")
            for key, value in raw_data.items():
                if isinstance(value, list):
                    debug_print(f"🔍 [CSV DEBUG] - {key}: {len(value)} records")
                else:
                    debug_print(f"🔍 [CSV DEBUG] - {key}: {type(value)} - {value}")
            
            csv_content = output.getvalue()
            debug_print(f"🔍 [CSV DEBUG] Generated CSV content length: {len(csv_content)} characters")
            debug_print(f"🔍 [CSV DEBUG] CSV content preview (first 500 chars): {csv_content[:500]}")
            output.close()
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"activity_trends_raw_export_{timestamp}.csv"
            
            # Return CSV as downloadable response
            from flask import make_response
            response = make_response(csv_content)
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            debug_print(f"Error exporting activity trends: {e}")
            return jsonify({'error': 'Failed to export data'}), 500

    @app.route('/api/admin/control-center/activity-trends/chat', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('dashboard')
    def api_chat_activity_trends():
        """
        Create a new chat conversation with activity trends data as CSV message.
        """
        try:
            data = request.get_json()
            
            # Parse request parameters
            charts = data.get('charts', ['logins', 'chats', 'documents'])  # Default to all charts
            time_window = data.get('time_window', '30')  # Default to 30 days
            start_date = data.get('start_date')  # For custom range
            end_date = data.get('end_date')  # For custom range
            
            # Determine date range
            if time_window == 'custom' and start_date and end_date:
                try:
                    start_date_obj = datetime.fromisoformat(start_date.replace('Z', '+00:00') if 'Z' in start_date else start_date)
                    end_date_obj = datetime.fromisoformat(end_date.replace('Z', '+00:00') if 'Z' in end_date else end_date)
                    end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                except ValueError:
                    return jsonify({'error': 'Invalid date format'}), 400
            else:
                # Use predefined ranges
                days = int(time_window) if time_window.isdigit() else 30
                end_date_obj = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                start_date_obj = end_date_obj - timedelta(days=days-1)
            
            # Get activity data using existing function
            activity_data = get_activity_trends_data(
                start_date_obj.strftime('%Y-%m-%d'),
                end_date_obj.strftime('%Y-%m-%d')
            )
            
            # Prepare CSV data
            csv_rows = []
            csv_rows.append(['Date', 'Chart Type', 'Activity Count'])
            
            # Process each requested chart type
            for chart_type in charts:
                if chart_type in activity_data:
                    chart_data = activity_data[chart_type]
                    # Sort dates for consistent output
                    sorted_dates = sorted(chart_data.keys())
                    
                    for date_key in sorted_dates:
                        count = chart_data[date_key]
                        chart_display_name = {
                            'logins': 'Logins',
                            'chats': 'Chats', 
                            'documents': 'Documents',
                            'personal_documents': 'Personal Documents',
                            'group_documents': 'Group Documents',
                            'public_documents': 'Public Documents'
                        }.get(chart_type, chart_type.title())
                        
                        csv_rows.append([date_key, chart_display_name, count])
            
            # Generate CSV content
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(csv_rows)
            csv_content = output.getvalue()
            output.close()
            
            # Get current user info
            user_id = session.get('user_id')
            user_email = session.get('email')
            user_display_name = session.get('display_name', user_email)
            
            if not user_id:
                return jsonify({'error': 'User not authenticated'}), 401
            
            # Create new conversation
            conversation_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Generate descriptive title with date range
            if time_window == 'custom':
                date_range = f"{start_date} to {end_date}"
            else:
                date_range = f"Last {time_window} Days"
            
            charts_text = ", ".join([c.title() for c in charts])
            conversation_title = f"Activity Trends - {charts_text} ({date_range})"
            
            # Create conversation document
            conversation_doc = {
                "id": conversation_id,
                "title": conversation_title,
                "user_id": user_id,
                "user_email": user_email,
                "user_display_name": user_display_name,
                "created": timestamp,
                "last_updated": timestamp,
                "messages": [],
                "system_message": "You are analyzing activity trends data from a control center dashboard. The user has provided activity data as a CSV file. Please analyze the data and provide insights about user activity patterns, trends, and any notable observations.",
                "message_count": 0,
                "settings": {
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            }
            
            # Create the initial message with CSV data (simulate file upload)
            message_id = str(uuid.uuid4())
            csv_filename = f"activity_trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Create message with file attachment structure
            initial_message = {
                "id": message_id,
                "role": "user",
                "content": f"Please analyze this activity trends data from our system dashboard. The data covers {date_range} and includes {charts_text} activity.",
                "timestamp": timestamp,
                "files": [{
                    "name": csv_filename,
                    "type": "text/csv",
                    "size": len(csv_content.encode('utf-8')),
                    "content": csv_content,
                    "id": str(uuid.uuid4())
                }]
            }
            
            conversation_doc["messages"].append(initial_message)
            conversation_doc["message_count"] = 1
            
            # Save conversation to database
            cosmos_conversations_container.create_item(conversation_doc)
            
            # Log the activity
            log_event("[ControlCenter] Activity Trends Chat Created", {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "charts": charts,
                "time_window": time_window,
                "date_range": date_range
            })
            
            return jsonify({
                'success': True,
                'conversation_id': conversation_id,
                'conversation_title': conversation_title,
                'redirect_url': f'/chat/{conversation_id}'
            }), 200
            
        except Exception as e:
            debug_print(f"Error creating activity trends chat: {e}")
            return jsonify({'error': 'Failed to create chat conversation'}), 500
    
    # Data Refresh API
    @app.route('/api/admin/control-center/refresh', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_refresh_control_center_data():
        """
        Refresh all Control Center metrics data and update admin timestamp.
        This will recalculate all user metrics and cache them in user settings.
        """
        try:
            debug_print("🔄 [REFRESH DEBUG] Starting Control Center data refresh...")
            debug_print("Starting Control Center data refresh...")
            
            # Check if request has specific user_id
            from flask import request
            try:
                request_data = request.get_json(force=True) or {}
            except:
                # Handle case where no JSON body is sent
                request_data = {}
                
            specific_user_id = request_data.get('user_id')
            force_refresh = request_data.get('force_refresh', False)
            
            debug_print(f"🔄 [REFRESH DEBUG] Request data: user_id={specific_user_id}, force_refresh={force_refresh}")
            
            # Get all users to refresh their metrics
            debug_print("🔄 [REFRESH DEBUG] Querying all users...")
            users_query = "SELECT c.id, c.email, c.display_name, c.lastUpdated, c.settings FROM c"
            all_users = list(cosmos_user_settings_container.query_items(
                query=users_query,
                enable_cross_partition_query=True
            ))
            debug_print(f"🔄 [REFRESH DEBUG] Found {len(all_users)} users to process")
            
            refreshed_count = 0
            failed_count = 0
            
            # Refresh metrics for each user
            debug_print("🔄 [REFRESH DEBUG] Starting user refresh loop...")
            for user in all_users:
                try:
                    user_id = user.get('id')
                    debug_print(f"🔄 [REFRESH DEBUG] Processing user {user_id}")
                    
                    # Force refresh of metrics for this user
                    enhanced_user = enhance_user_with_activity(user, force_refresh=True)
                    refreshed_count += 1
                    
                    debug_print(f"✅ [REFRESH DEBUG] Successfully refreshed user {user_id}")
                    debug_print(f"Refreshed metrics for user {user_id}")
                except Exception as user_error:
                    failed_count += 1
                    debug_print(f"❌ [REFRESH DEBUG] Failed to refresh user {user.get('id')}: {user_error}")
                    debug_print(f"❌ [REFRESH DEBUG] User error traceback:")
                    import traceback
                    debug_print(traceback.format_exc())
                    debug_print(f"Failed to refresh metrics for user {user.get('id')}: {user_error}")
            
            debug_print(f"🔄 [REFRESH DEBUG] User refresh loop completed. Refreshed: {refreshed_count}, Failed: {failed_count}")
            
            # Refresh metrics for all groups
            debug_print("🔄 [REFRESH DEBUG] Starting group refresh...")
            groups_refreshed_count = 0
            groups_failed_count = 0
            
            try:
                groups_query = "SELECT * FROM c"
                all_groups = list(cosmos_groups_container.query_items(
                    query=groups_query,
                    enable_cross_partition_query=True
                ))
                debug_print(f"🔄 [REFRESH DEBUG] Found {len(all_groups)} groups to process")
                
                # Refresh metrics for each group
                for group in all_groups:
                    try:
                        group_id = group.get('id')
                        debug_print(f"🔄 [REFRESH DEBUG] Processing group {group_id}")
                        
                        # Force refresh of metrics for this group
                        enhanced_group = enhance_group_with_activity(group, force_refresh=True)
                        groups_refreshed_count += 1
                        
                        debug_print(f"✅ [REFRESH DEBUG] Successfully refreshed group {group_id}")
                        debug_print(f"Refreshed metrics for group {group_id}")
                    except Exception as group_error:
                        groups_failed_count += 1
                        debug_print(f"❌ [REFRESH DEBUG] Failed to refresh group {group.get('id')}: {group_error}")
                        debug_print(f"❌ [REFRESH DEBUG] Group error traceback:")
                        import traceback
                        debug_print(traceback.format_exc())
                        debug_print(f"Failed to refresh metrics for group {group.get('id')}: {group_error}")
                        
            except Exception as groups_error:
                debug_print(f"❌ [REFRESH DEBUG] Error querying groups: {groups_error}")
                debug_print(f"Error querying groups for refresh: {groups_error}")
            
            debug_print(f"🔄 [REFRESH DEBUG] Group refresh loop completed. Refreshed: {groups_refreshed_count}, Failed: {groups_failed_count}")
            
            # Update admin settings with refresh timestamp
            debug_print("🔄 [REFRESH DEBUG] Updating admin settings...")
            try:
                from functions_settings import get_settings, update_settings
                
                settings = get_settings()
                if settings:
                    settings['control_center_last_refresh'] = datetime.now(timezone.utc).isoformat()
                    update_success = update_settings(settings)
                    
                    if not update_success:
                        debug_print("⚠️ [REFRESH DEBUG] Failed to update admin settings")
                        debug_print("Failed to update admin settings with refresh timestamp")
                    else:
                        debug_print("✅ [REFRESH DEBUG] Admin settings updated successfully")
                        debug_print("Updated admin settings with refresh timestamp")
                else:
                    debug_print("⚠️ [REFRESH DEBUG] Could not get admin settings")
                    
            except Exception as admin_error:
                debug_print(f"❌ [REFRESH DEBUG] Admin settings update failed: {admin_error}")
                debug_print(f"Error updating admin settings: {admin_error}")
            
            debug_print(f"🎉 [REFRESH DEBUG] Refresh completed! Users - Refreshed: {refreshed_count}, Failed: {failed_count}. Groups - Refreshed: {groups_refreshed_count}, Failed: {groups_failed_count}")
            debug_print(f"Control Center data refresh completed. Users: {refreshed_count} refreshed, {failed_count} failed. Groups: {groups_refreshed_count} refreshed, {groups_failed_count} failed")
            
            return jsonify({
                'success': True,
                'message': 'Control Center data refreshed successfully',
                'refreshed_users': refreshed_count,
                'failed_users': failed_count,
                'refreshed_groups': groups_refreshed_count,
                'failed_groups': groups_failed_count,
                'refresh_timestamp': datetime.now(timezone.utc).isoformat()
            }), 200
            
        except Exception as e:
            debug_print(f"💥 [REFRESH DEBUG] MAJOR ERROR in refresh endpoint: {e}")
            debug_print("💥 [REFRESH DEBUG] Full traceback:")
            import traceback
            debug_print(traceback.format_exc())
            debug_print(f"Error refreshing Control Center data: {e}")
            return jsonify({'error': 'Failed to refresh data'}), 500
    
    # Get refresh status API
    @app.route('/api/admin/control-center/refresh-status', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')  
    def api_get_refresh_status():
        """
        Get the last refresh timestamp for Control Center data.
        """
        try:
            from functions_settings import get_settings
            
            settings = get_settings()
            last_refresh = settings.get('control_center_last_refresh')
            
            return jsonify({
                'last_refresh': last_refresh,
                'last_refresh_formatted': None if not last_refresh else datetime.fromisoformat(last_refresh.replace('Z', '+00:00') if 'Z' in last_refresh else last_refresh).strftime('%m/%d/%Y %I:%M %p UTC')
            }), 200
            
        except Exception as e:
            debug_print(f"Error getting refresh status: {e}")
            return jsonify({'error': 'Failed to get refresh status'}), 500
    
    # Activity Log Migration APIs
    @app.route('/api/admin/control-center/migrate/status', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_migration_status():
        """
        Check if there are conversations and documents that need to be migrated to activity logs.
        Returns counts of records without the 'added_to_activity_log' flag.
        """
        try:
            migration_status = {
                'conversations_without_logs': 0,
                'personal_documents_without_logs': 0,
                'group_documents_without_logs': 0,
                'public_documents_without_logs': 0,
                'total_documents_without_logs': 0,
                'migration_needed': False,
                'estimated_total_records': 0
            }
            
            # Check conversations without the flag
            try:
                conversations_query = """
                    SELECT VALUE COUNT(1) 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                conversations_result = list(cosmos_conversations_container.query_items(
                    query=conversations_query,
                    enable_cross_partition_query=True
                ))
                migration_status['conversations_without_logs'] = conversations_result[0] if conversations_result else 0
            except Exception as e:
                debug_print(f"Error checking conversations migration status: {e}")
            
            # Check personal documents without the flag
            try:
                personal_docs_query = """
                    SELECT VALUE COUNT(1) 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                personal_docs_result = list(cosmos_user_documents_container.query_items(
                    query=personal_docs_query,
                    enable_cross_partition_query=True
                ))
                migration_status['personal_documents_without_logs'] = personal_docs_result[0] if personal_docs_result else 0
            except Exception as e:
                debug_print(f"Error checking personal documents migration status: {e}")
            
            # Check group documents without the flag
            try:
                group_docs_query = """
                    SELECT VALUE COUNT(1) 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                group_docs_result = list(cosmos_group_documents_container.query_items(
                    query=group_docs_query,
                    enable_cross_partition_query=True
                ))
                migration_status['group_documents_without_logs'] = group_docs_result[0] if group_docs_result else 0
            except Exception as e:
                debug_print(f"Error checking group documents migration status: {e}")
            
            # Check public documents without the flag
            try:
                public_docs_query = """
                    SELECT VALUE COUNT(1) 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                public_docs_result = list(cosmos_public_documents_container.query_items(
                    query=public_docs_query,
                    enable_cross_partition_query=True
                ))
                migration_status['public_documents_without_logs'] = public_docs_result[0] if public_docs_result else 0
            except Exception as e:
                debug_print(f"Error checking public documents migration status: {e}")
            
            # Calculate totals
            migration_status['total_documents_without_logs'] = (
                migration_status['personal_documents_without_logs'] +
                migration_status['group_documents_without_logs'] +
                migration_status['public_documents_without_logs']
            )
            
            migration_status['estimated_total_records'] = (
                migration_status['conversations_without_logs'] +
                migration_status['total_documents_without_logs']
            )
            
            migration_status['migration_needed'] = migration_status['estimated_total_records'] > 0
            
            return jsonify(migration_status), 200
            
        except Exception as e:
            debug_print(f"Error getting migration status: {e}")
            return jsonify({'error': 'Failed to get migration status'}), 500
    
    @app.route('/api/admin/control-center/migrate/all', methods=['POST'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_migrate_to_activity_logs():
        """
        Migrate all conversations and documents without activity logs.
        This adds activity log records and sets the 'added_to_activity_log' flag.
        
        WARNING: This may take a while for large datasets and could impact performance.
        Recommended to run during off-peak hours.
        """
        try:
            from functions_activity_logging import log_conversation_creation, log_document_creation_transaction
            
            results = {
                'conversations_migrated': 0,
                'conversations_failed': 0,
                'personal_documents_migrated': 0,
                'personal_documents_failed': 0,
                'group_documents_migrated': 0,
                'group_documents_failed': 0,
                'public_documents_migrated': 0,
                'public_documents_failed': 0,
                'total_migrated': 0,
                'total_failed': 0,
                'errors': []
            }
            
            # Migrate conversations
            debug_print("Starting conversation migration...")
            try:
                conversations_query = """
                    SELECT * 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                conversations = list(cosmos_conversations_container.query_items(
                    query=conversations_query,
                    enable_cross_partition_query=True
                ))
                
                debug_print(f"Found {len(conversations)} conversations to migrate")
                
                for conv in conversations:
                    try:
                        # Create activity log directly to preserve original timestamp
                        activity_log = {
                            'id': str(uuid.uuid4()),
                            'activity_type': 'conversation_creation',
                            'user_id': conv.get('user_id'),
                            'timestamp': conv.get('created_at') or conv.get('last_updated') or datetime.utcnow().isoformat(),
                            'created_at': conv.get('created_at') or conv.get('last_updated') or datetime.utcnow().isoformat(),
                            'conversation': {
                                'conversation_id': conv.get('id'),
                                'title': conv.get('title', 'Untitled'),
                                'context': conv.get('context', []),
                                'tags': conv.get('tags', [])
                            },
                            'workspace_type': 'personal',
                            'workspace_context': {}
                        }
                        
                        # Save to activity logs container
                        cosmos_activity_logs_container.upsert_item(activity_log)
                        
                        # Add flag to conversation
                        conv['added_to_activity_log'] = True
                        cosmos_conversations_container.upsert_item(conv)
                        
                        results['conversations_migrated'] += 1
                        
                    except Exception as conv_error:
                        results['conversations_failed'] += 1
                        error_msg = f"Failed to migrate conversation {conv.get('id')}: {str(conv_error)}"
                        debug_print(error_msg)
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during conversation migration: {str(e)}"
                debug_print(error_msg)
                results['errors'].append(error_msg)
            
            # Migrate personal documents
            debug_print("Starting personal documents migration...")
            try:
                personal_docs_query = """
                    SELECT * 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                personal_docs = list(cosmos_user_documents_container.query_items(
                    query=personal_docs_query,
                    enable_cross_partition_query=True
                ))
                
                for doc in personal_docs:
                    try:
                        # Create activity log directly to preserve original timestamp
                        activity_log = {
                            'id': str(uuid.uuid4()),
                            'user_id': doc.get('user_id'),
                            'activity_type': 'document_creation',
                            'workspace_type': 'personal',
                            'timestamp': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'created_at': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'document': {
                                'document_id': doc.get('id'),
                                'file_name': doc.get('file_name', 'Unknown'),
                                'file_type': doc.get('file_type', 'unknown'),
                                'file_size_bytes': doc.get('file_size', 0),
                                'page_count': doc.get('number_of_pages', 0),
                                'version': doc.get('version', 1)
                            },
                            'embedding_usage': {
                                'total_tokens': doc.get('embedding_tokens', 0),
                                'model_deployment_name': doc.get('embedding_model_deployment_name', 'unknown')
                            },
                            'document_metadata': {
                                'author': doc.get('author'),
                                'title': doc.get('title'),
                                'subject': doc.get('subject'),
                                'publication_date': doc.get('publication_date'),
                                'keywords': doc.get('keywords', []),
                                'abstract': doc.get('abstract')
                            },
                            'workspace_context': {}
                        }
                        
                        # Save to activity logs container
                        cosmos_activity_logs_container.upsert_item(activity_log)
                        
                        # Add flag to document
                        doc['added_to_activity_log'] = True
                        cosmos_user_documents_container.upsert_item(doc)
                        
                        results['personal_documents_migrated'] += 1
                        
                    except Exception as doc_error:
                        results['personal_documents_failed'] += 1
                        error_msg = f"Failed to migrate personal document {doc.get('id')}: {str(doc_error)}"
                        debug_print(error_msg)
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during personal documents migration: {str(e)}"
                debug_print(error_msg)
                results['errors'].append(error_msg)
            
            # Migrate group documents
            debug_print("Starting group documents migration...")
            try:
                group_docs_query = """
                    SELECT * 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                group_docs = list(cosmos_group_documents_container.query_items(
                    query=group_docs_query,
                    enable_cross_partition_query=True
                ))
                
                for doc in group_docs:
                    try:
                        # Create activity log directly to preserve original timestamp
                        activity_log = {
                            'id': str(uuid.uuid4()),
                            'user_id': doc.get('user_id'),
                            'activity_type': 'document_creation',
                            'workspace_type': 'group',
                            'timestamp': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'created_at': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'document': {
                                'document_id': doc.get('id'),
                                'file_name': doc.get('file_name', 'Unknown'),
                                'file_type': doc.get('file_type', 'unknown'),
                                'file_size_bytes': doc.get('file_size', 0),
                                'page_count': doc.get('number_of_pages', 0),
                                'version': doc.get('version', 1)
                            },
                            'embedding_usage': {
                                'total_tokens': doc.get('embedding_tokens', 0),
                                'model_deployment_name': doc.get('embedding_model_deployment_name', 'unknown')
                            },
                            'document_metadata': {
                                'author': doc.get('author'),
                                'title': doc.get('title'),
                                'subject': doc.get('subject'),
                                'publication_date': doc.get('publication_date'),
                                'keywords': doc.get('keywords', []),
                                'abstract': doc.get('abstract')
                            },
                            'workspace_context': {
                                'group_id': doc.get('group_id')
                            }
                        }
                        
                        # Save to activity logs container
                        cosmos_activity_logs_container.upsert_item(activity_log)
                        
                        # Add flag to document
                        doc['added_to_activity_log'] = True
                        cosmos_group_documents_container.upsert_item(doc)
                        
                        results['group_documents_migrated'] += 1
                        
                    except Exception as doc_error:
                        results['group_documents_failed'] += 1
                        error_msg = f"Failed to migrate group document {doc.get('id')}: {str(doc_error)}"
                        debug_print(error_msg)
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during group documents migration: {str(e)}"
                debug_print(error_msg)
                results['errors'].append(error_msg)
            
            # Migrate public documents
            debug_print("Starting public documents migration...")
            try:
                public_docs_query = """
                    SELECT * 
                    FROM c 
                    WHERE NOT IS_DEFINED(c.added_to_activity_log) OR c.added_to_activity_log = false
                """
                public_docs = list(cosmos_public_documents_container.query_items(
                    query=public_docs_query,
                    enable_cross_partition_query=True
                ))
                
                for doc in public_docs:
                    try:
                        # Create activity log directly to preserve original timestamp
                        activity_log = {
                            'id': str(uuid.uuid4()),
                            'user_id': doc.get('user_id'),
                            'activity_type': 'document_creation',
                            'workspace_type': 'public',
                            'timestamp': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'created_at': doc.get('upload_date') or datetime.utcnow().isoformat(),
                            'document': {
                                'document_id': doc.get('id'),
                                'file_name': doc.get('file_name', 'Unknown'),
                                'file_type': doc.get('file_type', 'unknown'),
                                'file_size_bytes': doc.get('file_size', 0),
                                'page_count': doc.get('number_of_pages', 0),
                                'version': doc.get('version', 1)
                            },
                            'embedding_usage': {
                                'total_tokens': doc.get('embedding_tokens', 0),
                                'model_deployment_name': doc.get('embedding_model_deployment_name', 'unknown')
                            },
                            'document_metadata': {
                                'author': doc.get('author'),
                                'title': doc.get('title'),
                                'subject': doc.get('subject'),
                                'publication_date': doc.get('publication_date'),
                                'keywords': doc.get('keywords', []),
                                'abstract': doc.get('abstract')
                            },
                            'workspace_context': {
                                'public_workspace_id': doc.get('public_workspace_id')
                            }
                        }
                        
                        # Save to activity logs container
                        cosmos_activity_logs_container.upsert_item(activity_log)
                        
                        # Add flag to document
                        doc['added_to_activity_log'] = True
                        cosmos_public_documents_container.upsert_item(doc)
                        
                        results['public_documents_migrated'] += 1
                        
                    except Exception as doc_error:
                        results['public_documents_failed'] += 1
                        error_msg = f"Failed to migrate public document {doc.get('id')}: {str(doc_error)}"
                        debug_print(error_msg)
                        results['errors'].append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error during public documents migration: {str(e)}"
                debug_print(error_msg)
                results['errors'].append(error_msg)
            
            # Calculate totals
            results['total_migrated'] = (
                results['conversations_migrated'] +
                results['personal_documents_migrated'] +
                results['group_documents_migrated'] +
                results['public_documents_migrated']
            )
            
            results['total_failed'] = (
                results['conversations_failed'] +
                results['personal_documents_failed'] +
                results['group_documents_failed'] +
                results['public_documents_failed']
            )
            
            debug_print(f"Migration complete: {results['total_migrated']} migrated, {results['total_failed']} failed")
            
            return jsonify(results), 200
            
        except Exception as e:
            debug_print(f"Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Migration failed: {str(e)}'}), 500

    @app.route('/api/admin/control-center/activity-logs', methods=['GET'])
    @swagger_route(security=get_auth_security())
    @login_required
    @control_center_required('admin')
    def api_get_activity_logs():
        """
        Get paginated and filtered activity logs from cosmos_activity_logs_container.
        Supports search and filtering by activity type.
        """
        try:
            # Get query parameters
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
            search_term = request.args.get('search', '').strip().lower()
            activity_type_filter = request.args.get('activity_type_filter', 'all').strip()
            
            # Build query conditions
            query_conditions = []
            parameters = []
            
            # Filter by activity type if not 'all'
            if activity_type_filter and activity_type_filter != 'all':
                query_conditions.append("c.activity_type = @activity_type")
                parameters.append({"name": "@activity_type", "value": activity_type_filter})
            
            # Build WHERE clause (empty if no conditions)
            where_clause = " WHERE " + " AND ".join(query_conditions) if query_conditions else ""

            # Get total count for pagination
            if query_conditions:
                count_query = "SELECT VALUE COUNT(1) FROM c WHERE " + " AND ".join(query_conditions)
            else:
                count_query = "SELECT VALUE COUNT(1) FROM c"
            total_items_result = list(cosmos_activity_logs_container.query_items(
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
            total_pages = (total_items + safe_per_page - 1) // safe_per_page if total_items > 0 else 1

            # Get paginated results
            if query_conditions:
                logs_query = f"""
                    SELECT * FROM c WHERE {" AND ".join(query_conditions)}
                    ORDER BY c.timestamp DESC
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            else:
                logs_query = f"""
                    SELECT * FROM c
                    ORDER BY c.timestamp DESC
                    OFFSET {offset} LIMIT {safe_per_page}
                """
            
            debug_print(f"Activity logs query: {logs_query}")
            debug_print(f"Query parameters: {parameters}")
            
            logs = list(cosmos_activity_logs_container.query_items(
                query=logs_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Apply search filter in Python (after fetching from Cosmos)
            if search_term:
                filtered_logs = []
                for log in logs:
                    # Search in various fields
                    searchable_text = ' '.join([
                        str(log.get('activity_type', '')),
                        str(log.get('user_id', '')),
                        str(log.get('login_method', '')),
                        str(log.get('conversation', {}).get('title', '')),
                        str(log.get('document', {}).get('file_name', '')),
                        str(log.get('token_type', '')),
                        str(log.get('workspace_type', ''))
                    ]).lower()
                    
                    if search_term in searchable_text:
                        filtered_logs.append(log)
                
                logs = filtered_logs
                # Recalculate total_items for filtered results
                total_items = len(logs)
                total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 1
            
            # Get unique user IDs from logs
            user_ids = set(log.get('user_id') for log in logs if log.get('user_id'))
            
            # Fetch user information for display names/emails
            user_map = {}
            if user_ids:
                for user_id in user_ids:
                    try:
                        user_doc = cosmos_user_settings_container.read_item(
                            item=user_id,
                            partition_key=user_id
                        )
                        user_map[user_id] = {
                            'email': user_doc.get('email', ''),
                            'display_name': user_doc.get('display_name', '')
                        }
                    except:
                        user_map[user_id] = {
                            'email': '',
                            'display_name': ''
                        }
            
            return jsonify({
                'logs': logs,
                'user_map': user_map,
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
            debug_print(f"Error getting activity logs: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Failed to fetch activity logs'}), 500

