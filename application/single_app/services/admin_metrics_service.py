# admin_metrics_service.py
# Activity metrics, user/group/workspace enhancement, and trend aggregation.
# Extracted from route_backend_control_center.py — Phase 4 God File Decomposition.

from config import *
from functions_settings import *
from functions_logging import *
from functions_activity_logging import *
from functions_documents import update_document, delete_document, delete_document_chunks
from datetime import datetime, timedelta, timezone
import json
from functions_debug import debug_print

def enhance_user_with_activity(user, force_refresh=False):
    """
    Enhance user data with activity information and computed fields.
    If force_refresh is False, will try to use cached metrics from user settings.
    """
    try:
        user_id = user.get('id')
        debug_print(f"👤 [USER DEBUG] Processing user {user_id}, force_refresh={force_refresh}")
        
        # Check both user and app settings for enhanced citations
        user_enhanced_citation = user.get('settings', {}).get('enable_enhanced_citation', False)
        from functions_settings import get_settings
        app_settings = get_settings()
        app_enhanced_citations = app_settings.get('enable_enhanced_citations', False) if app_settings else False
        
        debug_print(f"📋 [SETTINGS DEBUG] User enhanced citation: {user_enhanced_citation}")
        debug_print(f"📋 [SETTINGS DEBUG] App enhanced citations: {app_enhanced_citations}")
        debug_print(f"📋 [SETTINGS DEBUG] Will use app setting: {app_enhanced_citations}")
        enhanced = {
            'id': user.get('id'),
            'email': user.get('email', ''),
            'display_name': user.get('display_name', ''),
            'lastUpdated': user.get('lastUpdated'),
            'settings': user.get('settings', {}),
            'profile_image': user.get('settings', {}).get('profileImage'),  # Extract profile image
            'activity': {
                'login_metrics': {
                    'total_logins': 0,
                    'last_login': None
                },
                'chat_metrics': {
                    'last_day_conversations': 0,
                    'total_conversations': 0,
                    'total_messages': 0,
                    'total_content_size': 0  # Based on actual message content length
                },
                'document_metrics': {
                    'personal_workspace_enabled': user.get('settings', {}).get('enable_personal_workspace', False),
                    # enhanced_citation_enabled is NOT stored in user data - frontend gets it from app settings
                    'total_documents': 0,
                    'ai_search_size': 0,  # pages × 80KB  
                    'storage_account_size': 0  # Actual file sizes from storage
                }
            },
            'access_status': 'allow',  # default
            'file_upload_status': 'allow'  # default
        }
        
        # Extract access status
        access_settings = user.get('settings', {}).get('access', {})
        if access_settings.get('status') == 'deny':
            datetime_to_allow = access_settings.get('datetime_to_allow')
            if datetime_to_allow:
                # Check if time-based restriction has expired
                try:
                    allow_time = datetime.fromisoformat(datetime_to_allow.replace('Z', '+00:00') if 'Z' in datetime_to_allow else datetime_to_allow)
                    if datetime.now(timezone.utc) >= allow_time:
                        enhanced['access_status'] = 'allow'  # Expired, should be auto-restored
                    else:
                        enhanced['access_status'] = f"deny_until_{datetime_to_allow}"
                except:
                    enhanced['access_status'] = 'deny'
            else:
                enhanced['access_status'] = 'deny'
        
        # Extract file upload status
        file_upload_settings = user.get('settings', {}).get('file_uploads', {})
        if file_upload_settings.get('status') == 'deny':
            datetime_to_allow = file_upload_settings.get('datetime_to_allow')
            if datetime_to_allow:
                # Check if time-based restriction has expired
                try:
                    allow_time = datetime.fromisoformat(datetime_to_allow.replace('Z', '+00:00') if 'Z' in datetime_to_allow else datetime_to_allow)
                    if datetime.now(timezone.utc) >= allow_time:
                        enhanced['file_upload_status'] = 'allow'  # Expired, should be auto-restored
                    else:
                        enhanced['file_upload_status'] = f"deny_until_{datetime_to_allow}"
                except:
                    enhanced['file_upload_status'] = 'deny'
            else:
                enhanced['file_upload_status'] = 'deny'
                
        # Check for cached metrics if not forcing refresh
        if not force_refresh:
            cached_metrics = user.get('settings', {}).get('metrics')
            if cached_metrics and cached_metrics.get('calculated_at'):
                try:
                    debug_print(f"Using cached metrics for user {user.get('id')}")
                    # Use cached data regardless of age when not forcing refresh
                    if 'login_metrics' in cached_metrics:
                        enhanced['activity']['login_metrics'] = cached_metrics['login_metrics']
                    if 'chat_metrics' in cached_metrics:
                        enhanced['activity']['chat_metrics'] = cached_metrics['chat_metrics']
                    if 'document_metrics' in cached_metrics:
                        # Merge cached document metrics with settings-based flags
                        cached_doc_metrics = cached_metrics['document_metrics'].copy()
                        cached_doc_metrics['personal_workspace_enabled'] = user.get('settings', {}).get('enable_personal_workspace', False)
                        # Do NOT include enhanced_citation_enabled in user data - frontend gets it from app settings
                        enhanced['activity']['document_metrics'] = cached_doc_metrics
                    return enhanced
                except Exception as cache_e:
                    debug_print(f"Error using cached metrics for user {user.get('id')}: {cache_e}")
            
            # If no cached metrics and not forcing refresh, return with default/empty metrics
            # Do NOT include enhanced_citation_enabled in user data - frontend gets it from app settings
            debug_print(f"No cached metrics for user {user.get('id')}, returning default values (use refresh button to calculate)")
            return enhanced
            
        debug_print(f"Force refresh requested - calculating fresh metrics for user {user.get('id')}")
        
        
        # Try to get comprehensive conversation metrics
        try:
            # Get all user conversations with last_updated info
            user_conversations_query = """
                SELECT c.id, c.last_updated FROM c WHERE c.user_id = @user_id
            """
            user_conversations_params = [{"name": "@user_id", "value": user.get('id')}]
            user_conversations = list(cosmos_conversations_container.query_items(
                query=user_conversations_query,
                parameters=user_conversations_params,
                enable_cross_partition_query=True
            ))
            
            # Total conversations count (all time)
            enhanced['activity']['chat_metrics']['total_conversations'] = len(user_conversations)
            
            # Find last day conversation (most recent conversation with latest last_updated)
            last_day_conversation = None
            if user_conversations:
                # Sort by last_updated to get the most recent
                sorted_conversations = sorted(
                    user_conversations, 
                    key=lambda x: x.get('last_updated', ''), 
                    reverse=True
                )
                if sorted_conversations:
                    most_recent_conv = sorted_conversations[0]
                    last_updated = most_recent_conv.get('last_updated')
                    if last_updated:
                        # Parse the date and format as MM/DD/YYYY
                        try:
                            date_obj = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                            last_day_conversation = date_obj.strftime('%m/%d/%Y')
                        except:
                            last_day_conversation = 'Invalid date'
            
            enhanced['activity']['chat_metrics']['last_day_conversation'] = last_day_conversation or 'Never'
            
            # Get message count and total size using two-step query approach
            if user_conversations:
                conversation_ids = [conv['id'] for conv in user_conversations]
                total_messages = 0
                total_message_size = 0
                
                # Process conversations in batches to avoid query limits
                batch_size = 10
                for i in range(0, len(conversation_ids), batch_size):
                    batch_ids = conversation_ids[i:i+batch_size]
                    
                    # Use parameterized query with IN clause for message querying
                    try:
                        # Build the IN parameters for the batch
                        in_params = []
                        param_placeholders = []
                        for j, conv_id in enumerate(batch_ids):
                            param_name = f"@conv_id_{j}"
                            param_placeholders.append(param_name)
                            in_params.append({"name": param_name, "value": conv_id})
                        
                        # Split into separate queries to avoid MultipleAggregates issue
                        # First query: Get message count
                        messages_count_query = f"""
                            SELECT VALUE COUNT(1)
                            FROM m
                            WHERE m.conversation_id IN ({', '.join(param_placeholders)})
                        """
                        
                        count_result = list(cosmos_messages_container.query_items(
                            query=messages_count_query,
                            parameters=in_params,
                            enable_cross_partition_query=True
                        ))
                        
                        batch_messages = count_result[0] if count_result else 0
                        total_messages += batch_messages
                        
                        # Second query: Get message size 
                        messages_size_query = f"""
                            SELECT VALUE SUM(LENGTH(TO_STRING(m)))
                            FROM m
                            WHERE m.conversation_id IN ({', '.join(param_placeholders)})
                        """
                        
                        size_result = list(cosmos_messages_container.query_items(
                            query=messages_size_query,
                            parameters=in_params,
                            enable_cross_partition_query=True
                        ))
                        
                        batch_size = size_result[0] if size_result else 0
                        total_message_size += batch_size or 0
                        
                        debug_print(f"Messages batch {i//batch_size + 1}: {batch_messages} messages, {batch_size or 0} bytes")
                                
                    except Exception as msg_e:
                        debug_print(f"Could not query message sizes for batch {i//batch_size + 1}: {msg_e}")
                        # Try individual conversation queries as fallback
                        for conv_id in batch_ids:
                            try:
                                individual_params = [{"name": "@conv_id", "value": conv_id}]
                                
                                # Individual count query
                                individual_count_query = """
                                    SELECT VALUE COUNT(1)
                                    FROM m
                                    WHERE m.conversation_id = @conv_id
                                """
                                count_result = list(cosmos_messages_container.query_items(
                                    query=individual_count_query,
                                    parameters=individual_params,
                                    enable_cross_partition_query=True
                                ))
                                total_messages += count_result[0] if count_result else 0
                                
                                # Individual size query
                                individual_size_query = """
                                    SELECT VALUE SUM(LENGTH(TO_STRING(m)))
                                    FROM m
                                    WHERE m.conversation_id = @conv_id
                                """
                                size_result = list(cosmos_messages_container.query_items(
                                    query=individual_size_query,
                                    parameters=individual_params,
                                    enable_cross_partition_query=True
                                ))
                                total_message_size += size_result[0] if size_result and size_result[0] else 0
                                    
                            except Exception as individual_e:
                                debug_print(f"Could not query individual conversation {conv_id}: {individual_e}")
                                continue
                
                enhanced['activity']['chat_metrics']['total_messages'] = total_messages
                enhanced['activity']['chat_metrics']['total_message_size'] = total_message_size
                debug_print(f"Final chat metrics for user {user.get('id')}: {total_messages} messages, {total_message_size} bytes")
            
        except Exception as e:
            debug_print(f"Could not get chat metrics for user {user.get('id')}: {e}")
        
        # Try to get comprehensive login metrics
        try:
            # Get total login count (all time)
            total_logins_query = """
                SELECT VALUE COUNT(1) FROM c 
                WHERE c.user_id = @user_id AND c.activity_type = 'user_login'
            """
            login_params = [{"name": "@user_id", "value": user.get('id')}]
            total_logins = list(cosmos_activity_logs_container.query_items(
                query=total_logins_query,
                parameters=login_params,
                enable_cross_partition_query=True
            ))
            enhanced['activity']['login_metrics']['total_logins'] = total_logins[0] if total_logins else 0
            
            # Get last login timestamp
            last_login_query = """
                SELECT TOP 1 c.timestamp, c.created_at FROM c 
                WHERE c.user_id = @user_id AND c.activity_type = 'user_login'
                ORDER BY c.timestamp DESC
            """
            last_login_result = list(cosmos_activity_logs_container.query_items(
                query=last_login_query,
                parameters=login_params,
                enable_cross_partition_query=True
            ))
            if last_login_result:
                login_record = last_login_result[0]
                enhanced['activity']['login_metrics']['last_login'] = login_record.get('timestamp') or login_record.get('created_at')
                
        except Exception as e:
            debug_print(f"Could not get login metrics for user {user.get('id')}: {e}")
        
        # Try to get comprehensive document metrics
        try:
            # Get document count using separate query (avoid MultipleAggregates issue)
            doc_count_query = """
                SELECT VALUE COUNT(1)
                FROM c 
                WHERE c.user_id = @user_id AND c.type = 'document_metadata'
            """
            doc_metrics_params = [{"name": "@user_id", "value": user.get('id')}]
            doc_count_result = list(cosmos_user_documents_container.query_items(
                query=doc_count_query,
                parameters=doc_metrics_params,
                enable_cross_partition_query=True
            ))
            
            # Get total pages using separate query 
            doc_pages_query = """
                SELECT VALUE SUM(c.number_of_pages)
                FROM c 
                WHERE c.user_id = @user_id AND c.type = 'document_metadata'
            """
            doc_pages_result = list(cosmos_user_documents_container.query_items(
                query=doc_pages_query,
                parameters=doc_metrics_params,
                enable_cross_partition_query=True
            ))
            
            total_docs = doc_count_result[0] if doc_count_result else 0
            total_pages = doc_pages_result[0] if doc_pages_result and doc_pages_result[0] else 0
            
            enhanced['activity']['document_metrics']['total_documents'] = total_docs
            # AI search size = pages × 80KB
            enhanced['activity']['document_metrics']['ai_search_size'] = total_pages * 22 * 1024  # 22KB per page
            
            # Last day upload tracking removed - keeping only document count and sizes
            
            # Get actual storage account size if enhanced citation is enabled (check app settings)
            debug_print(f"💾 [STORAGE DEBUG] Enhanced citation enabled: {app_enhanced_citations}")
            if app_enhanced_citations:
                debug_print(f"💾 [STORAGE DEBUG] Starting storage calculation for user {user.get('id')}")
                try:
                    # Query actual file sizes from Azure Storage
                    storage_client = CLIENTS.get("storage_account_office_docs_client")
                    debug_print(f"💾 [STORAGE DEBUG] Storage client retrieved: {storage_client is not None}")
                    if storage_client:
                        user_folder_prefix = f"{user.get('id')}/"
                        total_storage_size = 0
                        
                        debug_print(f"💾 [STORAGE DEBUG] Looking for blobs with prefix: {user_folder_prefix}")
                        
                        # List all blobs in the user's folder
                        container_client = storage_client.get_container_client(storage_account_user_documents_container_name)
                        blob_list = container_client.list_blobs(name_starts_with=user_folder_prefix)
                        
                        blob_count = 0
                        for blob in blob_list:
                            total_storage_size += blob.size
                            blob_count += 1
                            debug_print(f"💾 [STORAGE DEBUG] Blob {blob.name}: {blob.size} bytes")
                            debug_print(f"Storage blob {blob.name}: {blob.size} bytes")
                        
                        debug_print(f"💾 [STORAGE DEBUG] Found {blob_count} blobs, total size: {total_storage_size} bytes")
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        debug_print(f"Total storage size for user {user.get('id')}: {total_storage_size} bytes")
                    else:
                        debug_print(f"💾 [STORAGE DEBUG] Storage client NOT available for user {user.get('id')}")
                        debug_print(f"Storage client not available for user {user.get('id')}")
                        # Fallback to estimation if storage client not available
                        storage_size_query = """
                            SELECT c.file_name, c.number_of_pages FROM c 
                            WHERE c.user_id = @user_id AND c.type = 'document_metadata'
                        """
                        storage_docs = list(cosmos_user_documents_container.query_items(
                            query=storage_size_query,
                            parameters=doc_metrics_params,
                            enable_cross_partition_query=True
                        ))
                        
                        total_storage_size = 0
                        for doc in storage_docs:
                            # Estimate file size based on pages and file type
                            pages = doc.get('number_of_pages', 1)
                            file_name = doc.get('file_name', '')
                            
                            if file_name.lower().endswith('.pdf'):
                                # PDF: ~500KB per page average
                                estimated_size = pages * 500 * 1024
                            elif file_name.lower().endswith(('.docx', '.doc')):
                                # Word docs: ~300KB per page average
                                estimated_size = pages * 300 * 1024
                            elif file_name.lower().endswith(('.pptx', '.ppt')):
                                # PowerPoint: ~800KB per page average
                                estimated_size = pages * 800 * 1024
                            else:
                                # Other files: ~400KB per page average
                                estimated_size = pages * 400 * 1024
                            
                            total_storage_size += estimated_size
                        
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        debug_print(f"💾 [STORAGE DEBUG] Fallback estimation complete: {total_storage_size} bytes")
                        debug_print(f"Estimated storage size for user {user.get('id')}: {total_storage_size} bytes")
                    
                except Exception as storage_e:
                    debug_print(f"❌ [STORAGE DEBUG] Storage calculation failed for user {user.get('id')}: {storage_e}")
                    debug_print(f"Could not calculate storage size for user {user.get('id')}: {storage_e}")
                    # Set to 0 if we can't calculate
                    enhanced['activity']['document_metrics']['storage_account_size'] = 0
                
        except Exception as e:
            debug_print(f"Could not get document metrics for user {user.get('id')}: {e}")
        
        # Save calculated metrics to user settings for caching (only if we calculated fresh data)
        if force_refresh or not user.get('settings', {}).get('metrics', {}).get('calculated_at'):
            try:
                from functions_settings import update_user_settings
                
                # Prepare metrics data for caching
                metrics_cache = {
                    'calculated_at': datetime.now(timezone.utc).isoformat(),
                    'login_metrics': enhanced['activity']['login_metrics'],
                    'chat_metrics': enhanced['activity']['chat_metrics'],
                    'document_metrics': {
                        'total_documents': enhanced['activity']['document_metrics']['total_documents'],
                        'ai_search_size': enhanced['activity']['document_metrics']['ai_search_size'],
                        'storage_account_size': enhanced['activity']['document_metrics']['storage_account_size']
                        # Note: personal_workspace_enabled and enhanced_citation_enabled are not cached as they're settings-based
                    }
                }
                
                # Update user settings with cached metrics
                settings_update = {'metrics': metrics_cache}
                update_success = update_user_settings(user.get('id'), settings_update)
                
                if update_success:
                    debug_print(f"Successfully cached metrics for user {user.get('id')}")
                else:
                    debug_print(f"Failed to cache metrics for user {user.get('id')}")
                    
            except Exception as cache_save_e:
                debug_print(f"Error saving metrics cache for user {user.get('id')}: {cache_save_e}")
        
        return enhanced
        
    except Exception as e:
        debug_print(f"Error enhancing user data: {e}")
        return user  # Return original user data if enhancement fails

def enhance_public_workspace_with_activity(workspace, force_refresh=False):
    """
    Enhance public workspace data with activity information and computed fields.
    Follows the same pattern as group enhancement but for public workspaces.
    """
    try:
        workspace_id = workspace.get('id')
        debug_print(f"🌐 [PUBLIC WORKSPACE DEBUG] Processing workspace {workspace_id}, force_refresh={force_refresh}")
        
        # Get app settings for enhanced citations
        from functions_settings import get_settings
        app_settings = get_settings()
        app_enhanced_citations = app_settings.get('enable_enhanced_citations', False) if app_settings else False
        
        debug_print(f"📋 [PUBLIC WORKSPACE SETTINGS DEBUG] App enhanced citations: {app_enhanced_citations}")
        
        # Create flat structure that matches frontend expectations
        owner_info = workspace.get('owner', {})
        
        enhanced = {
            'id': workspace.get('id'),
            'name': workspace.get('name', ''),
            'description': workspace.get('description', ''),
            'owner': workspace.get('owner', {}),
            'admins': workspace.get('admins', []),
            'documentManagers': workspace.get('documentManagers', []),
            'createdDate': workspace.get('createdDate'),
            'modifiedDate': workspace.get('modifiedDate'),
            'created_at': workspace.get('createdDate'),  # Alias for frontend
            
            # Flat fields expected by frontend
            'owner_name': owner_info.get('displayName') or owner_info.get('display_name') or owner_info.get('name', 'Unknown'),
            'owner_email': owner_info.get('email', ''),
            'created_by': owner_info.get('displayName') or owner_info.get('display_name') or owner_info.get('name', 'Unknown'),
            'document_count': 0,  # Will be updated from database
            'member_count': len(workspace.get('admins', [])) + len(workspace.get('documentManagers', [])) + (1 if owner_info else 0),  # Total members including owner
            'storage_size': 0,  # Will be updated from storage account
            'last_activity': None,  # Will be updated from public_documents
            'recent_activity_count': 0,  # Will be calculated
            'status': workspace.get('status', 'active'),  # Read from workspace document, default to 'active'
            'statusHistory': workspace.get('statusHistory', []),  # Include status change history
            
            # Keep nested structure for backward compatibility
            'activity': {
                'document_metrics': {
                    'total_documents': 0,
                    'ai_search_size': 0,  # pages × 80KB  
                    'storage_account_size': 0  # Actual file sizes from storage
                },
                'member_metrics': {
                    'total_members': len(workspace.get('admins', [])) + len(workspace.get('documentManagers', [])) + (1 if owner_info else 0),
                    'admin_count': len(workspace.get('admins', [])),
                    'document_manager_count': len(workspace.get('documentManagers', [])),
                }
            }
        }
        
        # Check for cached metrics if not forcing refresh
        if not force_refresh:
            cached_metrics = workspace.get('metrics')
            if cached_metrics and cached_metrics.get('calculated_at'):
                try:
                    # Check if cache is recent (within last 24 hours)
                    cache_time = datetime.fromisoformat(cached_metrics['calculated_at'].replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    
                    if now - cache_time < timedelta(hours=24):  # Use 24-hour cache window
                        debug_print(f"🌐 [PUBLIC WORKSPACE DEBUG] Using cached metrics for workspace {workspace_id} (cached at {cache_time})")
                        if 'document_metrics' in cached_metrics:
                            doc_metrics = cached_metrics['document_metrics']
                            enhanced['activity']['document_metrics'] = doc_metrics
                            # Update flat fields
                            enhanced['document_count'] = doc_metrics.get('total_documents', 0)
                            enhanced['storage_size'] = doc_metrics.get('storage_account_size', 0)
                        
                        # Apply cached activity metrics if available
                        if 'last_activity' in cached_metrics:
                            enhanced['last_activity'] = cached_metrics['last_activity']
                        if 'recent_activity_count' in cached_metrics:
                            enhanced['recent_activity_count'] = cached_metrics['recent_activity_count']
                        
                        debug_print(f"🌐 [PUBLIC WORKSPACE DEBUG] Returning cached data for {workspace_id}: {enhanced['activity']['document_metrics']}")
                        return enhanced
                    else:
                        debug_print(f"🌐 [PUBLIC WORKSPACE DEBUG] Cache expired for workspace {workspace_id} (cached at {cache_time}, age: {now - cache_time})")
                except Exception as cache_e:
                    debug_print(f"Error using cached metrics for workspace {workspace_id}: {cache_e}")
            
            debug_print(f"No cached metrics for workspace {workspace_id}, calculating basic document count")
            
            # Calculate at least the basic document count
            try:
                doc_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.public_workspace_id = @workspace_id AND c.type = 'document_metadata'"
                doc_count_params = [{"name": "@workspace_id", "value": workspace_id}]
                
                doc_count_results = list(cosmos_public_documents_container.query_items(
                    query=doc_count_query,
                    parameters=doc_count_params,
                    enable_cross_partition_query=True
                ))
                
                total_docs = 0
                if doc_count_results and len(doc_count_results) > 0:
                    total_docs = doc_count_results[0] if isinstance(doc_count_results[0], int) else 0
                
                debug_print(f"📄 [PUBLIC WORKSPACE BASIC DEBUG] Document count for workspace {workspace_id}: {total_docs}")
                enhanced['activity']['document_metrics']['total_documents'] = total_docs
                enhanced['document_count'] = total_docs
                
            except Exception as basic_e:
                debug_print(f"Error calculating basic document count for workspace {workspace_id}: {basic_e}")
            
            return enhanced
        
        # Force refresh - calculate fresh metrics
        debug_print(f"🌐 [PUBLIC WORKSPACE DEBUG] Force refresh - calculating fresh metrics for workspace {workspace_id}")
        
        # Calculate document metrics from public_documents container
        try:
            # Count documents for this workspace
            documents_count_query = """
                SELECT VALUE COUNT(1) FROM c 
                WHERE c.public_workspace_id = @workspace_id 
                AND c.type = 'document_metadata'
            """
            documents_count_params = [{"name": "@workspace_id", "value": workspace_id}]
            
            documents_count_result = list(cosmos_public_documents_container.query_items(
                query=documents_count_query,
                parameters=documents_count_params,
                enable_cross_partition_query=True
            ))
            
            total_documents = documents_count_result[0] if documents_count_result else 0
            enhanced['activity']['document_metrics']['total_documents'] = total_documents
            enhanced['document_count'] = total_documents
            
            # Calculate AI search size (pages × 80KB)
            pages_sum_query = """
                SELECT VALUE SUM(c.number_of_pages) FROM c 
                WHERE c.public_workspace_id = @workspace_id 
                AND c.type = 'document_metadata'
            """
            pages_sum_params = [{"name": "@workspace_id", "value": workspace_id}]
            
            pages_sum_result = list(cosmos_public_documents_container.query_items(
                query=pages_sum_query,
                parameters=pages_sum_params,
                enable_cross_partition_query=True
            ))
            
            total_pages = pages_sum_result[0] if pages_sum_result and pages_sum_result[0] else 0
            ai_search_size = total_pages * 22 * 1024  # 22KB per page
            enhanced['activity']['document_metrics']['ai_search_size'] = ai_search_size
            
            debug_print(f"📊 [PUBLIC WORKSPACE DOCUMENT DEBUG] Workspace {workspace_id}: {total_documents} documents, {total_pages} pages, {ai_search_size} AI search size")
            
            # Find last upload date
            last_upload_query = """
                SELECT c.upload_date
                FROM c 
                WHERE c.public_workspace_id = @workspace_id
                AND c.type = 'document_metadata'
            """
            last_upload_params = [{"name": "@workspace_id", "value": workspace_id}]
            
            upload_docs = list(cosmos_public_documents_container.query_items(
                query=last_upload_query,
                parameters=last_upload_params,
                enable_cross_partition_query=True
            ))
            
            # Last day upload tracking removed - keeping only document count and sizes
            debug_print(f"� [PUBLIC WORKSPACE DEBUG] Document metrics calculation complete for workspace {workspace_id}")
            
        except Exception as doc_e:
            debug_print(f"❌ [PUBLIC WORKSPACE DOCUMENT DEBUG] Error calculating document metrics for workspace {workspace_id}: {doc_e}")
            
        # Get actual storage account size if enhanced citation is enabled
        debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Enhanced citation enabled: {app_enhanced_citations}")
        if app_enhanced_citations:
                debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Starting storage calculation for workspace {workspace_id}")
                try:
                    # Query actual file sizes from Azure Storage for public workspace documents
                    storage_client = CLIENTS.get("storage_account_office_docs_client")
                    debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Storage client retrieved: {storage_client is not None}")
                    if storage_client:
                        workspace_folder_prefix = f"{workspace_id}/"
                        total_storage_size = 0
                        
                        debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Looking for blobs with prefix: {workspace_folder_prefix}")
                        
                        # List all blobs in the workspace's folder - use PUBLIC documents container
                        container_client = storage_client.get_container_client(storage_account_public_documents_container_name)
                        blob_list = container_client.list_blobs(name_starts_with=workspace_folder_prefix)
                        
                        blob_count = 0
                        for blob in blob_list:
                            total_storage_size += blob.size
                            blob_count += 1
                            debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Blob {blob.name}: {blob.size} bytes")
                        
                        debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Found {blob_count} blobs, total size: {total_storage_size} bytes")
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        enhanced['storage_size'] = total_storage_size  # Update flat field
                    else:
                        debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Storage client NOT available for workspace {workspace_id}")
                        # Fallback to estimation if storage client not available
                        storage_size_query = """
                            SELECT c.file_name, c.number_of_pages FROM c 
                            WHERE c.public_workspace_id = @workspace_id AND c.type = 'document_metadata'
                        """
                        storage_docs = list(cosmos_public_documents_container.query_items(
                            query=storage_size_query,
                            parameters=documents_count_params,
                            enable_cross_partition_query=True
                        ))
                        
                        total_storage_size = 0
                        for doc in storage_docs:
                            # Estimate file size based on pages and file type
                            pages = doc.get('number_of_pages', 1)
                            file_name = doc.get('file_name', '')
                            
                            if file_name.lower().endswith('.pdf'):
                                # PDF: ~500KB per page average
                                estimated_size = pages * 500 * 1024
                            elif file_name.lower().endswith(('.docx', '.doc')):
                                # Word docs: ~300KB per page average
                                estimated_size = pages * 300 * 1024
                            elif file_name.lower().endswith(('.pptx', '.ppt')):
                                # PowerPoint: ~800KB per page average
                                estimated_size = pages * 800 * 1024
                            else:
                                # Other files: ~400KB per page average
                                estimated_size = pages * 400 * 1024
                            
                            total_storage_size += estimated_size
                        
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        enhanced['storage_size'] = total_storage_size  # Update flat field
                        debug_print(f"💾 [PUBLIC WORKSPACE STORAGE DEBUG] Fallback estimation complete: {total_storage_size} bytes")
                        
                except Exception as storage_e:
                    debug_print(f"❌ [PUBLIC WORKSPACE STORAGE DEBUG] Storage calculation failed for workspace {workspace_id}: {storage_e}")
                    # Set to 0 if we can't calculate
                    enhanced['activity']['document_metrics']['storage_account_size'] = 0
                    enhanced['storage_size'] = 0
        
        # Cache the computed metrics in the workspace document
        if force_refresh:
            try:
                metrics_cache = {
                    'document_metrics': enhanced['activity']['document_metrics'],
                    'last_activity': enhanced.get('last_activity'),
                    'recent_activity_count': enhanced.get('recent_activity_count', 0),
                    'calculated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Update workspace document with cached metrics
                workspace['metrics'] = metrics_cache
                cosmos_public_workspaces_container.upsert_item(workspace)
                debug_print(f"Successfully cached metrics for workspace {workspace_id}")
                    
            except Exception as cache_save_e:
                debug_print(f"Error saving metrics cache for workspace {workspace_id}: {cache_save_e}")
    
        return enhanced
        
    except Exception as e:
        debug_print(f"Error enhancing public workspace data: {e}")
        return workspace  # Return original workspace data if enhancement fails

def enhance_group_with_activity(group, force_refresh=False):
    """
    Enhance group data with activity information and computed fields.
    Follows the same pattern as user enhancement but for groups.
    """
    try:
        group_id = group.get('id')
        debug_print(f"👥 [GROUP DEBUG] Processing group {group_id}, force_refresh={force_refresh}")
        
        # Get app settings for enhanced citations
        from functions_settings import get_settings
        app_settings = get_settings()
        app_enhanced_citations = app_settings.get('enable_enhanced_citations', False) if app_settings else False
        
        debug_print(f"📋 [GROUP SETTINGS DEBUG] App enhanced citations: {app_enhanced_citations}")
        
        # Create flat structure that matches frontend expectations
        owner_info = group.get('owner', {})
        users_list = group.get('users', [])
        
        enhanced = {
            'id': group.get('id'),
            'name': group.get('name', ''),
            'description': group.get('description', ''),
            'owner': group.get('owner', {}),
            'users': users_list,
            'admins': group.get('admins', []),
            'documentManagers': group.get('documentManagers', []),
            'pendingUsers': group.get('pendingUsers', []),
            'createdDate': group.get('createdDate'),
            'modifiedDate': group.get('modifiedDate'),
            'created_at': group.get('createdDate'),  # Alias for frontend
            
            # Flat fields expected by frontend
            'owner_name': owner_info.get('displayName') or owner_info.get('display_name') or owner_info.get('name', 'Unknown'),
            'owner_email': owner_info.get('email', ''),
            'created_by': owner_info.get('displayName') or owner_info.get('display_name') or owner_info.get('name', 'Unknown'),
            'member_count': len(users_list),  # Owner is already included in users_list
            'document_count': 0,  # Will be updated from database
            'storage_size': 0,  # Will be updated from storage account
            'last_activity': None,  # Will be updated from group_documents
            'recent_activity_count': 0,  # Will be calculated
            'status': group.get('status', 'active'),  # Read from group document, default to 'active'
            'statusHistory': group.get('statusHistory', []),  # Include status change history
            
            # Keep nested structure for backward compatibility
            'activity': {
                'document_metrics': {
                    'total_documents': 0,
                    'ai_search_size': 0,  # pages × 80KB  
                    'storage_account_size': 0  # Actual file sizes from storage
                },
                'member_metrics': {
                    'total_members': len(users_list),  # Owner is already included in users_list
                    'admin_count': len(group.get('admins', [])),
                    'document_manager_count': len(group.get('documentManagers', [])),
                    'pending_count': len(group.get('pendingUsers', []))
                }
            }
        }
        
        # Check for cached metrics if not forcing refresh
        if not force_refresh:
            # Groups don't have settings like users, but we could store metrics in the group doc
            cached_metrics = group.get('metrics')
            if cached_metrics and cached_metrics.get('calculated_at'):
                try:
                    # Check if cache is recent (within last hour)
                    cache_time = datetime.fromisoformat(cached_metrics['calculated_at'].replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    
                    if now - cache_time < timedelta(hours=24):  # Use 24-hour cache window
                        debug_print(f"👥 [GROUP DEBUG] Using cached metrics for group {group_id} (cached at {cache_time})")
                        if 'document_metrics' in cached_metrics:
                            doc_metrics = cached_metrics['document_metrics']
                            enhanced['activity']['document_metrics'] = doc_metrics
                            # Update flat fields
                            enhanced['document_count'] = doc_metrics.get('total_documents', 0)
                            enhanced['storage_size'] = doc_metrics.get('storage_account_size', 0)
                            # Cached document metrics applied successfully
                        
                        debug_print(f"👥 [GROUP DEBUG] Returning cached data for {group_id}: {enhanced['activity']['document_metrics']}")
                        return enhanced
                    else:
                        debug_print(f"👥 [GROUP DEBUG] Cache expired for group {group_id} (cached at {cache_time}, age: {now - cache_time})")
                except Exception as cache_e:
                    debug_print(f"Error using cached metrics for group {group_id}: {cache_e}")
            
            debug_print(f"No cached metrics for group {group_id}, calculating basic document count")
            
            # Calculate at least the basic document count
            try:
                doc_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.group_id = @group_id"
                doc_count_params = [{"name": "@group_id", "value": group_id}]
                
                doc_count_results = list(cosmos_group_documents_container.query_items(
                    query=doc_count_query,
                    parameters=doc_count_params,
                    enable_cross_partition_query=True
                ))
                
                total_docs = 0
                if doc_count_results and len(doc_count_results) > 0:
                    total_docs = doc_count_results[0] if isinstance(doc_count_results[0], int) else 0
                
                debug_print(f"📄 [GROUP BASIC DEBUG] Document count for group {group_id}: {total_docs}")
                enhanced['activity']['document_metrics']['total_documents'] = total_docs
                enhanced['document_count'] = total_docs
                
            except Exception as basic_e:
                debug_print(f"Error calculating basic document count for group {group_id}: {basic_e}")
            
            return enhanced
            
        # Force refresh - calculate fresh metrics
        debug_print(f"👥 [GROUP DEBUG] Force refresh - calculating fresh metrics for group {group_id}")
        
        # Calculate document metrics from group_documents container
        try:
            # Get document count using separate query (avoid MultipleAggregates issue) - same as user management
            doc_count_query = """
                SELECT VALUE COUNT(1)
                FROM c 
                WHERE c.group_id = @group_id AND c.type = 'document_metadata'
            """
            doc_metrics_params = [{"name": "@group_id", "value": group_id}]
            doc_count_result = list(cosmos_group_documents_container.query_items(
                query=doc_count_query,
                parameters=doc_metrics_params,
                enable_cross_partition_query=True
            ))
            
            # Get total pages using separate query - same as user management
            doc_pages_query = """
                SELECT VALUE SUM(c.number_of_pages)
                FROM c 
                WHERE c.group_id = @group_id AND c.type = 'document_metadata'
            """
            doc_pages_result = list(cosmos_group_documents_container.query_items(
                query=doc_pages_query,
                parameters=doc_metrics_params,
                enable_cross_partition_query=True
            ))
            
            total_docs = doc_count_result[0] if doc_count_result else 0
            total_pages = doc_pages_result[0] if doc_pages_result and doc_pages_result[0] else 0
            
            enhanced['activity']['document_metrics']['total_documents'] = total_docs
            enhanced['document_count'] = total_docs  # Update flat field
            # AI search size = pages × 22KB
            enhanced['activity']['document_metrics']['ai_search_size'] = total_pages * 22 * 1024  # 22KB per page
            
            debug_print(f"📄 [GROUP DOCUMENT DEBUG] Total documents for group {group_id}: {total_docs}")
            debug_print(f"📊 [GROUP AI SEARCH DEBUG] Total pages for group {group_id}: {total_pages}, AI search size: {total_pages * 22 * 1024} bytes")
            
            # Last day upload tracking removed - keeping only document count and sizes
            debug_print(f"� [GROUP DOCUMENT DEBUG] Document metrics calculation complete for group {group_id}")
            
            # Find the most recent document upload for last_activity (avoid ORDER BY composite index)
            recent_activity_query = """
                SELECT c.upload_date, c.created_at, c.modified_at
                FROM c 
                WHERE c.group_id = @group_id
            """
            recent_activity_params = [{"name": "@group_id", "value": group_id}]
            
            recent_docs = list(cosmos_group_documents_container.query_items(
                query=recent_activity_query,
                parameters=recent_activity_params,
                enable_cross_partition_query=True
            ))
            
            if recent_docs:
                # Find the most recent activity date from all documents in code
                most_recent_activity = None
                most_recent_activity_str = None
                
                for doc in recent_docs:
                    # Try multiple date fields to find the most recent activity
                    dates_to_check = [
                        doc.get('upload_date'),
                        doc.get('modified_at'), 
                        doc.get('created_at')
                    ]
                    
                    for date_str in dates_to_check:
                        if date_str:
                            try:
                                if isinstance(date_str, str):
                                    if 'T' in date_str:  # ISO format
                                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    else:  # Date only format
                                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                                else:
                                    date_obj = date_str  # Already datetime
                                
                                if most_recent_activity is None or date_obj > most_recent_activity:
                                    most_recent_activity = date_obj
                                    most_recent_activity_str = date_str
                            except Exception as date_parse_e:
                                debug_print(f"📅 [GROUP ACTIVITY DEBUG] Error parsing activity date '{date_str}': {date_parse_e}")
                                continue
                
                if most_recent_activity_str:
                    enhanced['last_activity'] = most_recent_activity_str
                    debug_print(f"📅 [GROUP ACTIVITY DEBUG] Last activity for group {group_id}: {most_recent_activity_str}")
                else:
                    debug_print(f"📅 [GROUP ACTIVITY DEBUG] No valid activity dates found for group {group_id}")
            
            # Calculate recent activity count (documents in last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_ago_str = week_ago.strftime('%Y-%m-%d')
            
            recent_activity_count_query = """
                SELECT VALUE COUNT(1) FROM c 
                WHERE c.group_id = @group_id 
                AND c.upload_date >= @week_ago
            """
            recent_activity_count_params = [
                {"name": "@group_id", "value": group_id},
                {"name": "@week_ago", "value": week_ago_str}
            ]
            
            recent_count_results = list(cosmos_group_documents_container.query_items(
                query=recent_activity_count_query,
                parameters=recent_activity_count_params,
                enable_cross_partition_query=True
            ))
            
            if recent_count_results:
                enhanced['recent_activity_count'] = recent_count_results[0]
                debug_print(f"📊 [GROUP ACTIVITY DEBUG] Recent activity count for group {group_id}: {recent_count_results[0]}")
            
            # AI search size already calculated above with document count
            
        except Exception as doc_e:
            debug_print(f"❌ [GROUP DOCUMENT DEBUG] Error calculating document metrics for group {group_id}: {doc_e}")
            
        # Get actual storage account size if enhanced citation is enabled (check app settings)
        debug_print(f"💾 [GROUP STORAGE DEBUG] Enhanced citation enabled: {app_enhanced_citations}")
        if app_enhanced_citations:
                debug_print(f"💾 [GROUP STORAGE DEBUG] Starting storage calculation for group {group_id}")
                try:
                    # Query actual file sizes from Azure Storage for group documents
                    storage_client = CLIENTS.get("storage_account_office_docs_client")
                    debug_print(f"💾 [GROUP STORAGE DEBUG] Storage client retrieved: {storage_client is not None}")
                    if storage_client:
                        group_folder_prefix = f"{group_id}/"
                        total_storage_size = 0
                        
                        debug_print(f"💾 [GROUP STORAGE DEBUG] Looking for blobs with prefix: {group_folder_prefix}")
                        
                        # List all blobs in the group's folder - use GROUP documents container, not user documents
                        container_client = storage_client.get_container_client(storage_account_group_documents_container_name)
                        blob_list = container_client.list_blobs(name_starts_with=group_folder_prefix)
                        
                        blob_count = 0
                        for blob in blob_list:
                            total_storage_size += blob.size
                            blob_count += 1
                            debug_print(f"💾 [GROUP STORAGE DEBUG] Blob {blob.name}: {blob.size} bytes")
                            debug_print(f"Group storage blob {blob.name}: {blob.size} bytes")
                        
                        debug_print(f"💾 [GROUP STORAGE DEBUG] Found {blob_count} blobs, total size: {total_storage_size} bytes")
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        enhanced['storage_size'] = total_storage_size  # Update flat field
                        debug_print(f"Total storage size for group {group_id}: {total_storage_size} bytes")
                    else:
                        debug_print(f"💾 [GROUP STORAGE DEBUG] Storage client NOT available for group {group_id}")
                        debug_print(f"Storage client not available for group {group_id}")
                        # Fallback to estimation if storage client not available
                        storage_size_query = """
                            SELECT c.file_name, c.number_of_pages FROM c 
                            WHERE c.group_id = @group_id AND c.type = 'document_metadata'
                        """
                        storage_docs = list(cosmos_group_documents_container.query_items(
                            query=storage_size_query,
                            parameters=doc_metrics_params,
                            enable_cross_partition_query=True
                        ))
                        
                        total_storage_size = 0
                        for doc in storage_docs:
                            # Estimate file size based on pages and file type
                            pages = doc.get('number_of_pages', 1)
                            file_name = doc.get('file_name', '')
                            
                            if file_name.lower().endswith('.pdf'):
                                # PDF: ~500KB per page average
                                estimated_size = pages * 500 * 1024
                            elif file_name.lower().endswith(('.docx', '.doc')):
                                # Word docs: ~300KB per page average
                                estimated_size = pages * 300 * 1024
                            elif file_name.lower().endswith(('.pptx', '.ppt')):
                                # PowerPoint: ~800KB per page average
                                estimated_size = pages * 800 * 1024
                            else:
                                # Other files: ~400KB per page average
                                estimated_size = pages * 400 * 1024
                            
                            total_storage_size += estimated_size
                        
                        enhanced['activity']['document_metrics']['storage_account_size'] = total_storage_size
                        enhanced['storage_size'] = total_storage_size  # Update flat field
                        debug_print(f"💾 [GROUP STORAGE DEBUG] Fallback estimation complete: {total_storage_size} bytes")
                        debug_print(f"Estimated storage size for group {group_id}: {total_storage_size} bytes")
                    
                except Exception as storage_e:
                    debug_print(f"❌ [GROUP STORAGE DEBUG] Storage calculation failed for group {group_id}: {storage_e}")
                    debug_print(f"Could not calculate storage size for group {group_id}: {storage_e}")
                    # Set to 0 if we can't calculate
                    enhanced['activity']['document_metrics']['storage_account_size'] = 0
                    enhanced['storage_size'] = 0
                
        # Cache the computed metrics in the group document
        if force_refresh:
            try:
                metrics_cache = {
                    'document_metrics': enhanced['activity']['document_metrics'],
                    'calculated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Update group document with cached metrics
                group['metrics'] = metrics_cache
                cosmos_groups_container.upsert_item(group)
                debug_print(f"Successfully cached metrics for group {group_id}")
                    
            except Exception as cache_save_e:
                debug_print(f"Error saving metrics cache for group {group_id}: {cache_save_e}")
        
        return enhanced
        
    except Exception as e:
        debug_print(f"Error enhancing group data: {e}")
        return group  # Return original group data if enhancement fails

def get_activity_trends_data(start_date, end_date):
    """
    Get aggregated activity data for the specified date range from existing containers.
    Returns daily activity counts by type using real application data.
    """
    try:
        # Debug logging
        debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Getting data for range: {start_date} to {end_date}")
        
        # Convert string dates to datetime objects if needed
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)
        
        # Initialize daily data structure
        daily_data = {}
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        while current_date <= end_date:
            date_key = current_date.strftime('%Y-%m-%d')
            daily_data[date_key] = {
                'date': date_key,
                'chats_created': 0,
                'chats_deleted': 0,
                'chats': 0,  # Keep for backward compatibility
                'personal_documents_created': 0,
                'personal_documents_deleted': 0,
                'group_documents_created': 0,
                'group_documents_deleted': 0,
                'public_documents_created': 0,
                'public_documents_deleted': 0,
                'personal_documents': 0,  # Keep for backward compatibility
                'group_documents': 0,     # Keep for backward compatibility
                'public_documents': 0,    # Keep for backward compatibility
                'documents': 0,           # Keep for backward compatibility
                'logins': 0,
                'total': 0
            }
            current_date += timedelta(days=1)
        
        debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Initialized {len(daily_data)} days of data: {list(daily_data.keys())}")
        
        # Parameters for queries
        parameters = [
            {"name": "@start_date", "value": start_date.isoformat()},
            {"name": "@end_date", "value": end_date.isoformat()}
        ]
        
        debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Query parameters: {parameters}")
        
        # Query 1: Get chat activity from activity logs (both creation and deletion)
        try:
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Querying conversations...")
            
            # Count conversation creations
            conversations_query = """
                SELECT c.timestamp, c.created_at
                FROM c 
                WHERE c.activity_type = 'conversation_creation'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            conversations = list(cosmos_activity_logs_container.query_items(
                query=conversations_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(conversations)} conversation creation logs")
            
            for conv in conversations:
                timestamp = conv.get('timestamp') or conv.get('created_at')
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            conv_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            conv_date = timestamp
                        
                        date_key = conv_date.strftime('%Y-%m-%d')
                        if date_key in daily_data:
                            daily_data[date_key]['chats_created'] += 1
                            daily_data[date_key]['chats'] += 1  # Keep total for backward compatibility
                    except Exception as e:
                        debug_print(f"Could not parse conversation timestamp {timestamp}: {e}")
            
            # Count conversation deletions
            deletions_query = """
                SELECT c.timestamp, c.created_at
                FROM c 
                WHERE c.activity_type = 'conversation_deletion'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            deletions = list(cosmos_activity_logs_container.query_items(
                query=deletions_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(deletions)} conversation deletion logs")
            
            for deletion in deletions:
                timestamp = deletion.get('timestamp') or deletion.get('created_at')
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            del_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            del_date = timestamp
                        
                        date_key = del_date.strftime('%Y-%m-%d')
                        if date_key in daily_data:
                            daily_data[date_key]['chats_deleted'] += 1
                    except Exception as e:
                        debug_print(f"Could not parse deletion timestamp {timestamp}: {e}")
                        
        except Exception as e:
            debug_print(f"Could not query conversation activity logs: {e}")
            debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Error querying chats: {e}")

        # Query 2: Get document activity from activity_logs (both creation and deletion)
        try:
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Querying documents from activity logs...")
            
            # Document creations
            documents_query = """
                SELECT c.timestamp, c.created_at, c.workspace_type
                FROM c 
                WHERE c.activity_type = 'document_creation'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            docs = list(cosmos_activity_logs_container.query_items(
                query=documents_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(docs)} document creation logs")
            
            for doc in docs:
                timestamp = doc.get('timestamp') or doc.get('created_at')
                workspace_type = doc.get('workspace_type', 'personal')
                
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            doc_date = timestamp
                        
                        date_key = doc_date.strftime('%Y-%m-%d')
                        if date_key in daily_data:
                            if workspace_type == 'group':
                                daily_data[date_key]['group_documents_created'] += 1
                                daily_data[date_key]['group_documents'] += 1
                            elif workspace_type == 'public':
                                daily_data[date_key]['public_documents_created'] += 1
                                daily_data[date_key]['public_documents'] += 1
                            else:
                                daily_data[date_key]['personal_documents_created'] += 1
                                daily_data[date_key]['personal_documents'] += 1
                            
                            daily_data[date_key]['documents'] += 1
                    except Exception as e:
                        debug_print(f"Could not parse document timestamp {timestamp}: {e}")
            
            # Document deletions
            deletions_query = """
                SELECT c.timestamp, c.created_at, c.workspace_type
                FROM c 
                WHERE c.activity_type = 'document_deletion'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            doc_deletions = list(cosmos_activity_logs_container.query_items(
                query=deletions_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(doc_deletions)} document deletion logs")
            
            for doc in doc_deletions:
                timestamp = doc.get('timestamp') or doc.get('created_at')
                workspace_type = doc.get('workspace_type', 'personal')
                
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            doc_date = timestamp
                        
                        date_key = doc_date.strftime('%Y-%m-%d')
                        if date_key in daily_data:
                            if workspace_type == 'group':
                                daily_data[date_key]['group_documents_deleted'] += 1
                            elif workspace_type == 'public':
                                daily_data[date_key]['public_documents_deleted'] += 1
                            else:
                                daily_data[date_key]['personal_documents_deleted'] += 1
                    except Exception as e:
                        debug_print(f"Could not parse document deletion timestamp {timestamp}: {e}")
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Total documents found: {len(docs)} created, {len(doc_deletions)} deleted")
                        
        except Exception as e:
            debug_print(f"Could not query document activity logs: {e}")
            debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Error querying documents: {e}")

        # Query 3: Get login activity from activity_logs container
        try:
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Querying login activity...")
            
            # Query login activity from activity_logs container
            
            # Count total records with login_method
            count_query = """
                SELECT VALUE COUNT(1)
                FROM c 
                WHERE c.login_method != null
            """
            
            login_count = list(cosmos_activity_logs_container.query_items(
                query=count_query,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Total records with login_method: {login_count[0] if login_count else 0}")
            
            # Query for login records using the correct activity_type
            # The data shows records have activity_type: "user_login" and proper timestamps
            login_query = """
                SELECT c.timestamp, c.created_at, c.activity_type, c.login_method, c.user_id
                FROM c 
                WHERE c.activity_type = 'user_login'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            login_activities = list(cosmos_activity_logs_container.query_items(
                query=login_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(login_activities)} user_login records")
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Date range: {start_date.isoformat()} to {end_date.isoformat()}")
            
            for login in login_activities:
                timestamp = login.get('timestamp') or login.get('created_at')
                if timestamp:
                    try:
                        if isinstance(timestamp, str):
                            login_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            login_date = timestamp
                        
                        date_key = login_date.strftime('%Y-%m-%d')
                        if date_key in daily_data:
                            daily_data[date_key]['logins'] += 1
                    except Exception as e:
                        debug_print(f"Could not parse login timestamp {timestamp}: {e}")
                        
        except Exception as e:
            debug_print(f"Could not query activity logs for login data: {e}")
            debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Error querying logins: {e}")

        # Query 4: Get token usage from activity_logs (token_usage activity_type)
        try:
            debug_print("🔍 [ACTIVITY TRENDS DEBUG] Querying token usage...")
            
            token_usage_query = """
                SELECT c.timestamp, c.created_at, c.token_type, c.usage.total_tokens as token_count
                FROM c
                WHERE c.activity_type = 'token_usage'
                AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                   OR (c.created_at >= @start_date AND c.created_at <= @end_date))
            """
            
            token_activities = list(cosmos_activity_logs_container.query_items(
                query=token_usage_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Found {len(token_activities)} token_usage records")
            
            # Initialize token tracking structure
            token_daily_data = {}
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                token_daily_data[date_key] = {
                    'embedding': 0,
                    'chat': 0,
                    'web_search': 0
                }
                current_date += timedelta(days=1)
            
            for token_record in token_activities:
                timestamp = token_record.get('timestamp') or token_record.get('created_at')
                token_type = token_record.get('token_type', '')
                token_count = token_record.get('token_count', 0)
                
                if timestamp and token_type in ['embedding', 'chat', 'web_search']:
                    try:
                        if isinstance(timestamp, str):
                            token_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                        else:
                            token_date = timestamp
                        
                        date_key = token_date.strftime('%Y-%m-%d')
                        if date_key in token_daily_data:
                            token_daily_data[date_key][token_type] += token_count
                    except Exception as e:
                        debug_print(f"Could not parse token timestamp {timestamp}: {e}")
            
            debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Token daily data: {token_daily_data}")
                        
        except Exception as e:
            debug_print(f"Could not query activity logs for token usage: {e}")
            debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Error querying tokens: {e}")
            # Initialize empty token data on error
            token_daily_data = {}
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            while current_date <= end_date:
                date_key = current_date.strftime('%Y-%m-%d')
                token_daily_data[date_key] = {'embedding': 0, 'chat': 0, 'web_search': 0}
                current_date += timedelta(days=1)

        # Calculate totals for each day
        for date_key in daily_data:
            daily_data[date_key]['total'] = (
                daily_data[date_key]['chats'] + 
                daily_data[date_key]['documents'] + 
                daily_data[date_key]['logins']
            )

        # Group by activity type for chart display  
        result = {
            'chats': {},
            'chats_created': {},
            'chats_deleted': {},
            'documents': {},           # Keep for backward compatibility
            'personal_documents': {},  # Keep for backward compatibility
            'group_documents': {},     # Keep for backward compatibility
            'public_documents': {},    # Keep for backward compatibility
            'personal_documents_created': {},
            'personal_documents_deleted': {},
            'group_documents_created': {},
            'group_documents_deleted': {},
            'public_documents_created': {},
            'public_documents_deleted': {},
            'logins': {},
            'tokens': token_daily_data  # Token usage by type (embedding, chat)
        }
        
        for date_key, data in daily_data.items():
            result['chats'][date_key] = data['chats']
            result['chats_created'][date_key] = data['chats_created']
            result['chats_deleted'][date_key] = data['chats_deleted']
            result['documents'][date_key] = data['documents']
            result['personal_documents'][date_key] = data['personal_documents']
            result['group_documents'][date_key] = data['group_documents']
            result['public_documents'][date_key] = data['public_documents']
            result['personal_documents_created'][date_key] = data['personal_documents_created']
            result['personal_documents_deleted'][date_key] = data['personal_documents_deleted']
            result['group_documents_created'][date_key] = data['group_documents_created']
            result['group_documents_deleted'][date_key] = data['group_documents_deleted']
            result['public_documents_created'][date_key] = data['public_documents_created']
            result['public_documents_deleted'][date_key] = data['public_documents_deleted']
            result['logins'][date_key] = data['logins']
        
        debug_print(f"🔍 [ACTIVITY TRENDS DEBUG] Final result: {result}")
        
        return result

    except Exception as e:
        debug_print(f"Error getting activity trends data: {e}")
        debug_print(f"❌ [ACTIVITY TRENDS DEBUG] Fatal error: {e}")
        return {
            'chats': {},
            'documents': {},
            'personal_documents': {},
            'group_documents': {},
            'public_documents': {},
            'logins': {},
            'tokens': {}
        }

def get_raw_activity_trends_data(start_date, end_date, charts):
    """
    Get raw detailed activity data for export instead of aggregated counts.
    Returns individual records with user information for each activity type.
    """
    try:
        debug_print(f"🔍 [RAW ACTIVITY DEBUG] Getting raw data for range: {start_date} to {end_date}")
        debug_print(f"🔍 [RAW ACTIVITY DEBUG] Requested charts: {charts}")
        
        result = {}
        
        # Parameters for queries
        parameters = [
            {"name": "@start_date", "value": start_date.isoformat()},
            {"name": "@end_date", "value": end_date.isoformat()}
        ]
        
        # Helper function to get user info
        def get_user_info(user_id):
            try:
                user_doc = cosmos_user_settings_container.read_item(
                    item=user_id,
                    partition_key=user_id
                )
                return {
                    'display_name': user_doc.get('display_name', ''),
                    'email': user_doc.get('email', '')
                }
            except Exception:
                return {
                    'display_name': '',
                    'email': ''
                }
        
        # Helper function to get AI Search size with caching
        def get_ai_search_size(doc, cosmos_container):
            """
            Get AI Search size for a document (pages × 80KB).
            Uses cached value from Cosmos if available, otherwise calculates and caches it.
            
            Args:
                doc: The document dict from Cosmos (to check for cached value)
                cosmos_container: Cosmos container to update with cached value
                
            Returns:
                AI Search size in bytes
            """
            try:
                # Check if AI Search size is already cached in the document
                cached_size = doc.get('ai_search_size', 0)
                if cached_size and cached_size > 0:
                    return cached_size
                
                # Not cached or zero, calculate from page count
                pages = doc.get('number_of_pages', 0) or 0
                ai_search_size = pages * 80 * 1024 if pages else 0  # 80KB per page
                
                # Cache the calculated size in Cosmos for future use using update_document
                # This ensures we only update the specific field without overwriting other metadata
                if ai_search_size > 0:
                    try:
                        document_id = doc.get('id') or doc.get('document_id')
                        user_id = doc.get('user_id')
                        group_id = doc.get('group_id')
                        public_workspace_id = doc.get('public_workspace_id')
                        
                        if document_id and user_id:
                            update_document(
                                document_id=document_id,
                                user_id=user_id,
                                group_id=group_id,
                                public_workspace_id=public_workspace_id,
                                ai_search_size=ai_search_size
                            )
                    except Exception as cache_e:
                        # Don't fail if caching fails, just return the calculated value
                        pass
                
                return ai_search_size
                
            except Exception as e:
                return 0
        
        # Helper function to get document storage size from Azure Storage with caching
        def get_document_storage_size(doc, cosmos_container, container_name, folder_prefix, document_id):
            """
            Get actual storage size for a document from Azure Storage.
            Uses cached value from Cosmos if available, otherwise calculates and caches it.
            
            Args:
                doc: The document dict from Cosmos (to check for cached value)
                cosmos_container: Cosmos container to update with cached value
                container_name: Azure Storage container name (e.g., 'user-documents', 'group-documents', 'public-documents')
                folder_prefix: Folder prefix (e.g., user_id, group_id, public_workspace_id)
                document_id: Document ID
                
            Returns:
                Total size in bytes of all blobs for this document
            """
            try:
                # Check if storage size is already cached in the document
                cached_size = doc.get('storage_account_size', 0)
                if cached_size and cached_size > 0:
                    debug_print(f"💾 [STORAGE CACHE] Using cached storage size for {document_id}: {cached_size} bytes")
                    return cached_size
                
                # Not cached or zero, calculate from Azure Storage
                storage_client = CLIENTS.get("storage_account_office_docs_client")
                if not storage_client:
                    debug_print(f"❌ [STORAGE DEBUG] Storage client not available for {document_id}")
                    return 0
                
                # Get the file_name from the document to construct the correct blob path
                # Blob path structure: {folder_prefix}/{file_name}
                # NOT {folder_prefix}/{document_id}/... 
                file_name = doc.get('file_name', '')
                if not file_name:
                    debug_print(f"⚠️ [STORAGE DEBUG] No file_name for document {document_id}, cannot calculate storage size")
                    return 0
                
                # Construct the exact blob path
                blob_path = f"{folder_prefix}/{file_name}"
                
                debug_print(f"💾 [STORAGE DEBUG] Looking for blob: {blob_path}")
                
                container_client = storage_client.get_container_client(container_name)
                
                # Try to get the specific blob
                try:
                    blob_client = container_client.get_blob_client(blob_path)
                    blob_properties = blob_client.get_blob_properties()
                    total_size = blob_properties.size
                    blob_count = 1
                    
                    debug_print(f"💾 [STORAGE CALC] Found blob {blob_path}: {total_size} bytes")
                except Exception as blob_e:
                    debug_print(f"⚠️ [STORAGE DEBUG] Blob not found or error: {blob_path} - {blob_e}")
                    return 0
                
                debug_print(f"💾 [STORAGE CALC] Calculated storage size for {document_id}: {total_size} bytes ({blob_count} blobs)")
                
                # Cache the calculated size in Cosmos for future use using update_document
                # This ensures we only update the specific field without overwriting other metadata
                if total_size > 0:
                    try:
                        user_id = doc.get('user_id')
                        group_id = doc.get('group_id')
                        public_workspace_id = doc.get('public_workspace_id')
                        
                        if document_id and user_id:
                            update_document(
                                document_id=document_id,
                                user_id=user_id,
                                group_id=group_id,
                                public_workspace_id=public_workspace_id,
                                storage_account_size=total_size
                            )
                            debug_print(f"💾 [STORAGE CACHE] Cached storage size in Cosmos for {document_id}")
                    except Exception as cache_e:
                        debug_print(f"⚠️ [STORAGE CACHE] Could not cache storage size for {document_id}: {cache_e}")
                        # Don't fail if caching fails, just return the calculated value
                
                return total_size
                
            except Exception as e:
                debug_print(f"❌ [STORAGE DEBUG] Error getting storage size for document {document_id}: {e}")
                return 0
        
        # 1. Login Data
        if 'logins' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting login records...")
            try:
                login_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, c.activity_type, c.login_method
                    FROM c 
                    WHERE c.activity_type = 'user_login'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                login_activities = list(cosmos_activity_logs_container.query_items(
                    query=login_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                login_records = []
                for login in login_activities:
                    user_id = login.get('user_id', '')
                    user_info = get_user_info(user_id)
                    timestamp = login.get('timestamp') or login.get('created_at')
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                login_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                login_date = timestamp
                            
                            login_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'login_time': login_date.strftime('%Y-%m-%d %H:%M:%S')
                            })
                        except Exception as e:
                            debug_print(f"Could not parse login timestamp {timestamp}: {e}")
                
                result['logins'] = login_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(login_records)} login records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting login data: {e}")
                result['logins'] = []
        
        # 2. Document Data - From activity_logs container using document_creation activity_type
        # Personal Documents
        if 'personal_documents' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting personal document records from activity logs...")
            try:
                personal_docs_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, c.document.document_id,
                           c.document.file_name, c.document.file_type, c.document.file_size_bytes,
                           c.document.page_count, c.document_metadata, c.embedding_usage
                    FROM c 
                    WHERE c.activity_type = 'document_creation'
                    AND c.workspace_type = 'personal'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                personal_docs = list(cosmos_activity_logs_container.query_items(
                    query=personal_docs_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                personal_document_records = []
                for doc in personal_docs:
                    user_id = doc.get('user_id', '')
                    user_info = get_user_info(user_id)
                    timestamp = doc.get('timestamp') or doc.get('created_at')
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                doc_date = timestamp
                            
                            document_info = doc.get('document', {})
                            doc_metadata = doc.get('document_metadata', {})
                            pages = document_info.get('page_count', 0) or 0
                            
                            # Calculate AI Search size (pages × 80KB)
                            ai_search_size = pages * 80 * 1024 if pages else 0
                            
                            # Get file size from activity log
                            storage_size = document_info.get('file_size_bytes', 0) or 0
                            
                            personal_document_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'document_id': document_info.get('document_id', ''),
                                'filename': document_info.get('file_name', ''),
                                'title': doc_metadata.get('title', 'Unknown Title'),
                                'page_count': pages,
                                'ai_search_size': ai_search_size,
                                'storage_account_size': storage_size,
                                'upload_date': doc_date.strftime('%Y-%m-%d %H:%M:%S'),
                                'document_type': 'Personal'
                            })
                        except Exception as e:
                            debug_print(f"Could not parse personal document timestamp {timestamp}: {e}")
                
                result['personal_documents'] = personal_document_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(personal_document_records)} personal document records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting personal document data: {e}")
                result['personal_documents'] = []
        
        # Group Documents
        if 'group_documents' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting group document records from activity logs...")
            try:
                group_docs_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, c.document.document_id,
                           c.document.file_name, c.document.file_type, c.document.file_size_bytes,
                           c.document.page_count, c.document_metadata, c.embedding_usage,
                           c.workspace_context.group_id
                    FROM c 
                    WHERE c.activity_type = 'document_creation'
                    AND c.workspace_type = 'group'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                group_docs = list(cosmos_activity_logs_container.query_items(
                    query=group_docs_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                group_document_records = []
                for doc in group_docs:
                    user_id = doc.get('user_id', '')
                    user_info = get_user_info(user_id)
                    timestamp = doc.get('timestamp') or doc.get('created_at')
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                doc_date = timestamp
                            
                            document_info = doc.get('document', {})
                            doc_metadata = doc.get('document_metadata', {})
                            pages = document_info.get('page_count', 0) or 0
                            
                            # Calculate AI Search size (pages × 80KB)
                            ai_search_size = pages * 80 * 1024 if pages else 0
                            
                            # Get file size from activity log
                            storage_size = document_info.get('file_size_bytes', 0) or 0
                            
                            group_document_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'document_id': document_info.get('document_id', ''),
                                'filename': document_info.get('file_name', ''),
                                'title': doc_metadata.get('title', 'Unknown Title'),
                                'page_count': pages,
                                'ai_search_size': ai_search_size,
                                'storage_account_size': storage_size,
                                'upload_date': doc_date.strftime('%Y-%m-%d %H:%M:%S'),
                                'document_type': 'Group'
                            })
                        except Exception as e:
                            debug_print(f"Could not parse group document timestamp {timestamp}: {e}")
                
                result['group_documents'] = group_document_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(group_document_records)} group document records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting group document data: {e}")
                result['group_documents'] = []
        
        # Public Documents
        if 'public_documents' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting public document records from activity logs...")
            try:
                public_docs_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, c.document.document_id,
                           c.document.file_name, c.document.file_type, c.document.file_size_bytes,
                           c.document.page_count, c.document_metadata, c.embedding_usage,
                           c.workspace_context.public_workspace_id
                    FROM c 
                    WHERE c.activity_type = 'document_creation'
                    AND c.workspace_type = 'public'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                public_docs = list(cosmos_activity_logs_container.query_items(
                    query=public_docs_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                public_document_records = []
                for doc in public_docs:
                    user_id = doc.get('user_id', '')
                    user_info = get_user_info(user_id)
                    timestamp = doc.get('timestamp') or doc.get('created_at')
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                doc_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                doc_date = timestamp
                            
                            document_info = doc.get('document', {})
                            doc_metadata = doc.get('document_metadata', {})
                            pages = document_info.get('page_count', 0) or 0
                            
                            # Calculate AI Search size (pages × 80KB)
                            ai_search_size = pages * 80 * 1024 if pages else 0
                            
                            # Get file size from activity log
                            storage_size = document_info.get('file_size_bytes', 0) or 0
                            
                            public_document_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'document_id': document_info.get('document_id', ''),
                                'filename': document_info.get('file_name', ''),
                                'title': doc_metadata.get('title', 'Unknown Title'),
                                'page_count': pages,
                                'ai_search_size': ai_search_size,
                                'storage_account_size': storage_size,
                                'upload_date': doc_date.strftime('%Y-%m-%d %H:%M:%S'),
                                'document_type': 'Public'
                            })
                        except Exception as e:
                            debug_print(f"Could not parse public document timestamp {timestamp}: {e}")
                
                result['public_documents'] = public_document_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(public_document_records)} public document records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting public document data: {e}")
                result['public_documents'] = []
        
        # Keep backward compatibility - if 'documents' is requested, combine all types
        if 'documents' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting combined document records for backward compatibility...")
            combined_records = []
            if 'personal_documents' in result:
                combined_records.extend(result['personal_documents'])
            if 'group_documents' in result:
                combined_records.extend(result['group_documents'])
            if 'public_documents' in result:
                combined_records.extend(result['public_documents'])
            result['documents'] = combined_records
            debug_print(f"🔍 [RAW ACTIVITY DEBUG] Combined {len(combined_records)} total document records")
        
        # 3. Chat Data - From activity_logs container using conversation_creation activity_type
        if 'chats' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting chat records from activity logs...")
            try:
                conversations_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, 
                           c.conversation.conversation_id as conversation_id, 
                           c.conversation.title as conversation_title
                    FROM c 
                    WHERE c.activity_type = 'conversation_creation'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                conversations = list(cosmos_activity_logs_container.query_items(
                    query=conversations_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                chat_records = []
                for conv in conversations:
                    user_id = conv.get('user_id', '')
                    user_info = get_user_info(user_id)
                    conversation_id = conv.get('conversation_id', '')
                    conversation_title = conv.get('conversation_title', '')
                    timestamp = conv.get('timestamp') or conv.get('created_at')
                    
                    # Get message count and total size for this conversation (still from messages container)
                    try:
                        messages_query = """
                            SELECT VALUE COUNT(1)
                            FROM c 
                            WHERE c.conversation_id = @conversation_id
                        """
                        
                        message_count_result = list(cosmos_messages_container.query_items(
                            query=messages_query,
                            parameters=[{"name": "@conversation_id", "value": conversation_id}],
                            enable_cross_partition_query=True
                        ))
                        message_count = message_count_result[0] if message_count_result else 0
                        
                        # Get total character count
                        messages_size_query = """
                            SELECT c.content
                            FROM c 
                            WHERE c.conversation_id = @conversation_id
                        """
                        
                        messages = list(cosmos_messages_container.query_items(
                            query=messages_size_query,
                            parameters=[{"name": "@conversation_id", "value": conversation_id}],
                            enable_cross_partition_query=True
                        ))
                        
                        total_size = sum(len(str(msg.get('content', ''))) for msg in messages)
                        
                    except Exception as msg_e:
                        debug_print(f"Could not get message data for conversation {conversation_id}: {msg_e}")
                        message_count = 0
                        total_size = 0
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                conv_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                conv_date = timestamp
                            
                            created_date_str = conv_date.strftime('%Y-%m-%d %H:%M:%S')
                            
                            chat_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'chat_id': conversation_id,
                                'chat_title': conversation_title,
                                'message_count': message_count,
                                'total_size': total_size,
                                'created_date': created_date_str
                            })
                        except Exception as e:
                            debug_print(f"Could not parse conversation timestamp {timestamp}: {e}")
                
                result['chats'] = chat_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(chat_records)} chat records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting chat data: {e}")
                result['chats'] = []
        
        # 4. Token Usage Data - From activity_logs container using token_usage activity_type
        if 'tokens' in charts:
            debug_print("🔍 [RAW ACTIVITY DEBUG] Getting token usage records from activity logs...")
            try:
                tokens_query = """
                    SELECT c.timestamp, c.created_at, c.user_id, c.token_type,
                           c.usage.model as model_name,
                           c.usage.prompt_tokens as prompt_tokens, 
                           c.usage.completion_tokens as completion_tokens, 
                           c.usage.total_tokens as total_tokens
                    FROM c 
                    WHERE c.activity_type = 'token_usage'
                    AND ((c.timestamp >= @start_date AND c.timestamp <= @end_date)
                       OR (c.created_at >= @start_date AND c.created_at <= @end_date))
                """
                
                token_activities = list(cosmos_activity_logs_container.query_items(
                    query=tokens_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                token_records = []
                for token_log in token_activities:
                    user_id = token_log.get('user_id', '')
                    user_info = get_user_info(user_id)
                    timestamp = token_log.get('timestamp') or token_log.get('created_at')
                    token_type = token_log.get('token_type', 'unknown')
                    
                    if timestamp:
                        try:
                            if isinstance(timestamp, str):
                                token_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00') if 'Z' in timestamp else timestamp)
                            else:
                                token_date = timestamp
                            
                            # Handle both chat and embedding tokens
                            prompt_tokens = token_log.get('prompt_tokens', 0) if token_type == 'chat' else 0
                            completion_tokens = token_log.get('completion_tokens', 0) if token_type == 'chat' else 0
                            
                            token_records.append({
                                'display_name': user_info['display_name'],
                                'email': user_info['email'],
                                'user_id': user_id,
                                'token_type': token_type,
                                'model_name': token_log.get('model_name', 'Unknown'),
                                'prompt_tokens': prompt_tokens,
                                'completion_tokens': completion_tokens,
                                'total_tokens': token_log.get('total_tokens', 0),
                                'timestamp': token_date.strftime('%Y-%m-%d %H:%M:%S')
                            })
                        except Exception as e:
                            debug_print(f"Could not parse token timestamp {timestamp}: {e}")
                
                result['tokens'] = token_records
                debug_print(f"🔍 [RAW ACTIVITY DEBUG] Found {len(token_records)} token usage records")
                
            except Exception as e:
                debug_print(f"❌ [RAW ACTIVITY DEBUG] Error getting token usage data: {e}")
                result['tokens'] = []
        
        debug_print(f"🔍 [RAW ACTIVITY DEBUG] Returning raw data with {len(result)} chart types")
        return result
        
    except Exception as e:
        debug_print(f"Error getting raw activity trends data: {e}")
        debug_print(f"❌ [RAW ACTIVITY DEBUG] Fatal error: {e}")
        return {}

