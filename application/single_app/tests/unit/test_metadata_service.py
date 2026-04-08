# tests/unit/test_metadata_service.py
# Unit tests for metadata_service.py utility functions.

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.usefixtures('set_test_env')
class TestCleanJsonCodeFence:
    """Test the clean_json_codeFence utility function."""

    def test_plain_json_unchanged(self):
        """Plain JSON string should be returned unchanged."""
        from services.metadata_service import clean_json_codeFence
        json_str = '{"key": "value", "number": 42}'
        result = clean_json_codeFence(json_str)
        assert result == json_str

    def test_json_fence_removed(self):
        """```json fences should be removed."""
        from services.metadata_service import clean_json_codeFence
        input_str = '```json\n{"key": "value"}\n```'
        expected = '{"key": "value"}'
        result = clean_json_codeFence(input_str)
        assert result == expected

    def test_generic_fence_removed(self):
        """Generic ``` fences should be removed."""
        from services.metadata_service import clean_json_codeFence
        input_str = '```\n{"key": "value"}\n```'
        expected = '{"key": "value"}'
        result = clean_json_codeFence(input_str)
        assert result == expected

    def test_whitespace_stripped(self):
        """Leading and trailing whitespace should be stripped."""
        from services.metadata_service import clean_json_codeFence
        input_str = '  \n```json\n  {"key": "value"}  \n```  \n'
        expected = '{"key": "value"}'
        result = clean_json_codeFence(input_str)
        assert result == expected

    def test_empty_string(self):
        """Empty string should return empty string."""
        from services.metadata_service import clean_json_codeFence
        result = clean_json_codeFence('')
        assert result == ''

    def test_only_whitespace(self):
        """Whitespace-only string should return empty string."""
        from services.metadata_service import clean_json_codeFence
        result = clean_json_codeFence('   \n\t   ')
        assert result == ''

    def test_fence_without_json_content(self):
        """Fences with no content should return empty string."""
        from services.metadata_service import clean_json_codeFence
        input_str = '```json\n```'
        result = clean_json_codeFence(input_str)
        assert result == ''

    def test_complex_json_structure(self):
        """Complex JSON with nested objects should work."""
        from services.metadata_service import clean_json_codeFence
        json_content = '{"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}'
        input_str = f'```json\n{json_content}\n```'
        result = clean_json_codeFence(input_str)
        assert result == json_content


@pytest.mark.usefixtures('set_test_env')
class TestEnsureList:
    """Test the ensure_list utility function."""

    def test_already_list_unchanged(self):
        """Lists should be returned as-is."""
        from services.metadata_service import ensure_list
        input_list = ["item1", "item2", "item3"]
        result = ensure_list(input_list)
        assert result == input_list
        assert result is input_list  # Same object reference

    def test_comma_separated_string(self):
        """Comma-separated string should be split."""
        from services.metadata_service import ensure_list
        result = ensure_list("item1, item2, item3")
        assert result == ["item1", "item2", "item3"]

    def test_semicolon_separated_string(self):
        """Semicolon-separated string should be split."""
        from services.metadata_service import ensure_list
        result = ensure_list("item1; item2; item3")
        assert result == ["item1", "item2", "item3"]

    def test_mixed_delimiters(self):
        """Mixed delimiters should work."""
        from services.metadata_service import ensure_list
        result = ensure_list("item1, item2; item3, item4")
        assert result == ["item1", "item2", "item3", "item4"]

    def test_single_item_no_delimiters(self):
        """Single item without delimiters should become single-item list."""
        from services.metadata_service import ensure_list
        result = ensure_list("single_item")
        assert result == ["single_item"]

    def test_empty_string_returns_empty_list(self):
        """Empty string should return empty list."""
        from services.metadata_service import ensure_list
        result = ensure_list("")
        assert result == []

    def test_none_returns_empty_list(self):
        """None should return empty list."""
        from services.metadata_service import ensure_list
        result = ensure_list(None)
        assert result == []

    def test_integer_returns_empty_list(self):
        """Non-string, non-list values should return empty list."""
        from services.metadata_service import ensure_list
        result = ensure_list(42)
        assert result == []

    def test_whitespace_trimmed(self):
        """Items should have whitespace trimmed."""
        from services.metadata_service import ensure_list
        result = ensure_list(" item1 , item2  , item3 ")
        assert result == ["item1", "item2", "item3"]

    def test_empty_items_filtered(self):
        """Empty items should be filtered out."""
        from services.metadata_service import ensure_list
        result = ensure_list("item1, , item2,  , item3")
        assert result == ["item1", "item2", "item3"]

    def test_custom_delimiters(self):
        """Custom delimiter pattern should work."""
        from services.metadata_service import ensure_list
        result = ensure_list("item1|item2|item3", delimiters=r"[|]")
        assert result == ["item1", "item2", "item3"]


@pytest.mark.usefixtures('set_test_env')
class TestIsEffectivelyEmpty:
    """Test the is_effectively_empty utility function."""

    def test_none_is_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty(None) is True

    def test_empty_string_is_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty("") is True

    def test_whitespace_string_is_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty("   ") is True
        assert is_effectively_empty("\n\t  \n") is True

    def test_non_empty_string_is_not_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty("content") is False
        assert is_effectively_empty("  content  ") is False

    def test_empty_list_is_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty([]) is True

    def test_list_of_empty_strings_is_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty([""]) is True
        assert is_effectively_empty(["", "  ", "\n"]) is True

    def test_list_with_content_is_not_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty(["item"]) is False
        assert is_effectively_empty(["", "item", ""]) is False

    def test_list_with_non_string_items_only(self):
        """List with only non-string items is empty (no string content)."""
        from services.metadata_service import is_effectively_empty
        # all() over empty iterable (no strings to check) returns True
        assert is_effectively_empty([42]) is True

    def test_list_with_mixed_string_and_non_string(self):
        """List with a non-empty string among non-strings is not empty."""
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty([42, "content"]) is False

    def test_other_types_not_empty(self):
        from services.metadata_service import is_effectively_empty
        assert is_effectively_empty(0) is False
        assert is_effectively_empty(False) is False
        assert is_effectively_empty({}) is False


@pytest.mark.usefixtures('set_test_env')
class TestEstimateWordCount:
    """Test the estimate_word_count utility function."""

    def test_normal_sentence(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count("This is a test sentence with seven words.") == 8

    def test_empty_string_returns_zero(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count("") == 0

    def test_none_returns_zero(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count(None) == 0

    def test_single_word(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count("word") == 1

    def test_multiple_spaces_handled(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count("word1    word2      word3") == 3

    def test_newlines_and_tabs(self):
        from services.metadata_service import estimate_word_count
        assert estimate_word_count("word1\nword2\tword3") == 3


@pytest.mark.usefixtures('set_test_env')
class TestDetectDocType:
    """Test the detect_doc_type function with mocking."""

    def test_found_in_user_docs_correct_user(self):
        from services.metadata_service import detect_doc_type
        mock_doc = {"id": "doc-123", "user_id": "user-456"}

        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True), \
             patch('services.metadata_service.cosmos_public_documents_container', create=True):
            mock_user.read_item.return_value = mock_doc
            result = detect_doc_type("doc-123", "user-456")
            assert result == ("personal", "user-456")

    def test_found_in_user_docs_wrong_user_continues_search(self):
        from services.metadata_service import detect_doc_type
        mock_user_doc = {"id": "doc-123", "user_id": "user-789"}
        mock_group_doc = {"id": "doc-123", "group_id": "group-123"}

        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True) as mock_group, \
             patch('services.metadata_service.cosmos_public_documents_container', create=True):
            mock_user.read_item.return_value = mock_user_doc
            mock_group.read_item.return_value = mock_group_doc
            result = detect_doc_type("doc-123", "user-456")
            assert result == ("group", "group-123")

    def test_found_in_group_docs(self):
        from services.metadata_service import detect_doc_type
        mock_group_doc = {"id": "doc-123", "group_id": "group-789"}

        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True) as mock_group, \
             patch('services.metadata_service.cosmos_public_documents_container', create=True):
            mock_user.read_item.side_effect = Exception("Not found")
            mock_group.read_item.return_value = mock_group_doc
            result = detect_doc_type("doc-123", "user-456")
            assert result == ("group", "group-789")

    def test_found_in_public_docs(self):
        from services.metadata_service import detect_doc_type
        mock_public_doc = {"id": "doc-123", "public_workspace_id": "ws-789"}

        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True) as mock_group, \
             patch('services.metadata_service.cosmos_public_documents_container', create=True) as mock_public:
            mock_user.read_item.side_effect = Exception("Not found")
            mock_group.read_item.side_effect = Exception("Not found")
            mock_public.read_item.return_value = mock_public_doc
            result = detect_doc_type("doc-123", "user-456")
            assert result == ("public", "ws-789")

    def test_not_found_anywhere_returns_none(self):
        from services.metadata_service import detect_doc_type
        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True) as mock_group, \
             patch('services.metadata_service.cosmos_public_documents_container', create=True) as mock_public:
            mock_user.read_item.side_effect = Exception("Not found")
            mock_group.read_item.side_effect = Exception("Not found")
            mock_public.read_item.side_effect = Exception("Not found")
            result = detect_doc_type("doc-123", "user-456")
            assert result is None

    def test_found_in_user_docs_no_user_id_provided(self):
        from services.metadata_service import detect_doc_type
        mock_doc = {"id": "doc-123", "user_id": "user-456"}
        with patch('services.metadata_service.cosmos_user_documents_container', create=True) as mock_user, \
             patch('services.metadata_service.cosmos_group_documents_container', create=True), \
             patch('services.metadata_service.cosmos_public_documents_container', create=True):
            mock_user.read_item.return_value = mock_doc
            result = detect_doc_type("doc-123")
            assert result == ("personal", "user-456")


@pytest.mark.usefixtures('set_test_env')
class TestProcessMetadataExtractionBackground:
    """Tests for process_metadata_extraction_background()."""

    def test_successful_personal_extraction(self):
        """Full happy path: extracts metadata and persists it for personal doc."""
        mock_metadata = {
            'title': 'My Report',
            'authors': ['Author A'],
            'abstract': 'Summary here',
            'keywords': ['kw1', 'kw2'],
            'publication_date': '01/2024',
            'organization': 'Org Inc',
        }
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.return_value = mock_metadata

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1')

            # Should call update_document 3 times: status start, metadata, status complete
            assert mock_update.call_count == 3

            # First call: status start
            first_call = mock_update.call_args_list[0]
            assert first_call[1]['status'] == 'Metadata extraction started...'
            assert first_call[1]['percentage_complete'] == 5

            # Second call: metadata fields
            second_call = mock_update.call_args_list[1]
            assert second_call[1]['title'] == 'My Report'
            assert second_call[1]['authors'] == ['Author A']
            assert second_call[1]['abstract'] == 'Summary here'
            assert second_call[1]['keywords'] == ['kw1', 'kw2']

            # Third call: status complete
            third_call = mock_update.call_args_list[2]
            assert third_call[1]['status'] == 'Metadata extraction complete'
            assert third_call[1]['percentage_complete'] == 100

    def test_successful_group_extraction(self):
        """Extracts metadata for group document, includes group_id in all calls."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.return_value = {
                'title': 'Group Doc', 'authors': [], 'abstract': '', 'keywords': [],
                'publication_date': '', 'organization': ''
            }

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1', group_id='grp-1')

            assert mock_update.call_count == 3
            # All calls should include group_id
            for c in mock_update.call_args_list:
                assert c[1].get('group_id') == 'grp-1'

            # extract_document_metadata should receive group_id
            mock_extract.assert_called_once_with(
                document_id='doc-1', user_id='user-1', group_id='grp-1'
            )

    def test_successful_public_workspace_extraction(self):
        """Extracts metadata for public workspace doc, includes public_workspace_id."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.return_value = {
                'title': 'Public Doc', 'authors': [], 'abstract': '', 'keywords': [],
                'publication_date': '', 'organization': ''
            }

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1', public_workspace_id='pw-1')

            assert mock_update.call_count == 3
            for c in mock_update.call_args_list:
                assert c[1].get('public_workspace_id') == 'pw-1'

            mock_extract.assert_called_once_with(
                document_id='doc-1', user_id='user-1', public_workspace_id='pw-1'
            )

    def test_empty_metadata_returns_early(self):
        """When extract returns None/empty, updates status and returns."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.return_value = None

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1')

            # Should call update_document 2 times: status start, empty status
            assert mock_update.call_count == 2
            second_call = mock_update.call_args_list[1]
            assert 'empty or failed' in second_call[1]['status']

    def test_empty_metadata_group_includes_group_id(self):
        """Empty metadata path for group doc includes group_id in status update."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.return_value = {}

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1', group_id='grp-1')

            # Empty dict is falsy, so should hit the "empty or failed" branch
            assert mock_update.call_count == 2
            for c in mock_update.call_args_list:
                assert c[1].get('group_id') == 'grp-1'

    def test_exception_updates_status(self):
        """When extract raises, status is updated with error message."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.side_effect = RuntimeError("LLM API timeout")

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1')

            # Should call update_document 2 times: status start, error status
            assert mock_update.call_count == 2
            second_call = mock_update.call_args_list[1]
            assert 'failed' in second_call[1]['status']
            assert 'LLM API timeout' in second_call[1]['status']

    def test_exception_public_workspace_includes_pw_id(self):
        """Exception path for public workspace includes public_workspace_id."""
        with patch('services.metadata_service.update_document', create=True) as mock_update, \
             patch('services.metadata_service.extract_document_metadata') as mock_extract:
            mock_extract.side_effect = Exception("Connection error")

            from services.metadata_service import process_metadata_extraction_background
            process_metadata_extraction_background('doc-1', 'user-1', public_workspace_id='pw-1')

            assert mock_update.call_count == 2
            second_call = mock_update.call_args_list[1]
            assert second_call[1].get('public_workspace_id') == 'pw-1'
            assert 'failed' in second_call[1]['status']
