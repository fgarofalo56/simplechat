# tests/unit/test_workspace.py
# Unit tests for services/workspace.py — workspace abstraction layer.

import pytest
from services.workspace import WorkspaceType, get_partition_key_field


class TestWorkspaceType:
    """Tests for WorkspaceType enum."""

    def test_personal_value(self):
        assert WorkspaceType.PERSONAL.value == "personal"

    def test_group_value(self):
        assert WorkspaceType.GROUP.value == "group"

    def test_public_value(self):
        assert WorkspaceType.PUBLIC.value == "public"

    def test_from_string_personal(self):
        assert WorkspaceType("personal") == WorkspaceType.PERSONAL

    def test_from_string_group(self):
        assert WorkspaceType("group") == WorkspaceType.GROUP

    def test_from_string_public(self):
        assert WorkspaceType("public") == WorkspaceType.PUBLIC

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            WorkspaceType("invalid")


class TestGetPartitionKeyField:
    """Tests for get_partition_key_field()."""

    def test_personal_returns_user_id(self):
        assert get_partition_key_field(WorkspaceType.PERSONAL) == "user_id"

    def test_group_returns_group_id(self):
        assert get_partition_key_field(WorkspaceType.GROUP) == "group_id"

    def test_public_returns_workspace_id(self):
        assert get_partition_key_field(WorkspaceType.PUBLIC) == "workspace_id"


class TestGetWorkspaceContainers:
    """Tests for get_workspace_containers()."""

    def test_personal_has_expected_keys(self):
        from unittest.mock import patch, MagicMock
        with patch('services.workspace.cosmos_user_documents_container', MagicMock(), create=True), \
             patch('services.workspace.cosmos_group_documents_container', MagicMock(), create=True), \
             patch('services.workspace.cosmos_public_documents_container', MagicMock(), create=True):
            # The function imports from config_database, so we need to mock at that level
            mock_containers = {}
            for name in [
                'cosmos_user_documents_container', 'cosmos_group_documents_container',
                'cosmos_public_documents_container', 'cosmos_user_prompts_container',
                'cosmos_group_prompts_container', 'cosmos_public_prompts_container',
                'cosmos_personal_agents_container', 'cosmos_group_agents_container',
                'cosmos_global_agents_container', 'cosmos_personal_actions_container',
                'cosmos_group_actions_container', 'cosmos_global_actions_container',
            ]:
                mock_containers[name] = MagicMock()

            with patch.dict('sys.modules', {'config_database': MagicMock(**mock_containers)}):
                from services.workspace import get_workspace_containers
                containers = get_workspace_containers(WorkspaceType.PERSONAL)
                assert "documents" in containers
                assert "prompts" in containers
                assert "agents" in containers
                assert "actions" in containers


class TestGetStorageContainerName:
    """Tests for get_storage_container_name()."""

    def test_returns_string_for_each_type(self):
        from unittest.mock import patch, MagicMock
        mock_config = MagicMock()
        mock_config.storage_account_user_documents_container_name = "user-docs"
        mock_config.storage_account_group_documents_container_name = "group-docs"
        mock_config.storage_account_public_documents_container_name = "public-docs"

        with patch.dict('sys.modules', {'config_constants': mock_config}):
            from services.workspace import get_storage_container_name
            assert get_storage_container_name(WorkspaceType.PERSONAL) == "user-docs"
            assert get_storage_container_name(WorkspaceType.GROUP) == "group-docs"
            assert get_storage_container_name(WorkspaceType.PUBLIC) == "public-docs"
