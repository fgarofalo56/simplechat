# test_document_service.py
# Unit tests for services/document_service.py — document utility functions and CRUD.

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.usefixtures('set_test_env')
class TestCreateDocument:
    """Tests for create_document() — creates document metadata in Cosmos."""

    def test_creates_personal_document_v1(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])  # No existing docs
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import create_document
            create_document('test.pdf', 'user-1', 'doc-1', 1, 'Queued for processing')
            mock_container.upsert_item.assert_called_once()
            doc = mock_container.upsert_item.call_args[0][0]
            assert doc['id'] == 'doc-1'
            assert doc['file_name'] == 'test.pdf'
            assert doc['user_id'] == 'user-1'
            assert doc['version'] == 1
            assert doc['status'] == 'Queued for processing'
            assert doc['tags'] == []
            assert doc['percentage_complete'] == 0

    def test_creates_version_2_when_existing(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'file_name': 'test.pdf', 'version': 1}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import create_document
            create_document('test.pdf', 'user-1', 'doc-2', 1, 'Queued')
            doc = mock_container.upsert_item.call_args[0][0]
            assert doc['version'] == 2

    def test_creates_group_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import create_document
            create_document('test.pdf', 'user-1', 'doc-1', 1, 'Queued', group_id='grp-1')
            doc = mock_container.upsert_item.call_args[0][0]
            assert doc['group_id'] == 'grp-1'
            assert 'shared_group_ids' in doc

    def test_creates_public_workspace_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import create_document
            create_document('test.pdf', 'user-1', 'doc-1', 1, 'Queued', public_workspace_id='pw-1')
            doc = mock_container.upsert_item.call_args[0][0]
            assert doc['public_workspace_id'] == 'pw-1'

    def test_cosmos_error_raises(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import create_document
            with pytest.raises(Exception, match="Cosmos error"):
                create_document('test.pdf', 'user-1', 'doc-1', 1, 'Queued')


@pytest.mark.usefixtures('set_test_env')
class TestUpdateDocument:
    """Tests for update_document() — updates document metadata in Cosmos."""

    def test_updates_status_field(self):
        mock_container = MagicMock()
        existing_doc = {
            'id': 'doc-1', 'user_id': 'user-1', 'file_name': 'test.pdf',
            'version': 1, 'status': 'Queued', 'percentage_complete': 0,
            'num_chunks': 0, 'tags': []
        }
        mock_container.query_items.return_value = iter([existing_doc])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            update_document(document_id='doc-1', user_id='user-1', status='Processing complete')
            mock_container.upsert_item.assert_called_once()

    def test_missing_document_id_raises(self):
        with patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            with pytest.raises(ValueError, match="document_id and user_id are required"):
                update_document(document_id=None, user_id='user-1')

    def test_missing_user_id_raises(self):
        with patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            with pytest.raises(ValueError, match="document_id and user_id are required"):
                update_document(document_id='doc-1', user_id=None)

    def test_document_not_found_raises_cosmos_error(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            with pytest.raises(CosmosResourceNotFoundError):
                update_document(document_id='doc-1', user_id='user-1', status='Processing')

    def test_increments_num_chunks(self):
        mock_container = MagicMock()
        existing_doc = {
            'id': 'doc-1', 'user_id': 'user-1', 'file_name': 'test.pdf',
            'version': 1, 'status': 'Processing', 'percentage_complete': 10,
            'num_chunks': 5, 'tags': []
        }
        mock_container.query_items.return_value = iter([existing_doc])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            update_document(document_id='doc-1', user_id='user-1', num_chunks_increment=3)
            upserted = mock_container.upsert_item.call_args[0][0]
            assert upserted['num_chunks'] == 8  # 5 + 3

    def test_group_document_update(self):
        mock_container = MagicMock()
        existing_doc = {
            'id': 'doc-1', 'group_id': 'grp-1', 'user_id': 'user-1',
            'file_name': 'test.pdf', 'version': 1, 'status': 'Queued',
            'percentage_complete': 0, 'num_chunks': 0, 'tags': [],
            'shared_group_ids': []
        }
        mock_container.query_items.return_value = iter([existing_doc])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            update_document(document_id='doc-1', user_id='user-1', group_id='grp-1', status='Processing')
            mock_container.upsert_item.assert_called_once()

    def test_no_change_skips_upsert(self):
        mock_container = MagicMock()
        existing_doc = {
            'id': 'doc-1', 'document_id': 'doc-1', 'user_id': 'user-1',
            'file_name': 'test.pdf', 'version': 1, 'status': 'Queued',
            'percentage_complete': 0, 'num_chunks': 0, 'tags': []
        }
        mock_container.query_items.return_value = iter([existing_doc])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import update_document
            # Update with same values — no actual change
            update_document(document_id='doc-1', user_id='user-1', status='Queued')
            mock_container.upsert_item.assert_not_called()


@pytest.mark.usefixtures('set_test_env')
class TestAllowedFile:
    """Tests for allowed_file() — file extension validation."""

    def test_allowed_txt_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('document.txt', {'txt', 'pdf', 'docx'}) is True

    def test_allowed_pdf_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('report.pdf', {'txt', 'pdf', 'docx'}) is True

    def test_disallowed_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('malware.exe', {'txt', 'pdf', 'docx'}) is False

    def test_no_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('noextension', {'txt', 'pdf'}) is False

    def test_uppercase_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('DOCUMENT.TXT', {'txt', 'pdf'}) is True

    def test_mixed_case_extension(self):
        from services.document_service import allowed_file
        assert allowed_file('File.PdF', {'txt', 'pdf'}) is True

    def test_double_extension_uses_last(self):
        from services.document_service import allowed_file
        assert allowed_file('archive.tar.gz', {'gz', 'zip'}) is True

    def test_empty_filename(self):
        from services.document_service import allowed_file
        assert allowed_file('', {'txt'}) is False

    def test_dot_only_filename(self):
        from services.document_service import allowed_file
        # '.' has no text after split, rsplit('.', 1) -> ['', '']
        # '' in {'txt'} is False
        assert allowed_file('.', {'txt'}) is False

    def test_hidden_file_with_valid_ext(self):
        from services.document_service import allowed_file
        assert allowed_file('.hidden.txt', {'txt'}) is True

    def test_uses_default_allowed_extensions(self):
        """When no allowed_extensions provided, falls back to ALLOWED_EXTENSIONS."""
        with patch('services.document_service.ALLOWED_EXTENSIONS', {'pdf', 'docx'}, create=True):
            from services.document_service import allowed_file
            assert allowed_file('test.pdf') is True
            assert allowed_file('test.exe') is False


@pytest.mark.usefixtures('set_test_env')
class TestCalculateProcessingPercentage:
    """Tests for calculate_processing_percentage() — progress computation."""

    def test_processing_complete_returns_100(self):
        from services.document_service import calculate_processing_percentage
        assert calculate_processing_percentage({'status': 'Processing complete'}) == 100

    def test_processing_complete_case_insensitive(self):
        from services.document_service import calculate_processing_percentage
        assert calculate_processing_percentage({'status': 'PROCESSING COMPLETE'}) == 100

    def test_already_at_100_returns_100(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'some status',
            'percentage_complete': 100
        })
        assert result == 100

    def test_error_status_keeps_current_percentage(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Error: something went wrong',
            'percentage_complete': 45
        })
        assert result == 45

    def test_failed_status_keeps_current_percentage(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Processing failed',
            'percentage_complete': 30
        })
        assert result == 30

    def test_queued_returns_zero(self):
        from services.document_service import calculate_processing_percentage
        assert calculate_processing_percentage({'status': 'Queued for processing'}) == 0

    def test_sending_returns_5(self):
        from services.document_service import calculate_processing_percentage
        assert calculate_processing_percentage({'status': 'Sending to Azure DI...'}) == 5

    def test_saving_page_halfway(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Saving page 5/10...',
            'number_of_pages': 10,
            'current_file_chunk': 5,
            'percentage_complete': 0
        })
        # 5 + (5/10 * 80) = 5 + 40 = 45
        assert result == 45

    def test_saving_chunk_at_start(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Saving chunk 1/100...',
            'number_of_pages': 100,
            'current_file_chunk': 1,
            'percentage_complete': 0
        })
        assert 5 <= result <= 10

    def test_saving_chunk_near_end(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Saving chunk 99/100...',
            'number_of_pages': 100,
            'current_file_chunk': 99,
            'percentage_complete': 0
        })
        assert result >= 80

    def test_saving_page_unknown_page_count(self):
        """When number_of_pages is 0 during page saving, returns 5."""
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Saving chunk 3/...',
            'number_of_pages': 0,
            'current_file_chunk': 3,
            'percentage_complete': 0
        })
        assert result == 5

    def test_extracting_final_metadata_returns_95(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Extracting final metadata...',
            'percentage_complete': 80
        })
        assert result == 95

    def test_unknown_status_uses_current_pct(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Some unknown status',
            'percentage_complete': 42
        })
        assert result == 42

    def test_empty_status_uses_current_pct(self):
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': '',
            'percentage_complete': 10
        })
        assert result == 10

    def test_no_metadata_returns_zero(self):
        from services.document_service import calculate_processing_percentage
        assert calculate_processing_percentage({}) == 0

    def test_dict_status_handled(self):
        """Status as dict should be JSON-serialized and processed."""
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': {'message': 'processing complete'},
            'percentage_complete': 0
        })
        assert result == 100

    def test_bytes_status_handled(self):
        """Status as bytes should be decoded and processed."""
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': b'Sending data...',
            'percentage_complete': 0
        })
        assert result == 5

    def test_percentage_never_goes_down(self):
        """Percentage should never decrease from current value."""
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Queued for processing',
            'percentage_complete': 50
        })
        # Queued computes 0, but current is 50, so max(0, 50) = 50
        assert result == 50

    def test_capped_at_99_before_complete(self):
        """Non-complete status should never exceed 99%."""
        from services.document_service import calculate_processing_percentage
        result = calculate_processing_percentage({
            'status': 'Saving chunk 100/100...',
            'number_of_pages': 100,
            'current_file_chunk': 100,
            'percentage_complete': 0
        })
        # 5 + (100/100 * 80) = 85, capped at min(85, 99) = 85
        assert result <= 99


@pytest.mark.usefixtures('set_test_env')
class TestDetectDocType:
    """Tests for detect_doc_type() — determines document workspace type."""

    def test_personal_document_found(self):
        with patch('services.document_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'doc-1',
                'user_id': 'user-1'
            }
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-1', 'user-1')
            assert result == ("personal", "user-1")

    def test_personal_doc_wrong_user_falls_through(self):
        """If user_id doesn't match, should try group and public containers."""
        mock_user = MagicMock()
        mock_user.read_item.return_value = {'id': 'doc-1', 'user_id': 'other-user'}
        mock_group = MagicMock()
        mock_group.read_item.side_effect = Exception("Not found")
        mock_public = MagicMock()
        mock_public.read_item.side_effect = Exception("Not found")

        with patch('services.document_service.cosmos_user_documents_container', mock_user, create=True), \
             patch('services.document_service.cosmos_group_documents_container', mock_group, create=True), \
             patch('services.document_service.cosmos_public_documents_container', mock_public, create=True):
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-1', 'user-1')
            assert result is None

    def test_group_document_found(self):
        mock_user = MagicMock()
        mock_user.read_item.side_effect = Exception("Not found")
        mock_group = MagicMock()
        mock_group.read_item.return_value = {'id': 'doc-1', 'group_id': 'group-1'}

        with patch('services.document_service.cosmos_user_documents_container', mock_user, create=True), \
             patch('services.document_service.cosmos_group_documents_container', mock_group, create=True):
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-1')
            assert result == ("group", "group-1")

    def test_public_document_found(self):
        mock_user = MagicMock()
        mock_user.read_item.side_effect = Exception("Not found")
        mock_group = MagicMock()
        mock_group.read_item.side_effect = Exception("Not found")
        mock_public = MagicMock()
        mock_public.read_item.return_value = {'id': 'doc-1', 'public_workspace_id': 'pw-1'}

        with patch('services.document_service.cosmos_user_documents_container', mock_user, create=True), \
             patch('services.document_service.cosmos_group_documents_container', mock_group, create=True), \
             patch('services.document_service.cosmos_public_documents_container', mock_public, create=True):
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-1')
            assert result == ("public", "pw-1")

    def test_document_not_found_anywhere(self):
        mock_user = MagicMock()
        mock_user.read_item.side_effect = Exception("Not found")
        mock_group = MagicMock()
        mock_group.read_item.side_effect = Exception("Not found")
        mock_public = MagicMock()
        mock_public.read_item.side_effect = Exception("Not found")

        with patch('services.document_service.cosmos_user_documents_container', mock_user, create=True), \
             patch('services.document_service.cosmos_group_documents_container', mock_group, create=True), \
             patch('services.document_service.cosmos_public_documents_container', mock_public, create=True):
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-nonexistent')
            assert result is None

    def test_no_user_id_returns_personal_for_any_user(self):
        """When user_id is None, should return personal doc without user check."""
        with patch('services.document_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'doc-1',
                'user_id': 'some-user'
            }
            from services.document_service import detect_doc_type
            result = detect_doc_type('doc-1', user_id=None)
            assert result == ("personal", "some-user")


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentMetadata:
    """Tests for get_document_metadata() — retrieves document metadata from Cosmos."""

    def test_personal_document_found(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'user_id': 'user-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True):
            from services.document_service import get_document_metadata
            result = get_document_metadata('doc-1', 'user-1')
            assert result is not None
            assert result['id'] == 'doc-1'
            mock_container.query_items.assert_called_once()

    def test_group_document_found(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'group_id': 'grp-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True):
            from services.document_service import get_document_metadata
            result = get_document_metadata('doc-1', 'user-1', group_id='grp-1')
            assert result is not None
            assert result['group_id'] == 'grp-1'

    def test_public_workspace_document_found(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'public_workspace_id': 'pw-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True):
            from services.document_service import get_document_metadata
            result = get_document_metadata('doc-1', 'user-1', public_workspace_id='pw-1')
            assert result is not None
            assert result['public_workspace_id'] == 'pw-1'

    def test_document_not_found_returns_none(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True):
            from services.document_service import get_document_metadata
            result = get_document_metadata('nonexistent', 'user-1')
            assert result is None

    def test_exception_returns_none(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import get_document_metadata
            result = get_document_metadata('doc-1', 'user-1')
            assert result is None

    def test_uses_parameterized_queries(self):
        """Verify parameterized queries are used (no f-string injection)."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.add_file_task_to_file_processing_log', create=True):
            from services.document_service import get_document_metadata
            get_document_metadata('doc-1', 'user-1')
            call_args = mock_container.query_items.call_args
            # Should use parameters kwarg, not f-string
            assert 'parameters' in call_args.kwargs or len(call_args.args) > 1


@pytest.mark.usefixtures('set_test_env', 'app_context')
class TestGetDocuments:
    """Tests for get_documents() — retrieves all documents for a user/group/workspace."""

    def test_personal_documents_returned(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'user_id': 'user-1', 'version': 1},
            {'id': 'doc-2', 'file_name': 'b.pdf', 'user_id': 'user-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1')
            assert status_code == 200
            data = response.get_json()
            assert len(data['documents']) == 2

    def test_latest_version_per_file(self):
        """When multiple versions exist, only latest should be returned."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'user_id': 'user-1', 'version': 1},
            {'id': 'doc-1-v2', 'file_name': 'a.pdf', 'user_id': 'user-1', 'version': 2}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1')
            assert status_code == 200
            data = response.get_json()
            assert len(data['documents']) == 1
            assert data['documents'][0]['version'] == 2

    def test_group_documents(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'group_id': 'grp-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1', group_id='grp-1')
            assert status_code == 200

    def test_public_workspace_documents(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'public_workspace_id': 'pw-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1', public_workspace_id='pw-1')
            assert status_code == 200

    def test_cosmos_error_returns_500(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos unavailable")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1')
            assert status_code == 500
            data = response.get_json()
            assert 'error' in data

    def test_empty_result_returns_empty_list(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_documents
            response, status_code = get_documents('user-1')
            assert status_code == 200
            data = response.get_json()
            assert data['documents'] == []


@pytest.mark.usefixtures('set_test_env', 'app_context')
class TestGetDocument:
    """Tests for get_document() — retrieves a single document by ID."""

    def test_personal_document_found(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'user_id': 'user-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document
            response, status_code = get_document('user-1', 'doc-1')
            assert status_code == 200
            data = response.get_json()
            assert data['id'] == 'doc-1'

    def test_document_not_found_returns_404(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document
            response, status_code = get_document('user-1', 'nonexistent')
            assert status_code == 404

    def test_group_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'group_id': 'grp-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_document
            response, status_code = get_document('user-1', 'doc-1', group_id='grp-1')
            assert status_code == 200

    def test_public_workspace_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'public_workspace_id': 'pw-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True):
            from services.document_service import get_document
            response, status_code = get_document('user-1', 'doc-1', public_workspace_id='pw-1')
            assert status_code == 200

    def test_cosmos_error_returns_500(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document
            response, status_code = get_document('user-1', 'doc-1')
            assert status_code == 500
            data = response.get_json()
            assert 'error' in data


@pytest.mark.usefixtures('set_test_env')
class TestGetLatestVersion:
    """Tests for get_latest_version() — retrieves latest document version number."""

    def test_returns_latest_version(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([{'version': 3}])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_latest_version
            result = get_latest_version('doc-1', 'user-1')
            assert result == 3

    def test_no_results_returns_none(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_latest_version
            result = get_latest_version('doc-1', 'user-1')
            assert result is None

    def test_group_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([{'version': 5}])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_latest_version
            result = get_latest_version('doc-1', 'user-1', group_id='grp-1')
            assert result == 5

    def test_public_workspace_document(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([{'version': 2}])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True):
            from services.document_service import get_latest_version
            result = get_latest_version('doc-1', 'user-1', public_workspace_id='pw-1')
            assert result == 2

    def test_exception_returns_none(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_latest_version
            result = get_latest_version('doc-1', 'user-1')
            assert result is None


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentVersions:
    """Tests for get_document_versions() — retrieves all versions of a document."""

    def test_returns_all_versions(self):
        mock_container = MagicMock()
        versions_data = [
            {'id': 'doc-1', 'file_name': 'a.pdf', 'version': 3, 'upload_date': '2024-01-03'},
            {'id': 'doc-1', 'file_name': 'a.pdf', 'version': 2, 'upload_date': '2024-01-02'},
            {'id': 'doc-1', 'file_name': 'a.pdf', 'version': 1, 'upload_date': '2024-01-01'},
        ]
        mock_container.query_items.return_value = iter(versions_data)
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_versions
            result = get_document_versions('user-1', 'doc-1')
            assert len(result) == 3
            assert result[0]['version'] == 3

    def test_no_versions_returns_empty_list(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_versions
            result = get_document_versions('user-1', 'doc-1')
            assert result == []

    def test_group_document_versions(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'version': 1, 'upload_date': '2024-01-01'}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_document_versions
            result = get_document_versions('user-1', 'doc-1', group_id='grp-1')
            assert len(result) == 1

    def test_public_workspace_versions(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'version': 1, 'upload_date': '2024-01-01'}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True):
            from services.document_service import get_document_versions
            result = get_document_versions('user-1', 'doc-1', public_workspace_id='pw-1')
            assert len(result) == 1

    def test_exception_returns_empty_list(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_versions
            result = get_document_versions('user-1', 'doc-1')
            assert result == []


@pytest.mark.usefixtures('set_test_env')
class TestDeleteDocument:
    """Tests for delete_document() — deletes a document from Cosmos and blob storage."""

    def test_successful_personal_doc_deletion(self):
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            'id': 'doc-1', 'user_id': 'user-1', 'file_name': 'test.pdf',
            'number_of_pages': 5, 'version': 1
        }
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.debug_print', create=True), \
             patch('functions_activity_logging.log_document_deletion_transaction', create=True), \
             patch('services.blob_service.delete_from_blob_storage', create=True):
            from services.document_service import delete_document
            delete_document('user-1', 'doc-1')
            mock_container.delete_item.assert_called_once_with(
                item='doc-1', partition_key='doc-1'
            )

    def test_unauthorized_personal_doc_raises(self):
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            'id': 'doc-1', 'user_id': 'other-user', 'file_name': 'test.pdf'
        }
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.debug_print', create=True), \
             patch('functions_activity_logging.log_document_deletion_transaction', create=True):
            from services.document_service import delete_document
            with pytest.raises(Exception, match="Unauthorized"):
                delete_document('user-1', 'doc-1')

    def test_unauthorized_group_doc_raises(self):
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            'id': 'doc-1', 'group_id': 'other-group', 'file_name': 'test.pdf'
        }
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.document_service.debug_print', create=True), \
             patch('functions_activity_logging.log_document_deletion_transaction', create=True):
            from services.document_service import delete_document
            with pytest.raises(Exception, match="Unauthorized"):
                delete_document('user-1', 'doc-1', group_id='grp-1')

    def test_not_found_raises(self):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        mock_container = MagicMock()
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            status_code=404, message="Not found"
        )
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import delete_document
            with pytest.raises(Exception, match="Document not found"):
                delete_document('user-1', 'nonexistent')

    def test_blob_deletion_failure_continues(self):
        """Blob storage errors should not prevent Cosmos deletion."""
        mock_container = MagicMock()
        mock_container.read_item.return_value = {
            'id': 'doc-1', 'user_id': 'user-1', 'file_name': 'test.pdf',
            'number_of_pages': 5, 'version': 1
        }
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.debug_print', create=True), \
             patch('functions_activity_logging.log_document_deletion_transaction', create=True), \
             patch('services.blob_service.delete_from_blob_storage', side_effect=Exception("Blob error"), create=True):
            from services.document_service import delete_document
            delete_document('user-1', 'doc-1')
            # Cosmos deletion should still happen
            mock_container.delete_item.assert_called_once()


@pytest.mark.usefixtures('set_test_env', 'app_context')
class TestGetDocumentVersion:
    """Tests for get_document_version() — retrieves a specific version of a document."""

    def test_personal_version_found(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'user_id': 'user-1', 'version': 2}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            response, status_code = get_document_version('user-1', 'doc-1', 2)
            assert status_code == 200
            data = response.get_json()
            assert data['id'] == 'doc-1'
            assert data['version'] == 2

    def test_version_not_found_returns_404(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            response, status_code = get_document_version('user-1', 'doc-1', 99)
            assert status_code == 404
            data = response.get_json()
            assert 'error' in data

    def test_group_document_version(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'group_id': 'grp-1', 'version': 3}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            response, status_code = get_document_version('user-1', 'doc-1', 3, group_id='grp-1')
            assert status_code == 200
            data = response.get_json()
            assert data['version'] == 3

    def test_public_workspace_version(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'public_workspace_id': 'pw-1', 'version': 1}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            response, status_code = get_document_version('user-1', 'doc-1', 1, public_workspace_id='pw-1')
            assert status_code == 200
            data = response.get_json()
            assert data['version'] == 1

    def test_cosmos_error_returns_500(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            response, status_code = get_document_version('user-1', 'doc-1', 1)
            assert status_code == 500
            data = response.get_json()
            assert 'error' in data

    def test_uses_parameterized_query_personal(self):
        """Verify parameterized query includes user_id, document_id, and version."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            get_document_version('user-1', 'doc-1', 2)
            call_kwargs = mock_container.query_items.call_args
            params = call_kwargs.kwargs.get('parameters', call_kwargs[1].get('parameters', []))
            param_names = [p['name'] for p in params]
            assert '@user_id' in param_names
            assert '@document_id' in param_names
            assert '@version' in param_names

    def test_uses_parameterized_query_group(self):
        """Verify parameterized query includes group_id for group documents."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True):
            from services.document_service import get_document_version
            get_document_version('user-1', 'doc-1', 1, group_id='grp-1')
            call_kwargs = mock_container.query_items.call_args
            params = call_kwargs.kwargs.get('parameters', call_kwargs[1].get('parameters', []))
            param_names = [p['name'] for p in params]
            assert '@group_id' in param_names
            assert '@document_id' in param_names
            assert '@version' in param_names


@pytest.mark.usefixtures('set_test_env')
class TestUpgradeLegacyDocuments:
    """Tests for upgrade_legacy_documents() — backfills legacy docs missing percentage_complete."""

    def test_no_legacy_docs_returns_zero(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True):
            from services.document_service import upgrade_legacy_documents
            result = upgrade_legacy_documents('user-1')
            assert result == 0

    def test_upgrades_personal_legacy_docs(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'user_id': 'user-1', 'number_of_pages': 5}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.update_document') as mock_update, \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import upgrade_legacy_documents
            result = upgrade_legacy_documents('user-1')
            assert result == 1
            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs['document_id'] == 'doc-1'
            assert call_kwargs['percentage_complete'] == 100
            assert call_kwargs['status'] == 'Processing complete'
            assert call_kwargs['enhanced_citations'] is False

    def test_upgrades_group_legacy_docs(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'group_id': 'grp-1', 'num_chunks': 3}
        ])
        with patch('services.document_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.document_service.update_document') as mock_update, \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import upgrade_legacy_documents
            result = upgrade_legacy_documents('user-1', group_id='grp-1')
            assert result == 1
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs['group_id'] == 'grp-1'
            assert call_kwargs['num_chunks'] == 3

    def test_upgrades_public_workspace_legacy_docs(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'public_workspace_id': 'pw-1'}
        ])
        with patch('services.document_service.cosmos_public_documents_container', mock_container, create=True), \
             patch('services.document_service.update_document') as mock_update, \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import upgrade_legacy_documents
            result = upgrade_legacy_documents('user-1', public_workspace_id='pw-1')
            assert result == 1

    def test_upgrades_multiple_legacy_docs(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'a.pdf', 'user_id': 'user-1', 'number_of_pages': 2},
            {'id': 'doc-2', 'file_name': 'b.pdf', 'user_id': 'user-1', 'number_of_pages': 4},
            {'id': 'doc-3', 'file_name': 'c.pdf', 'user_id': 'user-1', 'num_chunks': 1},
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.update_document') as mock_update, \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import upgrade_legacy_documents
            result = upgrade_legacy_documents('user-1')
            assert result == 3
            assert mock_update.call_count == 3

    def test_fallback_to_num_chunks_when_no_pages(self):
        """When number_of_pages is missing, should fall back to num_chunks."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'id': 'doc-1', 'file_name': 'test.pdf', 'user_id': 'user-1', 'num_chunks': 7}
        ])
        with patch('services.document_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.document_service.update_document') as mock_update, \
             patch('services.document_service.debug_print', create=True):
            from services.document_service import upgrade_legacy_documents
            upgrade_legacy_documents('user-1')
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs['num_chunks'] == 7
            assert call_kwargs['number_of_pages'] == 7
