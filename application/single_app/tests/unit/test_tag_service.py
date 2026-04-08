# test_tag_service.py
# Unit tests for services/tag_service.py — tag normalization, validation, and filtering.

import pytest
from unittest.mock import patch, MagicMock


class TestNormalizeTag:
    """Tests for normalize_tag()."""

    def test_basic_normalization(self):
        from services.tag_service import normalize_tag
        assert normalize_tag("Hello") == "hello"

    def test_strips_whitespace(self):
        from services.tag_service import normalize_tag
        assert normalize_tag("  hello  ") == "hello"

    def test_empty_string(self):
        from services.tag_service import normalize_tag
        assert normalize_tag("") == ""

    def test_non_string_input(self):
        from services.tag_service import normalize_tag
        assert normalize_tag(123) == ""
        assert normalize_tag(None) == ""
        assert normalize_tag([]) == ""

    def test_mixed_case(self):
        from services.tag_service import normalize_tag
        assert normalize_tag("MyTag-123") == "mytag-123"

    def test_unicode(self):
        from services.tag_service import normalize_tag
        assert normalize_tag("  CAFÉ  ") == "café"


class TestValidateTags:
    """Tests for validate_tags()."""

    def test_valid_tags(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["python", "Flask", "web-dev"])
        assert valid is True
        assert error is None
        assert normalized == ["python", "flask", "web-dev"]

    def test_non_list_input(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags("not-a-list")
        assert valid is False
        assert "array" in error.lower()
        assert normalized == []

    def test_non_string_tag(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["valid", 123])
        assert valid is False
        assert "strings" in error.lower()

    def test_tag_too_long(self):
        from services.tag_service import validate_tags
        long_tag = "a" * 51
        valid, error, normalized = validate_tags([long_tag])
        assert valid is False
        assert "50 characters" in error

    def test_tag_exactly_50_chars(self):
        from services.tag_service import validate_tags
        tag = "a" * 50
        valid, error, normalized = validate_tags([tag])
        assert valid is True
        assert len(normalized) == 1

    def test_invalid_characters(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["hello world"])
        assert valid is False
        assert "invalid characters" in error.lower()

    def test_special_chars_rejected(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["tag@name"])
        assert valid is False

    def test_hyphens_and_underscores_allowed(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["my-tag", "my_tag"])
        assert valid is True
        assert normalized == ["my-tag", "my_tag"]

    def test_empty_tags_skipped(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["valid", "", "  "])
        assert valid is True
        assert normalized == ["valid"]

    def test_duplicate_tags_deduplicated(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags(["Python", "python", "PYTHON"])
        assert valid is True
        assert normalized == ["python"]

    def test_empty_list(self):
        from services.tag_service import validate_tags
        valid, error, normalized = validate_tags([])
        assert valid is True
        assert normalized == []


class TestSanitizeTagsForFilter:
    """Tests for sanitize_tags_for_filter()."""

    def test_string_input(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter("python, flask, web-dev")
        assert result == ["python", "flask", "web-dev"]

    def test_list_input(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter(["Python", "Flask"])
        assert result == ["python", "flask"]

    def test_invalid_input_type(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter(123)
        assert result == []

    def test_skips_invalid_chars(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter("valid, inv@lid, ok-tag")
        assert "valid" in result
        assert "ok-tag" in result
        assert len(result) == 2

    def test_skips_long_tags(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter(["short", "a" * 51])
        assert result == ["short"]

    def test_deduplicates(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter("python, Python, PYTHON")
        assert result == ["python"]

    def test_empty_string(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter("")
        assert result == []

    def test_empty_list(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter([])
        assert result == []

    def test_skips_non_string_list_items(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter(["valid", 123, None, "ok"])
        assert result == ["valid", "ok"]

    def test_comma_separated_with_extra_spaces(self):
        from services.tag_service import sanitize_tags_for_filter
        result = sanitize_tags_for_filter("  tag1 ,  tag2 ,  tag3  ")
        assert result == ["tag1", "tag2", "tag3"]


@pytest.mark.usefixtures('set_test_env')
class TestGetDefaultTagColor:
    """Tests for get_default_tag_color() — deterministic tag color generation."""

    def test_returns_hex_color(self):
        from services.tag_service import get_default_tag_color
        color = get_default_tag_color("test")
        assert color.startswith('#')
        assert len(color) == 7

    def test_deterministic_for_same_name(self):
        """Same tag name should always produce the same color."""
        from services.tag_service import get_default_tag_color
        assert get_default_tag_color("python") == get_default_tag_color("python")

    def test_different_names_can_differ(self):
        """Different tag names should potentially produce different colors."""
        from services.tag_service import get_default_tag_color
        # Pick names known to hash to different values
        color1 = get_default_tag_color("a")
        color2 = get_default_tag_color("b")
        # They CAN be the same (hash collision), but test that the function at least works
        assert color1.startswith('#')
        assert color2.startswith('#')

    def test_returns_from_palette(self):
        """Result should be one of the predefined palette colors."""
        from services.tag_service import get_default_tag_color
        palette = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
        ]
        assert get_default_tag_color("test-tag") in palette

    def test_empty_string(self):
        """Empty string should still produce a valid color."""
        from services.tag_service import get_default_tag_color
        color = get_default_tag_color("")
        assert color.startswith('#')
        assert len(color) == 7

    def test_case_sensitive_hashing(self):
        """Different cases should produce different hash values (and potentially different colors)."""
        from services.tag_service import get_default_tag_color
        # 'A' (65) vs 'a' (97) will hash differently
        color_upper = get_default_tag_color("A")
        color_lower = get_default_tag_color("a")
        # Both valid colors
        assert color_upper.startswith('#')
        assert color_lower.startswith('#')

    def test_unicode_tag_name(self):
        """Unicode characters should work."""
        from services.tag_service import get_default_tag_color
        color = get_default_tag_color("café")
        assert color.startswith('#')
        assert len(color) == 7

    def test_long_tag_name(self):
        """Long tag names should still work."""
        from services.tag_service import get_default_tag_color
        color = get_default_tag_color("a" * 100)
        assert color.startswith('#')
        assert len(color) == 7


@pytest.mark.usefixtures('set_test_env')
class TestGetWorkspaceTags:
    """Tests for get_workspace_tags() — retrieves workspace tags with counts."""

    def test_personal_workspace_tags(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'tags': ['python', 'flask']},
            {'tags': ['python', 'api']},
        ])
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {
            'python': {'color': '#3b82f6'},
        }}}}
        with patch('services.tag_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True), \
             patch('functions_settings.get_user_settings', return_value=mock_user_settings):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1')
            tag_names = [t['name'] for t in result]
            assert 'python' in tag_names
            assert 'flask' in tag_names
            assert 'api' in tag_names
            # python appears twice, so should have count=2
            python_tag = next(t for t in result if t['name'] == 'python')
            assert python_tag['count'] == 2
            assert python_tag['color'] == '#3b82f6'

    def test_group_workspace_tags(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'tags': ['design']},
        ])
        mock_group = {'tag_definitions': {'design': {'color': '#ef4444'}}}
        with patch('services.tag_service.cosmos_group_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True), \
             patch('functions_group.find_group_by_id', return_value=mock_group):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1', group_id='grp-1')
            assert len(result) == 1
            assert result[0]['name'] == 'design'
            assert result[0]['color'] == '#ef4444'

    def test_public_workspace_tags(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'tags': ['report']},
        ])
        mock_ws = {'tag_definitions': {}}
        with patch('services.tag_service.cosmos_public_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True), \
             patch('functions_public_workspaces.find_public_workspace_by_id', return_value=mock_ws):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1', public_workspace_id='pw-1')
            assert len(result) == 1
            assert result[0]['name'] == 'report'

    def test_empty_documents_returns_defined_tags(self):
        """Tags defined but not used should still appear with count=0."""
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([])
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {
            'unused-tag': {'color': '#10b981'},
        }}}}
        with patch('services.tag_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True), \
             patch('functions_settings.get_user_settings', return_value=mock_user_settings):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1')
            assert len(result) == 1
            assert result[0]['name'] == 'unused-tag'
            assert result[0]['count'] == 0

    def test_sorted_by_count_desc_then_name(self):
        mock_container = MagicMock()
        mock_container.query_items.return_value = iter([
            {'tags': ['beta']},
            {'tags': ['alpha', 'beta']},
        ])
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {}}}}
        with patch('services.tag_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True), \
             patch('functions_settings.get_user_settings', return_value=mock_user_settings):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1')
            # beta has count=2, alpha has count=1
            assert result[0]['name'] == 'beta'
            assert result[1]['name'] == 'alpha'

    def test_exception_returns_empty_list(self):
        mock_container = MagicMock()
        mock_container.query_items.side_effect = Exception("Cosmos error")
        with patch('services.tag_service.cosmos_user_documents_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_workspace_tags
            result = get_workspace_tags('user-1')
            assert result == []


@pytest.mark.usefixtures('set_test_env')
class TestGetOrCreateTagDefinition:
    """Tests for get_or_create_tag_definition() — creates or retrieves tag definitions."""

    def test_personal_creates_new_tag(self):
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {}}}}
        with patch('functions_settings.get_user_settings', return_value=mock_user_settings), \
             patch('functions_settings.update_user_settings') as mock_update, \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'personal')
            assert 'color' in result
            assert 'created_at' in result
            mock_update.assert_called_once()

    def test_personal_returns_existing_tag(self):
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {
            'existing': {'color': '#3b82f6', 'created_at': '2024-01-01'}
        }}}}
        with patch('functions_settings.get_user_settings', return_value=mock_user_settings), \
             patch('functions_settings.update_user_settings') as mock_update, \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'existing', 'personal')
            assert result['color'] == '#3b82f6'
            mock_update.assert_not_called()

    def test_personal_with_custom_color(self):
        mock_user_settings = {'settings': {'tag_definitions': {'personal': {}}}}
        with patch('functions_settings.get_user_settings', return_value=mock_user_settings), \
             patch('functions_settings.update_user_settings'), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'personal', color='#ff0000')
            assert result['color'] == '#ff0000'

    def test_group_creates_new_tag(self):
        mock_group = {'id': 'grp-1', 'tag_definitions': {}}
        mock_container = MagicMock()
        with patch('functions_group.find_group_by_id', return_value=mock_group), \
             patch('services.tag_service.cosmos_groups_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'group', group_id='grp-1')
            assert 'color' in result
            mock_container.upsert_item.assert_called_once()

    def test_group_not_found_returns_default(self):
        with patch('functions_group.find_group_by_id', return_value=None), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'group', group_id='grp-1')
            assert 'color' in result

    def test_public_creates_new_tag(self):
        mock_ws = {'id': 'pw-1', 'tag_definitions': {}}
        mock_container = MagicMock()
        with patch('functions_public_workspaces.find_public_workspace_by_id', return_value=mock_ws), \
             patch('services.tag_service.cosmos_public_workspaces_container', mock_container, create=True), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'public', public_workspace_id='pw-1')
            assert 'color' in result
            mock_container.upsert_item.assert_called_once()

    def test_public_not_found_returns_default(self):
        with patch('functions_public_workspaces.find_public_workspace_by_id', return_value=None), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'public', public_workspace_id='pw-1')
            assert 'color' in result

    def test_personal_no_tag_definitions_key(self):
        """Should handle missing tag_definitions in settings gracefully."""
        mock_user_settings = {'settings': {}}
        with patch('functions_settings.get_user_settings', return_value=mock_user_settings), \
             patch('functions_settings.update_user_settings') as mock_update, \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import get_or_create_tag_definition
            result = get_or_create_tag_definition('user-1', 'new-tag', 'personal')
            assert 'color' in result
            mock_update.assert_called_once()


@pytest.mark.usefixtures('set_test_env')
class TestPropagateTagsToChunks:
    """Tests for propagate_tags_to_chunks() — propagates tags to document chunks."""

    def test_propagates_to_all_chunks(self):
        mock_chunks = [
            {'id': 'chunk-1'},
            {'id': 'chunk-2'},
            {'id': 'chunk-3'},
        ]
        with patch('services.tag_service.get_all_chunks', return_value=mock_chunks, create=True), \
             patch('services.tag_service.update_chunk_metadata', create=True) as mock_update, \
             patch('services.tag_service.propagate_tags_to_blob_metadata'), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import propagate_tags_to_chunks
            propagate_tags_to_chunks('doc-1', ['python', 'flask'], 'user-1')
            assert mock_update.call_count == 3

    def test_no_chunks_found(self):
        with patch('services.tag_service.get_all_chunks', return_value=[], create=True), \
             patch('services.tag_service.update_chunk_metadata', create=True) as mock_update, \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import propagate_tags_to_chunks
            propagate_tags_to_chunks('doc-1', ['python'], 'user-1')
            mock_update.assert_not_called()

    def test_chunk_error_continues(self):
        """If one chunk fails, should continue with others."""
        mock_chunks = [
            {'id': 'chunk-1'},
            {'id': 'chunk-2'},
        ]
        with patch('services.tag_service.get_all_chunks', return_value=mock_chunks, create=True), \
             patch('services.tag_service.update_chunk_metadata', side_effect=[Exception("fail"), None], create=True) as mock_update, \
             patch('services.tag_service.propagate_tags_to_blob_metadata'), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import propagate_tags_to_chunks
            propagate_tags_to_chunks('doc-1', ['python'], 'user-1')
            assert mock_update.call_count == 2

    def test_get_all_chunks_exception_reraises(self):
        """If get_all_chunks fails, exception should propagate."""
        with patch('services.tag_service.get_all_chunks', side_effect=Exception("Cosmos error"), create=True), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import propagate_tags_to_chunks
            with pytest.raises(Exception, match="Cosmos error"):
                propagate_tags_to_chunks('doc-1', ['python'], 'user-1')

    def test_propagates_with_group_id(self):
        mock_chunks = [{'id': 'chunk-1'}]
        with patch('services.tag_service.get_all_chunks', return_value=mock_chunks, create=True), \
             patch('services.tag_service.update_chunk_metadata', create=True) as mock_update, \
             patch('services.tag_service.propagate_tags_to_blob_metadata'), \
             patch('services.tag_service.debug_print', create=True):
            from services.tag_service import propagate_tags_to_chunks
            propagate_tags_to_chunks('doc-1', ['python'], 'user-1', group_id='grp-1')
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs['group_id'] == 'grp-1'
