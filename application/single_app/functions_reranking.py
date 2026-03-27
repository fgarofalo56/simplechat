# functions_reranking.py

import logging
import time
import requests

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event to avoid import-time dependency on azure.monitor."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


def reorder_for_attention(documents: list) -> list:
    """Reorder documents to optimize for LLM attention patterns.

    LLMs attend most strongly to the beginning and end of the context window,
    with weaker attention to the middle ("lost-in-the-middle" effect).
    This function places the highest-relevance documents at the start and end
    of the list, pushing lower-relevance items to the middle.

    Assumes the input list is already sorted by relevance (highest first).

    Args:
        documents: List of search result dicts, sorted by relevance descending.

    Returns:
        Reordered list with highest-relevance docs at start and end.
    """
    if len(documents) <= 2:
        return documents

    # Interleave: even-indexed items go to the top, odd-indexed to the bottom (reversed)
    top_half = documents[::2]      # indices 0, 2, 4, ... (highest, 3rd highest, ...)
    bottom_half = documents[1::2]  # indices 1, 3, 5, ... (2nd highest, 4th highest, ...)
    return top_half + list(reversed(bottom_half))


def rerank_with_cohere(query: str, documents: list, settings: dict, top_n: int = 10) -> list:
    """Rerank search results using Cohere Rerank v4 via Azure AI Services.

    Calls the Azure-hosted Cohere rerank endpoint and returns documents
    reordered by the Cohere relevance score.

    Args:
        query: The user's search query.
        documents: List of search result dicts with 'chunk_text' field.
        settings: App settings dict with 'cohere_rerank_endpoint' and
                  'cohere_rerank_api_key'.
        top_n: Maximum number of results to return after reranking.

    Returns:
        Reranked list of documents with 'rerank_score' field added.
        Returns original documents on error.
    """
    if not documents:
        return documents

    endpoint = settings.get("cohere_rerank_endpoint", "").rstrip("/")
    api_key = settings.get("cohere_rerank_api_key", "")

    if not endpoint or not api_key:
        logger.warning("Cohere rerank skipped: endpoint or API key not configured")
        return documents

    # Build the rerank API URL
    # Azure AI Services format: {endpoint}/providers/cohere/v2/rerank
    rerank_url = f"{endpoint}/providers/cohere/v2/rerank"

    doc_texts = [doc.get("chunk_text", "") for doc in documents]

    payload = {
        "model": "cohere-rerank-v4-fast",
        "query": query,
        "documents": doc_texts,
        "top_n": min(top_n, len(documents)),
    }

    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    start_time = time.time()
    try:
        response = requests.post(rerank_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        duration_ms = int((time.time() - start_time) * 1000)

        data = response.json()
        results = data.get("results", [])

        reranked = []
        for result in results:
            idx = result["index"]
            if idx < len(documents):
                doc = documents[idx].copy()
                doc["rerank_score"] = result["relevance_score"]
                doc["original_rank"] = idx
                reranked.append(doc)

        _log_event(
            "cohere_rerank_complete",
            level=logging.INFO,
            extra={
                "duration_ms": duration_ms,
                "input_count": len(documents),
                "output_count": len(reranked),
                "top_n": top_n,
            }
        )

        return reranked

    except requests.exceptions.Timeout:
        duration_ms = int((time.time() - start_time) * 1000)
        _log_event(
            "cohere_rerank_timeout",
            level=logging.WARNING,
            extra={"duration_ms": duration_ms, "doc_count": len(documents)}
        )
        return documents

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        _log_event(
            "cohere_rerank_error",
            level=logging.ERROR,
            extra={"error": str(e), "duration_ms": duration_ms}
        )
        return documents


def log_search_quality_metrics(query: str, results: list, was_reranked: bool = False,
                               was_reordered: bool = False):
    """Log retrieval quality metrics to Application Insights.

    Args:
        query: The search query.
        results: Final search results list.
        was_reranked: Whether Cohere reranking was applied.
        was_reordered: Whether attention reordering was applied.
    """
    if not results:
        _log_event(
            "search_quality_metrics",
            level=logging.INFO,
            extra={
                "query_length": len(query),
                "result_count": 0,
                "reranked": was_reranked,
                "reordered": was_reordered,
            }
        )
        return

    scores = [r.get("score", 0) for r in results]
    reranker_scores = [r.get("reranker_score", 0) for r in results if r.get("reranker_score") is not None]

    # Source diversity: unique documents / total chunks
    unique_files = len(set(r.get("file_name", "") for r in results))
    total_chunks = len(results)

    # Rerank displacement: average position change from original to reranked order
    avg_displacement = 0.0
    if was_reranked:
        displacements = [abs(i - r.get("original_rank", i)) for i, r in enumerate(results)]
        avg_displacement = sum(displacements) / len(displacements) if displacements else 0.0

    _log_event(
        "search_quality_metrics",
        level=logging.INFO,
        extra={
            "query_length": len(query),
            "result_count": len(results),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "top_score": scores[0] if scores else 0,
            "avg_reranker_score": sum(reranker_scores) / len(reranker_scores) if reranker_scores else 0,
            "reranked": was_reranked,
            "reordered": was_reordered,
            "rerank_displacement": round(avg_displacement, 2),
            "source_diversity": round(unique_files / total_chunks, 3) if total_chunks > 0 else 0,
            "unique_sources": unique_files,
        }
    )


# ---------------------------------------------------------------------------
# MMR (Maximal Marginal Relevance) diversity filtering (Task 5.6)
# ---------------------------------------------------------------------------

def mmr_filter(query_embedding: list, documents: list,
               lambda_param: float = 0.7, k: int = 10) -> list:
    """Select diverse documents using Maximal Marginal Relevance.

    MMR balances relevance to the query with diversity among selected documents.
    lambda=0.7 means 70% relevance, 30% diversity.

    Args:
        query_embedding: The query's embedding vector.
        documents: List of document dicts with 'embedding' key.
        lambda_param: Trade-off between relevance and diversity (0-1).
        k: Number of documents to select.

    Returns:
        List of k most relevant and diverse documents.
    """
    if not documents or not query_embedding:
        return documents[:k] if documents else []

    import numpy as np

    def cosine_sim(a, b):
        a = np.array(a, dtype=np.float32)
        b = np.array(b, dtype=np.float32)
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return dot / norm if norm > 0 else 0.0

    # Filter to only docs that have embeddings
    docs_with_emb = [d for d in documents if d.get("embedding")]
    docs_without_emb = [d for d in documents if not d.get("embedding")]

    if not docs_with_emb:
        return documents[:k]

    selected = []
    remaining = list(range(len(docs_with_emb)))

    query_emb = np.array(query_embedding, dtype=np.float32)

    for _ in range(min(k, len(docs_with_emb))):
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            doc_emb = docs_with_emb[idx]["embedding"]
            relevance = cosine_sim(query_emb, doc_emb)

            diversity = 0.0
            if selected:
                diversity = max(
                    cosine_sim(doc_emb, docs_with_emb[s]["embedding"])
                    for s in selected
                )

            mmr_score = lambda_param * relevance - (1 - lambda_param) * diversity

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)

    result = [docs_with_emb[i] for i in selected]
    # Append docs without embeddings at the end
    result.extend(docs_without_emb[:max(0, k - len(result))])
    return result[:k]
