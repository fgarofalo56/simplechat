# tests/unit/test_web_search_service.py
# Unit tests for services/web_search_service.py — citation extraction and token usage.

import pytest
from unittest.mock import patch


@pytest.mark.usefixtures('set_test_env')
class TestExtractWebSearchCitations:
    """Tests for _extract_web_search_citations_from_content()."""

    def _extract(self, content):
        from services.web_search_service import _extract_web_search_citations_from_content
        return _extract_web_search_citations_from_content(content)

    def test_empty_string_returns_empty(self):
        assert self._extract("") == []

    def test_none_returns_empty(self):
        assert self._extract(None) == []

    def test_markdown_link(self):
        content = "Check out [Example](https://example.com) for details."
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "Example"

    def test_markdown_link_with_title(self):
        content = '[Example](https://example.com "My Title")'
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "My Title"

    def test_html_link(self):
        content = '<a href="https://example.com">Example Site</a>'
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "Example Site"

    def test_html_link_with_title_attr(self):
        content = '<a href="https://example.com" title="My Title">Example</a>'
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "My Title"

    def test_bare_url(self):
        content = "Visit https://example.com for more info."
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "https://example.com"
        assert result[0]["title"] == "https://example.com"

    def test_bare_url_not_duplicated_from_markdown(self):
        """URLs inside markdown links should not be extracted as bare URLs."""
        content = "[Example](https://example.com)"
        result = self._extract(content)
        assert len(result) == 1  # Only the markdown citation, not a duplicate bare URL

    def test_multiple_citations(self):
        content = (
            "See [Google](https://google.com) and [Bing](https://bing.com) "
            "or visit https://yahoo.com directly."
        )
        result = self._extract(content)
        assert len(result) == 3
        urls = [c["url"] for c in result]
        assert "https://google.com" in urls
        assert "https://bing.com" in urls
        assert "https://yahoo.com" in urls

    def test_no_urls_returns_empty(self):
        content = "This is plain text with no links."
        result = self._extract(content)
        assert result == []

    def test_url_trailing_punctuation_stripped(self):
        content = "Visit https://example.com."
        result = self._extract(content)
        assert result[0]["url"] == "https://example.com"

    def test_http_url(self):
        content = "See http://example.com for details."
        result = self._extract(content)
        assert len(result) == 1
        assert result[0]["url"] == "http://example.com"


@pytest.mark.usefixtures('set_test_env')
class TestExtractTokenUsageFromMetadata:
    """Tests for _extract_token_usage_from_metadata()."""

    def _extract(self, metadata):
        from services.web_search_service import _extract_token_usage_from_metadata
        return _extract_token_usage_from_metadata(metadata)

    def test_valid_usage_dict(self):
        metadata = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }
        result = self._extract(metadata)
        assert result == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def test_usage_as_json_string(self):
        import json
        usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        metadata = {"usage": json.dumps(usage)}
        result = self._extract(metadata)
        assert result == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

    def test_usage_as_python_repr_string(self):
        metadata = {"usage": "{'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}"}
        result = self._extract(metadata)
        assert result == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

    def test_no_usage_field(self):
        metadata = {"other": "data"}
        result = self._extract(metadata)
        assert result == {}

    def test_none_metadata(self):
        result = self._extract(None)
        assert result == {}

    def test_non_mapping_metadata(self):
        result = self._extract("not a dict")
        assert result == {}

    def test_empty_usage_string(self):
        metadata = {"usage": ""}
        result = self._extract(metadata)
        assert result == {}

    def test_missing_total_tokens(self):
        metadata = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        result = self._extract(metadata)
        assert result == {}

    def test_float_values_converted_to_int(self):
        metadata = {
            "usage": {
                "prompt_tokens": 100.5,
                "completion_tokens": 50.3,
                "total_tokens": 150.8,
            }
        }
        result = self._extract(metadata)
        assert result["total_tokens"] == 150
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50

    def test_string_values_converted(self):
        metadata = {
            "usage": {
                "prompt_tokens": "100",
                "completion_tokens": "50",
                "total_tokens": "150",
            }
        }
        result = self._extract(metadata)
        assert result == {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}

    def test_invalid_usage_string_returns_empty(self):
        metadata = {"usage": "not json or python repr"}
        result = self._extract(metadata)
        assert result == {}

    def test_usage_none_returns_empty(self):
        metadata = {"usage": None}
        result = self._extract(metadata)
        assert result == {}

    def test_usage_list_returns_empty(self):
        metadata = {"usage": [1, 2, 3]}
        result = self._extract(metadata)
        assert result == {}

    def test_missing_prompt_and_completion_defaults_to_zero(self):
        """If prompt_tokens and completion_tokens are missing, they default to 0."""
        metadata = {"usage": {"total_tokens": 200}}
        result = self._extract(metadata)
        assert result["total_tokens"] == 200
        assert result["prompt_tokens"] == 0
        assert result["completion_tokens"] == 0


@pytest.mark.usefixtures('set_test_env')
class TestPerformWebSearchDisabled:
    """Tests for perform_web_search() when web search is disabled."""

    def test_disabled_returns_true(self):
        settings = {'enable_web_search': False}
        with patch('services.web_search_service.debug_print', create=True):
            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                conversation_id='conv-1',
                user_id='user-1',
                user_message='test query',
                user_message_id='msg-1',
                chat_type='personal',
                document_scope='all',
                active_group_id=None,
                active_public_workspace_id=None,
                search_query='test',
                system_messages_for_augmentation=[],
                agent_citations_list=[],
                web_search_citations_list=[],
            )
            assert result is True

    def test_disabled_with_none_returns_true(self):
        settings = {'enable_web_search': None}
        with patch('services.web_search_service.debug_print', create=True):
            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                conversation_id='conv-1',
                user_id='user-1',
                user_message='test',
                user_message_id='msg-1',
                chat_type='personal',
                document_scope='all',
                active_group_id=None,
                active_public_workspace_id=None,
                search_query='test',
                system_messages_for_augmentation=[],
                agent_citations_list=[],
                web_search_citations_list=[],
            )
            assert result is True


def _make_settings(agent_id='agent-123', enable=True):
    """Helper to build settings dict for perform_web_search tests."""
    return {
        'enable_web_search': enable,
        'web_search_agent': {
            'other_settings': {
                'azure_ai_foundry': {
                    'agent_id': agent_id,
                    'project_id': 'proj-1',
                    'endpoint': 'https://foundry.example.com',
                }
            }
        }
    }


def _call_kwargs(**overrides):
    """Common keyword arguments for perform_web_search."""
    defaults = dict(
        conversation_id='conv-1',
        user_id='user-1',
        user_message='What is the weather today?',
        user_message_id='msg-1',
        chat_type='personal',
        document_scope='all',
        active_group_id=None,
        active_public_workspace_id=None,
        search_query='weather today',
        system_messages_for_augmentation=[],
        agent_citations_list=[],
        web_search_citations_list=[],
    )
    defaults.update(overrides)
    return defaults


@pytest.mark.usefixtures('set_test_env')
class TestPerformWebSearchNoAgentId:
    """Tests for perform_web_search when agent_id is not configured."""

    def test_missing_agent_id_returns_false(self):
        """Should return False and add a system message when agent_id is empty."""
        settings = _make_settings(agent_id='')
        sys_msgs = []
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True):
            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                **{k: v for k, v in _call_kwargs(system_messages_for_augmentation=sys_msgs).items()
                   if k != 'settings'}
            )
            assert result is False
            assert len(sys_msgs) == 1
            assert 'not properly configured' in sys_msgs[0]['content']

    def test_no_foundry_settings_returns_false(self):
        """Missing foundry settings means no agent_id → returns False."""
        settings = {'enable_web_search': True, 'web_search_agent': {}}
        sys_msgs = []
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True):
            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                **{k: v for k, v in _call_kwargs(system_messages_for_augmentation=sys_msgs).items()
                   if k != 'settings'}
            )
            assert result is False


@pytest.mark.usefixtures('set_test_env')
class TestPerformWebSearchEmptyQuery:
    """Tests for perform_web_search when query text is empty."""

    def test_empty_query_returns_true(self):
        settings = _make_settings()
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True):
            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                **{k: v for k, v in _call_kwargs(
                    search_query='',
                    user_message='',
                ).items() if k != 'settings'}
            )
            assert result is True  # empty query isn't an error, just nothing to search


@pytest.mark.usefixtures('set_test_env')
class TestPerformWebSearchSuccess:
    """Tests for perform_web_search happy path — successful Foundry invocation."""

    def _make_result(self, message='The weather is sunny.', citations=None, metadata=None, model=None):
        """Build a mock FoundryAgentResult."""
        from unittest.mock import MagicMock
        result = MagicMock()
        result.message = message
        result.citations = citations or []
        result.metadata = metadata or {}
        result.model = model or 'gpt-4o'
        return result

    def test_successful_search_returns_true(self):
        settings = _make_settings()
        sys_msgs = []
        agent_cits = []
        web_cits = []
        mock_result = self._make_result(
            message='The weather is sunny. See [Weather](https://weather.com) for details.',
            citations=[{'url': 'https://weather.com', 'title': 'Weather'}],
            metadata={'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}},
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True) as mock_log_tokens, \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=sys_msgs,
                agent_citations_list=agent_cits,
                web_search_citations_list=web_cits,
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True
            # System message was added with web search results
            assert len(sys_msgs) == 1
            assert 'Web search results' in sys_msgs[0]['content']
            # Agent citations were created
            assert len(agent_cits) == 1
            assert agent_cits[0]['tool_name'] == 'Weather'
            # Web citations extracted from message
            assert len(web_cits) >= 1
            # Token usage was logged
            mock_log_tokens.assert_called_once()

    def test_search_no_message_no_augmentation(self):
        """When result.message is empty, no system message is added."""
        settings = _make_settings()
        sys_msgs = []
        mock_result = self._make_result(message=None, citations=[], metadata={})
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=sys_msgs,
                agent_citations_list=[],
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True
            assert len(sys_msgs) == 0  # No message to add

    def test_search_with_group_chat_type(self):
        """Group chat sets workspace_type='group' for token logging."""
        settings = _make_settings()
        mock_result = self._make_result(
            metadata={'usage': {'prompt_tokens': 5, 'completion_tokens': 10, 'total_tokens': 15}},
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True) as mock_log, \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=[],
                web_search_citations_list=[],
                conversation_id='conv-1',
                user_id='user-1',
                user_message='test',
                user_message_id='msg-1',
                chat_type='group',
                document_scope='all',
                active_group_id='grp-1',
                active_public_workspace_id=None,
                search_query='test query',
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs['workspace_type'] == 'group'
            assert call_kwargs['group_id'] == 'grp-1'

    def test_search_with_public_workspace(self):
        """Public workspace chat sets workspace_type='public' for token logging."""
        settings = _make_settings()
        mock_result = self._make_result(
            metadata={'usage': {'prompt_tokens': 5, 'completion_tokens': 10, 'total_tokens': 15}},
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True) as mock_log, \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=[],
                web_search_citations_list=[],
                conversation_id='conv-1',
                user_id='user-1',
                user_message='test',
                user_message_id='msg-1',
                chat_type='personal',
                document_scope='all',
                active_group_id=None,
                active_public_workspace_id='pw-1',
                search_query='test query',
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs['workspace_type'] == 'public'
            assert call_kwargs['public_workspace_id'] == 'pw-1'

    def test_token_logging_error_does_not_fail(self):
        """If log_token_usage raises, perform_web_search still returns True."""
        settings = _make_settings()
        mock_result = self._make_result(
            metadata={'usage': {'prompt_tokens': 5, 'completion_tokens': 10, 'total_tokens': 15}},
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True) as mock_log, \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result
            mock_log.side_effect = RuntimeError("Logging failed")

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=[],
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True  # Still succeeds despite logging failure

    def test_citation_with_url_and_title_dict(self):
        """Citation dicts with url and title are properly serialized."""
        settings = _make_settings()
        agent_cits = []

        mock_result = self._make_result(
            citations=[{'url': 'https://example.com/info', 'title': 'Example Info'}],
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=agent_cits,
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True
            assert len(agent_cits) == 1
            assert agent_cits[0]['tool_name'] == 'Example Info'
            assert agent_cits[0]['function_name'] == 'azure_ai_foundry_web_search'

    def test_citation_without_title_uses_url(self):
        """Citation dict without title falls back to url for tool_name."""
        settings = _make_settings()
        agent_cits = []

        mock_result = self._make_result(
            citations=[{'url': 'https://example.com/page'}],
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=agent_cits,
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True
            assert agent_cits[0]['tool_name'] == 'https://example.com/page'

    def test_citation_without_title_or_url_uses_default(self):
        """Citation dict without title or url uses default tool_name."""
        settings = _make_settings()
        agent_cits = []

        mock_result = self._make_result(
            citations=[{'snippet': 'some text only'}],
        )
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.log_token_usage', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.return_value = mock_result

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=[],
                agent_citations_list=agent_cits,
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is True
            assert agent_cits[0]['tool_name'] == 'Web search source'


@pytest.mark.usefixtures('set_test_env')
class TestPerformWebSearchErrors:
    """Tests for perform_web_search error paths."""

    def test_foundry_invocation_error_returns_false(self):
        """FoundryAgentInvocationError is caught and returns False."""
        settings = _make_settings()
        sys_msgs = []
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            from services.web_search_service import perform_web_search
            from foundry_agent_runtime import FoundryAgentInvocationError
            mock_asyncio.run.side_effect = FoundryAgentInvocationError("Agent failed")

            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=sys_msgs,
                agent_citations_list=[],
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is False
            assert len(sys_msgs) == 1
            assert 'failed' in sys_msgs[0]['content'].lower()

    def test_unexpected_error_returns_false(self):
        """Generic exceptions are caught and return False."""
        settings = _make_settings()
        sys_msgs = []
        with patch('services.web_search_service.debug_print', create=True), \
             patch('services.web_search_service.log_event', create=True), \
             patch('services.web_search_service.asyncio') as mock_asyncio, \
             patch('services.web_search_service.ChatMessageContent', create=True):

            mock_asyncio.run.side_effect = ConnectionError("Network down")

            from services.web_search_service import perform_web_search
            result = perform_web_search(
                settings=settings,
                system_messages_for_augmentation=sys_msgs,
                agent_citations_list=[],
                web_search_citations_list=[],
                **{k: v for k, v in _call_kwargs().items()
                   if k not in ('settings', 'system_messages_for_augmentation',
                                'agent_citations_list', 'web_search_citations_list')}
            )

            assert result is False
            assert len(sys_msgs) == 1
            assert 'unexpected error' in sys_msgs[0]['content'].lower()
