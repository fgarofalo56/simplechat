# utils/query.py
# Parameterized Cosmos DB query builder.
# Provides safe query construction to prevent NoSQL injection.

from typing import Any, List, Optional


class CosmosQuery:
    """Builder for parameterized Cosmos DB queries.

    Eliminates the risk of NoSQL injection by enforcing parameterized queries.

    Usage:
        query = (CosmosQuery("SELECT * FROM c")
            .where_equals("c.user_id", user_id)
            .where_equals("c.type", "document")
            .where_contains("c.name", search_term)
            .order_by("c._ts", descending=True)
            .offset_limit(offset, limit)
            .build())

        results = container.query_items(
            query=query.sql,
            parameters=query.parameters,
            enable_cross_partition_query=query.cross_partition,
        )
    """

    def __init__(self, base_sql: str = "SELECT * FROM c"):
        self._select = base_sql
        self._conditions: List[str] = []
        self._parameters: List[dict] = []
        self._order_by: Optional[str] = None
        self._offset: Optional[int] = None
        self._limit: Optional[int] = None
        self._param_counter = 0
        self.cross_partition = True

    def _next_param_name(self, prefix: str = "p") -> str:
        """Generate a unique parameter name."""
        self._param_counter += 1
        return f"@{prefix}_{self._param_counter}"

    def where_equals(self, field: str, value: Any, param_name: str = None) -> "CosmosQuery":
        """Add an equality condition: field = @value.

        Args:
            field: The Cosmos DB field path (e.g., 'c.user_id').
            value: The value to compare against.
            param_name: Optional explicit parameter name.
        """
        name = param_name or self._next_param_name()
        self._conditions.append(f"{field} = {name}")
        self._parameters.append({"name": name, "value": value})
        return self

    def where_not_equals(self, field: str, value: Any) -> "CosmosQuery":
        """Add an inequality condition: field != @value."""
        name = self._next_param_name()
        self._conditions.append(f"{field} != {name}")
        self._parameters.append({"name": name, "value": value})
        return self

    def where_contains(self, field: str, value: str) -> "CosmosQuery":
        """Add a CONTAINS condition for text search."""
        name = self._next_param_name()
        self._conditions.append(f"CONTAINS(LOWER({field}), {name})")
        self._parameters.append({"name": name, "value": value.lower()})
        return self

    def where_in(self, field: str, values: List[Any]) -> "CosmosQuery":
        """Add an IN condition: field IN (@v1, @v2, ...).

        Args:
            field: The Cosmos DB field path.
            values: List of values to check membership.
        """
        if not values:
            # Empty IN clause — add impossible condition
            self._conditions.append("1=0")
            return self

        names = []
        for val in values:
            name = self._next_param_name("in")
            names.append(name)
            self._parameters.append({"name": name, "value": val})
        self._conditions.append(f"{field} IN ({', '.join(names)})")
        return self

    def where_raw(self, condition: str, params: List[dict] = None) -> "CosmosQuery":
        """Add a raw WHERE condition with optional parameters.

        Use sparingly — prefer typed methods above. Ensure the condition
        string does NOT contain user input (only field names and @params).

        Args:
            condition: SQL condition string (e.g., "c.status = @status").
            params: List of parameter dicts [{"name": "@status", "value": "active"}].
        """
        self._conditions.append(condition)
        if params:
            self._parameters.extend(params)
        return self

    def order_by(self, field: str, descending: bool = False) -> "CosmosQuery":
        """Set the ORDER BY clause."""
        direction = "DESC" if descending else "ASC"
        self._order_by = f"ORDER BY {field} {direction}"
        return self

    def offset_limit(self, offset: int, limit: int) -> "CosmosQuery":
        """Set OFFSET and LIMIT for pagination."""
        self._offset = max(0, offset)
        self._limit = max(1, min(limit, 1000))  # Cap at 1000
        return self

    def set_cross_partition(self, enabled: bool = True) -> "CosmosQuery":
        """Set whether the query should cross partitions."""
        self.cross_partition = enabled
        return self

    def build(self) -> "CosmosQuery":
        """Build the final query. Returns self for convenience."""
        return self

    @property
    def sql(self) -> str:
        """Get the complete SQL query string."""
        parts = [self._select]
        if self._conditions:
            parts.append("WHERE " + " AND ".join(self._conditions))
        if self._order_by:
            parts.append(self._order_by)
        if self._offset is not None and self._limit is not None:
            parts.append(f"OFFSET {self._offset} LIMIT {self._limit}")
        return " ".join(parts)

    @property
    def parameters(self) -> List[dict]:
        """Get the query parameters list."""
        return self._parameters

    def count(self) -> "CosmosQuery":
        """Convert this query to a COUNT query."""
        # Replace SELECT clause with COUNT
        if "SELECT" in self._select.upper():
            self._select = "SELECT VALUE COUNT(1) FROM c"
        return self
