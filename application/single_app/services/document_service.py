# document_service.py
# Document CRUD operations — create, read, update, delete, versioning, and migration.

import json
import os
import traceback
from config import *
from functions_settings import get_settings
from functions_logging import *
from functions_debug import debug_print


def allowed_file(filename, allowed_extensions=None):
    if not allowed_extensions:
        allowed_extensions = ALLOWED_EXTENSIONS
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def create_document(file_name, user_id, document_id, num_file_chunks, status, group_id=None, public_workspace_id=None):
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.file_name = @file_name
                AND c.public_workspace_id = @public_workspace_id
        """
        parameters = [
            {"name": "@file_name", "value": file_name},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.file_name = @file_name
                AND c.group_id = @group_id
        """
        parameters = [
            {"name": "@file_name", "value": file_name},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.file_name = @file_name
                AND c.user_id = @user_id
        """
        parameters = [
            {"name": "@file_name", "value": file_name},
            {"name": "@user_id", "value": user_id}
        ]

    try:
        existing_document = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )
        version = existing_document[0]['version'] + 1 if existing_document else 1

        if is_public_workspace:
            document_metadata = {
                "id": document_id,
                "file_name": file_name,
                "num_chunks": 0,
                "number_of_pages": 0,
                "current_file_chunk": 0,
                "num_file_chunks": num_file_chunks,
                "upload_date": current_time,
                "last_updated": current_time,
                "version": version,
                "status": status,
                "percentage_complete": 0,
                "document_classification": "None",
                "type": "document_metadata",
                "public_workspace_id": public_workspace_id,
                "user_id": user_id,
                "tags": []
            }
        elif is_group:
            document_metadata = {
                "id": document_id,
                "file_name": file_name,
                "num_chunks": 0,
                "number_of_pages": 0,
                "current_file_chunk": 0,
                "num_file_chunks": num_file_chunks,
                "upload_date": current_time,
                "last_updated": current_time,
                "version": version,
                "status": status,
                "percentage_complete": 0,
                "document_classification": "None",
                "type": "document_metadata",
                "group_id": group_id,
                "shared_group_ids": [],
                "tags": []
            }
        else:
            document_metadata = {
                "id": document_id,
                "file_name": file_name,
                "num_chunks": 0,
                "number_of_pages": 0,
                "current_file_chunk": 0,
                "num_file_chunks": num_file_chunks,
                "upload_date": current_time,
                "last_updated": current_time,
                "version": version,
                "status": status,
                "percentage_complete": 0,
                "document_classification": "None",
                "type": "document_metadata",
                "user_id": user_id,
                "shared_user_ids": [],
                "embedding_tokens": 0,
                "embedding_model_deployment_name": None,
                "tags": []
            }

        cosmos_container.upsert_item(document_metadata)

        add_file_task_to_file_processing_log(
            document_id,
            user_id,
            f"Document {file_name} created."
        )

    except Exception as e:
        debug_print(f"Error creating document: {e}")
        raise


def get_document_metadata(document_id, user_id, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND (c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_user_ids, @user_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
        content=f"Query is {query}, parameters are {parameters}."
    )
    try:
        document_items = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
            content=f"Document metadata retrieved: {document_items}."
        )
        return document_items[0] if document_items else None

    except Exception as e:
        debug_print(f"Error retrieving document metadata: {repr(e)}\nTraceback:\n{traceback.format_exc()}")
        return None


def calculate_processing_percentage(doc_metadata):
    """
    Calculates a simpler, step-based processing percentage based on status
    and page saving progress.

    Args:
        doc_metadata (dict): The current document metadata dictionary.

    Returns:
        int: The calculated percentage (0-100).
    """
    status = doc_metadata.get('status', '')
    if isinstance(status, str):
        status = status.lower()
    elif isinstance(status, bytes):
        status = status.decode('utf-8').lower()
    elif isinstance(status, dict):
        status = json.dumps(status).lower()


    current_pct = doc_metadata.get('percentage_complete', 0)
    estimated_pages = doc_metadata.get('number_of_pages', 0)
    total_chunks_saved = doc_metadata.get('current_file_chunk', 0)

    # --- Final States ---
    if "processing complete" in status or current_pct == 100:
        # Ensure it stays 100 if it ever reached it
        return 100
    if "error" in status or "failed" in status:
        # Keep the last known percentage on error/failure
        return current_pct

    # --- Calculate percentage based on phase/status ---
    calculated_pct = 0

    # Phase 1: Initial steps up to sending to DI
    if "queued" in status:
        calculated_pct = 0

    elif "sending" in status:
        # Explicitly sending data for analysis
        calculated_pct = 5

    # Phase 3: Saving Pages (The main progress happens here: 10% -> 90%)
    elif "saving page" in status or "saving chunk" in status: # Status indicating the loop saving pages is active
        if estimated_pages > 0:
            # Calculate progress ratio (0.0 to 1.0)
            # Ensure saved count doesn't exceed estimate for the ratio
            safe_chunks_saved = min(total_chunks_saved, estimated_pages)
            progress_ratio = safe_chunks_saved / estimated_pages

            # Map the ratio to the percentage range [10, 90]
            # The range covers 80 percentage points (90 - 10)
            calculated_pct = 5 + (progress_ratio * 80)
        else:
            # If page count is unknown, we can't show granular progress.
            # Stay at the beginning of this phase.
            calculated_pct = 5

    # Phase 4: Final Metadata Extraction (Optional, after page saving)
    elif "extracting final metadata" in status:
        # This phase should start after page saving is effectively done (>=90%)
        # Assign a fixed value during this step.
        calculated_pct = 95

    # Default/Fallback: If status doesn't match known phases,
    # use the current percentage. This handles intermediate statuses like
    # "Chunk X/Y saved" which might occur between "saving page" updates.
    else:
        calculated_pct = current_pct


    # --- Final Adjustments ---

    # Cap at 99% - only "Processing Complete" status should trigger 100%
    final_pct = min(int(round(calculated_pct)), 99)

    # Prevent percentage from going down, unless it's due to an error state (handled above)
    # Compare the newly calculated capped percentage with the value read at the function start
    # This ensures progress is monotonic upwards until completion or error.
    return max(final_pct, current_pct)


def update_document(**kwargs):
    document_id = kwargs.get('document_id')
    user_id = kwargs.get('user_id')
    group_id = kwargs.get('group_id')
    public_workspace_id = kwargs.get('public_workspace_id')
    num_chunks_increment = kwargs.pop('num_chunks_increment', 0)

    if not document_id or not user_id:
        # Cannot proceed without these identifiers
        debug_print("Error: document_id and user_id are required for update_document")
        # Depending on context, you might raise an error or return failure
        raise ValueError("document_id and user_id are required")

    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.group_id = @group_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.user_id = @user_id
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

    add_file_task_to_file_processing_log(
        document_id=document_id,
        user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
        content=f"Query is {query}, parameters are {parameters}."
    )

    try:
        existing_documents = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        status = kwargs.get('status', '')

        if status:
            add_file_task_to_file_processing_log(
                document_id=document_id,
                user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
                content=f"Status: {status}"
            )

        if not existing_documents:
            # Log specific error before raising
            log_msg = f"Document {document_id} not found for user {user_id} during update."
            debug_print(log_msg)
            add_file_task_to_file_processing_log(
                document_id=document_id,
                user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
                content=log_msg
            )
            raise CosmosResourceNotFoundError(
                message=f"Document {document_id} not found",
                status=404
            )


        existing_document = existing_documents[0]
        original_percentage = existing_document.get('percentage_complete', 0) # Store for comparison

        # 2. Apply updates from kwargs
        update_occurred = False
        updated_fields_requiring_chunk_sync = set() # Track fields needing propagation

        if num_chunks_increment > 0:
            current_num_chunks = existing_document.get('num_chunks', 0)
            existing_document['num_chunks'] = current_num_chunks + num_chunks_increment
            update_occurred = True # Incrementing counts as an update
            add_file_task_to_file_processing_log(
                document_id=document_id,
                user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
                content=f"Incrementing num_chunks by {num_chunks_increment} to {existing_document['num_chunks']}"
            )

        for key, value in kwargs.items():
            if value is not None and existing_document.get(key) != value:
                # Avoid overwriting num_chunks if it was just incremented
                if key == 'num_chunks' and num_chunks_increment > 0:
                    continue # Skip direct assignment if increment was used
                existing_document[key] = value
                update_occurred = True
                if key in ['title', 'authors', 'file_name', 'document_classification', 'tags']:
                    updated_fields_requiring_chunk_sync.add(key)
                # Propagate shared_group_ids to group chunks if changed
                if is_group and key == 'shared_group_ids':
                    updated_fields_requiring_chunk_sync.add('shared_group_ids')

        # 3. If any update happened, handle timestamps and percentage
        if update_occurred:
            existing_document['last_updated'] = current_time

            # Calculate new percentage based on the *updated* existing_document state
            # This now includes the potentially incremented num_chunks
            new_percentage = calculate_processing_percentage(existing_document)

            # Handle final state overrides for percentage

            status_lower = existing_document.get('status', '')
            if isinstance(status_lower, str):
                status_lower = status_lower.lower()
            elif isinstance(status_lower, bytes):
                status_lower = status_lower.decode('utf-8').lower()
            elif isinstance(status_lower, dict):
                status_lower = json.dumps(status_lower).lower()

            if "processing complete" in status_lower:
                new_percentage = 100
            elif "error" in status_lower or "failed" in status_lower:
                 pass # Percentage already calculated by helper based on 'failed' status

            # Ensure percentage doesn't decrease (unless reset on failure or hitting 100)
            # Compare against original_percentage fetched *before* any updates in this call
            if new_percentage < original_percentage and new_percentage != 0 and "failed" not in status_lower and "error" not in status_lower:
                 existing_document['percentage_complete'] = original_percentage
            else:
                 existing_document['percentage_complete'] = new_percentage

        # 4. Propagate relevant changes to search index chunks
        # This happens regardless of 'update_occurred' flag because the *intent* from kwargs might trigger it,
        # even if the main doc update didn't happen (e.g., only percentage changed).
        # However, it's better to only do this if the relevant fields *actually* changed.
        if update_occurred and updated_fields_requiring_chunk_sync:
            try:
                from services.chunk_service import get_all_chunks, update_chunk_metadata
                chunks_to_update = get_all_chunks(document_id, user_id)
                for chunk in chunks_to_update:
                    chunk_updates = {}
                    if 'title' in updated_fields_requiring_chunk_sync:
                        chunk_updates['title'] = existing_document.get('title')
                    if 'authors' in updated_fields_requiring_chunk_sync:
                         # Ensure authors is a list for the chunk metadata if needed
                        chunk_updates['author'] = existing_document.get('authors')
                    if 'file_name' in updated_fields_requiring_chunk_sync:
                        chunk_updates['file_name'] = existing_document.get('file_name')
                    if 'document_classification' in updated_fields_requiring_chunk_sync:
                        chunk_updates['document_classification'] = existing_document.get('document_classification')
                    if 'tags' in updated_fields_requiring_chunk_sync:
                        chunk_updates['document_tags'] = existing_document.get('tags', [])

                    if chunk_updates: # Only call update if there's something to change
                        # Build the call parameters
                        update_params = {
                            'chunk_id': chunk['id'],
                            'user_id': user_id,
                            'document_id': document_id,
                            'group_id': group_id,
                            **chunk_updates
                        }

                        # Only include shared_group_ids for group workspaces
                        if is_group and 'shared_group_ids' in updated_fields_requiring_chunk_sync:
                            update_params['shared_group_ids'] = existing_document.get('shared_group_ids')

                        update_chunk_metadata(**update_params)
                add_file_task_to_file_processing_log(
                    document_id=document_id,
                    user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
                    content=f"Propagated updates for fields {updated_fields_requiring_chunk_sync} to search chunks."
                )
            except Exception as chunk_sync_error:
                # Log error but don't necessarily fail the whole document update
                error_msg = f"Warning: Failed to sync metadata updates to search chunks for doc {document_id}: {chunk_sync_error}"
                debug_print(error_msg)
                add_file_task_to_file_processing_log(
                    document_id=document_id,
                    user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
                    content=error_msg
                )


        # 5. Upsert the document if changes were made
        if update_occurred:
            cosmos_container.upsert_item(existing_document)

    except CosmosResourceNotFoundError as e:
        # Error already logged where it was first detected
        debug_print(f"Document {document_id} not found or access denied: {e}")
        raise # Re-raise for the caller to handle
    except Exception as e:
        error_msg = f"Error during update_document for {document_id}: {repr(e)}\nTraceback:\n{traceback.format_exc()}"
        debug_print(error_msg)
        add_file_task_to_file_processing_log(
            document_id=document_id,
            user_id=public_workspace_id if is_public_workspace else (group_id if is_group else user_id),
            content=error_msg
        )
        # Optionally update status to failure here if the exception is critical
        # try:
        #    existing_document['status'] = f"Update failed: {str(e)[:100]}" # Truncate error
        #    existing_document['percentage_complete'] = calculate_processing_percentage(existing_document) # Recalculate % based on failure
        #    documents_container.upsert_item(existing_document)
        # except Exception as inner_e:
        #    print(f"Failed to update status to error state for {document_id}: {inner_e}")
        raise # Re-raise the original exception


def get_documents(user_id, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.public_workspace_id = @public_workspace_id
        """
        parameters = [
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id)
        """
        parameters = [
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_user_ids, @user_id)
        """
        parameters = [
            {"name": "@user_id", "value": user_id}
        ]

    try:
        documents = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        latest_documents = {}

        for doc in documents:
            file_name = doc['file_name']
            if file_name not in latest_documents or doc['version'] > latest_documents[file_name]['version']:
                latest_documents[file_name] = doc

        return jsonify({"documents": list(latest_documents.values())}), 200
    except Exception as e:
        return jsonify({'error': f'Error retrieving documents: {str(e)}'}), 500


def get_document(user_id, document_id, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.id = @document_id
                AND (c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.id = @document_id
                AND (
                    c.user_id = @user_id
                    OR ARRAY_CONTAINS(c.shared_user_ids, @user_id)
                    OR EXISTS(SELECT VALUE s FROM s IN c.shared_user_ids WHERE STARTSWITH(s, @user_id_prefix))
                )
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id},
            {"name": "@user_id_prefix", "value": f"{user_id},"}
        ]

    try:
        document_results = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        if not document_results:
            return jsonify({'error': 'Document not found or access denied'}), 404

        return jsonify(document_results[0]), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving document: {str(e)}'}), 500


def get_latest_version(document_id, user_id, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct cosmos_container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT TOP 1 *
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT c.version
            FROM c
            WHERE c.id = @document_id
                AND (c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT c.version
            FROM c
            WHERE c.id = @document_id
                AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_user_ids, @user_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

    try:
        results = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        if results:
            return results[0]['version']
        else:
            return None

    except Exception as e:
        return None


def get_document_version(user_id, document_id, version, group_id=None, public_workspace_id=None):
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.version = @version
                AND c.public_workspace_id = @public_workspace_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@version", "value": version},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.version = @version
                AND (c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@version", "value": version},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.id = @document_id
                AND c.version = @version
                AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_user_ids, @user_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@version", "value": version},
            {"name": "@user_id", "value": user_id}
        ]

    try:
        document_results = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        if not document_results:
            return jsonify({'error': 'Document version not found'}), 404

        return jsonify(document_results[0]), 200

    except Exception as e:
        return jsonify({'error': f'Error retrieving document version: {str(e)}'}), 500


def delete_document(user_id, document_id, group_id=None, public_workspace_id=None):
    """Delete a document from the user's documents in Cosmos DB and blob storage if enhanced citations are enabled."""
    from functions_debug import debug_print

    debug_print(f"[DELETE DOCUMENT] Starting deletion for document: {document_id}, user: {user_id}, group: {group_id}, public_workspace: {public_workspace_id}")

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    try:
        document_item = cosmos_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Log document deletion transaction before deletion
        try:
            from functions_activity_logging import log_document_deletion_transaction

            # Determine workspace type
            if public_workspace_id:
                workspace_type = 'public'
            elif group_id:
                workspace_type = 'group'
            else:
                workspace_type = 'personal'

            # Extract file extension from filename
            file_name = document_item.get('file_name', '')
            file_ext = os.path.splitext(file_name)[-1].lower() if file_name else None

            # Log the deletion transaction with document metadata
            log_document_deletion_transaction(
                user_id=user_id,
                document_id=document_id,
                workspace_type=workspace_type,
                file_name=file_name,
                file_type=file_ext,
                page_count=document_item.get('number_of_pages'),
                version=document_item.get('version'),
                group_id=group_id,
                public_workspace_id=public_workspace_id,
                document_metadata=document_item  # Store full metadata
            )
        except Exception as log_error:
            debug_print(f"⚠️  Warning: Failed to log document deletion transaction: {log_error}")
            # Don't fail the deletion if logging fails

        if is_public_workspace:
            if document_item.get('public_workspace_id') != public_workspace_id:
                raise Exception("Unauthorized access to document")
        elif is_group:
            # For group documents, only the owning group can delete (not shared groups)
            if document_item.get('group_id') != group_id:
                raise Exception("Unauthorized access to document - only document owning group can delete")
        else:
            # For personal documents, only the owner can delete (not shared users)
            if document_item.get('user_id') != user_id:
                raise Exception("Unauthorized access to document - only document owner can delete")

        # Get the file name from the document to use for blob deletion
        file_name = document_item.get('file_name')

        # Delete from blob storage
        try:
            if file_name:
                from services.blob_service import delete_from_blob_storage
                delete_from_blob_storage(document_id, user_id, file_name, group_id, public_workspace_id)
        except Exception as blob_error:
            # Log the error but continue with Cosmos DB deletion
            debug_print(f"Error deleting from blob storage (continuing with document deletion): {str(blob_error)}")

        # Then delete from Cosmos DB
        cosmos_container.delete_item(
            item=document_id,
            partition_key=document_id
        )

    except CosmosResourceNotFoundError:
        raise Exception("Document not found")
    except Exception as e:
        raise


def get_document_versions(user_id, document_id, group_id=None, public_workspace_id=None):
    """ Get all versions of a document for a user."""
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT c.id, c.file_name, c.version, c.upload_date
            FROM c
            WHERE c.id = @document_id
                AND c.public_workspace_id = @public_workspace_id
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@public_workspace_id", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT c.id, c.file_name, c.version, c.upload_date
            FROM c
            WHERE c.id = @document_id
                AND (c.group_id = @group_id OR ARRAY_CONTAINS(c.shared_group_ids, @group_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@group_id", "value": group_id}
        ]
    else:
        query = """
            SELECT c.id, c.file_name, c.version, c.upload_date
            FROM c
            WHERE c.id = @document_id
                AND (c.user_id = @user_id OR ARRAY_CONTAINS(c.shared_user_ids, @user_id))
            ORDER BY c.version DESC
        """
        parameters = [
            {"name": "@document_id", "value": document_id},
            {"name": "@user_id", "value": user_id}
        ]

    try:
        versions_results = list(
            cosmos_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        if not versions_results:
            return []
        return versions_results

    except Exception as e:
        return []


def detect_doc_type(document_id, user_id=None):
    """
    Check Cosmos to see if this doc belongs to the user's docs (has user_id),
    the group's docs (has group_id), or public workspace docs (has public_workspace_id).
    Returns one of: "personal", "group", "public", or None if not found.
    Optionally checks if user_id matches (for user docs).
    """

    try:
        doc_item = cosmos_user_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        if user_id and doc_item.get('user_id') != user_id:
            pass
        else:
            return "personal", doc_item['user_id']
    except:
        pass

    try:
        group_doc_item = cosmos_group_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        return "group", group_doc_item['group_id']
    except:
        pass

    try:
        public_doc_item = cosmos_public_documents_container.read_item(
            document_id,
            partition_key=document_id
        )
        return "public", public_doc_item['public_workspace_id']
    except:
        pass

    return None


def upgrade_legacy_documents(user_id, group_id=None, public_workspace_id=None):
    """
    Finds all user or group docs missing percentage_complete
    and backfills them with the new fields.
    Returns the number of docs updated.
    """
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    # Choose the correct container and query parameters
    if is_public_workspace:
        cosmos_container = cosmos_public_documents_container
    elif is_group:
        cosmos_container = cosmos_group_documents_container
    else:
        cosmos_container = cosmos_user_documents_container

    if is_public_workspace:
        query = """
            SELECT *
            FROM c
            WHERE c.public_workspace_id = @owner
              AND NOT IS_DEFINED(c.percentage_complete)
        """
        parameters = [
            {"name": "@owner", "value": public_workspace_id}
        ]
    elif is_group:
        query = """
            SELECT *
            FROM c
            WHERE c.group_id = @owner
              AND NOT IS_DEFINED(c.percentage_complete)
        """
        parameters = [
            {"name": "@owner", "value": group_id}
        ]
    else:
        query = """
            SELECT *
            FROM c
            WHERE c.user_id = @owner
              AND NOT IS_DEFINED(c.percentage_complete)
        """
        parameters = [
            {"name": "@owner", "value": user_id}
        ]

    # Fetch all legacy docs
    legacy_docs = list(
        cosmos_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
    )

    for doc in legacy_docs:
        # Build the patch arguments
        # Always include document_id first
        if is_group:
            # Group document
            update_document(
                document_id=doc["id"],
                group_id=group_id,
                user_id=user_id,
                status="Processing complete",
                percentage_complete=100,
                num_chunks=doc.get("number_of_pages", doc.get("num_chunks", 1)),
                number_of_pages=doc.get("number_of_pages", doc.get("num_chunks", 1)),
                current_file_chunk=doc.get("num_chunks", 1),
                num_file_chunks=1,
                enhanced_citations=False,
                document_classification="None",
                title="",
                authors=[],
                organization="",
                publication_date="",
                keywords=[],
                abstract="",
                shared_group_ids=[]
            )
        else:
            # Personal document
            update_document(
                document_id=doc["id"],
                user_id=user_id,
                status="Processing complete",
                percentage_complete=100,
                num_chunks=doc.get("number_of_pages", doc.get("num_chunks", 1)),
                number_of_pages=doc.get("number_of_pages", doc.get("num_chunks", 1)),
                current_file_chunk=doc.get("num_chunks", 1),
                num_file_chunks=1,
                enhanced_citations=False,
                document_classification="None",
                title="",
                authors=[],
                organization="",
                publication_date="",
                keywords=[],
                abstract="",
                shared_user_ids=[]
            )

    return len(legacy_docs)