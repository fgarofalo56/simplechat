#!/usr/bin/env python3
"""
Functional test for Phase 5: Context Optimization & Advanced Search.
Version: 0.239.002
Implemented in: 0.239.003

Tests token budgeting, conversation summarization, map-reduce,
multi-query, HyDE, MMR, contextual compression, and admin settings.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


def test_token_budget_allocation():
    """Test token budget allocation across search, history, summary."""
    print("Testing Task 5.2: Token budget allocation...")
    try:
        from functions_context_optimization import build_optimized_context

        context = build_optimized_context(
            system_prompt="You are a helpful assistant.",
            conversation_history=[
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you!"},
                {"role": "user", "content": "Tell me about Python."},
            ],
            search_results=[
                {"chunk_text": "Python is a programming language." * 10},
                {"chunk_text": "Flask is a web framework." * 10},
            ],
            user_message="What is Python?",
            max_context_tokens=12000,
            model="gpt-4o",
        )

        assert "token_breakdown" in context, "Missing token_breakdown"
        assert "recent_messages" in context, "Missing recent_messages"
        assert "search_context" in context, "Missing search_context"

        tb = context["token_breakdown"]
        assert tb["available"] > 0, f"Available tokens should be > 0, got {tb['available']}"
        assert tb["search_budget"] > 0, "Search budget should be > 0"
        assert tb["recent_budget"] > 0, "Recent budget should be > 0"

        print(f"  PASS: Budget allocated (available={tb['available']}, search={tb['search_budget']}, recent={tb['recent_budget']})")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sliding_window():
    """Test sliding window selects most recent messages within budget."""
    print("Testing Task 5.2: Sliding window...")
    try:
        from functions_context_optimization import _sliding_window

        messages = [
            {"role": "user", "content": "Message " + str(i) * 100}
            for i in range(10)
        ]

        # Small budget should select only most recent messages
        result = _sliding_window(messages, budget=200, model="gpt-4o")
        assert len(result) < len(messages), "Should select fewer messages than total"
        assert result[-1] == messages[-1], "Last message should be the most recent"

        # Empty messages
        assert _sliding_window([], 1000, "gpt-4o") == []

        print(f"  PASS: Sliding window selected {len(result)}/{len(messages)} messages")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fit_within_budget():
    """Test fitting search results within token budget."""
    print("Testing Task 5.2: Fit within budget...")
    try:
        from functions_context_optimization import _fit_within_budget

        results = [
            {"chunk_text": "Short text."},
            {"chunk_text": "A bit longer text with more tokens in it."},
            {"chunk_text": "Very long text. " * 500},  # This should exceed budget
        ]

        # Small budget should only fit first 1-2 results
        fitted = _fit_within_budget(results, budget=50, model="gpt-4o")
        assert len(fitted) < len(results), "Should fit fewer results than total"
        assert len(fitted) >= 1, "Should fit at least one result"

        # Large budget should fit all
        fitted_all = _fit_within_budget(results, budget=100000, model="gpt-4o")
        assert len(fitted_all) == len(results), "Large budget should fit all"

        print(f"  PASS: Budget fitting works ({len(fitted)} of {len(results)} at 50 tokens)")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_expansion_module():
    """Test query expansion module exists with required functions."""
    print("Testing Tasks 5.4/5.5/5.7: Query expansion module...")
    try:
        src_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_query_expansion.py'
        )
        with open(src_path, 'r', encoding='utf-8') as f:
            source = f.read()

        assert 'def generate_query_variations' in source, "Missing multi-query function"
        assert 'def hyde_generate' in source, "Missing HyDE function"
        assert 'def compress_chunk' in source, "Missing contextual compression"

        print("  PASS: Query expansion module has all required functions")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mmr_filter():
    """Test MMR diversity filtering."""
    print("Testing Task 5.6: MMR diversity filtering...")
    try:
        from functions_reranking import mmr_filter
        import numpy as np

        # Create test documents with embeddings
        np.random.seed(42)
        query_emb = np.random.randn(10).tolist()

        docs = []
        for i in range(5):
            emb = np.random.randn(10).tolist()
            docs.append({"id": i, "chunk_text": f"doc {i}", "embedding": emb})

        # Add a duplicate-ish document (same embedding as doc 0)
        docs.append({"id": 5, "chunk_text": "dup of 0", "embedding": docs[0]["embedding"]})

        result = mmr_filter(query_emb, docs, lambda_param=0.7, k=3)
        assert len(result) == 3, f"Should return 3 docs, got {len(result)}"

        # The duplicate should be penalized by diversity
        result_ids = [d["id"] for d in result]
        assert not (0 in result_ids and 5 in result_ids), \
            "MMR should not select both original and duplicate"

        # Empty input
        assert mmr_filter(query_emb, [], k=3) == []
        assert mmr_filter([], docs, k=3) == docs[:3]

        print(f"  PASS: MMR selected {len(result)} diverse documents")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_optimization_settings():
    """Test context optimization settings defaults."""
    print("Testing Task 5.8: Context optimization settings...")
    try:
        settings_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'functions_settings.py'
        )
        with open(settings_path, 'r') as f:
            source = f.read()

        required = [
            "'enable_context_optimization': False",
            "'context_token_budget': 12000",
            "'search_token_budget_pct': 0.50",
            "'enable_conversation_summarization': False",
            "'enable_multi_query': False",
            "'enable_hyde': False",
            "'enable_mmr': False",
            "'mmr_lambda': 0.7",
            "'enable_contextual_compression': False",
        ]

        for setting in required:
            assert setting in source, f"Missing: {setting}"

        print("  PASS: All context optimization settings present")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_admin_route_phase5_settings():
    """Test admin route processes Phase 5 settings."""
    print("Testing Task 5.8: Admin route Phase 5 settings...")
    try:
        route_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'application', 'single_app', 'route_frontend_admin_settings.py'
        )
        with open(route_path, 'r', encoding='utf-8') as f:
            source = f.read()

        entries = [
            "'enable_context_optimization':",
            "'context_token_budget':",
            "'enable_conversation_summarization':",
            "'enable_multi_query':",
            "'enable_hyde':",
            "'enable_mmr':",
            "'mmr_lambda':",
            "'enable_contextual_compression':",
        ]

        for entry in entries:
            assert entry in source, f"Missing in admin route: {entry}"

        print("  PASS: Admin route processes all Phase 5 settings")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []
    results.append(test_token_budget_allocation())
    results.append(test_sliding_window())
    results.append(test_fit_within_budget())
    results.append(test_query_expansion_module())
    results.append(test_mmr_filter())
    results.append(test_context_optimization_settings())
    results.append(test_admin_route_phase5_settings())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All Phase 5 tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
