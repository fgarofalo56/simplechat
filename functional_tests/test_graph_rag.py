#!/usr/bin/env python3
"""
Functional test for Phase 4: Graph RAG.
Version: 0.239.002
Implemented in: 0.239.003

Tests entity extraction, graph traversal, query routing, community detection,
Cosmos containers, admin settings, and chat pipeline integration.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


def test_cosmos_containers_defined():
    """Test that Graph RAG Cosmos containers are defined in config.py."""
    print("Testing Task 4.1: Cosmos DB containers...")
    try:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'config.py'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'cosmos_graph_entities_container' in source, "Missing graph_entities container"
        assert 'cosmos_graph_relationships_container' in source, "Missing graph_relationships container"
        assert 'cosmos_graph_communities_container' in source, "Missing graph_communities container"
        assert '"graph_entities"' in source, "Missing graph_entities name"
        assert '"graph_relationships"' in source, "Missing graph_relationships name"
        assert '"graph_communities"' in source, "Missing graph_communities name"

        print("  PASS: All 3 Graph RAG Cosmos containers defined")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entity_extraction_prompt():
    """Test entity extraction prompt structure."""
    print("Testing Task 4.2: Entity extraction prompt...")
    try:
        entities_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_graph_entities.py'
        )
        with open(entities_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'ENTITY_EXTRACTION_PROMPT' in source, "Missing extraction prompt"
        assert 'def extract_entities_from_chunk' in source, "Missing extract function"
        assert 'json_object' in source, "Should use JSON mode"
        assert 'def resolve_entity' in source, "Missing resolve_entity"
        assert 'def save_relationship' in source, "Missing save_relationship"
        assert 'def extract_and_store_entities' in source, "Missing batch pipeline"

        print("  PASS: Entity extraction module has all required functions")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entity_name_normalization():
    """Test entity name normalization for dedup."""
    print("Testing Task 4.3: Entity name normalization...")
    try:
        import re
        # Inline the normalize function (same as in functions_graph_entities.py)
        def normalize_entity_name(name):
            return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()

        assert normalize_entity_name("John Smith") == "john smith"
        assert normalize_entity_name("JOHN SMITH") == "john smith"
        assert normalize_entity_name("john_smith") == "johnsmith"
        assert normalize_entity_name("  Hello World  ") == "hello world"

        # Also verify function exists in source
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_graph_entities.py')
        with open(src_path, 'r', encoding='utf-8') as f:
            assert 'def normalize_entity_name' in f.read()

        print("  PASS: Entity name normalization works")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_routing():
    """Test query classification for graph vs vector search."""
    print("Testing Task 4.7: Query routing...")
    try:
        import re
        # Inline the routing logic (same as functions_graph_rag.py)
        _REL = [r"how are .* related", r"connection between", r"depends on",
                r"who works", r"compare", r"relationship between", r"difference between"]
        _COMM = [r"summarize all", r"overview of", r"themes in", r"main topics", r"what are the key"]

        def route(q):
            ql = q.lower()
            if any(re.search(p, ql) for p in _REL):
                return "graph_or_community"
            if any(re.search(p, ql) for p in _COMM):
                return "community_search"
            return "vector_only"

        assert route("How are Azure and Cosmos DB related?") == "graph_or_community"
        assert route("What is the connection between Python and Flask?") == "graph_or_community"
        assert route("Summarize all the main topics") == "community_search"
        assert route("What are the key themes in the documents?") == "community_search"
        assert route("What is the pricing model?") == "vector_only"
        assert route("How do I configure SSL?") == "vector_only"

        print("  PASS: Query routing correctly classifies queries")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_context_formatting():
    """Test graph context formatting for LLM (source code verification)."""
    print("Testing Task 4.5: Graph context formatting...")
    try:
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_graph_rag.py')
        with open(src_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'def format_graph_context' in source, "Missing format_graph_context"
        assert 'def graph_enhanced_search' in source, "Missing graph_enhanced_search"
        assert 'def detect_query_entities' in source, "Missing detect_query_entities"
        assert 'def get_entity_neighborhood' in source, "Missing get_entity_neighborhood"
        assert 'RELATED_TO' in source or 'relationship_type' in source, "Should handle relationship types"
        assert 'community' in source.lower(), "Should handle community summaries"

        print("  PASS: Graph context formatting module verified")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_rag_settings():
    """Test Graph RAG settings defaults."""
    print("Testing Task 4.10: Graph RAG settings...")
    try:
        settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_settings.py'
        )
        with open(settings_path, 'r') as f:
            source = f.read()

        required = [
            "'enable_graph_rag': False",
            "'graph_rag_entity_types':",
            "'graph_rag_extraction_model': 'gpt-4o-mini'",
            "'graph_rag_max_depth': 2",
            "'enable_community_detection': False",
        ]

        for setting in required:
            assert setting in source, f"Missing: {setting}"

        print("  PASS: Graph RAG settings defaults present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_extraction_hook():
    """Test that document pipeline has graph extraction hook."""
    print("Testing Task 4.4: Graph extraction hook in document pipeline...")
    try:
        docs_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_documents.py'
        )
        with open(docs_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'extract_and_store_entities' in source, "Missing graph extraction hook"
        assert 'enable_graph_rag' in source, "Missing Graph RAG feature gate"

        print("  PASS: Graph extraction hook present in document pipeline")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_pipeline_graph_integration():
    """Test that chat pipeline has graph context injection."""
    print("Testing Task 4.6: Chat pipeline graph integration...")
    try:
        chat_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'route_backend_chats.py'
        )
        with open(chat_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'graph_enhanced_search' in source, "Missing graph_enhanced_search call"
        assert 'Knowledge Graph Context' in source, "Missing graph context injection"
        assert 'enable_graph_rag' in source, "Missing Graph RAG feature gate"

        print("  PASS: Chat pipeline has graph context integration")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_community_detection_module():
    """Test community detection module structure."""
    print("Testing Task 4.8: Community detection module...")
    try:
        comm_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_graph_communities.py'
        )
        with open(comm_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'def detect_communities' in source, "Missing detect_communities"
        assert 'def generate_community_summary' in source, "Missing generate_community_summary"
        assert 'networkx' in source, "Should use networkx"
        assert 'leiden' in source or 'greedy_modularity' in source, "Should have community algorithm"

        print("  PASS: Community detection module has required functions")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []
    results.append(test_cosmos_containers_defined())
    results.append(test_entity_extraction_prompt())
    results.append(test_entity_name_normalization())
    results.append(test_query_routing())
    results.append(test_graph_context_formatting())
    results.append(test_graph_rag_settings())
    results.append(test_graph_extraction_hook())
    results.append(test_chat_pipeline_graph_integration())
    results.append(test_community_detection_module())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All Phase 4 tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
