"""Postgres full-text search fallback for Tier 1 (no Elasticsearch).

Uses PostgreSQL ``tsvector`` / ``tsquery`` for BM25-equivalent full-text
search.  Vector search returns empty results in Tier 1; hybrid search
falls back to full-text only.  ``pgvector`` support can be layered on
later without changing this interface.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class PostgresFTSIndex:
    """Postgres ``tsvector``-based search index.

    Drop-in replacement for ``ElasticsearchRuleIndex`` in Tier 1
    deployments.  Implements the same public interface so callers
    (``SearchService``) can use either adapter via duck typing.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Write operations (no-ops — Postgres already owns the data)
    # ------------------------------------------------------------------

    async def index_rule(self, rule_id: UUID, document: dict[str, Any], *, tenant_id: str | None = None) -> None:
        """No-op: the rule already lives in Postgres."""

    async def delete_rule(self, rule_id: UUID) -> None:
        """No-op: rule lifecycle is managed by the Postgres CRUD layer."""

    # ------------------------------------------------------------------
    # Read / search operations
    # ------------------------------------------------------------------

    async def search_fulltext(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """BM25-equivalent full-text search using ``tsvector``.

        Args:
            query: Free-text search query.
            filters: Optional column-level filters.
            page: 1-based page number.
            page_size: Results per page.

        Returns:
            A tuple of ``(hits, total)`` where *hits* is a list of
            ``(rule_id, score)`` pairs ordered by relevance.
        """
        offset = (page - 1) * page_size
        filter_clause, params = self._build_filter_clause(filters)

        count_sql = text(
            f"SELECT COUNT(*) FROM rules "
            f"WHERE to_tsvector('english', statement) @@ plainto_tsquery('english', :query) "
            f"{filter_clause}"
        )
        search_sql = text(
            f"SELECT id::text, "
            f"ts_rank(to_tsvector('english', statement), plainto_tsquery('english', :query)) AS score "
            f"FROM rules "
            f"WHERE to_tsvector('english', statement) @@ plainto_tsquery('english', :query) "
            f"{filter_clause} "
            f"ORDER BY score DESC "
            f"LIMIT :limit OFFSET :offset"
        )
        params.update({"query": query, "limit": page_size, "offset": offset})

        count_result = await self._session.execute(count_sql, params)
        total = count_result.scalar() or 0

        result = await self._session.execute(search_sql, params)
        hits = [(row[0], float(row[1])) for row in result.fetchall()]

        logger.debug("postgres_fts_search", query=query[:100], hits=len(hits), total=total)
        return hits, total

    async def search_vector(
        self,
        embedding: list[float],
        *,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
        k: int = 50,
    ) -> tuple[list[tuple[str, float]], int]:
        """Vector similarity search — not available in Tier 1.

        Returns empty results.  Install ``pgvector`` and add an
        embedding column to enable this in a future iteration.
        """
        logger.debug("postgres_fts_vector_search_unavailable")
        return [], 0

    async def search_hybrid(
        self,
        query: str,
        embedding: list[float],
        *,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """Hybrid search — falls back to full-text only in Tier 1."""
        return await self.search_fulltext(query, filters=filters, page=page, page_size=page_size)

    async def search_category(
        self,
        *,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[tuple[str, float]], int]:
        """Filter-only category search (no free-text query).

        Args:
            filters: Column-level filter criteria.
            page: 1-based page number.
            page_size: Results per page.

        Returns:
            A tuple of ``(hits, total)``.
        """
        offset = (page - 1) * page_size
        filter_clause, params = self._build_filter_clause(filters)

        # Convert leading ``AND`` into a ``WHERE`` clause
        where_clause = filter_clause.strip()
        if where_clause.upper().startswith("AND "):
            where_clause = "WHERE " + where_clause[4:]
        elif where_clause:
            where_clause = "WHERE " + where_clause

        count_sql = text(f"SELECT COUNT(*) FROM rules {where_clause}")
        search_sql = text(
            f"SELECT id::text, 1.0 AS score FROM rules {where_clause} "
            f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        params.update({"limit": page_size, "offset": offset})

        count_result = await self._session.execute(count_sql, params)
        total = count_result.scalar() or 0

        result = await self._session.execute(search_sql, params)
        hits = [(row[0], float(row[1])) for row in result.fetchall()]

        return hits, total

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_filter_clause(
        filters: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any]]:
        """Build a SQL ``AND ...`` clause from a filter dictionary.

        Returns:
            A tuple of ``(clause_string, bind_params)``.
        """
        if not filters:
            return "", {}

        clauses: list[str] = []
        params: dict[str, Any] = {}
        for i, (key, value) in enumerate(filters.items()):
            if value is None:
                continue
            param_name = f"f_{i}"
            if isinstance(value, list):
                clauses.append(f"AND {key} = ANY(:{param_name})")
                params[param_name] = value
            else:
                clauses.append(f"AND {key} = :{param_name}")
                params[param_name] = value

        return " ".join(clauses), params
