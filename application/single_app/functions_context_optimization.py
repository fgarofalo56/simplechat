# functions_context_optimization.py

import logging
import tiktoken

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)

# Cache encoders to avoid repeated initialization
_encoder_cache = {}


def _get_encoder(model: str):
    """Get or create a cached tiktoken encoder for the given model."""
    if model not in _encoder_cache:
        try:
            _encoder_cache[model] = tiktoken.encoding_for_model(model)
        except KeyError:
            _encoder_cache[model] = tiktoken.get_encoding("cl100k_base")
    return _encoder_cache[model]


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens for a given text and model.

    Args:
        text: The text to count tokens for.
        model: The model name to use for tokenization. Falls back to
               cl100k_base encoding if the model is not recognized.

    Returns:
        Number of tokens in the text.
    """
    if not text:
        return 0
    enc = _get_encoder(model)
    return len(enc.encode(text))


def count_messages_tokens(messages: list, model: str = "gpt-4o") -> int:
    """Count tokens for a list of chat messages.

    Follows the OpenAI token counting convention:
    - Each message has a 4-token overhead (role/content framing)
    - 2 tokens for reply priming at the end

    Args:
        messages: List of message dicts with 'role' and 'content' keys.
        model: The model name to use for tokenization.

    Returns:
        Total token count across all messages including overhead.
    """
    if not messages:
        return 0
    total = 0
    for msg in messages:
        total += 4  # message overhead
        total += count_tokens(msg.get("content", ""), model)
        total += count_tokens(msg.get("role", ""), model)
        if msg.get("name"):
            total += count_tokens(msg["name"], model)
            total -= 1  # name replaces role in token count
    total += 2  # reply priming
    return total


# ---------------------------------------------------------------------------
# Progressive conversation summarization (Task 5.1)
# ---------------------------------------------------------------------------

def summarize_conversation(messages: list, max_tokens: int, model: str,
                           gpt_client=None, gpt_model: str = None) -> str:
    """Summarize older conversation turns, preserving key facts and decisions.

    Args:
        messages: List of message dicts to summarize.
        max_tokens: Maximum tokens for the summary output.
        model: tiktoken model name for counting.
        gpt_client: Azure OpenAI client instance.
        gpt_model: Model deployment name for GPT.

    Returns:
        Summary text string.
    """
    if not messages:
        return ""

    if gpt_client is None:
        try:
            from config import gpt_client as _client, gpt_model as _model
            gpt_client = _client
            gpt_model = gpt_model or _model
        except ImportError:
            return ""

    text = "\n".join([f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages])

    try:
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[{
                "role": "user",
                "content": (
                    "Summarize this conversation history, preserving key facts, "
                    "decisions, and context needed to continue the discussion. "
                    "Be concise.\n\n" + text[:3000]
                ),
            }],
            max_tokens=min(max_tokens, 500),
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Conversation summarization failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Token budget allocation (Task 5.2)
# ---------------------------------------------------------------------------

def build_optimized_context(system_prompt: str, conversation_history: list,
                            search_results: list, user_message: str,
                            max_context_tokens: int = 12000,
                            model: str = "gpt-4o",
                            gpt_client=None, gpt_model: str = None) -> dict:
    """Allocate token budget across search results, history, and summary.

    Budget split: search 50%, recent history 35%, conversation summary 15%.

    Returns dict with: summary, recent_messages, search_context, token_breakdown
    """
    system_tokens = count_tokens(system_prompt, model)
    user_tokens = count_tokens(user_message, model)
    response_reserve = 2000
    available = max_context_tokens - system_tokens - user_tokens - response_reserve

    if available <= 0:
        return {
            "summary": None,
            "recent_messages": conversation_history[-2:] if conversation_history else [],
            "search_context": search_results[:3] if search_results else [],
            "token_breakdown": {"available": 0, "system": system_tokens, "user": user_tokens},
        }

    search_budget = int(available * 0.50)
    recent_budget = int(available * 0.35)
    summary_budget = int(available * 0.15)

    # Fit search results within budget
    search_context = _fit_within_budget(search_results, search_budget, model)

    # Sliding window for recent messages
    recent_msgs = _sliding_window(conversation_history, recent_budget, model)

    # Summarize older messages
    older_msgs = conversation_history[:len(conversation_history) - len(recent_msgs)]
    summary = None
    if older_msgs and summary_budget > 50:
        summary = summarize_conversation(older_msgs, summary_budget, model, gpt_client, gpt_model)

    token_breakdown = {
        "available": available,
        "search_budget": search_budget,
        "recent_budget": recent_budget,
        "summary_budget": summary_budget,
        "search_used": sum(count_tokens(r.get("chunk_text", ""), model) for r in search_context),
        "recent_used": count_messages_tokens(recent_msgs, model),
        "summary_used": count_tokens(summary or "", model),
    }

    _log_event(
        "context_optimization_applied",
        level=logging.INFO,
        extra=token_breakdown,
    )

    return {
        "summary": summary,
        "recent_messages": recent_msgs,
        "search_context": search_context,
        "token_breakdown": token_breakdown,
    }


def _fit_within_budget(results: list, budget: int, model: str) -> list:
    """Select results that fit within the token budget."""
    fitted = []
    used = 0
    for r in results:
        text = r.get("chunk_text", "")
        tokens = count_tokens(text, model)
        if used + tokens > budget:
            break
        fitted.append(r)
        used += tokens
    return fitted


def _sliding_window(messages: list, budget: int, model: str) -> list:
    """Select most recent messages that fit within budget (newest first)."""
    if not messages:
        return []
    selected = []
    used = 0
    for msg in reversed(messages):
        tokens = count_tokens(msg.get("content", ""), model) + 4
        if used + tokens > budget:
            break
        selected.insert(0, msg)
        used += tokens
    return selected


# ---------------------------------------------------------------------------
# Map-reduce summarization (Task 5.3)
# ---------------------------------------------------------------------------

def map_reduce_summarize(query: str, documents: list, batch_size: int = 5,
                          gpt_client=None, gpt_model: str = None) -> str:
    """Map: summarize each batch in context of query. Reduce: synthesize summaries."""
    if not documents:
        return ""

    if gpt_client is None:
        try:
            from config import gpt_client as _client, gpt_model as _model
            gpt_client = _client
            gpt_model = gpt_model or _model
        except ImportError:
            return ""

    batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]

    batch_summaries = []
    for batch in batches:
        batch_text = "\n\n".join([d.get("chunk_text", "") for d in batch])
        try:
            response = gpt_client.chat.completions.create(
                model=gpt_model,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Given this query: {query}\n\n"
                        f"Summarize the key information from these documents "
                        f"that is relevant to the query:\n\n{batch_text[:3000]}"
                    ),
                }],
                max_tokens=300,
                temperature=0,
            )
            batch_summaries.append(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Map-reduce batch summarization failed: {e}")

    if not batch_summaries:
        return ""

    if len(batch_summaries) == 1:
        return batch_summaries[0]

    # Reduce: synthesize
    try:
        combined = "\n\n".join(batch_summaries)
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[{
                "role": "user",
                "content": (
                    f"Given this query: {query}\n\n"
                    f"Synthesize these summaries into a comprehensive answer:\n\n"
                    f"{combined[:3000]}"
                ),
            }],
            max_tokens=500,
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Map-reduce synthesis failed: {e}")
        return "\n\n".join(batch_summaries)
