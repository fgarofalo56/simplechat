# tests/unit/test_sharing_service.py
# Unit tests for services/sharing_service.py — document sharing operations.

import pytest
from datetime import timezone
from unittest.mock import patch, MagicMock


# Custom exception class used across all tests
_CosmosNotFound = type('CosmosResourceNotFoundError', (Exception,), {})


@pytest.mark.usefixtures('set_test_env')
class TestShareDocumentWithUser:
    """Tests for share_document_with_user()."""

    def test_success(self):
        mock_datetime = MagicMock()
        mock_datetime.now.return_value.strftime.return_value = '2024-01-01T10:00:00Z'
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': [], 'file_name': 'test.pdf'
        }

        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.datetime', mock_datetime, create=True), \
             patch('services.sharing_service.timezone', timezone, create=True), \
             patch('services.chunk_service.get_all_chunks', return_value=[{'id': 'c1'}]), \
             patch('services.chunk_service.update_chunk_metadata'), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_user
            result = share_document_with_user('doc123', 'owner123', 'user456')
            assert result is True
            mock_c.upsert_item.assert_called_once()
            upserted = mock_c.upsert_item.call_args[0][0]
            assert 'user456,not_approved' in upserted['shared_user_ids']

    def test_already_shared_idempotent(self):
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': ['user456,not_approved'], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_user
            result = share_document_with_user('doc123', 'owner123', 'user456')
            assert result is True
            mock_c.upsert_item.assert_not_called()

    def test_non_owner_denied(self):
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': [], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_user
            result = share_document_with_user('doc123', 'not_owner', 'user456')
            assert result is False
            mock_c.upsert_item.assert_not_called()

    def test_document_not_found(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import share_document_with_user
            result = share_document_with_user('nonexistent', 'owner123', 'user456')
            assert result is False


@pytest.mark.usefixtures('set_test_env')
class TestUnshareDocumentFromUser:
    """Tests for unshare_document_from_user()."""

    def test_owner_unshares(self):
        mock_datetime = MagicMock()
        mock_datetime.now.return_value.strftime.return_value = '2024-01-01T10:00:00Z'
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': ['user456,approved', 'user789,not_approved'],
            'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.datetime', mock_datetime, create=True), \
             patch('services.sharing_service.timezone', timezone, create=True), \
             patch('services.chunk_service.get_all_chunks', return_value=[]), \
             patch('services.chunk_service.update_chunk_metadata'), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import unshare_document_from_user
            result = unshare_document_from_user('doc123', 'owner123', 'user456')
            assert result is True
            upserted = mock_c.upsert_item.call_args[0][0]
            assert 'user456,approved' not in upserted['shared_user_ids']
            assert 'user789,not_approved' in upserted['shared_user_ids']

    def test_self_removal(self):
        mock_datetime = MagicMock()
        mock_datetime.now.return_value.strftime.return_value = '2024-01-01T10:00:00Z'
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': ['user456,approved'], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.datetime', mock_datetime, create=True), \
             patch('services.sharing_service.timezone', timezone, create=True), \
             patch('services.chunk_service.get_all_chunks', return_value=[]), \
             patch('services.chunk_service.update_chunk_metadata'), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import unshare_document_from_user
            result = unshare_document_from_user('doc123', 'user456', 'user456')
            assert result is True
            mock_c.upsert_item.assert_called_once()

    def test_non_owner_denied(self):
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': ['user456,approved'], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import unshare_document_from_user
            result = unshare_document_from_user('doc123', 'not_owner', 'user456')
            assert result is False
            mock_c.upsert_item.assert_not_called()

    def test_document_not_found(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import unshare_document_from_user
            result = unshare_document_from_user('nonexistent', 'owner123', 'user456')
            assert result is False


@pytest.mark.usefixtures('set_test_env')
class TestGetSharedUsersForDocument:
    """Tests for get_shared_users_for_document()."""

    def test_returns_parsed_list(self):
        mock_document = {
            'id': 'doc123', 'user_id': 'owner123',
            'shared_user_ids': ['user456,approved', 'user789,not_approved', 'user999'],
        }
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import get_shared_users_for_document
            result = get_shared_users_for_document('doc123', 'owner123')
            expected = [
                {'id': 'user456', 'approval_status': 'approved'},
                {'id': 'user789', 'approval_status': 'not_approved'},
                {'id': 'user999', 'approval_status': 'unknown'},
            ]
            assert result == expected

    def test_non_owner_returns_none(self):
        mock_document = {'id': 'doc123', 'user_id': 'owner123', 'shared_user_ids': []}
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import get_shared_users_for_document
            result = get_shared_users_for_document('doc123', 'not_owner')
            assert result is None

    def test_not_found_returns_none(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import get_shared_users_for_document
            result = get_shared_users_for_document('nonexistent', 'owner123')
            assert result is None


@pytest.mark.usefixtures('set_test_env')
class TestIsDocumentSharedWithUser:
    """Tests for is_document_shared_with_user()."""

    def test_owner_returns_true(self):
        mock_doc = {'id': 'doc123', 'user_id': 'owner123', 'shared_user_ids': []}
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('doc123', 'owner123') is True

    def test_approved_user_returns_true(self):
        mock_doc = {'id': 'doc123', 'user_id': 'owner123', 'shared_user_ids': ['user456,approved']}
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('doc123', 'user456') is True

    def test_not_approved_returns_false(self):
        mock_doc = {'id': 'doc123', 'user_id': 'owner123', 'shared_user_ids': ['user456,not_approved']}
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('doc123', 'user456') is False

    def test_not_shared_returns_false(self):
        mock_doc = {'id': 'doc123', 'user_id': 'owner123', 'shared_user_ids': []}
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('doc123', 'user456') is False


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentsSharedWithUser:
    """Tests for get_documents_shared_with_user()."""

    def test_returns_only_approved_latest_versions(self):
        mock_docs = [
            {'id': 'doc1', 'user_id': 'o1', 'shared_user_ids': ['u456,approved'],
             'file_name': 'f1.pdf', 'version': 1},
            {'id': 'doc2', 'user_id': 'o2', 'shared_user_ids': ['u456,not_approved'],
             'file_name': 'f2.pdf', 'version': 1},
            {'id': 'doc3', 'user_id': 'o1', 'shared_user_ids': ['u456,approved'],
             'file_name': 'f1.pdf', 'version': 2},
        ]
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.return_value = mock_docs
            from services.sharing_service import get_documents_shared_with_user
            result = get_documents_shared_with_user('u456')
            assert len(result) == 1
            assert result[0]['id'] == 'doc3'
            assert result[0]['version'] == 2


@pytest.mark.usefixtures('set_test_env')
class TestShareDocumentWithGroup:
    """Tests for share_document_with_group()."""

    def test_success(self):
        mock_datetime = MagicMock()
        mock_datetime.now.return_value.strftime.return_value = '2024-01-01T10:00:00Z'
        mock_document = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': [], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.datetime', mock_datetime, create=True), \
             patch('services.sharing_service.timezone', timezone, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_group
            result = share_document_with_group('doc123', 'group123', 'group456')
            assert result is True
            upserted = mock_c.upsert_item.call_args[0][0]
            assert 'group456,not_approved' in upserted['shared_group_ids']

    def test_already_shared_idempotent(self):
        mock_document = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': ['group456,approved'], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_group
            result = share_document_with_group('doc123', 'group123', 'group456')
            assert result is True
            mock_c.upsert_item.assert_not_called()


@pytest.mark.usefixtures('set_test_env')
class TestIsDocumentSharedWithGroup:
    """Tests for is_document_shared_with_group()."""

    def test_owner_returns_true(self):
        mock_doc = {'id': 'doc123', 'group_id': 'group123', 'shared_group_ids': []}
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_group
            assert is_document_shared_with_group('doc123', 'group123') is True

    def test_approved_returns_true(self):
        mock_doc = {'id': 'doc123', 'group_id': 'group123', 'shared_group_ids': ['group456,approved']}
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_group
            assert is_document_shared_with_group('doc123', 'group456') is True

    def test_not_approved_returns_false(self):
        mock_doc = {'id': 'doc123', 'group_id': 'group123', 'shared_group_ids': ['group456,not_approved']}
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import is_document_shared_with_group
            assert is_document_shared_with_group('doc123', 'group456') is False


@pytest.mark.usefixtures('set_test_env')
class TestUnshareDocumentFromGroup:
    """Tests for unshare_document_from_group()."""

    def test_success(self):
        mock_datetime = MagicMock()
        mock_datetime.now.return_value.strftime.return_value = '2024-01-01T10:00:00Z'
        mock_document = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': ['group456,approved', 'group789,not_approved'],
            'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.datetime', mock_datetime, create=True), \
             patch('services.sharing_service.timezone', timezone, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import unshare_document_from_group
            result = unshare_document_from_group('doc123', 'group123', 'group456')
            assert result is True
            upserted = mock_c.upsert_item.call_args[0][0]
            assert 'group456,approved' not in upserted['shared_group_ids']
            assert 'group789,not_approved' in upserted['shared_group_ids']


@pytest.mark.usefixtures('set_test_env')
class TestGetSharedGroupsForDocument:
    """Tests for get_shared_groups_for_document()."""

    def test_returns_shared_groups(self):
        mock_doc = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': ['group456,approved', 'group789,not_approved'],
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import get_shared_groups_for_document
            result = get_shared_groups_for_document('doc123', 'group123')
            assert result == ['group456,approved', 'group789,not_approved']

    def test_non_owner_returns_none(self):
        mock_doc = {'id': 'doc123', 'group_id': 'group123', 'shared_group_ids': []}
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_doc
            from services.sharing_service import get_shared_groups_for_document
            result = get_shared_groups_for_document('doc123', 'not_owner')
            assert result is None

    def test_not_found_returns_none(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import get_shared_groups_for_document
            result = get_shared_groups_for_document('nonexistent', 'group123')
            assert result is None

    def test_exception_returns_none(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = Exception("Cosmos error")
            from services.sharing_service import get_shared_groups_for_document
            result = get_shared_groups_for_document('doc123', 'group123')
            assert result is None


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentsSharedWithGroup:
    """Tests for get_documents_shared_with_group()."""

    def test_returns_latest_versions(self):
        mock_docs = [
            {'id': 'doc1', 'group_id': 'g1', 'shared_group_ids': ['g456,approved'],
             'file_name': 'f1.pdf', 'version': 1},
            {'id': 'doc1v2', 'group_id': 'g1', 'shared_group_ids': ['g456,approved'],
             'file_name': 'f1.pdf', 'version': 2},
        ]
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.return_value = mock_docs
            from services.sharing_service import get_documents_shared_with_group
            result = get_documents_shared_with_group('g456')
            assert len(result) == 1
            assert result[0]['version'] == 2

    def test_empty_result(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.return_value = []
            from services.sharing_service import get_documents_shared_with_group
            result = get_documents_shared_with_group('g456')
            assert result == []

    def test_exception_returns_empty_list(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.side_effect = Exception("Cosmos error")
            from services.sharing_service import get_documents_shared_with_group
            result = get_documents_shared_with_group('g456')
            assert result == []


@pytest.mark.usefixtures('set_test_env')
class TestShareDocumentWithGroupEdgeCases:
    """Additional edge case tests for group sharing functions."""

    def test_share_non_owner_group_denied(self):
        mock_document = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': [], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import share_document_with_group
            result = share_document_with_group('doc123', 'not_owner_group', 'group456')
            assert result is False

    def test_share_not_found(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import share_document_with_group
            result = share_document_with_group('nonexistent', 'group123', 'group456')
            assert result is False

    def test_unshare_non_owner_denied(self):
        mock_document = {
            'id': 'doc123', 'group_id': 'group123',
            'shared_group_ids': ['group456,approved'], 'file_name': 'test.pdf'
        }
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.return_value = mock_document
            from services.sharing_service import unshare_document_from_group
            result = unshare_document_from_group('doc123', 'not_owner', 'group456')
            assert result is False

    def test_unshare_not_found(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import unshare_document_from_group
            result = unshare_document_from_group('nonexistent', 'group123', 'group456')
            assert result is False

    def test_unshare_exception_returns_false(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = Exception("Cosmos error")
            from services.sharing_service import unshare_document_from_group
            result = unshare_document_from_group('doc123', 'group123', 'group456')
            assert result is False

    def test_is_shared_not_found_returns_false(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import is_document_shared_with_group
            assert is_document_shared_with_group('nonexistent', 'group456') is False

    def test_is_shared_exception_returns_false(self):
        with patch('services.sharing_service.cosmos_group_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = Exception("Cosmos error")
            from services.sharing_service import is_document_shared_with_group
            assert is_document_shared_with_group('doc123', 'group456') is False


@pytest.mark.usefixtures('set_test_env')
class TestGetDocumentsSharedWithUserEdgeCases:
    """Additional edge case tests for get_documents_shared_with_user."""

    def test_empty_result(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.return_value = []
            from services.sharing_service import get_documents_shared_with_user
            result = get_documents_shared_with_user('user456')
            assert result == []

    def test_exception_returns_empty_list(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.query_items.side_effect = Exception("Cosmos error")
            from services.sharing_service import get_documents_shared_with_user
            result = get_documents_shared_with_user('user456')
            assert result == []

    def test_is_shared_user_not_found_returns_false(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = _CosmosNotFound()
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('nonexistent', 'user456') is False

    def test_is_shared_user_exception_returns_false(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = Exception("Cosmos error")
            from services.sharing_service import is_document_shared_with_user
            assert is_document_shared_with_user('doc123', 'user456') is False

    def test_get_shared_users_exception_returns_none(self):
        with patch('services.sharing_service.cosmos_user_documents_container', create=True) as mock_c, \
             patch('services.sharing_service.CosmosResourceNotFoundError', _CosmosNotFound, create=True), \
             patch('services.sharing_service.debug_print'):
            mock_c.read_item.side_effect = Exception("Cosmos error")
            from services.sharing_service import get_shared_users_for_document
            result = get_shared_users_for_document('doc123', 'owner123')
            assert result is None
