# Advanced RAG - Search Quality Foundation

## Overview
The Search Quality Foundation enhances SimpleChat's hybrid search pipeline with intelligent result reranking, attention-aware document ordering, diversity selection, and quality metrics logging. These features improve the relevance and accuracy of AI-generated responses by ensuring the most pertinent search results are prioritized in the LLM context window.

**Version Implemented:** 0.239.001
**Phase:** Advanced RAG Phase 1

## Dependencies
- Azure AI Foundry (Cohere Rerank v4 Fast deployment)
- Azure OpenAI (embeddings for MMR cosine similarity)
- tiktoken (token counting)
- Azure Application Insights (quality metrics logging)
- Azure AI Search (hybrid search pipeline)

## Architecture Overview

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Cohere Reranking | `functions_reranking.py` | Rerank search results using Cohere Rerank v4 via Azure AI Services |
| Attention Reordering | `functions_reranking.py` | Optimize document order for LLM attention patterns (lost-in-the-middle) |
| MMR Diversity | `functions_reranking.py` | Maximal Marginal Relevance filtering for diverse results |
| Quality Metrics | `functions_reranking.py` | Log retrieval quality metrics to Application Insights |
| Token Counting | `functions_context_optimization.py` | tiktoken-based token counting for budget management |

### Key Functions

#### `rerank_with_cohere(query, documents, settings, top_n)`
Calls the Cohere Rerank v4 Fast model deployed on Azure AI Foundry to re-score search results by semantic relevance to the query. Returns documents sorted by relevance score with low-scoring results filtered out.

**Configuration:**
- `cohere_rerank_endpoint`: Azure AI Foundry endpoint URL
- `cohere_rerank_api_key`: API key for the deployment
- `cohere_rerank_top_n`: Number of top results to return (default: 5)
- `cohere_rerank_threshold`: Minimum relevance score threshold

#### `reorder_for_attention(documents)`
Implements the "lost-in-the-middle" optimization pattern. Research shows LLMs pay most attention to the beginning and end of their context window, with reduced attention to middle sections. This function interleaves high and low-relevance documents to place the most important results at attention-peak positions.

**Pattern:** [1st, 3rd, 5th, ..., 6th, 4th, 2nd] - odd-ranked items first (ascending), then even-ranked items (descending).

#### `mmr_filter(query_embedding, documents, lambda_param, k)`
Maximal Marginal Relevance selection balances relevance against diversity. It iteratively selects documents that are both relevant to the query and dissimilar to already-selected documents, reducing redundancy in search results.

**Parameters:**
- `lambda_param`: Balance between relevance (1.0) and diversity (0.0). Default: 0.7
- `k`: Maximum number of documents to select

#### `log_search_quality_metrics(query, results, was_reranked, was_reordered)`
Logs structured retrieval metrics to Application Insights for monitoring search quality over time:
- Result count, average/min/max scores
- Reranking and reordering flags
- Score distribution percentiles

### Search Pipeline Flow

```
User Query
    ↓
Azure AI Search (hybrid: vector + semantic)
    ↓
[Optional] Cohere Rerank v4 (re-score by relevance)
    ↓
[Optional] Attention Reorder (lost-in-the-middle optimization)
    ↓
[Optional] MMR Filter (diversity selection)
    ↓
Quality Metrics Logging
    ↓
LLM Context Window
```

## Admin Settings

Located in **Admin Settings > Search Quality** tab with two sections:

### Cohere Reranking Section
- **Enable Cohere Reranking**: Toggle on/off
- **Endpoint URL**: Azure AI Foundry deployment endpoint
- **API Key**: Authentication key
- **Top N Results**: Number of results to return after reranking
- **Relevance Threshold**: Minimum score to include a result

### Attention Optimization Section
- **Enable Attention Reordering**: Toggle lost-in-the-middle optimization
- **Reorder Strategy**: Selection of reordering algorithm

## Configuration Keys

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `enable_cohere_rerank` | bool | false | Enable Cohere reranking |
| `cohere_rerank_endpoint` | string | "" | Azure AI Foundry endpoint |
| `cohere_rerank_api_key` | string | "" | API key |
| `cohere_rerank_top_n` | int | 5 | Top results to keep |
| `cohere_rerank_threshold` | float | 0.0 | Minimum relevance score |
| `enable_attention_reorder` | bool | false | Enable attention reordering |

## Testing

### Functional Tests
- `functional_tests/test_search_quality.py` — 9 test cases covering reranking, reordering, MMR, and metrics logging

## Files Modified/Added

| File | Changes |
|------|---------|
| `functions_reranking.py` (265 lines) | New file: reranking, attention reorder, MMR, metrics |
| `functions_context_optimization.py` | Token counting utilities |
| `functions_search.py` | Integration of reranking pipeline into `hybrid_search()` |
| `functions_settings.py` | New configuration keys |
| `admin_settings.html` | Search Quality tab with Cohere and Attention sections |
| `_sidebar_nav.html` | Search Quality sidebar navigation entry |
| `admin_sidebar_nav.js` | Section scroll mappings |
| `config.py` | Default settings values |

(Ref: Advanced RAG Phase 1, Search Quality Foundation, Cohere Rerank, attention reordering)
