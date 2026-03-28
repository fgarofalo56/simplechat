# functions_graph_rag.py

import logging
import re

from config import (
    cosmos_graph_entities_container,
    cosmos_graph_relationships_container,
    cosmos_graph_communities_container,
)

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message)


# ---------------------------------------------------------------------------
# Query routing
# ---------------------------------------------------------------------------

_RELATIONSHIP_PATTERNS = [
    r"how are .* related",
    r"connection between",
    r"depends on",
    r"who works",
    r"compare",
    r"relationship between",
    r"difference between",
]

_COMMUNITY_PATTERNS = [
    r"summarize all",
    r"overview of",
    r"themes in",
    r"main topics",
    r"what are the key",
]


def route_query(query: str, workspace_id: str, settings: dict) -> str:
    """Route query to appropriate retrieval method.

    Returns:
        "graph_first" — Graph traversal + vector search
        "community_search" — Search community summaries
        "vector_only" — Standard hybrid search (default)
    """
    query_lower = query.lower()

    is_relationship = any(re.search(p, query_lower) for p in _RELATIONSHIP_PATTERNS)
    is_community = any(re.search(p, query_lower) for p in _COMMUNITY_PATTERNS)

    if is_relationship:
        entities = detect_query_entities(query, workspace_id)
        if entities:
            return "graph_first"
        return "community_search"

    if is_community:
        return "community_search"

    return "vector_only"


# ---------------------------------------------------------------------------
# Entity detection in queries
# ---------------------------------------------------------------------------

def detect_query_entities(query: str, workspace_id: str) -> list:
    """Detect known entities mentioned in a query.

    Searches the graph for entities whose names appear in the query text.
    """
    try:
        # Get all entity names for this workspace
        entities_query = (
            "SELECT c.id, c.entity_name, c.entity_type, c.description, c.community_id "
            "FROM c WHERE c.workspace_id = @ws AND c.type = 'graph_entity'"
        )
        params = [{"name": "@ws", "value": workspace_id}]

        all_entities = list(cosmos_graph_entities_container.query_items(
            query=entities_query, parameters=params, partition_key=workspace_id
        ))

        query_lower = query.lower()
        matched = []
        for entity in all_entities:
            name = entity.get("entity_name", "").lower()
            if name and len(name) >= 3 and name in query_lower:
                matched.append(entity)

        return matched[:10]  # Limit to top 10 matches

    except Exception as e:
        logger.error(f"Entity detection failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Graph traversal
# ---------------------------------------------------------------------------

def get_entity_neighborhood(entity_id: str, workspace_id: str,
                            depth: int = 2) -> tuple:
    """Get the neighborhood of an entity (1-N hops).

    Returns:
        (neighbors: list of entity dicts, relationships: list of rel dicts)
    """
    visited_entities = {entity_id}
    all_neighbors = []
    all_relationships = []

    current_ids = [entity_id]

    for hop in range(depth):
        if not current_ids:
            break

        next_ids = []
        for eid in current_ids:
            # Get outgoing relationships
            rels = _get_relationships_for_entity(eid, workspace_id)
            for rel in rels:
                all_relationships.append(rel)
                target = rel.get("target_entity_id")
                source = rel.get("source_entity_id")

                neighbor_id = target if target != eid else source
                if neighbor_id and neighbor_id not in visited_entities:
                    visited_entities.add(neighbor_id)
                    next_ids.append(neighbor_id)

                    # Fetch neighbor entity
                    try:
                        neighbor = cosmos_graph_entities_container.read_item(
                            item=neighbor_id, partition_key=workspace_id
                        )
                        all_neighbors.append(neighbor)
                    except Exception as e:
                        logger.warning(f"Failed to fetch neighbor entity {neighbor_id}: {e}")

        current_ids = next_ids

    return all_neighbors, all_relationships


def _get_relationships_for_entity(entity_id: str, workspace_id: str) -> list:
    """Get all relationships where entity is source or target."""
    query = (
        "SELECT * FROM c WHERE c.workspace_id = @ws "
        "AND (c.source_entity_id = @eid OR c.target_entity_id = @eid) "
        "AND c.type = 'graph_relationship'"
    )
    params = [
        {"name": "@ws", "value": workspace_id},
        {"name": "@eid", "value": entity_id},
    ]

    try:
        return list(cosmos_graph_relationships_container.query_items(
            query=query, parameters=params, partition_key=workspace_id
        ))
    except Exception as e:
        logger.warning(f"Failed to query relationships for entity {entity_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# Graph context formatting
# ---------------------------------------------------------------------------

def format_graph_context(entity: dict, neighbors: list, relationships: list) -> list:
    """Format graph neighborhood as context text for LLM."""
    context_parts = []

    entity_name = entity.get("entity_name", "Unknown")
    entity_type = entity.get("entity_type", "")
    description = entity.get("description", "")

    header = f"Entity: {entity_name} ({entity_type})"
    if description:
        header += f"\nDescription: {description}"
    context_parts.append(header)

    if relationships:
        rel_lines = []
        # Build name lookup
        name_lookup = {entity.get("id", ""): entity_name}
        for n in neighbors:
            name_lookup[n.get("id", "")] = n.get("entity_name", "Unknown")

        for rel in relationships:
            source_name = name_lookup.get(rel.get("source_entity_id"), "?")
            target_name = name_lookup.get(rel.get("target_entity_id"), "?")
            rel_type = rel.get("relationship_type", "RELATED_TO")
            rel_desc = rel.get("description", "")
            line = f"  {source_name} --[{rel_type}]--> {target_name}"
            if rel_desc:
                line += f" ({rel_desc})"
            rel_lines.append(line)

        if rel_lines:
            context_parts.append("Relationships:\n" + "\n".join(rel_lines))

    return context_parts


# ---------------------------------------------------------------------------
# Community summaries
# ---------------------------------------------------------------------------

def get_community_summary(community_id: str, workspace_id: str) -> dict:
    """Get the summary for a specific community."""
    try:
        return cosmos_graph_communities_container.read_item(
            item=community_id, partition_key=workspace_id
        )
    except Exception as e:
        logger.warning(f"Failed to read community summary {community_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main integration: graph-enhanced search
# ---------------------------------------------------------------------------

def graph_enhanced_search(query: str, vector_results: list,
                          workspace_id: str, settings: dict) -> tuple:
    """Augment vector search results with graph context.

    Returns:
        (vector_results, graph_context_text)
    """
    max_depth = settings.get("graph_rag_max_depth", 2)

    # Detect entities in query
    query_entities = detect_query_entities(query, workspace_id)
    if not query_entities:
        _log_event("graph_search_no_entities", extra={"query_length": len(query), "workspace_id": workspace_id})
        return vector_results, ""

    _log_event("graph_search_entities_detected", extra={
        "query_length": len(query), "entity_count": len(query_entities),
        "entities": [e.get("entity_name") for e in query_entities[:5]], "workspace_id": workspace_id,
    })

    graph_context = []

    # Get neighborhood for detected entities
    for entity in query_entities[:5]:
        neighbors, relationships = get_entity_neighborhood(
            entity["id"], workspace_id, depth=max_depth
        )
        context_parts = format_graph_context(entity, neighbors, relationships)
        graph_context.extend(context_parts)

    # Get community summaries
    community_ids = {
        e.get("community_id") for e in query_entities
        if e.get("community_id")
    }
    for comm_id in list(community_ids)[:3]:
        summary = get_community_summary(comm_id, workspace_id)
        if summary:
            graph_context.append(
                f"Topic Cluster: {summary.get('title', 'Unknown')}\n"
                f"{summary.get('summary', '')}"
            )

    return vector_results, "\n\n---\n\n".join(graph_context)
