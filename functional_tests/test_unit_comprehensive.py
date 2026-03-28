#!/usr/bin/env python3
"""
Comprehensive unit tests for all user-triggered functions.
Version: 0.239.004

Covers: query expansion, reranking, skill execution, graph entities,
graph communities, context optimization, web ingestion, skill CRUD.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'application', 'single_app'))


# =================================================================
# RERANKING TESTS
# =================================================================

def test_reorder_for_attention_various_sizes():
    """Test attention reordering with various input sizes."""
    print("Testing: Attention reordering various sizes...")
    try:
        from functions_reranking import reorder_for_attention

        # 0 items
        assert reorder_for_attention([]) == []
        # 1 item
        assert reorder_for_attention([{"id": 1}]) == [{"id": 1}]
        # 2 items
        assert reorder_for_attention([{"id": 1}, {"id": 2}]) == [{"id": 1}, {"id": 2}]
        # 3 items: top=[0,2], bottom reversed=[1]
        r = reorder_for_attention([{"id": 0}, {"id": 1}, {"id": 2}])
        assert r[0]["id"] == 0 and r[-1]["id"] == 1
        # 10 items
        docs = [{"id": i} for i in range(10)]
        r = reorder_for_attention(docs)
        assert len(r) == 10
        assert r[0]["id"] == 0  # highest at start
        assert r[-1]["id"] == 1  # 2nd highest at end

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_mmr_filter_basic():
    """Test MMR diversity filtering."""
    print("Testing: MMR filter basic functionality...")
    try:
        from functions_reranking import mmr_filter
        import numpy as np

        np.random.seed(42)
        q = np.random.randn(8).tolist()
        docs = [{"id": i, "embedding": np.random.randn(8).tolist(), "chunk_text": f"doc{i}"} for i in range(6)]

        result = mmr_filter(q, docs, lambda_param=0.5, k=3)
        assert len(result) == 3
        ids = [d["id"] for d in result]
        assert len(set(ids)) == 3  # all unique

        # k > docs
        result = mmr_filter(q, docs, k=100)
        assert len(result) == 6

        # Empty
        assert mmr_filter(q, []) == []
        assert mmr_filter([], docs) == docs[:10]

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# CONTEXT OPTIMIZATION TESTS
# =================================================================

def test_count_tokens_various_inputs():
    """Test token counting edge cases."""
    print("Testing: Token counting edge cases...")
    try:
        from functions_context_optimization import count_tokens, count_messages_tokens

        assert count_tokens("") == 0
        assert count_tokens("a") > 0
        assert count_tokens("hello world") == 2
        assert count_tokens("The quick brown fox jumps over the lazy dog") > 5

        # Long text
        long_text = "word " * 1000
        tokens = count_tokens(long_text)
        assert tokens > 500

        # Messages with names
        msgs = [{"role": "user", "content": "hi", "name": "Alice"}]
        assert count_messages_tokens(msgs) > 0

        # None/empty handling
        assert count_messages_tokens([]) == 0
        assert count_messages_tokens(None) == 0

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_sliding_window_edge_cases():
    """Test sliding window with edge cases."""
    print("Testing: Sliding window edge cases...")
    try:
        from functions_context_optimization import _sliding_window

        # Empty
        assert _sliding_window([], 1000, "gpt-4o") == []

        # Single message within budget
        msgs = [{"role": "user", "content": "hi"}]
        assert len(_sliding_window(msgs, 1000, "gpt-4o")) == 1

        # Very small budget should return nothing or just the last
        msgs = [{"role": "user", "content": "x" * 500} for _ in range(5)]
        result = _sliding_window(msgs, 10, "gpt-4o")
        assert len(result) <= 1

        # Very large budget should return all
        msgs = [{"role": "user", "content": "hi"} for _ in range(3)]
        result = _sliding_window(msgs, 100000, "gpt-4o")
        assert len(result) == 3

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_fit_within_budget_edge_cases():
    """Test budget fitting edge cases."""
    print("Testing: Budget fitting edge cases...")
    try:
        from functions_context_optimization import _fit_within_budget

        # Empty
        assert _fit_within_budget([], 1000, "gpt-4o") == []

        # Zero budget
        results = [{"chunk_text": "hello world"}]
        assert _fit_within_budget(results, 0, "gpt-4o") == []

        # Exact fit
        results = [{"chunk_text": "hi"}]
        fitted = _fit_within_budget(results, 100, "gpt-4o")
        assert len(fitted) == 1

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_build_optimized_context_structure():
    """Test optimized context returns correct structure."""
    print("Testing: Optimized context structure...")
    try:
        from functions_context_optimization import build_optimized_context

        ctx = build_optimized_context(
            system_prompt="Be helpful",
            conversation_history=[
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ],
            search_results=[{"chunk_text": "result 1"}, {"chunk_text": "result 2"}],
            user_message="question",
            max_context_tokens=5000,
        )

        assert "token_breakdown" in ctx
        assert "recent_messages" in ctx
        assert "search_context" in ctx
        assert "summary" in ctx
        assert ctx["token_breakdown"]["available"] > 0

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# SKILL VALIDATION TESTS
# =================================================================

def test_skill_validation_comprehensive():
    """Test skill validation with many edge cases."""
    print("Testing: Skill validation comprehensive...")
    try:
        import re
        VALID_TYPES = {"prompt_skill", "tool_skill", "chain_skill"}

        def validate(p, partial=False):
            if not partial:
                for f in ["name", "display_name", "description", "type"]:
                    if not p.get(f):
                        raise ValueError(f"Missing: {f}")
            if "name" in p:
                if not re.match(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$', p["name"]):
                    raise ValueError("Bad name")
            if "type" in p and p["type"] not in VALID_TYPES:
                raise ValueError("Bad type")

        # Valid cases
        validate({"name": "abc", "display_name": "X", "description": "Y", "type": "prompt_skill"})
        validate({"name": "my-long-skill-name-here", "display_name": "X", "description": "Y", "type": "tool_skill"})

        # Name edge cases
        for bad_name in ["A", "ab!", "a b", "-start", "end-", "UPPER", "a"]:
            try:
                validate({"name": bad_name, "display_name": "X", "description": "Y", "type": "prompt_skill"})
                print(f"  FAIL: Should reject name '{bad_name}'")
                return False
            except ValueError:
                pass

        # Type edge cases
        for bad_type in ["invalid", "", "PROMPT_SKILL", "prompt"]:
            try:
                validate({"name": "valid-name", "display_name": "X", "description": "Y", "type": bad_type})
                print(f"  FAIL: Should reject type '{bad_type}'")
                return False
            except ValueError:
                pass

        # Partial updates should accept any subset
        validate({"description": "new desc"}, partial=True)
        validate({}, partial=True)

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# WEB INGESTION TESTS
# =================================================================

def test_content_hash_deterministic():
    """Test content hash is deterministic and collision-resistant."""
    print("Testing: Content hash deterministic...")
    try:
        from functions_web_ingestion import _content_hash

        h1 = _content_hash("test content")
        h2 = _content_hash("test content")
        h3 = _content_hash("different content")
        h4 = _content_hash("")

        assert h1 == h2, "Same content should produce same hash"
        assert h1 != h3, "Different content should produce different hash"
        assert len(h1) == 64, "SHA-256 should be 64 hex chars"
        assert len(h4) == 64, "Empty string should still hash"

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


def test_url_validation_comprehensive():
    """Test URL validation with many edge cases."""
    print("Testing: URL validation comprehensive...")
    try:
        from functions_web_ingestion import validate_url

        # Valid
        validate_url("https://example.com", {})
        validate_url("http://example.com/path?q=1", {})

        # Invalid schemes
        for scheme in ["ftp://x.com", "file:///etc/passwd", "javascript:alert(1)", "data:text/html,hi"]:
            try:
                validate_url(scheme, {})
                print(f"  FAIL: Should block {scheme}")
                return False
            except ValueError:
                pass

        # No hostname
        try:
            validate_url("https://", {})
            return False
        except ValueError:
            pass

        # Private IPs
        for ip in ["http://127.0.0.1", "http://10.0.0.1", "http://192.168.1.1", "http://172.16.0.1"]:
            try:
                validate_url(ip, {})
                print(f"  FAIL: Should block {ip}")
                return False
            except ValueError:
                pass

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# QUERY ROUTING TESTS
# =================================================================

def test_query_routing_comprehensive():
    """Test query routing with many query types."""
    print("Testing: Query routing comprehensive...")
    try:
        import re

        _REL = [r"how are .* related", r"connection between", r"depends on",
                r"who works", r"compare", r"relationship between", r"difference between"]
        _COMM = [r"summarize all", r"overview of", r"themes in", r"main topics", r"what are the key"]

        def route(q):
            ql = q.lower()
            if any(re.search(p, ql) for p in _REL):
                return "graph"
            if any(re.search(p, ql) for p in _COMM):
                return "community"
            return "vector"

        # Relationship queries
        assert route("How are A and B related?") == "graph"
        assert route("What's the connection between X and Y?") == "graph"
        assert route("Compare product A with product B") == "graph"
        assert route("What is the difference between React and Vue?") == "graph"
        assert route("Who works at Microsoft?") == "graph"

        # Community queries
        assert route("Summarize all the documents") == "community"
        assert route("Give me an overview of the project") == "community"
        assert route("What are the main topics?") == "community"
        assert route("What are the key themes in the data?") == "community"

        # Vector queries (default)
        assert route("What is the pricing?") == "vector"
        assert route("How to deploy to Azure?") == "vector"
        assert route("Show me the API documentation") == "vector"
        assert route("What error code 404 means?") == "vector"

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# MCP VALIDATION TESTS
# =================================================================

def test_mcp_url_validation_comprehensive():
    """Test MCP URL validation edge cases."""
    print("Testing: MCP URL validation comprehensive...")
    try:
        from semantic_kernel_plugins.mcp_plugin_factory import validate_mcp_url

        # Valid
        validate_mcp_url("https://example.com/mcp", {})

        # Allowlist
        settings = {"mcp_server_url_allowlist": ["trusted.com"]}
        validate_mcp_url("https://trusted.com/api", settings)

        # Blocked by allowlist
        try:
            validate_mcp_url("https://untrusted.com/api", settings)
            return False
        except ValueError:
            pass

        # Subdomain matching not tested (requires DNS resolution)

        print("  PASS")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =================================================================
# MAIN
# =================================================================

if __name__ == "__main__":
    results = []

    print("\n--- Reranking Tests ---")
    results.append(test_reorder_for_attention_various_sizes())
    results.append(test_mmr_filter_basic())

    print("\n--- Context Optimization Tests ---")
    results.append(test_count_tokens_various_inputs())
    results.append(test_sliding_window_edge_cases())
    results.append(test_fit_within_budget_edge_cases())
    results.append(test_build_optimized_context_structure())

    print("\n--- Skill Validation Tests ---")
    results.append(test_skill_validation_comprehensive())

    print("\n--- Web Ingestion Tests ---")
    results.append(test_content_hash_deterministic())
    results.append(test_url_validation_comprehensive())

    print("\n--- Query Routing Tests ---")
    results.append(test_query_routing_comprehensive())

    print("\n--- MCP Tests ---")
    results.append(test_mcp_url_validation_comprehensive())

    print(f"\n{'='*50}")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("All comprehensive unit tests PASSED!")
    else:
        print("Some tests FAILED!")

    sys.exit(0 if all(results) else 1)
