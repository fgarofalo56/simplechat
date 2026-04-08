# test_chunk_service.py
# Unit tests for services/chunk_service.py

import pytest
from unittest.mock import Mock, patch, MagicMock


# All names imported into chunk_service via 'from config import *' and
# 'from functions_logging import *' may or may not exist on the module
# depending on which parts of the config chain loaded successfully in
# the test environment.  Using create=True lets patch create the attribute
# if it doesn't already exist.


@pytest.mark.usefixtures('set_test_env')
class TestSaveChunks:
    """Test save_chunks function with various inputs and workspace types."""

    def test_save_chunks_personal_document(self):
        """Test saving chunks for personal documents."""
        with patch('services.document_service.get_document_metadata') as mock_get_metadata, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_generate_embedding, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients:

            mock_metadata = {
                'version': 2,
                'tags': ['tag1', 'tag2'],
                'shared_user_ids': ['user2', 'user3']
            }
            mock_get_metadata.return_value = mock_metadata
            mock_generate_embedding.return_value = ([0.1, 0.2, 0.3], {'tokens': 100})
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_chunks

            token_usage = save_chunks(
                page_text_content="Sample text content",
                page_number=1,
                file_name="test.pdf",
                user_id="user1",
                document_id="doc1"
            )

            assert token_usage == {'tokens': 100}
            mock_get_metadata.assert_called_once()
            mock_generate_embedding.assert_called_once_with("Sample text content")
            mock_search_client.upload_documents.assert_called_once()

            uploaded_doc = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded_doc['id'] == "doc1_1"
            assert uploaded_doc['document_id'] == "doc1"
            assert uploaded_doc['chunk_text'] == "Sample text content"

    def test_save_chunks_empty_text(self):
        """Test saving chunks with empty text content."""
        with patch('services.document_service.get_document_metadata') as mock_get_metadata, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_generate_embedding, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients:

            mock_get_metadata.return_value = {'version': 1}
            mock_generate_embedding.return_value = ([0.0], {'tokens': 1})
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_chunks

            save_chunks(
                page_text_content="",
                page_number=1,
                file_name="empty.txt",
                user_id="user1",
                document_id="doc1"
            )

            uploaded_doc = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded_doc['chunk_text'] == ""
            mock_generate_embedding.assert_called_once_with("")

    def test_save_chunks_missing_metadata(self):
        """Test error handling when document metadata is not found."""
        with patch('services.document_service.get_document_metadata') as mock_get_metadata, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True):

            mock_get_metadata.return_value = None

            from services.chunk_service import save_chunks

            with pytest.raises(ValueError, match="No metadata found for document"):
                save_chunks(
                    page_text_content="test",
                    page_number=1,
                    file_name="test.txt",
                    user_id="user1",
                    document_id="nonexistent"
                )


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentMetadataForCitations:
    """Test get_document_metadata_for_citations function."""

    def test_get_metadata_personal_document_success(self):
        """Test retrieving metadata for personal document."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_doc = {
                'id': 'doc1',
                'keywords': ['keyword1', 'keyword2'],
                'abstract': 'Document abstract',
                'file_name': 'test.pdf'
            }
            mock_container.read_item.return_value = mock_doc

            from services.chunk_service import get_document_metadata_for_citations

            result = get_document_metadata_for_citations("doc1", user_id="user1")

            assert result == {
                'keywords': ['keyword1', 'keyword2'],
                'abstract': 'Document abstract',
                'file_name': 'test.pdf'
            }

    def test_get_metadata_no_keywords_or_abstract(self):
        """Test when document has no keywords or abstract."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_doc = {'id': 'doc1', 'file_name': 'test.pdf'}
            mock_container.read_item.return_value = mock_doc

            from services.chunk_service import get_document_metadata_for_citations

            result = get_document_metadata_for_citations("doc1", user_id="user1")

            assert result is None

    def test_get_metadata_document_not_found(self):
        """Test when document is not found."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.side_effect = Exception("Document not found")

            from services.chunk_service import get_document_metadata_for_citations

            result = get_document_metadata_for_citations("nonexistent", user_id="user1")

            assert result is None


@pytest.mark.usefixtures('set_test_env')
class TestGetBatchDocumentMetadataForCitations:
    """Test get_batch_document_metadata_for_citations function."""

    def test_batch_metadata_empty_requests(self):
        """Test batch retrieval with empty request list."""
        from services.chunk_service import get_batch_document_metadata_for_citations

        result = get_batch_document_metadata_for_citations([])
        assert result == {}

    def test_batch_metadata_mixed_containers(self):
        """Test batch retrieval from different container types."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_user_container, \
             patch('services.chunk_service.cosmos_group_documents_container', create=True) as mock_group_container, \
             patch('services.chunk_service.cosmos_public_documents_container', create=True) as mock_public_container:

            mock_user_container.read_item.return_value = {
                'keywords': ['user'], 'abstract': 'User doc', 'file_name': 'user.pdf'
            }
            mock_group_container.read_item.return_value = {
                'keywords': ['group'], 'abstract': 'Group doc', 'file_name': 'group.pdf'
            }
            mock_public_container.read_item.return_value = {
                'keywords': ['public'], 'abstract': 'Public doc', 'file_name': 'public.pdf'
            }

            requests = [
                {'document_id': 'user_doc', 'user_id': 'user1'},
                {'document_id': 'group_doc', 'group_id': 'group1'},
                {'document_id': 'public_doc', 'public_workspace_id': 'public1'}
            ]

            from services.chunk_service import get_batch_document_metadata_for_citations

            result = get_batch_document_metadata_for_citations(requests)

            assert len(result) == 3
            assert result['user_doc']['keywords'] == ['user']
            assert result['group_doc']['keywords'] == ['group']
            assert result['public_doc']['keywords'] == ['public']


@pytest.mark.usefixtures('set_test_env')
class TestGetAllChunks:
    """Test get_all_chunks function."""

    def test_get_all_chunks_personal_document(self):
        """Test retrieving all chunks for personal document."""
        with patch('services.sharing_service.is_document_shared_with_user') as mock_is_shared, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients:

            mock_is_shared.return_value = True
            mock_search_client = Mock()
            mock_results = [
                {'id': 'doc1_1', 'chunk_text': 'chunk 1'},
                {'id': 'doc1_2', 'chunk_text': 'chunk 2'}
            ]
            mock_search_client.search.return_value = mock_results
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import get_all_chunks

            result = get_all_chunks("doc1", "user1")

            assert result == mock_results
            mock_is_shared.assert_called_once_with("doc1", "user1")

    def test_get_all_chunks_no_access(self):
        """Test access denied when user doesn't have document access."""
        with patch('services.sharing_service.is_document_shared_with_user') as mock_is_shared:
            mock_is_shared.return_value = False

            from services.chunk_service import get_all_chunks

            result = get_all_chunks("doc1", "user1")

            assert result == []


@pytest.mark.usefixtures('set_test_env')
class TestDeleteDocumentChunks:
    """Test delete_document_chunks function."""

    def test_delete_chunks_personal_document(self):
        """Test deleting chunks for personal document."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.sanitize_odata_value', create=True) as mock_sanitize, \
             patch('services.chunk_service.IndexDocumentsBatch', create=True) as mock_batch_class:

            mock_sanitize.return_value = "doc1"
            mock_search_client = Mock()
            mock_search_client.search.return_value = [{'id': 'doc1_1'}, {'id': 'doc1_2'}]
            mock_batch = Mock()
            mock_batch_class.return_value = mock_batch
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import delete_document_chunks

            delete_document_chunks("doc1")

            mock_search_client.search.assert_called_once()
            mock_batch.add_delete_actions.assert_called_once()
            mock_search_client.index_documents.assert_called_once_with(mock_batch)

    def test_delete_chunks_no_chunks_found(self):
        """Test deleting chunks when no chunks exist."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.sanitize_odata_value', create=True) as mock_sanitize:

            mock_sanitize.return_value = "doc1"
            mock_search_client = Mock()
            mock_search_client.search.return_value = []
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import delete_document_chunks

            delete_document_chunks("doc1")

            mock_search_client.search.assert_called_once()
            mock_search_client.index_documents.assert_not_called()


@pytest.mark.usefixtures('set_test_env')
class TestGetPdfPageCount:
    """Test get_pdf_page_count function."""

    def test_get_pdf_page_count_success(self):
        """Test getting PDF page count successfully."""
        with patch('fitz.open') as mock_fitz_open:
            mock_doc = Mock()
            mock_doc.page_count = 10
            mock_fitz_open.return_value.__enter__ = Mock(return_value=mock_doc)
            mock_fitz_open.return_value.__exit__ = Mock(return_value=False)

            from services.chunk_service import get_pdf_page_count

            result = get_pdf_page_count("/path/to/test.pdf")
            assert result == 10

    def test_get_pdf_page_count_exception(self):
        """Test handling exception when reading PDF fails."""
        with patch('fitz.open') as mock_fitz_open:
            mock_fitz_open.side_effect = Exception("File not found")

            from services.chunk_service import get_pdf_page_count

            result = get_pdf_page_count("/nonexistent/file.pdf")
            assert result == 0


@pytest.mark.usefixtures('set_test_env')
class TestChunkPdf:
    """Test chunk_pdf function."""

    def test_chunk_pdf_exception(self):
        """Test handling exception during PDF chunking."""
        with patch('fitz.open') as mock_fitz_open:
            mock_fitz_open.side_effect = Exception("File corrupted")

            from services.chunk_service import chunk_pdf

            result = chunk_pdf("/path/to/corrupted.pdf")
            assert result == []


@pytest.mark.usefixtures('set_test_env')
class TestSaveVideoChunk:
    """Test save_video_chunk function."""

    def test_save_video_chunk_personal_document(self):
        """Test saving video chunk for personal document."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.generate_embedding', create=True) as mock_generate_embedding, \
             patch('services.document_service.get_document_metadata') as mock_get_metadata, \
             patch('services.chunk_service.datetime', create=True) as mock_datetime:

            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_metadata = {'version': 1, 'tags': ['video'], 'shared_user_ids': []}
            mock_get_metadata.return_value = mock_metadata
            mock_generate_embedding.return_value = ([0.1, 0.2, 0.3], None)
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_video_chunk

            save_video_chunk(
                page_text_content="Video transcript text",
                ocr_chunk_text="OCR extracted text",
                start_time="00:01:30.500",
                file_name="video.mp4",
                user_id="user1",
                document_id="video_doc1",
                group_id=None
            )

            mock_generate_embedding.assert_called_once_with("Video transcript text")
            mock_search_client.upload_documents.assert_called_once()

    def test_save_video_chunk_time_conversion(self):
        """Test video timestamp to seconds conversion."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.datetime', create=True) as mock_datetime:

            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_meta.return_value = {'version': 1}
            mock_embed.return_value = ([0.1], None)
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_video_chunk

            save_video_chunk(
                page_text_content="Test",
                ocr_chunk_text="",
                start_time="01:05:30.250",
                file_name="test.mp4",
                user_id="user1",
                document_id="test_doc",
                group_id=None
            )

            uploaded_doc = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded_doc['id'] == "test_doc_3930"
            assert uploaded_doc['chunk_sequence'] == 3930


@pytest.mark.usefixtures('set_test_env')
class TestUpdateChunkMetadata:
    """Tests for update_chunk_metadata() — updates chunk fields in search index."""

    def test_updates_personal_chunk(self):
        mock_chunk = {
            'id': 'chunk-1', 'user_id': 'user-1', 'document_id': 'doc-1',
            'chunk_keywords': [], 'document_tags': []
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            update_chunk_metadata(
                chunk_id='chunk-1', user_id='user-1',
                document_id='doc-1', document_tags=['python']
            )
            mock_search_client.upload_documents.assert_called_once()
            uploaded = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded['document_tags'] == ['python']

    def test_updates_group_chunk(self):
        mock_chunk = {
            'id': 'chunk-1', 'group_id': 'grp-1', 'document_id': 'doc-1',
            'chunk_keywords': [], 'document_tags': []
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            update_chunk_metadata(
                chunk_id='chunk-1', user_id='user-1', group_id='grp-1',
                document_id='doc-1', document_tags=['flask']
            )
            mock_search_client.upload_documents.assert_called_once()

    def test_updates_public_chunk(self):
        mock_chunk = {
            'id': 'chunk-1', 'public_workspace_id': 'pw-1', 'document_id': 'doc-1',
            'chunk_keywords': [], 'document_tags': []
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_public': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            update_chunk_metadata(
                chunk_id='chunk-1', user_id='user-1', public_workspace_id='pw-1',
                document_id='doc-1', document_tags=['report']
            )
            mock_search_client.upload_documents.assert_called_once()

    def test_unauthorized_personal_raises(self):
        mock_chunk = {
            'id': 'chunk-1', 'user_id': 'other-user', 'document_id': 'doc-1'
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            with pytest.raises(Exception, match="Unauthorized"):
                update_chunk_metadata(
                    chunk_id='chunk-1', user_id='user-1',
                    document_id='doc-1'
                )

    def test_wrong_document_raises(self):
        mock_chunk = {
            'id': 'chunk-1', 'user_id': 'user-1', 'document_id': 'different-doc'
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            with pytest.raises(Exception, match="does not belong"):
                update_chunk_metadata(
                    chunk_id='chunk-1', user_id='user-1',
                    document_id='doc-1'
                )

    def test_chunk_not_found_raises(self):
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = None
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            with pytest.raises(Exception, match="not found"):
                update_chunk_metadata(
                    chunk_id='nonexistent', user_id='user-1',
                    document_id='doc-1'
                )

    def test_shared_group_ids_only_for_groups(self):
        """shared_group_ids should only be updatable for group workspace chunks."""
        mock_chunk = {
            'id': 'chunk-1', 'group_id': 'grp-1', 'document_id': 'doc-1',
            'chunk_keywords': []
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            update_chunk_metadata(
                chunk_id='chunk-1', user_id='user-1', group_id='grp-1',
                document_id='doc-1', shared_group_ids=['grp-2']
            )
            uploaded = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded['shared_group_ids'] == ['grp-2']


@pytest.mark.usefixtures('set_test_env')
class TestGetAllChunksEdgeCases:
    """Additional tests for get_all_chunks()."""

    def test_group_chunks(self):
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [
            {'id': 'chunk-1', 'group_id': 'grp-1'}
        ]
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.sharing_service.is_document_shared_with_group', return_value=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import get_all_chunks
            result = list(get_all_chunks('doc-1', 'user-1', group_id='grp-1'))
            assert len(result) == 1
            mock_search_client.search.assert_called_once()

    def test_public_workspace_chunks(self):
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [
            {'id': 'chunk-1', 'public_workspace_id': 'pw-1'}
        ]
        with patch('services.chunk_service.CLIENTS', {'search_client_public': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import get_all_chunks
            result = list(get_all_chunks('doc-1', 'user-1', public_workspace_id='pw-1'))
            assert len(result) == 1

    def test_search_exception_raises(self):
        mock_search_client = MagicMock()
        mock_search_client.search.side_effect = Exception("Search error")
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True), \
             patch('services.sharing_service.is_document_shared_with_user', return_value=True):
            from services.chunk_service import get_all_chunks
            with pytest.raises(Exception, match="Search error"):
                list(get_all_chunks('doc-1', 'user-1'))


@pytest.mark.usefixtures('set_test_env')
class TestDeleteDocumentChunksEdgeCases:
    """Additional tests for delete_document_chunks()."""

    def test_delete_group_chunks(self):
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [
            {'id': 'chunk-1'},
            {'id': 'chunk-2'},
        ]
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.IndexDocumentsBatch', create=True) as mock_batch_cls, \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_chunks
            delete_document_chunks('doc-1', group_id='grp-1')
            mock_search_client.index_documents.assert_called_once()

    def test_delete_public_workspace_chunks(self):
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [
            {'id': 'chunk-1'},
        ]
        with patch('services.chunk_service.CLIENTS', {'search_client_public': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.IndexDocumentsBatch', create=True) as mock_batch_cls, \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_chunks
            delete_document_chunks('doc-1', public_workspace_id='pw-1')
            mock_search_client.index_documents.assert_called_once()

    def test_delete_exception_raises(self):
        mock_search_client = MagicMock()
        mock_search_client.search.side_effect = Exception("Search failed")
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_chunks
            with pytest.raises(Exception, match="Search failed"):
                delete_document_chunks('doc-1')

    def test_no_chunks_returns_early(self):
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = []
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_chunks
            delete_document_chunks('doc-1')
            mock_search_client.index_documents.assert_not_called()


@pytest.mark.usefixtures('set_test_env')
class TestSaveChunksGroupAndPublic:
    """Tests for save_chunks() with group and public workspace documents."""

    def _base_patches(self):
        """Return a list of common patches for save_chunks tests."""
        return {
            'metadata': patch('services.document_service.get_document_metadata'),
            'log': patch('services.chunk_service.add_file_task_to_file_processing_log', create=True),
            'embed': patch('services.chunk_service.generate_embedding', create=True),
            'clients': patch('services.chunk_service.CLIENTS', create=True),
            'debug': patch('services.chunk_service.debug_print', create=True),
        }

    def test_save_chunks_group_document(self):
        """Group chunks include group_id and shared_group_ids."""
        with patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.debug_print', create=True):

            mock_meta.return_value = {
                'version': 3, 'tags': ['t1'], 'shared_group_ids': ['grp-2', 'grp-3']
            }
            mock_embed.return_value = ([0.5], {'tokens': 42})
            mock_search = Mock()
            mock_clients.__getitem__.return_value = mock_search

            from services.chunk_service import save_chunks
            token_usage = save_chunks(
                page_text_content="Group content",
                page_number=2,
                file_name="report.pdf",
                user_id="user-1",
                document_id="doc-g1",
                group_id="grp-1",
            )

            assert token_usage == {'tokens': 42}
            uploaded = mock_search.upload_documents.call_args[1]['documents'][0]
            assert uploaded['group_id'] == 'grp-1'
            assert uploaded['shared_group_ids'] == ['grp-2', 'grp-3']
            assert 'user_id' not in uploaded  # group docs don't have user_id field
            assert uploaded['version'] == 3
            assert uploaded['document_tags'] == ['t1']

    def test_save_chunks_public_workspace_document(self):
        """Public workspace chunks include public_workspace_id."""
        with patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.debug_print', create=True):

            mock_meta.return_value = {
                'version': 1, 'tags': ['public-tag'],
            }
            mock_embed.return_value = ([0.9], {'tokens': 10})
            mock_search = Mock()
            mock_clients.__getitem__.return_value = mock_search

            from services.chunk_service import save_chunks
            token_usage = save_chunks(
                page_text_content="Public content",
                page_number=1,
                file_name="public.txt",
                user_id="user-1",
                document_id="doc-p1",
                public_workspace_id="pw-1",
            )

            assert token_usage == {'tokens': 10}
            uploaded = mock_search.upload_documents.call_args[1]['documents'][0]
            assert uploaded['public_workspace_id'] == 'pw-1'
            assert 'user_id' not in uploaded
            assert 'group_id' not in uploaded
            assert uploaded['document_tags'] == ['public-tag']

    def test_save_chunks_with_vision_analysis(self):
        """Vision analysis metadata is appended to chunk_text."""
        with patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.debug_print', create=True):

            mock_meta.return_value = {
                'version': 1,
                'tags': [],
                'shared_user_ids': [],
                'vision_analysis': {
                    'model': 'gpt-4o',
                    'description': 'A photo of a cat',
                    'objects': ['cat', 'sofa'],
                    'text': 'Welcome home',
                    'analysis': 'Indoor scene with pet',
                },
            }
            mock_embed.return_value = ([0.1], {'tokens': 5})
            mock_search = Mock()
            mock_clients.__getitem__.return_value = mock_search

            from services.chunk_service import save_chunks
            save_chunks(
                page_text_content="Base text",
                page_number=1,
                file_name="photo.png",
                user_id="user-1",
                document_id="doc-v1",
            )

            uploaded = mock_search.upload_documents.call_args[1]['documents'][0]
            assert "AI Vision Analysis" in uploaded['chunk_text']
            assert "gpt-4o" in uploaded['chunk_text']
            assert "A photo of a cat" in uploaded['chunk_text']
            assert "cat, sofa" in uploaded['chunk_text']
            assert "Welcome home" in uploaded['chunk_text']
            assert "Indoor scene with pet" in uploaded['chunk_text']
            # Original text is still present at the start
            assert uploaded['chunk_text'].startswith("Base text")

    def test_save_chunks_with_web_ingestion_metadata(self):
        """Web ingestion metadata (source_url, source_type, content_hash) is included."""
        with patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.debug_print', create=True):

            mock_meta.return_value = {
                'version': 1,
                'tags': [],
                'shared_user_ids': [],
                'source_url': 'https://example.com/page',
                'source_type': 'web',
                'content_hash': 'abc123hash',
            }
            mock_embed.return_value = ([0.1], {'tokens': 5})
            mock_search = Mock()
            mock_clients.__getitem__.return_value = mock_search

            from services.chunk_service import save_chunks
            save_chunks(
                page_text_content="Web text",
                page_number=1,
                file_name="page.html",
                user_id="user-1",
                document_id="doc-w1",
            )

            uploaded = mock_search.upload_documents.call_args[1]['documents'][0]
            assert uploaded['source_url'] == 'https://example.com/page'
            assert uploaded['source_type'] == 'web'
            assert uploaded['content_hash'] == 'abc123hash'

    def test_save_chunks_embedding_error_raises(self):
        """Embedding generation failure propagates the exception."""
        with patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.add_file_task_to_file_processing_log', create=True), \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.debug_print', create=True):

            mock_meta.return_value = {'version': 1, 'tags': []}
            mock_embed.side_effect = RuntimeError("Embedding API down")

            from services.chunk_service import save_chunks
            with pytest.raises(RuntimeError, match="Embedding API down"):
                save_chunks(
                    page_text_content="text",
                    page_number=1,
                    file_name="test.txt",
                    user_id="user-1",
                    document_id="doc-err",
                )


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentMetadataForCitationsContainers:
    """Tests for get_document_metadata_for_citations with group/public containers."""

    def test_group_document_metadata(self):
        """Retrieves metadata from group documents container."""
        with patch('services.chunk_service.cosmos_group_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'gdoc-1',
                'keywords': ['finance'],
                'abstract': 'Quarterly report',
                'file_name': 'q1.pdf',
            }
            from services.chunk_service import get_document_metadata_for_citations
            result = get_document_metadata_for_citations("gdoc-1", group_id="grp-1")
            assert result['keywords'] == ['finance']
            assert result['abstract'] == 'Quarterly report'
            assert result['file_name'] == 'q1.pdf'

    def test_public_workspace_document_metadata(self):
        """Retrieves metadata from public workspace documents container."""
        with patch('services.chunk_service.cosmos_public_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'pdoc-1',
                'keywords': ['policy'],
                'abstract': 'Company policy doc',
                'file_name': 'policy.pdf',
            }
            from services.chunk_service import get_document_metadata_for_citations
            result = get_document_metadata_for_citations("pdoc-1", public_workspace_id="pw-1")
            assert result['keywords'] == ['policy']

    def test_only_abstract_returns_result(self):
        """Returns metadata if only abstract is present (no keywords)."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'doc-1',
                'abstract': 'Some abstract',
                'file_name': 'doc.txt',
            }
            from services.chunk_service import get_document_metadata_for_citations
            result = get_document_metadata_for_citations("doc-1", user_id="u1")
            assert result is not None
            assert result['abstract'] == 'Some abstract'
            assert result['keywords'] == []


@pytest.mark.usefixtures('set_test_env')
class TestGetBatchDocumentMetadataEdgeCases:
    """Additional tests for get_batch_document_metadata_for_citations()."""

    def test_no_keywords_or_abstract_returns_none(self):
        """Documents without keywords or abstract get None in results."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.return_value = {
                'id': 'doc-1', 'file_name': 'test.pdf'
            }
            from services.chunk_service import get_batch_document_metadata_for_citations
            result = get_batch_document_metadata_for_citations([
                {'document_id': 'doc-1', 'user_id': 'u1'}
            ])
            assert result['doc-1'] is None

    def test_exception_on_read_returns_none(self):
        """Read errors result in None for that document."""
        with patch('services.chunk_service.cosmos_user_documents_container', create=True) as mock_container:
            mock_container.read_item.side_effect = Exception("Cosmos error")
            from services.chunk_service import get_batch_document_metadata_for_citations
            result = get_batch_document_metadata_for_citations([
                {'document_id': 'doc-err', 'user_id': 'u1'}
            ])
            assert result['doc-err'] is None

    def test_missing_document_id_skipped(self):
        """Requests without document_id are silently skipped."""
        from services.chunk_service import get_batch_document_metadata_for_citations
        result = get_batch_document_metadata_for_citations([
            {'user_id': 'u1'},  # no document_id
            {},
        ])
        assert result == {}


@pytest.mark.usefixtures('set_test_env')
class TestDeleteDocumentVersionChunks:
    """Tests for delete_document_version_chunks()."""

    def test_delete_version_chunks_personal(self):
        """Deletes chunks for a specific version from personal search index."""
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [
            {'id': 'doc1_v2_1'},
            {'id': 'doc1_v2_2'},
        ]
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_version_chunks
            delete_document_version_chunks('doc-1', version=2)
            mock_search_client.delete_documents.assert_called_once()

    def test_delete_version_chunks_group(self):
        """Deletes chunks for a specific version from group search index."""
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [{'id': 'c1'}]
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_version_chunks
            delete_document_version_chunks('doc-1', version=1, group_id='grp-1')
            mock_search_client.delete_documents.assert_called_once()

    def test_delete_version_chunks_public(self):
        """Deletes chunks for a specific version from public search index."""
        mock_search_client = MagicMock()
        mock_search_client.search.return_value = [{'id': 'c1'}]
        with patch('services.chunk_service.CLIENTS', {'search_client_public': mock_search_client}, create=True), \
             patch('services.chunk_service.sanitize_odata_value', side_effect=lambda x: x, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import delete_document_version_chunks
            delete_document_version_chunks('doc-1', version=3, public_workspace_id='pw-1')
            mock_search_client.delete_documents.assert_called_once()


@pytest.mark.usefixtures('set_test_env')
class TestUpdateChunkMetadataAuthEdgeCases:
    """Extra auth edge cases for update_chunk_metadata()."""

    def test_unauthorized_group_raises(self):
        """Wrong group_id on chunk raises Unauthorized."""
        mock_chunk = {
            'id': 'chunk-1', 'group_id': 'wrong-grp', 'document_id': 'doc-1',
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_group': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            with pytest.raises(Exception, match="Unauthorized"):
                update_chunk_metadata(
                    chunk_id='chunk-1', user_id='user-1', group_id='grp-1',
                    document_id='doc-1'
                )

    def test_unauthorized_public_raises(self):
        """Wrong public_workspace_id on chunk raises Unauthorized."""
        mock_chunk = {
            'id': 'chunk-1', 'public_workspace_id': 'wrong-pw', 'document_id': 'doc-1',
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_public': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            with pytest.raises(Exception, match="Unauthorized"):
                update_chunk_metadata(
                    chunk_id='chunk-1', user_id='user-1', public_workspace_id='pw-1',
                    document_id='doc-1'
                )

    def test_shared_group_ids_not_updatable_for_personal(self):
        """shared_group_ids kwarg is ignored for personal workspace chunks."""
        mock_chunk = {
            'id': 'chunk-1', 'user_id': 'user-1', 'document_id': 'doc-1',
            'chunk_keywords': []
        }
        mock_search_client = MagicMock()
        mock_search_client.get_document.return_value = mock_chunk
        with patch('services.chunk_service.CLIENTS', {'search_client_user': mock_search_client}, create=True), \
             patch('services.chunk_service.debug_print', create=True):
            from services.chunk_service import update_chunk_metadata
            update_chunk_metadata(
                chunk_id='chunk-1', user_id='user-1',
                document_id='doc-1', shared_group_ids=['grp-1']
            )
            uploaded = mock_search_client.upload_documents.call_args[1]['documents'][0]
            # shared_group_ids should NOT have been applied to a personal chunk
            assert 'shared_group_ids' not in uploaded or uploaded.get('shared_group_ids') is None or mock_chunk.get('shared_group_ids') is None


@pytest.mark.usefixtures('set_test_env')
class TestSaveVideoChunkEdgeCases:
    """Additional tests for save_video_chunk()."""

    def test_save_video_chunk_group_document(self):
        """Video chunk for group doc sets group_id and uses group search client."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.datetime', create=True) as mock_datetime:

            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_meta.return_value = {'version': 2, 'tags': ['video'], 'shared_group_ids': []}
            mock_embed.return_value = ([0.1, 0.2], None)
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_video_chunk
            save_video_chunk(
                page_text_content="Group video transcript",
                ocr_chunk_text="Group OCR",
                start_time="00:00:30.000",
                file_name="group_video.mp4",
                user_id="user-1",
                document_id="vdoc-g1",
                group_id="grp-1",
            )

            mock_search_client.upload_documents.assert_called_once()
            uploaded = mock_search_client.upload_documents.call_args[1]['documents'][0]
            assert uploaded['group_id'] == 'grp-1'
            assert 'user_id' not in uploaded

    def test_save_video_chunk_embedding_failure_returns_early(self):
        """If embedding generation fails, save_video_chunk returns without uploading."""
        with patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.chunk_service.datetime', create=True) as mock_datetime, \
             patch('services.chunk_service.debug_print', create=True), \
             patch('services.chunk_service.CLIENTS', create=True) as mock_clients:

            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_embed.side_effect = RuntimeError("API error")
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_video_chunk
            save_video_chunk(
                page_text_content="transcript",
                ocr_chunk_text="ocr",
                start_time="00:00:00.000",
                file_name="v.mp4",
                user_id="u1",
                document_id="vd1",
                group_id=None,
            )

            # Upload should NOT have been called because embedding failed
            mock_search_client.upload_documents.assert_not_called()

    def test_save_video_chunk_metadata_failure_returns_early(self):
        """If metadata retrieval fails, save_video_chunk returns without uploading."""
        with patch('services.chunk_service.CLIENTS', create=True) as mock_clients, \
             patch('services.chunk_service.generate_embedding', create=True) as mock_embed, \
             patch('services.document_service.get_document_metadata') as mock_meta, \
             patch('services.chunk_service.datetime', create=True) as mock_datetime, \
             patch('services.chunk_service.debug_print', create=True):

            mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_embed.return_value = ([0.1], None)
            mock_meta.side_effect = Exception("Cosmos down")
            mock_search_client = Mock()
            mock_clients.__getitem__.return_value = mock_search_client

            from services.chunk_service import save_video_chunk
            save_video_chunk(
                page_text_content="text",
                ocr_chunk_text="",
                start_time="00:00:10.000",
                file_name="v.mp4",
                user_id="u1",
                document_id="vd1",
                group_id=None,
            )

            mock_search_client.upload_documents.assert_not_called()


@pytest.mark.usefixtures('set_test_env')
class TestChunkPdfSuccess:
    """Tests for chunk_pdf() happy path."""

    def test_chunk_pdf_single_chunk(self):
        """PDF with fewer pages than max_pages produces one chunk."""
        mock_chunk_doc = MagicMock()
        mock_main_doc = MagicMock()
        mock_main_doc.page_count = 10

        with patch('fitz.open') as mock_fitz_open:
            # First call = context manager for main doc
            mock_fitz_open.return_value.__enter__ = Mock(return_value=mock_main_doc)
            mock_fitz_open.return_value.__exit__ = Mock(return_value=False)
            # Subsequent calls (inside the loop) = chunk docs
            # We need fitz.open() to return a new doc for creating chunks
            # Inside the loop, fitz.open() is called without args
            call_count = [0]
            original_fitz_open = mock_fitz_open

            def fitz_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # Main document open (context manager)
                    cm = MagicMock()
                    cm.__enter__ = Mock(return_value=mock_main_doc)
                    cm.__exit__ = Mock(return_value=False)
                    return cm
                else:
                    # Chunk document creation (no context manager)
                    return mock_chunk_doc

            mock_fitz_open.side_effect = fitz_side_effect

            from services.chunk_service import chunk_pdf
            result = chunk_pdf("/path/to/test.pdf", max_pages=500)

            # With 10 pages and max_pages=500, should produce 1 chunk
            assert len(result) == 1
            assert "_chunk_1" in result[0]

    def test_chunk_pdf_multiple_chunks(self):
        """PDF with more pages than max_pages produces multiple chunks."""
        mock_main_doc = MagicMock()
        mock_main_doc.page_count = 25

        call_count = [0]

        def fitz_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                cm = MagicMock()
                cm.__enter__ = Mock(return_value=mock_main_doc)
                cm.__exit__ = Mock(return_value=False)
                return cm
            else:
                return MagicMock()

        with patch('fitz.open') as mock_fitz_open:
            mock_fitz_open.side_effect = fitz_side_effect

            from services.chunk_service import chunk_pdf
            result = chunk_pdf("/path/to/large.pdf", max_pages=10)

            # 25 pages / 10 per chunk = 3 chunks
            assert len(result) == 3
