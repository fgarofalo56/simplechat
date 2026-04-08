# tests/unit/test_query_builder.py
# Unit tests for utils/query.py — the parameterized Cosmos DB query builder.

import pytest
import sys
import os

APP_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
if APP_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(APP_DIR))

from utils.query import CosmosQuery


class TestCosmosQueryBasic:
    """Tests for basic query construction."""

    def test_default_select(self):
        q = CosmosQuery().build()
        assert q.sql == "SELECT * FROM c"
        assert q.parameters == []

    def test_custom_select(self):
        q = CosmosQuery("SELECT c.id, c.name FROM c").build()
        assert q.sql == "SELECT c.id, c.name FROM c"

    def test_where_equals(self):
        q = CosmosQuery().where_equals("c.user_id", "user-123").build()
        assert "c.user_id = @p_1" in q.sql
        assert q.parameters[0]["name"] == "@p_1"
        assert q.parameters[0]["value"] == "user-123"

    def test_where_not_equals(self):
        q = CosmosQuery().where_not_equals("c.status", "deleted").build()
        assert "c.status != @p_1" in q.sql

    def test_multiple_conditions(self):
        q = (CosmosQuery()
             .where_equals("c.user_id", "u1")
             .where_equals("c.type", "doc")
             .build())
        assert "AND" in q.sql
        assert len(q.parameters) == 2


class TestCosmosQueryAdvanced:
    """Tests for advanced query features."""

    def test_where_contains(self):
        q = CosmosQuery().where_contains("c.name", "Hello").build()
        assert "CONTAINS(LOWER(c.name), @p_1)" in q.sql
        assert q.parameters[0]["value"] == "hello"  # Lowercased

    def test_where_in_with_values(self):
        q = CosmosQuery().where_in("c.id", ["a", "b", "c"]).build()
        assert "c.id IN (" in q.sql
        assert len(q.parameters) == 3

    def test_where_in_empty_list(self):
        q = CosmosQuery().where_in("c.id", []).build()
        assert "1=0" in q.sql  # Impossible condition

    def test_order_by_ascending(self):
        q = CosmosQuery().order_by("c.name").build()
        assert "ORDER BY c.name ASC" in q.sql

    def test_order_by_descending(self):
        q = CosmosQuery().order_by("c._ts", descending=True).build()
        assert "ORDER BY c._ts DESC" in q.sql

    def test_offset_limit(self):
        q = CosmosQuery().offset_limit(10, 25).build()
        assert "OFFSET 10 LIMIT 25" in q.sql

    def test_offset_limit_caps_at_1000(self):
        q = CosmosQuery().offset_limit(0, 5000).build()
        assert "LIMIT 1000" in q.sql

    def test_offset_limit_minimum_1(self):
        q = CosmosQuery().offset_limit(0, 0).build()
        assert "LIMIT 1" in q.sql

    def test_negative_offset_becomes_zero(self):
        q = CosmosQuery().offset_limit(-5, 10).build()
        assert "OFFSET 0" in q.sql

    def test_count_query(self):
        q = CosmosQuery().where_equals("c.user_id", "u1").count().build()
        assert "SELECT VALUE COUNT(1) FROM c" in q.sql
        # Should still have the WHERE clause
        assert "WHERE" in q.sql

    def test_where_raw(self):
        q = CosmosQuery().where_raw(
            "c.status = @status",
            [{"name": "@status", "value": "active"}]
        ).build()
        assert "c.status = @status" in q.sql
        assert q.parameters[0]["value"] == "active"


class TestCosmosQuerySafety:
    """Tests ensuring the query builder prevents injection."""

    def test_values_are_parameterized_not_interpolated(self):
        """User input should NEVER appear in the SQL string."""
        malicious_input = "'; DROP TABLE c; --"
        q = CosmosQuery().where_equals("c.name", malicious_input).build()
        assert malicious_input not in q.sql
        assert malicious_input in q.parameters[0]["value"]

    def test_contains_input_not_in_sql(self):
        q = CosmosQuery().where_contains("c.name", "Robert'); DROP TABLE--").build()
        assert "DROP" not in q.sql

    def test_cross_partition_default_true(self):
        q = CosmosQuery().build()
        assert q.cross_partition is True

    def test_cross_partition_can_be_disabled(self):
        q = CosmosQuery().set_cross_partition(False).build()
        assert q.cross_partition is False

    def test_custom_param_name(self):
        q = CosmosQuery().where_equals("c.id", "123", param_name="@docId").build()
        assert "@docId" in q.sql
        assert q.parameters[0]["name"] == "@docId"


class TestCosmosQueryChaining:
    """Tests for fluent interface / method chaining."""

    def test_full_chain(self):
        q = (CosmosQuery("SELECT c.id, c.name FROM c")
             .where_equals("c.user_id", "user-1")
             .where_equals("c.type", "document")
             .where_contains("c.name", "report")
             .order_by("c._ts", descending=True)
             .offset_limit(0, 10)
             .build())

        assert "SELECT c.id, c.name FROM c" in q.sql
        assert "WHERE" in q.sql
        assert "AND" in q.sql
        assert "ORDER BY c._ts DESC" in q.sql
        assert "OFFSET 0 LIMIT 10" in q.sql
        assert len(q.parameters) == 3

    def test_count_chain(self):
        q = (CosmosQuery()
             .where_equals("c.user_id", "u1")
             .count()
             .build())
        assert "COUNT(1)" in q.sql
        assert "WHERE" in q.sql
