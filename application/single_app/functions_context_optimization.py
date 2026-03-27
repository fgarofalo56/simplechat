# functions_context_optimization.py

import tiktoken
import logging

logger = logging.getLogger(__name__)

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
