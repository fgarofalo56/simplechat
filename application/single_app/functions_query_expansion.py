# functions_query_expansion.py

import logging

logger = logging.getLogger(__name__)


def generate_query_variations(query: str, gpt_client, gpt_model: str,
                              n: int = 3) -> list:
    """Generate N query variations for broader retrieval.

    Each variation approaches the question from a different angle.

    Args:
        query: Original user query.
        gpt_client: Azure OpenAI client.
        gpt_model: Model deployment name.
        n: Number of variations to generate.

    Returns:
        List of query strings (original + variations).
    """
    try:
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[{
                "role": "user",
                "content": (
                    f"Generate {n} different versions of this question, each "
                    f"approaching it from a different angle. Return only the "
                    f"questions, one per line, no numbering:\n\n{query}"
                ),
            }],
            max_tokens=200,
            temperature=0.7,
        )

        queries = [query]  # Always include original
        for line in response.choices[0].message.content.strip().split("\n"):
            cleaned = line.strip().lstrip("0123456789.)- ")
            if cleaned and len(cleaned) > 10:
                queries.append(cleaned)

        return queries[:n + 1]

    except Exception as e:
        logger.error(f"Query variation generation failed: {e}")
        return [query]


def hyde_generate(query: str, gpt_client, gpt_model: str) -> str:
    """Generate a hypothetical answer document for embedding (HyDE).

    The hypothetical document is embedded and used as an additional
    vector query alongside the original query embedding.

    Args:
        query: User's query.
        gpt_client: Azure OpenAI client.
        gpt_model: Model deployment name.

    Returns:
        Hypothetical document text.
    """
    try:
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[{
                "role": "user",
                "content": (
                    "Write a detailed paragraph that would perfectly answer "
                    f"this question, as if from an expert document:\n\n{query}"
                ),
            }],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"HyDE generation failed: {e}")
        return ""


def compress_chunk(query: str, chunk_text: str, gpt_client, gpt_model: str) -> str:
    """Extract only query-relevant sentences from a chunk (contextual compression).

    Reduces context size while preserving relevance. Should only be applied
    to top-N chunks after reranking to control cost.

    Args:
        query: User's query.
        chunk_text: Full chunk text.
        gpt_client: Azure OpenAI client.
        gpt_model: Model deployment name.

    Returns:
        Compressed chunk text with only relevant sentences.
    """
    try:
        response = gpt_client.chat.completions.create(
            model=gpt_model,
            messages=[{
                "role": "user",
                "content": (
                    f"Extract only the sentences from the following text that are "
                    f"directly relevant to answering: {query}\n\n"
                    f"Text:\n{chunk_text}\n\n"
                    f"Return only the relevant sentences, nothing else. "
                    f"If nothing is relevant, return 'No relevant content.'"
                ),
            }],
            max_tokens=500,
            temperature=0,
        )
        result = response.choices[0].message.content.strip()
        if result == "No relevant content.":
            return chunk_text  # Fallback to original
        return result

    except Exception as e:
        logger.error(f"Contextual compression failed: {e}")
        return chunk_text
