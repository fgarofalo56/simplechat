# web_search_service.py
# Web search orchestration, citation extraction, and token usage parsing.
# Extracted from route_backend_chats.py — Phase 4 God File Decomposition.

import ast
import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from functions_debug import debug_print
from functions_logging import log_event
from functions_activity_logging import log_token_usage
from foundry_agent_runtime import FoundryAgentInvocationError, execute_foundry_agent
from semantic_kernel.contents.chat_message_content import ChatMessageContent


def _extract_web_search_citations_from_content(content: str) -> List[Dict[str, str]]:
    if not content:
        return []
    debug_print(f"[Citation Extraction] Extracting citations from:\n{content}\n")

    citations: List[Dict[str, str]] = []

    markdown_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^\s\)]+)(?:\s+\"([^\"]+)\")?\)")
    html_pattern = re.compile(
        r"<a[^>]+href=\"(https?://[^\"]+)\"([^>]*)>(.*?)</a>",
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(r"title=\"([^\"]+)\"", re.IGNORECASE)
    url_pattern = re.compile(r"https?://[^\s\)\]\">]+")

    occupied_spans: List[range] = []

    for match in markdown_pattern.finditer(content):
        text, url, title = match.groups()
        url = (url or "").strip().rstrip(".,)")
        if not url:
            continue
        display_title = (title or text or url).strip()
        citations.append({"url": url, "title": display_title})
        occupied_spans.append(range(match.start(), match.end()))

    for match in html_pattern.finditer(content):
        url, attrs, inner = match.groups()
        url = (url or "").strip().rstrip(".,)")
        if not url:
            continue
        title_match = title_pattern.search(attrs or "")
        title = title_match.group(1) if title_match else None
        inner_text = re.sub(r"<[^>]+>", "", inner or "").strip()
        display_title = (title or inner_text or url).strip()
        citations.append({"url": url, "title": display_title})
        occupied_spans.append(range(match.start(), match.end()))

    for match in url_pattern.finditer(content):
        if any(match.start() in span for span in occupied_spans):
            continue
        url = (match.group(0) or "").strip().rstrip(".,)")
        if not url:
            continue
        citations.append({"url": url, "title": url})
    debug_print(f"[Citation Extraction] Extracted {len(citations)} citations. - {citations}\n")

    return citations


def _extract_token_usage_from_metadata(metadata: Dict[str, Any]) -> Dict[str, int]:
    if not isinstance(metadata, Mapping):
        debug_print(
            "[Web Search][Token Usage Extraction] Metadata is not a mapping. "
            f"type={type(metadata)}"
        )
        return {}

    usage = metadata.get("usage")
    if not usage:
        debug_print("[Web Search][Token Usage Extraction] No usage field found in metadata.")
        return {}

    if isinstance(usage, str):
        raw_usage = usage.strip()
        if not raw_usage:
            debug_print("[Web Search][Token Usage Extraction] Usage string was empty.")
            return {}
        try:
            usage = json.loads(raw_usage)
        except json.JSONDecodeError:
            try:
                usage = ast.literal_eval(raw_usage)
            except (ValueError, SyntaxError):
                debug_print(
                    "[Web Search][Token Usage Extraction] Failed to parse usage string."
                )
                return {}

    if not isinstance(usage, Mapping):
        debug_print(
            "[Web Search][Token Usage Extraction] Usage is not a mapping. "
            f"type={type(usage)}"
        )
        return {}

    def to_int(value: Any) -> Optional[int]:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    total_tokens = to_int(usage.get("total_tokens"))
    if total_tokens is None:
        debug_print(
            "[Web Search][Token Usage Extraction] total_tokens missing or invalid. "
            f"usage={usage}"
        )
        return {}

    prompt_tokens = to_int(usage.get("prompt_tokens")) or 0
    completion_tokens = to_int(usage.get("completion_tokens")) or 0
    debug_print(
        "[Web Search][Token Usage Extraction] Extracted token usage - "
        f"prompt: {prompt_tokens}, completion: {completion_tokens}, total: {total_tokens}"
    )

    return {
        "total_tokens": int(total_tokens),
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
    }


def perform_web_search(
    *,
    settings,
    conversation_id,
    user_id,
    user_message,
    user_message_id,
    chat_type,
    document_scope,
    active_group_id,
    active_public_workspace_id,
    search_query,
    system_messages_for_augmentation,
    agent_citations_list,
    web_search_citations_list,
):
    debug_print("[WebSearch] ========== ENTERING perform_web_search ==========")
    debug_print(f"[WebSearch] Parameters received:")
    debug_print(f"[WebSearch]   conversation_id: {conversation_id}")
    debug_print(f"[WebSearch]   user_id: {user_id}")
    debug_print(f"[WebSearch]   user_message: {user_message[:100] if user_message else None}...")
    debug_print(f"[WebSearch]   user_message_id: {user_message_id}")
    debug_print(f"[WebSearch]   chat_type: {chat_type}")
    debug_print(f"[WebSearch]   document_scope: {document_scope}")
    debug_print(f"[WebSearch]   active_group_id: {active_group_id}")
    debug_print(f"[WebSearch]   active_public_workspace_id: {active_public_workspace_id}")
    debug_print(f"[WebSearch]   search_query: {search_query[:100] if search_query else None}...")

    enable_web_search = settings.get("enable_web_search")
    debug_print(f"[WebSearch] enable_web_search setting: {enable_web_search}")

    if not enable_web_search:
        debug_print("[WebSearch] Web search is DISABLED in settings, returning early")
        return True  # Not an error, just disabled

    debug_print("[WebSearch] Web search is ENABLED, proceeding...")

    web_search_agent = settings.get("web_search_agent") or {}
    debug_print(f"[WebSearch] web_search_agent config present: {bool(web_search_agent)}")
    if web_search_agent:
        # Avoid logging sensitive data, just log structure
        debug_print(f"[WebSearch]   web_search_agent keys: {list(web_search_agent.keys())}")

    other_settings = web_search_agent.get("other_settings") or {}
    debug_print(f"[WebSearch] other_settings keys: {list(other_settings.keys()) if other_settings else '<empty>'}")

    foundry_settings = other_settings.get("azure_ai_foundry") or {}
    debug_print(f"[WebSearch] foundry_settings present: {bool(foundry_settings)}")
    if foundry_settings:
        # Log only non-sensitive keys
        safe_keys = ['agent_id', 'project_id', 'endpoint']
        safe_info = {k: foundry_settings.get(k, '<not set>') for k in safe_keys}
        debug_print(f"[WebSearch]   foundry_settings (safe keys): {safe_info}")

    agent_id = (foundry_settings.get("agent_id") or "").strip()
    debug_print(f"[WebSearch] Extracted agent_id: '{agent_id}'")

    if not agent_id:
        log_event(
            "[WebSearch] Skipping Foundry web search: agent_id is not configured",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
            level=logging.WARNING,
        )
        debug_print("[WebSearch] Foundry agent_id not configured, skipping web search.")
        # Add failure message so the model knows search was requested but not configured
        system_messages_for_augmentation.append({
            "role": "system",
            "content": "Web search was requested but is not properly configured. Please inform the user that web search is currently unavailable and you cannot provide real-time information. Do not attempt to answer questions requiring current information from your training data.",
        })
        return False  # Configuration error

    debug_print(f"[WebSearch] Agent ID is configured: {agent_id}")

    query_text = None
    try:
        query_text = search_query
        debug_print(f"[WebSearch] Using search_query as query_text: {query_text[:100] if query_text else None}...")
    except NameError:
        query_text = None
        debug_print("[WebSearch] search_query not defined, query_text is None")

    query_text = (query_text or user_message or "").strip()
    debug_print(f"[WebSearch] Final query_text after fallback: '{query_text[:100] if query_text else ''}'")

    if not query_text:
        debug_print("[WebSearch] Query text is EMPTY after processing, skipping web search")
        log_event(
            "[WebSearch] Skipping Foundry web search: empty query",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
            level=logging.WARNING,
        )
        return True  # Not an error, just empty query

    debug_print(f"[WebSearch] Building message history with query: {query_text[:100]}...")
    message_history = [
        ChatMessageContent(role="user", content=query_text)
    ]
    debug_print(f"[WebSearch] Message history created with {len(message_history)} message(s)")

    try:
        foundry_metadata = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message_id": user_message_id,
            "chat_type": chat_type,
            "document_scope": document_scope,
            "group_id": active_group_id if chat_type == "group" else None,
            "public_workspace_id": active_public_workspace_id,
            "search_query": query_text,
        }
        debug_print(f"[WebSearch] Foundry metadata prepared: {json.dumps(foundry_metadata, default=str)}")

        debug_print("[WebSearch] Calling execute_foundry_agent...")
        debug_print(f"[WebSearch]   foundry_settings keys: {list(foundry_settings.keys())}")
        debug_print(f"[WebSearch]   global_settings type: {type(settings)}")

        result = asyncio.run(
            execute_foundry_agent(
                foundry_settings=foundry_settings,
                global_settings=settings,
                message_history=message_history,
                metadata={k: v for k, v in foundry_metadata.items() if v is not None},
            )
        )
    except FoundryAgentInvocationError as exc:
        log_event(
            f"[WebSearch] Foundry agent invocation failed: {exc}",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "agent_id": agent_id,
            },
            level=logging.ERROR,
            exceptionTraceback=True,
        )
        # Add failure message so the model informs the user
        system_messages_for_augmentation.append({
            "role": "system",
            "content": f"Web search failed with error: {exc}. Please inform the user that the web search encountered an error and you cannot provide real-time information for this query. Do not attempt to answer questions requiring current information from your training data - instead, acknowledge the search failure and suggest the user try again.",
        })
        return False  # Search failed
    except Exception as exc:
        log_event(
            f"[WebSearch] Unexpected error invoking Foundry agent: {exc}",
            extra={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "agent_id": agent_id,
            },
            level=logging.ERROR,
            exceptionTraceback=True,
        )
        # Add failure message so the model informs the user
        system_messages_for_augmentation.append({
            "role": "system",
            "content": f"Web search failed with an unexpected error: {exc}. Please inform the user that the web search encountered an error and you cannot provide real-time information for this query. Do not attempt to answer questions requiring current information from your training data - instead, acknowledge the search failure and suggest the user try again.",
        })
        return False  # Search failed

    debug_print("[WebSearch] ========== FOUNDRY AGENT RESULT ==========")
    debug_print(f"[WebSearch] Result type: {type(result)}")
    debug_print(f"[WebSearch] Result has message: {bool(result.message)}")
    debug_print(f"[WebSearch] Result has citations: {bool(result.citations)}")
    debug_print(f"[WebSearch] Result has metadata: {bool(result.metadata)}")
    debug_print(f"[WebSearch] Result model: {getattr(result, 'model', 'N/A')}")

    if result.message:
        debug_print(f"[WebSearch] Result message length: {len(result.message)} chars")
        debug_print(f"[WebSearch] Result message preview: {result.message[:500] if len(result.message) > 500 else result.message}")
    else:
        debug_print("[WebSearch] Result message is EMPTY or None")

    if result.citations:
        debug_print(f"[WebSearch] Result citations count: {len(result.citations)}")
        for i, cit in enumerate(result.citations[:3]):
            debug_print(f"[WebSearch]   Citation {i}: {json.dumps(cit, default=str)[:200]}...")
    else:
        debug_print("[WebSearch] Result citations is EMPTY or None")

    if result.metadata:
        try:
            metadata_payload = json.dumps(result.metadata, default=str)
        except (TypeError, ValueError):
            metadata_payload = str(result.metadata)
        debug_print(f"[WebSearch] Foundry metadata: {metadata_payload}")
    else:
        debug_print("[WebSearch] Foundry metadata: <empty>")

    if result.message:
        debug_print("[WebSearch] Adding result message to system_messages_for_augmentation")
        system_messages_for_augmentation.append({
            "role": "system",
            "content": f"Web search results:\n{result.message}",
        })
        debug_print(f"[WebSearch] Added system message to augmentation list. Total augmentation messages: {len(system_messages_for_augmentation)}")

        debug_print("[WebSearch] Extracting web citations from result message...")
        web_citations = _extract_web_search_citations_from_content(result.message)
        debug_print(f"[WebSearch] Extracted {len(web_citations)} web citations from message content")
        if web_citations:
            web_search_citations_list.extend(web_citations)
            debug_print(f"[WebSearch] Total web_search_citations_list now has {len(web_search_citations_list)} citations")
        else:
            debug_print("[WebSearch] No web citations extracted from message content")
    else:
        debug_print("[WebSearch] No result.message to process for augmentation")

    citations = result.citations or []
    debug_print(f"[WebSearch] Processing {len(citations)} citations from result.citations")
    if citations:
        for i, citation in enumerate(citations):
            debug_print(f"[WebSearch] Processing citation {i}: {json.dumps(citation, default=str)[:200]}...")
            try:
                serializable = json.loads(json.dumps(citation, default=str))
            except (TypeError, ValueError):
                serializable = {"value": str(citation)}
            citation_title = serializable.get("title") or serializable.get("url") or "Web search source"
            debug_print(f"[WebSearch] Adding agent citation with title: {citation_title}")
            agent_citations_list.append({
                "tool_name": citation_title,
                "function_name": "azure_ai_foundry_web_search",
                "plugin_name": "azure_ai_foundry",
                "function_arguments": serializable,
                "function_result": serializable,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True,
            })
        debug_print(f"[WebSearch] Total agent_citations_list now has {len(agent_citations_list)} citations")
    else:
        debug_print("[WebSearch] No citations in result.citations to process")

    debug_print(f"[WebSearch] Starting token usage extraction from Foundry metadata. Metadata: {result.metadata}")
    token_usage = _extract_token_usage_from_metadata(result.metadata or {})
    if token_usage.get("total_tokens"):
        try:
            workspace_type = 'personal'
            if active_public_workspace_id:
                workspace_type = 'public'
            elif active_group_id:
                workspace_type = 'group'

            log_token_usage(
                user_id=user_id,
                token_type='web_search',
                total_tokens=token_usage.get('total_tokens', 0),
                model=result.model or 'azure-ai-foundry-web-search',
                workspace_type=workspace_type,
                prompt_tokens=token_usage.get('prompt_tokens'),
                completion_tokens=token_usage.get('completion_tokens'),
                conversation_id=conversation_id,
                message_id=user_message_id,
                group_id=active_group_id,
                public_workspace_id=active_public_workspace_id,
                additional_context={
                    'agent_id': agent_id,
                    'search_query': query_text,
                    'token_source': 'foundry_metadata'
                }
            )
        except Exception as log_error:
            log_event(
                f"[WebSearch] Failed to log web search token usage: {log_error}",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "agent_id": agent_id,
                },
                level=logging.WARNING,
            )

    debug_print("[WebSearch] ========== FINAL SUMMARY ==========")
    debug_print(f"[WebSearch] system_messages_for_augmentation count: {len(system_messages_for_augmentation)}")
    debug_print(f"[WebSearch] agent_citations_list count: {len(agent_citations_list)}")
    debug_print(f"[WebSearch] web_search_citations_list count: {len(web_search_citations_list)}")
    debug_print(f"[WebSearch] Token usage extracted: {token_usage}")
    debug_print("[WebSearch] ========== EXITING perform_web_search ==========")

    log_event(
        "[WebSearch] Foundry web search invocation complete",
        extra={
            "conversation_id": conversation_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "citation_count": len(citations),
        },
        level=logging.INFO,
    )

    return True  # Search succeeded
