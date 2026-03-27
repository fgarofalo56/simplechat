#!/usr/bin/env python3
"""
Functional test for Phase 1 Tasks 1.1-1.3: Search Quality Foundation.
Version: 0.239.002
Implemented in: 0.239.003

This test ensures that:
- extract_search_results captures reranker_score and captions fields
- tiktoken token counting returns accurate results
- Lost-in-the-middle reordering places highest-relevance docs at start and end
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


def test_extract_search_results_reranker_fields():
    """Test that extract_search_results captures reranker_score and captions.

    Validates the source code directly since importing functions_search.py
    requires the full application dependency chain.
    """
    print("Testing Task 1.1: Reranker score and caption capture...")
    try:
        # Verify the source code contains the reranker fields
        search_module_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_search.py'
        )
        with open(search_module_path, 'r') as f:
            source = f.read()

        # Check that extract_search_results captures the new fields
        assert '"reranker_score": r.get("@search.rerankerScore")' in source, \
            "Missing reranker_score capture in extract_search_results"
        assert '"captions": r.get("@search.captions")' in source, \
            "Missing captions capture in extract_search_results"

        # Verify the fields use .get() for safe access (returns None when absent)
        assert 'r.get("@search.rerankerScore")' in source, \
            "rerankerScore should use .get() for safe access"
        assert 'r.get("@search.captions")' in source, \
            "captions should use .get() for safe access"

        # Verify existing fields are still present
        assert '"score": r["@search.score"]' in source, \
            "Existing score field should still be present"
        assert '"chunk_text": r["chunk_text"]' in source, \
            "Existing chunk_text field should still be present"

        print("  PASS: extract_search_results correctly captures reranker_score and captions")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tiktoken_counting():
    """Test that token counting utility works correctly."""
    print("Testing Task 1.2: tiktoken token counting...")
    try:
        from functions_context_optimization import count_tokens, count_messages_tokens

        # Basic token counting
        tokens = count_tokens("hello world", "gpt-4o")
        assert tokens == 2, f"Expected 2 tokens for 'hello world', got {tokens}"

        # Empty string
        assert count_tokens("", "gpt-4o") == 0, "Empty string should return 0 tokens"

        # Unknown model falls back gracefully
        tokens_unknown = count_tokens("hello world", "nonexistent-model-xyz")
        assert tokens_unknown > 0, "Unknown model should fall back and still count tokens"

        # Message counting
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        msg_tokens = count_messages_tokens(messages, "gpt-4o")
        assert msg_tokens > 0, f"Message tokens should be > 0, got {msg_tokens}"

        # Empty messages
        assert count_messages_tokens([], "gpt-4o") == 0, "Empty messages should return 0"

        print(f"  PASS: Token counting works (sample: 'hello world' = {tokens} tokens)")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_attention_reordering():
    """Test lost-in-the-middle reordering."""
    print("Testing Task 1.3: Attention reordering...")
    try:
        from functions_reranking import reorder_for_attention

        # Test with ranked documents (descending relevance)
        docs = [{"id": i, "score": 10 - i} for i in range(6)]
        # Input order: [0(10), 1(9), 2(8), 3(7), 4(6), 5(5)]

        reordered = reorder_for_attention(docs)

        # Top half (even indices): 0, 2, 4 -> scores 10, 8, 6
        # Bottom half (odd indices reversed): 5, 3, 1 -> scores 5, 7, 9
        assert reordered[0]["id"] == 0, f"First should be highest relevance, got id={reordered[0]['id']}"
        assert reordered[-1]["id"] == 1, f"Last should be 2nd highest relevance, got id={reordered[-1]['id']}"

        # Middle should have lower relevance items
        middle_ids = [d["id"] for d in reordered[2:4]]
        assert 4 in middle_ids or 5 in middle_ids, "Middle should contain lower-relevance items"

        # Edge cases
        assert reorder_for_attention([]) == [], "Empty list should return empty"
        assert reorder_for_attention([{"id": 1}]) == [{"id": 1}], "Single item should return as-is"
        assert reorder_for_attention([{"id": 1}, {"id": 2}]) == [{"id": 1}, {"id": 2}], "Two items should return as-is"

        print(f"  PASS: Attention reordering works (6 docs -> first={reordered[0]['id']}, last={reordered[-1]['id']})")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cohere_rerank_live():
    """Test Cohere Rerank v4 live endpoint on Azure AI Services."""
    print("Testing Task 1.4/1.5: Cohere Rerank v4 live call...")
    try:
        import subprocess
        result = subprocess.run(
            ['az', 'cognitiveservices', 'account', 'keys', 'list',
             '--name', 'fgaro-mdg63bud-eastus2',
             '--resource-group', 'rg-dlz-aiml-stack-dev',
             '--query', 'key1', '-o', 'tsv'],
            capture_output=True, text=True, timeout=30
        )
        api_key = result.stdout.strip()
        if not api_key:
            print("  SKIP: Could not retrieve Azure API key (az CLI not available)")
            return True  # Don't fail in CI

        import requests
        url = 'https://fgaro-mdg63bud-eastus2.cognitiveservices.azure.com/providers/cohere/v2/rerank'
        headers = {'Content-Type': 'application/json', 'api-key': api_key}
        payload = {
            'query': 'What is Python programming?',
            'documents': [
                'Python is a high-level programming language.',
                'The python is a large non-venomous snake.',
                'Python was created by Guido van Rossum.'
            ],
            'top_n': 2,
            'model': 'cohere-rerank-v4-fast'
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200]}"

        data = resp.json()
        results = data.get('results', [])
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert results[0]['index'] == 0, f"Top result should be index 0 (Python language), got {results[0]['index']}"
        assert 'relevance_score' in results[0], "Missing relevance_score"

        print(f"  PASS: Cohere Rerank returned {len(results)} results, top score={results[0]['relevance_score']:.4f}")
        return True
    except FileNotFoundError:
        print("  SKIP: az CLI not available")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rerank_with_cohere_function():
    """Test the rerank_with_cohere function handles errors gracefully."""
    print("Testing Task 1.5: rerank_with_cohere error handling...")
    try:
        from functions_reranking import rerank_with_cohere

        docs = [{"chunk_text": "test doc", "score": 0.5}]

        # Test with missing settings — should return original docs
        result = rerank_with_cohere("test query", docs, {})
        assert result == docs, "Missing settings should return original documents"

        # Test with empty documents
        result = rerank_with_cohere("test query", [], {"cohere_rerank_endpoint": "http://fake", "cohere_rerank_api_key": "fake"})
        assert result == [], "Empty documents should return empty list"

        print("  PASS: rerank_with_cohere handles errors gracefully")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_quality_metrics():
    """Test log_search_quality_metrics function."""
    print("Testing Task 1.6: Search quality metrics logging...")
    try:
        from functions_reranking import log_search_quality_metrics

        # Test with results
        docs = [
            {"score": 0.9, "reranker_score": 3.5, "file_name": "a.pdf", "original_rank": 0},
            {"score": 0.7, "reranker_score": 2.1, "file_name": "b.pdf", "original_rank": 2},
            {"score": 0.5, "file_name": "a.pdf"},  # same file, no reranker score
        ]
        log_search_quality_metrics("test query", docs, was_reranked=True, was_reordered=True)

        # Test with empty results
        log_search_quality_metrics("empty query", [], was_reranked=False, was_reordered=False)

        print("  PASS: Search quality metrics logged without errors")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_admin_settings_defaults():
    """Test that search quality settings exist in default_settings."""
    print("Testing Task 1.7: Admin settings defaults...")
    try:
        settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_settings.py'
        )
        with open(settings_path, 'r') as f:
            source = f.read()

        required_settings = [
            "'enable_cohere_rerank': False",
            "'cohere_rerank_endpoint': ''",
            "'cohere_rerank_api_key': ''",
            "'cohere_rerank_top_n': 10",
            "'enable_attention_reorder': True",
        ]

        for setting in required_settings:
            assert setting in source, f"Missing default setting: {setting}"

        print("  PASS: All search quality defaults present in functions_settings.py")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_admin_settings_ui_exists():
    """Test that the Search Quality tab exists in admin_settings.html."""
    print("Testing Task 1.7: Admin settings UI...")
    try:
        template_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'templates', 'admin_settings.html'
        )
        with open(template_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Tab button exists
        assert 'id="search-quality-tab"' in source, "Missing Search Quality tab button"
        assert 'id="search-quality"' in source, "Missing Search Quality tab pane"

        # Settings fields exist
        assert 'name="enable_cohere_rerank"' in source, "Missing enable_cohere_rerank toggle"
        assert 'name="cohere_rerank_endpoint"' in source, "Missing cohere_rerank_endpoint input"
        assert 'name="cohere_rerank_api_key"' in source, "Missing cohere_rerank_api_key input"
        assert 'name="cohere_rerank_top_n"' in source, "Missing cohere_rerank_top_n input"
        assert 'name="enable_attention_reorder"' in source, "Missing enable_attention_reorder toggle"

        print("  PASS: Search Quality tab and all fields present in admin template")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_admin_route_processes_settings():
    """Test that the admin POST route processes search quality settings."""
    print("Testing Task 1.7: Admin route processes settings...")
    try:
        route_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'route_frontend_admin_settings.py'
        )
        with open(route_path, 'r') as f:
            source = f.read()

        required_entries = [
            "'enable_cohere_rerank':",
            "'cohere_rerank_endpoint':",
            "'cohere_rerank_api_key':",
            "'cohere_rerank_top_n':",
            "'enable_attention_reorder':",
        ]

        for entry in required_entries:
            assert entry in source, f"Missing in admin route: {entry}"

        print("  PASS: Admin route processes all search quality settings")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []
    results.append(test_extract_search_results_reranker_fields())
    results.append(test_tiktoken_counting())
    results.append(test_attention_reordering())
    results.append(test_cohere_rerank_live())
    results.append(test_rerank_with_cohere_function())
    results.append(test_search_quality_metrics())
    results.append(test_admin_settings_defaults())
    results.append(test_admin_settings_ui_exists())
    results.append(test_admin_route_processes_settings())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All Phase 1 foundation tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
