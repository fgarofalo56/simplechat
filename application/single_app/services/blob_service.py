# blob_service.py
# Azure Blob Storage operations — upload, delete, and content type management.

from config import *
from functions_settings import get_settings
from functions_debug import debug_print


def upload_to_blob(temp_file_path, user_id, document_id, blob_filename, update_callback, group_id=None, public_workspace_id=None):
    """Uploads the file to Azure Blob Storage."""

    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        storage_account_container_name = storage_account_public_documents_container_name
    elif is_group:
        storage_account_container_name = storage_account_group_documents_container_name
    else:
        storage_account_container_name = storage_account_user_documents_container_name

    try:
        if is_public_workspace:
            blob_path = f"{public_workspace_id}/{blob_filename}"
        elif is_group:
            blob_path = f"{group_id}/{blob_filename}"
        else:
            blob_path = f"{user_id}/{blob_filename}"

        blob_service_client = CLIENTS.get("storage_account_office_docs_client")
        if not blob_service_client:
            raise Exception("Blob service client not available or not configured.")

        blob_client = blob_service_client.get_blob_client(
            container=storage_account_container_name,
            blob=blob_path
        )

        metadata = {
            "document_id": str(document_id),
            "group_id": str(group_id) if is_group else None,
            "user_id": str(user_id) if not is_group else None
        }

        metadata = {k: v for k, v in metadata.items() if v is not None}

        update_callback(status=f"Uploading {blob_filename} to Blob Storage...")

        with open(temp_file_path, "rb") as f:
            blob_client.upload_blob(f, overwrite=True, metadata=metadata)

        debug_print(f"Successfully uploaded {blob_filename} to blob storage at {blob_path}")
        return blob_path

    except Exception as e:
        debug_print(f"Error uploading {blob_filename} to Blob Storage: {str(e)}")
        raise Exception(f"Error uploading {blob_filename} to Blob Storage: {str(e)}")


def delete_from_blob_storage(document_id, user_id, file_name, group_id=None, public_workspace_id=None):
    """Delete a document from Azure Blob Storage."""
    is_group = group_id is not None
    is_public_workspace = public_workspace_id is not None

    if is_public_workspace:
        storage_account_container_name = storage_account_public_documents_container_name
    elif is_group:
        storage_account_container_name = storage_account_group_documents_container_name
    else:
        storage_account_container_name = storage_account_user_documents_container_name

    # Check if enhanced citations are enabled and blob client is available
    settings = get_settings()
    enable_enhanced_citations = settings.get("enable_enhanced_citations", False)

    if not enable_enhanced_citations:
        return  # No need to proceed if enhanced citations are disabled

    try:
        # Construct the blob path using the same format as in upload_to_blob
        blob_path = f"{group_id}/{file_name}" if is_group else f"{user_id}/{file_name}"

        # Get the blob client
        blob_service_client = CLIENTS.get("storage_account_office_docs_client")
        if not blob_service_client:
            debug_print(f"Warning: Enhanced citations enabled but blob service client not configured.")
            return

        # Get container client
        container_client = blob_service_client.get_container_client(storage_account_container_name)
        if not container_client:
            debug_print(f"Warning: Could not get container client for {storage_account_container_name}")
            return

        # Get blob client
        blob_client = container_client.get_blob_client(blob_path)

        # Delete the blob if it exists
        if blob_client.exists():
            blob_client.delete_blob()
            debug_print(f"Successfully deleted blob at {blob_path}")
        else:
            debug_print(f"No blob found at {blob_path} to delete")

    except Exception as e:
        debug_print(f"Error deleting document from blob storage: {str(e)}")
        # Don't raise the exception, as we want the Cosmos DB deletion to proceed
        # even if blob deletion fails