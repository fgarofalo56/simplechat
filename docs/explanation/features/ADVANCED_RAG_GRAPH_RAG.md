# Advanced RAG - Graph RAG

## Overview
Graph RAG adds knowledge graph capabilities to SimpleChat's retrieval pipeline. Entities and relationships are automatically extracted from documents and stored in Azure Cosmos DB, enabling graph-enhanced search that augments traditional vector search with structured knowledge context. Community detection groups related entities for thematic summaries.

**Version Implemented:** 0.239.003
**Phase:** Advanced RAG Phase 4

## Dependencies
- Azure Cosmos DB (entity/relationship/community storage)
- Azure OpenAI (entity extraction via GPT, community summarization)
- Azure AI Search (vector search integration)
- `networkx` (graph algorithms, optional for community detection)

## Architecture Overview

### Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Entity Extraction | `functions_graph_entities.py` | 287 | Extract entities/relationships from document chunks via GPT |
| Graph RAG Search | `functions_graph_rag.py` | 278 | Query routing, graph-enhanced search, neighborhood traversal |
| Community Detection | `functions_graph_communities.py` | 206 | Leiden community detection, thematic summarization |

### Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `graph_entities` | `/workspace_id` | Entity nodes (name, type, description, sources) |
| `graph_relationships` | `/workspace_id` | Edges between entities (type, description, weight) |
| `graph_communities` | `/workspace_id` | Detected communities with summaries |

### Key Functions

#### Entity Extraction (`functions_graph_entities.py`)

- **`extract_entities_from_chunk(chunk_text, settings)`**: Uses GPT to extract named entities (people, organizations, concepts, technologies, events) and their relationships from a text chunk. Returns structured JSON with entity names, types, descriptions, and relationship triples.

- **`resolve_entity(entity, workspace_id, settings)`**: Entity resolution/deduplication — matches extracted entities against existing graph nodes using normalized name matching. Returns an existing entity ID if found, or creates a new entity node.

- **`save_relationship(source_entity_id, target_entity_id, rel_type, description, workspace_id, source_document_ids)`**: Persists a relationship edge between two entities with type, description, and source document references.

- **`extract_and_store_entities(document_id, user_id, group_id, public_workspace_id, settings)`**: Orchestrates the full extraction pipeline — fetches all chunks for a document, extracts entities from each chunk, resolves against the graph, and saves relationships.

#### Graph RAG Search (`functions_graph_rag.py`)

- **`route_query(query, workspace_id, settings)`**: Analyzes a query to determine if graph search would be beneficial. Returns a routing decision (vector-only, graph-only, or hybrid).

- **`detect_query_entities(query, workspace_id)`**: Identifies known entities mentioned in a user query by matching against the workspace's entity graph.

- **`get_entity_neighborhood(entity_id, workspace_id, depth)`**: Traverses the graph to collect an entity's neighborhood up to N hops, returning connected entities and relationships.

- **`format_graph_context(entity, neighbors, relationships)`**: Formats graph neighborhood data as natural language context text for injection into the LLM prompt.

- **`graph_enhanced_search(query, vector_results, workspace_id, settings)`**: The main integration point — augments vector search results with graph context. Detects entities in the query, retrieves their neighborhoods, and prepends structured graph knowledge to the search context.

#### Community Detection (`functions_graph_communities.py`)

- **`detect_communities(workspace_id, settings)`**: Runs community detection on the workspace's entity graph. Builds a NetworkX graph from Cosmos DB entities and relationships, applies the Leiden algorithm, and stores detected communities.

- **`generate_community_summary(community_id, workspace_id, settings)`**: Uses GPT to generate a thematic summary for a community of entities, describing the common themes, key entities, and their relationships.

### Search Enhancement Flow

```
User Query
    ↓
Query Entity Detection (match against known entities)
    ↓
Entity Neighborhood Retrieval (1-2 hop traversal)
    ↓
Format Graph Context (structured knowledge text)
    ↓
Merge with Vector Search Results
    ↓
Enhanced LLM Context (graph knowledge + document chunks)
```

## Admin Settings

Located in **Admin Settings > Graph RAG** tab:

- **Enable Graph RAG**: Master toggle for graph-enhanced search
- **Auto-Extract Entities**: Automatically extract entities when documents are uploaded
- **Entity Extraction Model**: GPT model to use for extraction
- **Community Detection**: Enable/disable automatic community detection
- **Graph Traversal Depth**: Maximum hops for neighborhood queries (1-3)
- **Query Routing**: Enable intelligent routing between vector and graph search

## Configuration Keys

| Setting Key | Type | Default | Description |
|-------------|------|---------|-------------|
| `enable_graph_rag` | bool | false | Enable graph RAG features |
| `graph_auto_extract` | bool | true | Auto-extract entities on upload |
| `graph_extraction_model` | string | "" | GPT model for extraction |
| `graph_community_detection` | bool | false | Enable community detection |
| `graph_traversal_depth` | int | 2 | Max hops for neighborhood |
| `graph_query_routing` | bool | true | Enable intelligent query routing |

## Testing

### Functional Tests
- `functional_tests/test_graph_rag.py` — Tests for entity extraction, resolution, neighborhood traversal, graph-enhanced search

## Files Modified/Added

| File | Changes |
|------|---------|
| `functions_graph_entities.py` (287 lines) | New file: entity extraction, resolution, storage |
| `functions_graph_rag.py` (278 lines) | New file: graph search, query routing, context formatting |
| `functions_graph_communities.py` (206 lines) | New file: community detection, summarization |
| `admin_settings.html` | Graph RAG tab with settings |
| `_sidebar_nav.html` | Graph RAG sidebar navigation entry |
| `config.py` | Cosmos container configuration, default settings |
| `requirements.txt` | networkx dependency |

(Ref: Advanced RAG Phase 4, Graph RAG, Entity Extraction, Community Detection, Knowledge Graph)
