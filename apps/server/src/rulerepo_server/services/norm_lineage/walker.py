"""Norm Lineage Walker — traverses the DERIVES_FROM chain.

Two operations:
- upstream(rule_id): walks DERIVES_FROM edges upward to the highest-tier norm
- downstream(rule_id): walks DERIVES_FROM edges downward to all descendants

See CLAUDE.md §14.4 and PROJECT.md §5.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LineageNode:
    """A node in the norm lineage chain."""

    rule_id: str
    statement: str
    norm_tier: str
    norm_authority: str | None = None
    depth: int = 0


@dataclass
class LineageChain:
    """The result of a lineage walk."""

    root_rule_id: str
    nodes: list[LineageNode] = field(default_factory=list)
    direction: str = "upstream"  # "upstream" or "downstream"


class NormLineageWalker:
    """Walks the DERIVES_FROM relationship chain in the rule graph.

    Uses raw SQL queries against the ``rules`` and ``rule_relationships``
    tables in PostgreSQL.  Neo4j is the authoritative graph store for
    relationships, but Postgres mirrors them for transactional consistency
    (see CLAUDE.md §10.3).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upstream(self, rule_id: str, *, max_depth: int = 20) -> LineageChain:
        """Walk DERIVES_FROM edges upward to the highest-tier norm.

        Returns the chain from this rule up to the source law/regulation.
        """
        from sqlalchemy import text

        chain = LineageChain(root_rule_id=rule_id, direction="upstream")
        visited: set[str] = set()
        current_id: str | None = rule_id
        depth = 0

        while current_id and depth < max_depth:
            if current_id in visited:
                logger.warning(
                    "cycle_detected_in_upstream_lineage",
                    rule_id=current_id,
                    root_rule_id=rule_id,
                )
                break
            visited.add(current_id)

            # Get rule details
            result = await self._session.execute(
                text("SELECT id, statement, norm_tier, norm_authority FROM rules WHERE id = :id"),
                {"id": current_id},
            )
            row = result.first()
            if not row:
                logger.warning(
                    "rule_not_found_during_lineage_walk",
                    rule_id=current_id,
                    direction="upstream",
                )
                break

            chain.nodes.append(
                LineageNode(
                    rule_id=str(row[0]),
                    statement=row[1] or "",
                    norm_tier=row[2] or "OPERATIONAL_RULE",
                    norm_authority=row[3],
                    depth=depth,
                )
            )

            # Find parent via DERIVES_FROM (source derives from target)
            result = await self._session.execute(
                text(
                    "SELECT target_id FROM rule_relationships "
                    "WHERE source_id = :id AND relationship_type = 'DERIVES_FROM' "
                    "LIMIT 1"
                ),
                {"id": current_id},
            )
            parent_row = result.first()
            current_id = str(parent_row[0]) if parent_row else None
            depth += 1

        logger.info(
            "upstream_lineage_walk_complete",
            root_rule_id=rule_id,
            nodes_found=len(chain.nodes),
        )
        return chain

    async def downstream(self, rule_id: str, *, max_depth: int = 20) -> LineageChain:
        """Walk DERIVES_FROM edges downward to all descendants.

        Returns all rules that transitively derive from this rule.
        Uses breadth-first traversal.
        """
        from sqlalchemy import text

        chain = LineageChain(root_rule_id=rule_id, direction="downstream")
        queue: list[tuple[str, int]] = [(rule_id, 0)]
        visited: set[str] = set()

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            if depth > max_depth:
                logger.warning(
                    "max_depth_reached_in_downstream_lineage",
                    rule_id=current_id,
                    root_rule_id=rule_id,
                    max_depth=max_depth,
                )
                continue
            visited.add(current_id)

            result = await self._session.execute(
                text("SELECT id, statement, norm_tier, norm_authority FROM rules WHERE id = :id"),
                {"id": current_id},
            )
            row = result.first()
            if not row:
                logger.warning(
                    "rule_not_found_during_lineage_walk",
                    rule_id=current_id,
                    direction="downstream",
                )
                continue

            chain.nodes.append(
                LineageNode(
                    rule_id=str(row[0]),
                    statement=row[1] or "",
                    norm_tier=row[2] or "OPERATIONAL_RULE",
                    norm_authority=row[3],
                    depth=depth,
                )
            )

            # Find children (rules that derive from this one)
            result = await self._session.execute(
                text(
                    "SELECT source_id FROM rule_relationships "
                    "WHERE target_id = :id AND relationship_type = 'DERIVES_FROM'"
                ),
                {"id": current_id},
            )
            for child_row in result.fetchall():
                queue.append((str(child_row[0]), depth + 1))

        logger.info(
            "downstream_lineage_walk_complete",
            root_rule_id=rule_id,
            nodes_found=len(chain.nodes),
        )
        return chain
