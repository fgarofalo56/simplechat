# functions_graph_communities.py

import logging
import uuid
from datetime import datetime, timezone

from config import (
    cosmos_graph_entities_container,
    cosmos_graph_relationships_container,
    cosmos_graph_communities_container,
)

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


def detect_communities(workspace_id: str, settings: dict) -> list:
    """Run community detection on workspace graph using Leiden algorithm.

    This is a batch operation, not per-query. Should be triggered:
    - After significant new documents are uploaded
    - On-demand via admin action

    Returns list of community dicts with entity assignments.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.error("networkx not installed, cannot detect communities")
        return []

    # Load all entities
    entity_query = (
        "SELECT c.id, c.entity_name, c.entity_type FROM c "
        "WHERE c.workspace_id = @ws AND c.type = 'graph_entity'"
    )
    entities = list(cosmos_graph_entities_container.query_items(
        query=entity_query,
        parameters=[{"name": "@ws", "value": workspace_id}],
        partition_key=workspace_id,
    ))

    if len(entities) < 3:
        logger.info(f"Not enough entities ({len(entities)}) for community detection")
        return []

    # Load all relationships
    rel_query = (
        "SELECT c.source_entity_id, c.target_entity_id, c.weight FROM c "
        "WHERE c.workspace_id = @ws AND c.type = 'graph_relationship'"
    )
    relationships = list(cosmos_graph_relationships_container.query_items(
        query=rel_query,
        parameters=[{"name": "@ws", "value": workspace_id}],
        partition_key=workspace_id,
    ))

    # Build networkx graph
    G = nx.Graph()
    entity_ids = {e["id"] for e in entities}
    for e in entities:
        G.add_node(e["id"], name=e.get("entity_name", ""), type=e.get("entity_type", ""))

    for r in relationships:
        src = r.get("source_entity_id")
        tgt = r.get("target_entity_id")
        if src in entity_ids and tgt in entity_ids:
            G.add_edge(src, tgt, weight=r.get("weight", 1.0))

    # Run community detection
    try:
        from graspologic.partition import leiden
        partition = leiden(G, random_seed=42)
    except ImportError:
        # Fallback: use networkx greedy modularity
        from networkx.algorithms.community import greedy_modularity_communities
        communities_nx = greedy_modularity_communities(G)
        partition = {}
        for i, community in enumerate(communities_nx):
            for node in community:
                partition[node] = i

    # Group entities by community
    community_members = {}
    for node_id, comm_id in partition.items():
        comm_key = str(comm_id)
        if comm_key not in community_members:
            community_members[comm_key] = []
        community_members[comm_key].append(node_id)

    # Store community assignments
    now = datetime.now(timezone.utc).isoformat()
    communities = []

    for comm_key, member_ids in community_members.items():
        community_id = str(uuid.uuid4())

        # Update entities with community_id
        for eid in member_ids:
            try:
                entity = cosmos_graph_entities_container.read_item(
                    item=eid, partition_key=workspace_id
                )
                entity["community_id"] = community_id
                cosmos_graph_entities_container.upsert_item(entity)
            except Exception as e:
                logger.warning(f"Failed to assign community {community_id} to entity {eid}: {e}")

        # Get entity names for the community
        member_entities = [e for e in entities if e["id"] in member_ids]
        entity_names = [e.get("entity_name", "") for e in member_entities]

        community_doc = {
            "id": community_id,
            "type": "graph_community",
            "title": f"Cluster: {', '.join(entity_names[:3])}{'...' if len(entity_names) > 3 else ''}",
            "summary": "",  # Will be filled by generate_community_summary
            "entity_ids": member_ids,
            "workspace_id": workspace_id,
            "created_at": now,
        }

        try:
            cosmos_graph_communities_container.create_item(body=community_doc)
            communities.append(community_doc)
        except Exception as e:
            logger.error(f"Failed to create community: {e}")

    _log_event(
        "community_detection_complete",
        level=logging.INFO,
        extra={
            "workspace_id": workspace_id,
            "entities": len(entities),
            "relationships": len(relationships),
            "communities": len(communities),
        },
    )

    return communities


def generate_community_summary(community_id: str, workspace_id: str,
                                settings: dict) -> dict:
    """Generate a thematic summary for a community of entities using GPT."""
    try:
        community = cosmos_graph_communities_container.read_item(
            item=community_id, partition_key=workspace_id
        )
    except Exception as e:
        logger.warning(f"Failed to read community {community_id} for summary generation: {e}")
        return None

    entity_ids = community.get("entity_ids", [])
    entities = []
    for eid in entity_ids[:20]:
        try:
            entity = cosmos_graph_entities_container.read_item(
                item=eid, partition_key=workspace_id
            )
            entities.append(entity)
        except Exception as e:
            logger.warning(f"Failed to read entity {eid} for community summary: {e}")

    if not entities:
        return community

    entity_descriptions = "\n".join([
        f"- {e.get('entity_name', '?')} ({e.get('entity_type', '?')}): {e.get('description', 'No description')}"
        for e in entities
    ])

    prompt = (
        "Summarize the main theme of this group of related entities in 2-3 sentences. "
        "What connects them? What topic or domain do they represent?\n\n"
        f"Entities:\n{entity_descriptions}"
    )

    try:
        from config import gpt_client, gpt_model
        model = settings.get("graph_rag_extraction_model", "gpt-4o-mini")
        response = gpt_client.chat.completions.create(
            model=model or gpt_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0,
        )
        summary = response.choices[0].message.content.strip()

        community["summary"] = summary
        community["title"] = summary[:80] if len(summary) > 80 else summary
        cosmos_graph_communities_container.upsert_item(community)

        return community

    except Exception as e:
        logger.error(f"Failed to generate community summary: {e}")
        return community
