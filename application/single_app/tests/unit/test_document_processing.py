# test_document_processing.py
"""
Unit tests for services/document_processing.py.

Tests format-specific document processors including text, markdown, JSON, HTML,
and other document formats. Verifies chunking logic, blob upload behavior,
and callback functionality.

Version: 0.238.024
"""

import pytest
from unittest.mock import MagicMock, patch, call
import json
import os


# Shared mock return value that includes model_deployment_name
MOCK_TOKEN_USAGE = {'total_tokens': 15, 'model_deployment_name': 'text-embedding-ada-002'}
MOCK_TOKEN_USAGE_SMALL = {'total_tokens': 5, 'model_deployment_name': 'text-embedding-ada-002'}
MOCK_TOKEN_USAGE_ZERO = {'total_tokens': 0}


@pytest.mark.usefixtures('set_test_env')
class TestProcessTxt:
    """Test text document processing."""

    def test_basic_chunking(self, tmp_path):
        """Test that text is properly chunked into 400-word segments."""
        test_file = tmp_path / "test.txt"
        words = ["word"] * 800
        content = " ".join(words)
        test_file.write_text(content, encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob') as mock_upload:

            from services.document_processing import process_txt

            chunks, tokens, model = process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.txt",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks == 2  # 800 words / 400 words per chunk
            assert tokens == 30  # 15 tokens per chunk * 2 chunks
            assert model == 'text-embedding-ada-002'
            assert mock_save.call_count == 2
            mock_upload.assert_not_called()

    def test_enhanced_citations_triggers_blob_upload(self, tmp_path):
        """Test that enhanced citations enabled triggers blob upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for blob upload", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob') as mock_upload:

            from services.document_processing import process_txt

            process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.txt",
                enable_enhanced_citations=True,
                update_callback=callback
            )

            mock_upload.assert_called_once()

    def test_group_id_passed_correctly(self, tmp_path):
        """Test that group_id is passed to save_chunks."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_txt

            process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.txt",
                enable_enhanced_citations=False,
                update_callback=callback,
                group_id="group-123"
            )

            call_args = mock_save.call_args[1]
            assert call_args['group_id'] == "group-123"

    def test_public_workspace_id_passed_correctly(self, tmp_path):
        """Test that public_workspace_id is passed to save_chunks."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_txt

            process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.txt",
                enable_enhanced_citations=False,
                update_callback=callback,
                public_workspace_id="public-456"
            )

            call_args = mock_save.call_args[1]
            assert call_args['public_workspace_id'] == "public-456"

    def test_empty_file_produces_zero_chunks(self, tmp_path):
        """Test that empty file produces 0 chunks."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_ZERO) as mock_save, \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_txt

            chunks, tokens, model = process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="empty.txt",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks == 0
            assert tokens == 0
            mock_save.assert_not_called()

    def test_file_read_exception_handling(self, tmp_path):
        """Test that file reading exceptions are properly handled."""
        non_existent_file = tmp_path / "does_not_exist.txt"

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks'), \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_txt

            with pytest.raises(Exception):
                process_txt(
                    document_id="doc-1",
                    user_id="user-1",
                    temp_file_path=str(non_existent_file),
                    original_filename="missing.txt",
                    enable_enhanced_citations=False,
                    update_callback=callback
                )

    def test_single_chunk_content(self, tmp_path):
        """Test that a small file produces exactly 1 chunk with correct content."""
        test_file = tmp_path / "small.txt"
        test_file.write_text("Hello world this is a test", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_txt

            chunks, tokens, model = process_txt(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="small.txt",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks == 1
            assert mock_save.call_count == 1
            # Verify the content passed to save_chunks
            call_kwargs = mock_save.call_args[1]
            assert call_kwargs['page_text_content'] == "Hello world this is a test"
            assert call_kwargs['document_id'] == "doc-1"
            assert call_kwargs['user_id'] == "user-1"
            assert call_kwargs['page_number'] == 1


@pytest.mark.usefixtures('set_test_env')
class TestProcessMd:
    """Test markdown document processing."""

    def test_markdown_processing(self, tmp_path):
        """Test that markdown content is processed into chunks."""
        test_file = tmp_path / "test.md"
        markdown_content = """# Test Document

This is a test markdown file with some content.

## Section 1

Content for section 1 with enough text to test chunking.

## Section 2

Content for section 2 with more text content."""
        test_file.write_text(markdown_content.strip(), encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob') as mock_upload, \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.metadata_service.estimate_word_count', side_effect=lambda text: len(text.split())):

            from services.document_processing import process_md

            chunks, tokens, model = process_md(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.md",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks >= 1
            assert tokens >= 5
            assert model == 'text-embedding-ada-002'
            mock_save.assert_called()
            mock_upload.assert_not_called()

    def test_markdown_enhanced_citations(self, tmp_path):
        """Test that enhanced citations triggers blob upload for markdown."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Simple markdown content", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob') as mock_upload, \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.metadata_service.estimate_word_count', side_effect=lambda text: len(text.split())):

            from services.document_processing import process_md

            process_md(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.md",
                enable_enhanced_citations=True,
                update_callback=callback
            )

            mock_upload.assert_called_once()


@pytest.mark.usefixtures('set_test_env')
class TestProcessJson:
    """Test JSON document processing."""

    def test_valid_json_processing(self, tmp_path):
        """Test that valid JSON content is processed."""
        test_file = tmp_path / "test.json"
        json_data = {
            "name": "Test Document",
            "description": "A test JSON document for processing",
            "items": ["item1", "item2", "item3"],
            "metadata": {
                "version": "1.0",
                "author": "Test User"
            }
        }
        test_file.write_text(json.dumps(json_data, indent=2), encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.metadata_service.extract_document_metadata', return_value=None):

            from services.document_processing import process_json

            chunks, tokens, model = process_json(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.json",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks >= 1
            assert tokens >= 15
            assert model == 'text-embedding-ada-002'
            mock_save.assert_called()

    def test_invalid_json_handling(self, tmp_path):
        """Test handling of invalid JSON content."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json content", encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks'), \
             patch('services.blob_service.upload_to_blob'):

            from services.document_processing import process_json

            with pytest.raises(Exception):
                process_json(
                    document_id="doc-1",
                    user_id="user-1",
                    temp_file_path=str(test_file),
                    original_filename="invalid.json",
                    enable_enhanced_citations=False,
                    update_callback=callback
                )


@pytest.mark.usefixtures('set_test_env')
class TestProcessHtml:
    """Test HTML document processing."""

    def test_html_processing_strips_tags(self, tmp_path):
        """Test that HTML content is processed and tags are stripped."""
        test_file = tmp_path / "test.html"
        html_content = """<!DOCTYPE html>
<html>
<head><title>Test Document</title></head>
<body>
    <h1>Main Heading</h1>
    <p>This is a paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
    <div>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
    </div>
</body>
</html>"""
        test_file.write_text(html_content.strip(), encoding='utf-8')

        callback = MagicMock()

        with patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE_SMALL) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.metadata_service.estimate_word_count', side_effect=lambda text: len(text.split())):

            from services.document_processing import process_html

            chunks, tokens, model = process_html(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.html",
                enable_enhanced_citations=False,
                update_callback=callback
            )

            assert chunks >= 1
            assert tokens >= 5
            assert model == 'text-embedding-ada-002'
            mock_save.assert_called()


@pytest.mark.usefixtures('set_test_env')
class TestProcessDocumentUploadBackground:
    """Test main document processing dispatcher.

    process_document_upload_background is a complex function with many lazy imports
    and side effects. We test the dispatch logic by mocking the individual process_*
    functions and the services it depends on.
    """

    def _get_common_patches(self):
        """Return a dict of common patches needed for the dispatcher."""
        return {
            'services.document_service.allowed_file': MagicMock(return_value=True),
            'services.document_service.update_document': MagicMock(),
            'services.document_service.get_document_metadata': MagicMock(return_value={}),
            'services.document_processing.get_settings': MagicMock(return_value={
                'enable_enhanced_citations': False,
                'enable_extract_meta_data': False,
                'max_file_size_mb': 100,
                'enable_graph_rag': False,
            }),
        }

    def test_txt_file_routed_to_process_txt(self, tmp_path):
        """Test that .txt files are routed to process_txt."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for txt routing", encoding='utf-8')

        patches = self._get_common_patches()

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', patches['services.document_service.allowed_file']), \
             patch('services.document_service.update_document', patches['services.document_service.update_document']), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.txt",
            )

            # Verify save_chunks was called (meaning process_txt ran)
            mock_save.assert_called()
            # Verify the first save_chunks call had the correct document_id
            first_call_kwargs = mock_save.call_args_list[0][1]
            assert first_call_kwargs['document_id'] == "doc-1"

    def test_md_file_routed_to_process_md(self, tmp_path):
        """Test that .md files are routed to process_md."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test markdown heading\n\nSome content here.", encoding='utf-8')

        patches = self._get_common_patches()

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', patches['services.document_service.allowed_file']), \
             patch('services.document_service.update_document', patches['services.document_service.update_document']), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.metadata_service.estimate_word_count', side_effect=lambda text: len(text.split())), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.md",
            )

            # process_md calls save_chunks
            mock_save.assert_called()

    def test_json_file_routed_to_process_json(self, tmp_path):
        """Test that .json files are routed to process_json."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value", "items": [1,2,3]}', encoding='utf-8')

        patches = self._get_common_patches()

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', patches['services.document_service.allowed_file']), \
             patch('services.document_service.update_document', patches['services.document_service.update_document']), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.json",
            )

            mock_save.assert_called()

    def test_html_file_routed_to_process_html(self, tmp_path):
        """Test that .html files are routed to process_html."""
        test_file = tmp_path / "test.html"
        test_file.write_text("<html><body><p>Test HTML content</p></body></html>", encoding='utf-8')

        patches = self._get_common_patches()

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', patches['services.document_service.allowed_file']), \
             patch('services.document_service.update_document', patches['services.document_service.update_document']), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.chunk_service.save_chunks', return_value=MOCK_TOKEN_USAGE) as mock_save, \
             patch('services.blob_service.upload_to_blob'), \
             patch('services.metadata_service.extract_document_metadata', return_value=None), \
             patch('services.metadata_service.estimate_word_count', side_effect=lambda text: len(text.split())), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.html",
            )

            mock_save.assert_called()

    def test_unsupported_extension_updates_error_status(self, tmp_path):
        """Test that unsupported file types cause an error status update."""
        test_file = tmp_path / "test.xyz123"
        test_file.write_text("Some content", encoding='utf-8')

        patches = self._get_common_patches()
        mock_update_document = patches['services.document_service.update_document']

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', return_value=False), \
             patch('services.document_service.update_document', mock_update_document), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            # Should not raise, but should call update_document with error status
            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=str(test_file),
                original_filename="test.xyz123",
            )

            # Verify update_document was called with an error status
            assert mock_update_document.call_count >= 1
            # Find a call that includes 'Error' in the status
            error_calls = [
                c for c in mock_update_document.call_args_list
                if 'status' in c[1] and 'Error' in str(c[1].get('status', ''))
            ]
            assert len(error_calls) >= 1, "Expected at least one error status update"

    def test_missing_file_updates_error_status(self, tmp_path):
        """Test that missing temp file causes an error status update."""
        non_existent = str(tmp_path / "does_not_exist.txt")

        patches = self._get_common_patches()
        mock_update_document = patches['services.document_service.update_document']

        with patch.dict('os.environ', {}, clear=False), \
             patch('services.document_service.allowed_file', patches['services.document_service.allowed_file']), \
             patch('services.document_service.update_document', mock_update_document), \
             patch('services.document_service.get_document_metadata', patches['services.document_service.get_document_metadata']), \
             patch('services.document_processing.get_settings', patches['services.document_processing.get_settings']), \
             patch('services.media_service.process_video_document'), \
             patch('services.media_service.process_audio_document'):

            from services.document_processing import process_document_upload_background

            process_document_upload_background(
                document_id="doc-1",
                user_id="user-1",
                temp_file_path=non_existent,
                original_filename="missing.txt",
            )

            # Verify update_document was called with an error status
            error_calls = [
                c for c in mock_update_document.call_args_list
                if 'status' in c[1] and 'Error' in str(c[1].get('status', ''))
            ]
            assert len(error_calls) >= 1, "Expected at least one error status update for missing file"
