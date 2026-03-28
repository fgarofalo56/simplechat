# functions_graph_entities.py

import json
import logging
import re
import uuid
from datetime import datetime, timezone

from config import (
    cosmos_graph_entities_container,
    cosmos_graph_relationships_container,
    CLIENTS,
)

logger = logging.getLogger(__name__)


def _log_event(message, level=logging.INFO, extra=None):
    """Lazy wrapper for log_event."""
    try:
        from functions_appinsights import log_event
        log_event(message, level=level, extra=extra)
    except ImportError:
        logger.log(level, message, extra=extra)


# ---------------------------------------------------------------------------
# Entity extraction prompt
# ---------------------------------------------------------------------------

ENTITY_EXTRACTION_PROMPT = """You are an expert at extracting structured knowledge from text.
Given a text passage, extract all entities and relationships.

For each ENTITY provide: entity_name, entity_type (one of: {entity_types}), description (1-2 sentences)
For each RELATIONSHIP provide: source (entity name), target (entity name), relationship_type (e.g., WORKS_AT, MENTIONS, USES, DEPENDS_ON, LOCATED_IN, REPORTS_TO, PART_OF, RELATED_TO), description (1 sentence)

Return valid JSON with exactly this structure:
{{"entities": [{{"entity_name": "...", "entity_type": "...", "description": "..."}}], "relationships": [{{"source": "...", "target": "...", "relationship_type": "...", "description": "..."}}]}}

If no entities or relationships are found, return: {{"entities": [], "relationships": []}}"""


def extract_entities_from_chunk(chunk_text: str, settings: dict) -> dict:
    """Extract entities and relationships from a single chunk using GPT.

    Args:
        chunk_text: The text content to extract from.
        settings: App settings dict with GPT configuration.

    Returns:
        Dict with 'entities' and 'relationships' lists.
    """
    if not chunk_text or len(chunk_text.strip()) < 50:
        return {"entities": [], "relationships": []}

    model = settings.get("graph_rag_extraction_model", "gpt-4o-mini")
    entity_types = settings.get("graph_rag_entity_types",
        ["person", "organization", "location", "concept", "technology", "document"])

    try:
        from config import gpt_client, gpt_model
        client = gpt_client
        deployment = model if model else gpt_model

        system_prompt = ENTITY_EXTRACTION_PROMPT.format(
            entity_types=", ".join(entity_types)
        )

        response = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text:\n{chunk_text[:3000]}"},
            ],
            max_tokens=2000,
            temperature=0,
        )

        result = json.loads(response.choices[0].message.content)
        return {
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
        }

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return {"entities": [], "relationships": []}


# ---------------------------------------------------------------------------
# Entity resolution and deduplication
# ---------------------------------------------------------------------------

def normalize_entity_name(name: str) -> str:
    """Normalize entity name for dedup matching."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def resolve_entity(entity: dict, workspace_id: str, settings: dict) -> str:
    """Resolve entity against existing graph. Returns entity_id (existing or new).

    Two-stage dedup:
    1. Exact match on normalized name + type
    2. Semantic match using embedding similarity > 0.85
    """
    normalized_name = normalize_entity_name(entity.get("entity_name", ""))
    entity_type = entity.get("entity_type", "concept")

    # Stage 1: Exact match
    query = (
        "SELECT * FROM c WHERE c.entity_name_normalized = @name "
        "AND c.entity_type = @type AND c.workspace_id = @ws"
    )
    params = [
        {"name": "@name", "value": normalized_name},
        {"name": "@type", "value": entity_type},
        {"name": "@ws", "value": workspace_id},
    ]

    existing = list(cosmos_graph_entities_container.query_items(
        query=query, parameters=params, partition_key=workspace_id
    ))

    if existing:
        # Merge source references
        _merge_entity_sources(existing[0], entity)
        return existing[0]["id"]

    # Stage 2: Create new entity (skip semantic match for performance in MVP)
    entity_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Generate embedding for the entity
    embedding = []
    try:
        from functions_documents import generate_embedding
        result = generate_embedding(entity.get("entity_name", "") + " " + entity.get("description", ""))
        if isinstance(result, tuple):
            embedding = result[0]
        elif result:
            embedding = result
    except Exception as e:
        logger.warning(f"Failed to generate embedding for entity '{entity.get('entity_name', 'unknown')}': {e}")

    entity_doc = {
        "id": entity_id,
        "type": "graph_entity",
        "entity_type": entity_type,
        "entity_name": entity.get("entity_name", ""),
        "entity_name_normalized": normalized_name,
        "description": entity.get("description", ""),
        "source_document_ids": entity.get("source_document_ids", []),
        "source_chunk_ids": entity.get("source_chunk_ids", []),
        "workspace_id": workspace_id,
        "embedding": embedding if embedding else [],
        "community_id": None,
        "properties": entity.get("properties", {}),
        "created_at": now,
    }

    try:
        cosmos_graph_entities_container.create_item(body=entity_doc)
    except Exception as e:
        logger.error(f"Failed to create entity: {e}")

    return entity_id


def _merge_entity_sources(existing: dict, new_entity: dict):
    """Merge source document/chunk references into existing entity."""
    doc_ids = set(existing.get("source_document_ids", []))
    chunk_ids = set(existing.get("source_chunk_ids", []))

    for did in new_entity.get("source_document_ids", []):
        doc_ids.add(did)
    for cid in new_entity.get("source_chunk_ids", []):
        chunk_ids.add(cid)

    existing["source_document_ids"] = list(doc_ids)
    existing["source_chunk_ids"] = list(chunk_ids)

    try:
        cosmos_graph_entities_container.upsert_item(existing)
    except Exception as e:
        logger.error(f"Failed to merge entity sources: {e}")


def save_relationship(source_entity_id: str, target_entity_id: str,
                      rel_type: str, description: str,
                      workspace_id: str, source_document_ids: list = None):
    """Save a relationship between two entities."""
    rel_id = str(uuid.uuid4())
    rel_doc = {
        "id": rel_id,
        "type": "graph_relationship",
        "relationship_type": rel_type,
        "source_entity_id": source_entity_id,
        "target_entity_id": target_entity_id,
        "description": description,
        "weight": 1.0,
        "source_document_ids": source_document_ids or [],
        "workspace_id": workspace_id,
    }

    try:
        cosmos_graph_relationships_container.create_item(body=rel_doc)
    except Exception as e:
        logger.error(f"Failed to save relationship: {e}")

    return rel_id


# ---------------------------------------------------------------------------
# Batch extraction pipeline
# ---------------------------------------------------------------------------

def extract_and_store_entities(document_id: str, user_id: str,
                                group_id: str = None,
                                public_workspace_id: str = None,
                                settings: dict = None):
    """Extract entities from all chunks of a document and store in graph.

    This is called as a background task after document processing.
    """
    if settings is None:
        from functions_settings import get_settings
        settings = get_settings()

    workspace_id = public_workspace_id or group_id or user_id

    try:
        from functions_documents import get_all_chunks
        chunks = get_all_chunks(document_id, user_id,
                                group_id=group_id,
                                public_workspace_id=public_workspace_id)

        total_entities = 0
        total_relationships = 0

        for chunk in chunks:
            chunk_text = chunk.get("chunk_text", "")
            chunk_id = chunk.get("id", "")

            result = extract_entities_from_chunk(chunk_text, settings)

            # Resolve and store entities
            entity_name_to_id = {}
            for entity in result.get("entities", []):
                entity["source_document_ids"] = [document_id]
                entity["source_chunk_ids"] = [chunk_id]
                entity_id = resolve_entity(entity, workspace_id, settings)
                entity_name_to_id[entity["entity_name"]] = entity_id
                total_entities += 1

            # Store relationships
            for rel in result.get("relationships", []):
                source_id = entity_name_to_id.get(rel.get("source"))
                target_id = entity_name_to_id.get(rel.get("target"))
                if source_id and target_id:
                    save_relationship(
                        source_id, target_id,
                        rel.get("relationship_type", "RELATED_TO"),
                        rel.get("description", ""),
                        workspace_id,
                        [document_id],
                    )
                    total_relationships += 1

        _log_event(
            "graph_extraction_complete",
            level=logging.INFO,
            extra={
                "document_id": document_id,
                "entities": total_entities,
                "relationships": total_relationships,
                "workspace_id": workspace_id,
            },
        )

    except Exception as e:
        logger.error(f"Graph extraction failed for document {document_id}: {e}")
        _log_event(
            "graph_extraction_failed",
            level=logging.ERROR,
            extra={"document_id": document_id, "error": str(e)},
        )
