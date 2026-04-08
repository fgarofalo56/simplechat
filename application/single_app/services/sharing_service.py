# sharing_service.py
# Document sharing operations — user and group sharing with approval workflows.

from config import *
from functions_debug import debug_print

def share_document_with_user(document_id, owner_user_id, target_user_id):
    """
    Share a personal document with another user by adding them to shared_user_ids as 'oid,not_approved'.
    Only the document owner can share documents.
    Returns True if successful, False if document not found or access denied.
    """
    try:
        # Get the document to verify ownership and current state
        document_item = cosmos_user_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting user is the owner
        if document_item.get('user_id') != owner_user_id:
            raise Exception("Only document owner can share documents")

        # Initialize shared_user_ids if it doesn't exist
        shared_user_ids = document_item.get('shared_user_ids', [])

        # Check if already shared (by OID, regardless of approval status)
        already_shared = any(entry.startswith(f"{target_user_id},") for entry in shared_user_ids)
        if not already_shared:
            shared_user_ids.append(f"{target_user_id},not_approved")
            document_item['shared_user_ids'] = shared_user_ids
            document_item['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Update the document
            cosmos_user_documents_container.upsert_item(document_item)

            # Update all chunks with the new shared_user_ids
            try:
                from services.chunk_service import get_all_chunks, update_chunk_metadata
                chunks = get_all_chunks(document_id, owner_user_id)
                for chunk in chunks:
                    chunk_id = chunk.get('id')
                    if chunk_id:
                        try:
                            update_chunk_metadata(
                                chunk_id=chunk_id,
                                user_id=owner_user_id,
                                group_id=None,
                                public_workspace_id=None,
                                document_id=document_id,
                                shared_user_ids=shared_user_ids
                            )
                        except Exception as chunk_e:
                            debug_print(f"Warning: Failed to update chunk {chunk_id}: {chunk_e}")
                            # Continue with other chunks
            except Exception as e:
                debug_print(f"Warning: Failed to update chunks for document {document_id}: {e}")
                # Don't fail the whole operation if chunk update fails

            return True

        return True  # Already shared

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error sharing document {document_id}: {e}")
        return False

def unshare_document_from_user(document_id, owner_user_id, target_user_id):
    """
    Remove a user from a document's shared_user_ids list.
    Only the document owner can unshare documents, OR users can remove themselves.
    Returns True if successful, False if document not found or access denied.
    """
    try:
        # Get the document to verify ownership and current state
        document_item = cosmos_user_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting user is the owner OR the user is removing themselves
        actual_owner_id = document_item.get('user_id')
        is_owner = actual_owner_id == owner_user_id
        is_self_removal = owner_user_id == target_user_id

        if not is_owner and not is_self_removal:
            raise Exception("Only document owner can unshare documents, or users can remove themselves")

        # Get current shared_user_ids
        shared_user_ids = document_item.get('shared_user_ids', [])

        # Remove all entries for the target user (by oid prefix)
        new_shared_user_ids = [entry for entry in shared_user_ids if not entry.startswith(f"{target_user_id},")]
        if len(new_shared_user_ids) != len(shared_user_ids):
            document_item['shared_user_ids'] = new_shared_user_ids
            document_item['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Update the document
            cosmos_user_documents_container.upsert_item(document_item)

            # Update all chunks with the new shared_user_ids
            try:
                from services.chunk_service import get_all_chunks, update_chunk_metadata
                chunks = get_all_chunks(document_id, owner_user_id)
                for chunk in chunks:
                    chunk_id = chunk.get('id')
                    if chunk_id:
                        try:
                            update_chunk_metadata(
                                chunk_id=chunk_id,
                                user_id=owner_user_id,
                                group_id=None,
                                public_workspace_id=None,
                                document_id=document_id,
                                shared_user_ids=new_shared_user_ids
                            )
                        except Exception as chunk_e:
                            debug_print(f"Warning: Failed to update chunk {chunk_id}: {chunk_e}")
                            # Continue with other chunks
            except Exception as e:
                debug_print(f"Warning: Failed to update chunks for document {document_id}: {e}")
                # Don't fail the whole operation if chunk update fails

        return True

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error unsharing document {document_id}: {e}")
        return False

def get_shared_users_for_document(document_id, owner_user_id):
    """
    Get the list of users a document is shared with, including approval status.
    Only the document owner can view this information.
    Returns list of dicts: [{'id': oid, 'approval_status': status}, ...] or None if not found/access denied.
    """
    try:
        # Get the document to verify ownership
        document_item = cosmos_user_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting user is the owner
        if document_item.get('user_id') != owner_user_id:
            return None

        shared_user_ids = document_item.get('shared_user_ids', [])
        result = []
        for entry in shared_user_ids:
            if ',' in entry:
                oid, status = entry.split(',', 1)
                result.append({'id': oid, 'approval_status': status})
            else:
                result.append({'id': entry, 'approval_status': 'unknown'})
        return result

    except CosmosResourceNotFoundError:
        return None
    except Exception as e:
        debug_print(f"Error getting shared users for document {document_id}: {e}")
        return None

def is_document_shared_with_user(document_id, user_id):
    """
    Check if a document is shared with a specific user (approved only).
    Returns True if the user has access (owner or shared and approved), False otherwise.
    """
    try:
        # Get the document
        document_item = cosmos_user_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Check if user is owner
        if document_item.get('user_id') == user_id:
            return True

        # Check if user is in shared list with approved status
        shared_user_ids = document_item.get('shared_user_ids', [])
        return any(entry == f"{user_id},approved" for entry in shared_user_ids)

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error checking document access for {document_id}: {e}")
        return False

def get_documents_shared_with_user(user_id):
    """
    Get all documents that are shared with a specific user (not owned by them, and approved).
    Returns list of document metadata or empty list.
    """
    try:
        # Since we can't filter on substring in ARRAY_CONTAINS, fetch all docs and filter in Python
        query = """
            SELECT *
            FROM c
            WHERE c.user_id != @user_id
        """
        parameters = [
            {"name": "@user_id", "value": user_id}
        ]

        documents = list(
            cosmos_user_documents_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        # Only include docs where shared_user_ids contains "{user_id},approved"
        filtered_docs = []
        for doc in documents:
            shared_user_ids = doc.get('shared_user_ids', [])
            if any(entry == f"{user_id},approved" for entry in shared_user_ids):
                filtered_docs.append(doc)

        # Get latest versions only
        latest_documents = {}
        for doc in filtered_docs:
            file_name = doc['file_name']
            if file_name not in latest_documents or doc['version'] > latest_documents[file_name]['version']:
                latest_documents[file_name] = doc

        return list(latest_documents.values())

    except Exception as e:
        debug_print(f"Error getting documents shared with user {user_id}: {e}")
        return []

def share_document_with_group(document_id, owner_group_id, target_group_id):
    """
    Share a group document with another group by adding them to shared_group_ids.
    Only the document owning group can share documents.
    Returns True if successful, False if document not found or access denied.
    """
    try:
        # Get the document to verify ownership and current state
        document_item = cosmos_group_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting group is the owner
        if document_item.get('group_id') != owner_group_id:
            raise Exception("Only document owning group can share documents")

        # Initialize shared_group_ids if it doesn't exist
        shared_group_ids = document_item.get('shared_group_ids', [])

        # Check if already shared (by group OID, regardless of approval status)
        already_shared = any(entry.startswith(f"{target_group_id},") for entry in shared_group_ids)
        if not already_shared:
            shared_group_ids.append(f"{target_group_id},not_approved")
            document_item['shared_group_ids'] = shared_group_ids
            document_item['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Update the document
            cosmos_group_documents_container.upsert_item(document_item)
            return True

        return True  # Already shared

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error sharing document {document_id} with group: {e}")
        return False

def unshare_document_from_group(document_id, owner_group_id, target_group_id):
    """
    Remove a group from a document's shared_group_ids list.
    Only the document owning group can unshare documents.
    Returns True if successful, False if document not found or access denied.
    """
    try:
        # Get the document to verify ownership and current state
        document_item = cosmos_group_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting group is the owner
        if document_item.get('group_id') != owner_group_id:
            raise Exception("Only document owning group can unshare documents")

        # Get current shared_group_ids
        shared_group_ids = document_item.get('shared_group_ids', [])

        # Remove target group if they are in the list
        # Remove all entries for the target group (by oid prefix)
        new_shared_group_ids = [entry for entry in shared_group_ids if not entry.startswith(f"{target_group_id},")]
        if len(new_shared_group_ids) != len(shared_group_ids):
            document_item['shared_group_ids'] = new_shared_group_ids
            document_item['last_updated'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Update the document
            cosmos_group_documents_container.upsert_item(document_item)

        return True

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error unsharing document {document_id} from group: {e}")
        return False

def get_shared_groups_for_document(document_id, owner_group_id):
    """
    Get the list of groups a document is shared with.
    Only the document owning group can view this information.
    Returns list of group IDs or None if document not found or access denied.
    """
    try:
        # Get the document to verify ownership
        document_item = cosmos_group_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Verify the requesting group is the owner
        if document_item.get('group_id') != owner_group_id:
            return None

        return document_item.get('shared_group_ids', [])

    except CosmosResourceNotFoundError:
        return None
    except Exception as e:
        debug_print(f"Error getting shared groups for document {document_id}: {e}")
        return None

def is_document_shared_with_group(document_id, group_id):
    """
    Check if a document is shared with a specific group.
    Returns True if the group has access (owner or shared), False otherwise.
    """
    try:
        # Get the document
        document_item = cosmos_group_documents_container.read_item(
            item=document_id,
            partition_key=document_id
        )

        # Check if group is owner
        if document_item.get('group_id') == group_id:
            return True

        # Check if group is in shared list
        shared_group_ids = document_item.get('shared_group_ids', [])

        # Only allow access if group is owner or in shared_group_ids as approved
        return any(entry == f"{group_id},approved" for entry in shared_group_ids)

    except CosmosResourceNotFoundError:
        return False
    except Exception as e:
        debug_print(f"Error checking document access for group {group_id} on document {document_id}: {e}")
        return False

def get_documents_shared_with_group(group_id):
    """
    Get all documents that are shared with a specific group (not owned by them).
    Returns list of document metadata or empty list.
    """
    try:
        query = """
            SELECT *
            FROM c
            WHERE ARRAY_CONTAINS(c.shared_group_ids, @group_id)
                AND c.group_id != @group_id
        """
        parameters = [
            {"name": "@group_id", "value": group_id}
        ]

        documents = list(
            cosmos_group_documents_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
        )

        # Get latest versions only
        latest_documents = {}
        for doc in documents:
            file_name = doc['file_name']
            if file_name not in latest_documents or doc['version'] > latest_documents[file_name]['version']:
                latest_documents[file_name] = doc

        return list(latest_documents.values())

    except Exception as e:
        debug_print(f"Error getting documents shared with group {group_id}: {e}")
        return []