# test_blob_service.py
# Unit tests for services/blob_service.py — Azure Blob Storage operations.

import pytest
from unittest.mock import MagicMock, patch, mock_open


class TestUploadToBlob:
    """Tests for upload_to_blob()."""

    @patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": MagicMock()})
    @patch("services.blob_service.storage_account_user_documents_container_name", "user-docs")
    def test_upload_personal_document(self):
        from services.blob_service import upload_to_blob

        mock_callback = MagicMock()
        mock_blob_client = MagicMock()
        blob_service = MagicMock()
        blob_service.get_blob_client.return_value = mock_blob_client

        with patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": blob_service}):
            with patch("builtins.open", mock_open(read_data=b"file content")):
                result = upload_to_blob(
                    temp_file_path="/tmp/test.pdf",
                    user_id="user-123",
                    document_id="doc-456",
                    blob_filename="test.pdf",
                    update_callback=mock_callback,
                )

        assert result == "user-123/test.pdf"
        mock_callback.assert_called()
        mock_blob_client.upload_blob.assert_called_once()

    @patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": MagicMock()})
    @patch("services.blob_service.storage_account_group_documents_container_name", "group-docs")
    def test_upload_group_document(self):
        from services.blob_service import upload_to_blob

        mock_callback = MagicMock()
        blob_service = MagicMock()
        mock_blob_client = MagicMock()
        blob_service.get_blob_client.return_value = mock_blob_client

        with patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": blob_service}):
            with patch("builtins.open", mock_open(read_data=b"file content")):
                result = upload_to_blob(
                    temp_file_path="/tmp/test.pdf",
                    user_id="user-123",
                    document_id="doc-456",
                    blob_filename="test.pdf",
                    update_callback=mock_callback,
                    group_id="group-789",
                )

        assert result == "group-789/test.pdf"
        blob_service.get_blob_client.assert_called_once()

    @patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": MagicMock()})
    @patch("services.blob_service.storage_account_public_documents_container_name", "public-docs")
    def test_upload_public_document(self):
        from services.blob_service import upload_to_blob

        mock_callback = MagicMock()
        blob_service = MagicMock()
        mock_blob_client = MagicMock()
        blob_service.get_blob_client.return_value = mock_blob_client

        with patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": blob_service}):
            with patch("builtins.open", mock_open(read_data=b"file content")):
                result = upload_to_blob(
                    temp_file_path="/tmp/test.pdf",
                    user_id="user-123",
                    document_id="doc-456",
                    blob_filename="test.pdf",
                    update_callback=mock_callback,
                    public_workspace_id="pub-ws-001",
                )

        assert result == "pub-ws-001/test.pdf"

    def test_upload_without_client_raises(self):
        from services.blob_service import upload_to_blob

        with patch("services.blob_service.CLIENTS", {}):
            with pytest.raises(Exception, match="Blob service client not available"):
                upload_to_blob(
                    temp_file_path="/tmp/test.pdf",
                    user_id="user-123",
                    document_id="doc-456",
                    blob_filename="test.pdf",
                    update_callback=MagicMock(),
                )

    def test_upload_propagates_blob_error(self):
        from services.blob_service import upload_to_blob

        blob_service = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob.side_effect = Exception("Connection timeout")
        blob_service.get_blob_client.return_value = mock_blob_client

        with patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": blob_service}):
            with patch("builtins.open", mock_open(read_data=b"file content")):
                with pytest.raises(Exception, match="Error uploading"):
                    upload_to_blob(
                        temp_file_path="/tmp/test.pdf",
                        user_id="user-123",
                        document_id="doc-456",
                        blob_filename="test.pdf",
                        update_callback=MagicMock(),
                    )


class TestDeleteFromBlobStorage:
    """Tests for delete_from_blob_storage()."""

    @patch("services.blob_service.get_settings")
    def test_skip_when_enhanced_citations_disabled(self, mock_get_settings):
        from services.blob_service import delete_from_blob_storage

        mock_get_settings.return_value = {"enable_enhanced_citations": False}

        # Should return without doing anything
        result = delete_from_blob_storage(
            document_id="doc-123",
            user_id="user-456",
            file_name="test.pdf",
        )
        assert result is None

    @patch("services.blob_service.get_settings")
    def test_delete_personal_document(self, mock_get_settings):
        from services.blob_service import delete_from_blob_storage

        mock_get_settings.return_value = {"enable_enhanced_citations": True}
        mock_blob_client = MagicMock()
        mock_blob_client.exists.return_value = True
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        blob_service = MagicMock()
        blob_service.get_container_client.return_value = mock_container_client

        with patch("services.blob_service.CLIENTS", {"storage_account_office_docs_client": blob_service}):
            with patch("services.blob_service.storage_account_user_documents_container_name", "user-docs"):
                delete_from_blob_storage(
                    document_id="doc-123",
                    user_id="user-456",
                    file_name="test.pdf",
                )

        blob_service.get_container_client.assert_called_once_with("user-docs")
        mock_blob_client.delete_blob.assert_called_once()
