# Advanced RAG - Context Optimization & Advanced Search

## Overview
Context Optimization provides intelligent token budget management, conversation summarization, and advanced query expansion techniques to maximize the quality and efficiency of AI-generated responses. Features include HyDE (Hypothetical Document Embeddings), multi-query expansion, MMR (Maximal Marginal Relevance) diversity filtering, contextual compression, and map-reduce summarization.

**Version Implemented:** 0.239.003
**Phase:** Advanced RAG Phase 5

## Dependencies
- `tiktoken` (token counting)
- Azure OpenAI (GPT for summarization, query expansion, compression)
- Azure AI Search (search pipeline integration)

## Architecture Overview

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Token Budget Management | `functions_context_optimization.py` | 290 | Token counting, context budget allocation, conversation summarization |
| Query Expansion | `functions_query_expansion.py` | 132 | HyDE, multi-query generation, contextual compression |
| MMR Diversity | `functions_reranking.py` | — | Maximal Marginal Relevance filtering |

### Key Functions

#### Token Budget Management (`functions_context_optimization.py`)

- **`count_tokens(text, model)`**: Count tokens for text using tiktoken with encoder caching. Supports GPT-3.5, GPT-4, and GPT-4o model families.

- **`count_messages_tokens(messages, model)`**: Count tokens for a list of chat messages, including message overhead tokens per the OpenAI token counting spec.

- **`summarize_conversation(messages, max_tokens, model, gpt_client, gpt_model)`**: Summarizes older conversation turns to fit within a token budget while preserving key facts, decisions, and context. Uses GPT to generate a concise summary.

- **`build_optimized_context(system_prompt, conversation_history, search_results, user_message, max_context_tokens, model, gpt_client, gpt_model)`**: The main orchestrator — allocates token budget across system prompt, search results, conversation history, and user message. Applies summarization when history exceeds budget. Priority order: system prompt → user message → search results → history.

- **`_fit_within_budget(results, budget, model)`**: Greedily selects search results that fit within the allocated token budget, preserving relevance ordering.

- **`_sliding_window(messages, budget, model)`**: Selects the most recent conversation messages that fit within the history budget (newest first).

- **`map_reduce_summarize(query, documents, batch_size, gpt_client, gpt_model)`**: Two-phase summarization for large document sets. Map phase: summarize each batch in context of the query. Reduce phase: synthesize batch summaries into a coherent answer.

#### Query Expansion (`functions_query_expansion.py`)

- **`generate_query_variations(query, gpt_client, gpt_model, n)`**: Generates N semantically diverse variations of a user query using GPT. Each variation rephrases the query to capture different aspects or phrasings, improving recall when searching.

- **`hyde_generate(query, gpt_client, gpt_model)`**: Hypothetical Document Embeddings — generates a hypothetical answer document for a query using GPT. The hypothetical answer is then embedded and used for vector search, often improving retrieval quality for complex or abstract queries.

- **`compress_chunk(query, chunk_text, gpt_client, gpt_model)`**: Contextual compression — extracts only the query-relevant sentences from a document chunk using GPT. Reduces noise in the context window by removing irrelevant content from search results.

### Context Budget Allocation

```
Total Token Budget (e.g., 8192)
    ├── System Prompt (fixed cost, always included)
    ├── User Message (fixed cost, always included)
    ├── Search Results (50% of remaining budget)
    │   ├── Result 1 (highest relevance)
    │   ├── Result 2
    │   └── ... (greedy fit)
    └── Conversation History (50% of remaining budget)
        ├── Most Recent Messages (sliding window)
        └── Summary of Older Messages (if budget exceeded)
```

### Advanced Retrieval Pipeline

```
User Query
    ↓
[Optional] Multi-Query Expansion (N variations)
    ↓
[Optional] HyDE Generation (hypothetical answer)
    ↓
Vector/Hybrid Search (per query variation)
    ↓
Result Merging & Deduplication
    ↓
[Optional] Contextual Compression (per chunk)
    ↓
[Optional] MMR Diversity Filtering
    ↓
Token Budget Fitting
    ↓
Optimized LLM Context
```

## Admin Settings

Located in **Admin Settings > Context Optimization** tab:

### Token Budget Section
- **Enable Token Budget Management**: Toggle budget-aware context building
- **Max Context Tokens**: Maximum tokens for the LLM context window
- **Search Result Budget %**: Percentage of budget for search results (default: 50%)
- **Enable Conversation Summarization**: Summarize older turns when history exceeds budget

### Advanced Retrieval Section
- **Enable Multi-Query Expansion**: Generate query variations for broader retrieval
- **Number of Query Variations**: How many variations to generate (default: 3)
- **Enable HyDE**: Use hypothetical document embeddings
- **Enable Contextual Compression**: Compress chunks to query-relevant content
- **Enable Map-Reduce Summarization**: Use map-reduce for large document sets

## Configuration Keys

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `enable_token_budget` | bool | false | Enable token budget management |
| `max_context_tokens` | int | 8192 | Max tokens for context window |
| `search_budget_pct` | int | 50 | % of budget for search results |
| `enable_conversation_summarization` | bool | false | Summarize older conversation turns |
| `enable_multi_query` | bool | false | Enable multi-query expansion |
| `multi_query_count` | int | 3 | Number of query variations |
| `enable_hyde` | bool | false | Enable HyDE |
| `enable_contextual_compression` | bool | false | Enable contextual compression |
| `enable_map_reduce` | bool | false | Enable map-reduce summarization |

## Testing

### Functional Tests
- `functional_tests/test_context_optimization.py` — Token counting, budget allocation, summarization
- `functional_tests/test_query_expansion.py` — HyDE, multi-query, compression

## Files Modified/Added

| File | Changes |
|------|---------|
| `functions_context_optimization.py` (290 lines) | New file: token budgeting, summarization, map-reduce |
| `functions_query_expansion.py` (132 lines) | New file: HyDE, multi-query, contextual compression |
| `functions_reranking.py` | MMR diversity filtering |
| `admin_settings.html` | Context Optimization tab sections |
| `_sidebar_nav.html` | Context Optimization sidebar navigation entry |
| `config.py` | Default settings values |

(Ref: Advanced RAG Phase 5, Context Optimization, Token Budget, HyDE, Multi-Query, MMR, Contextual Compression)
