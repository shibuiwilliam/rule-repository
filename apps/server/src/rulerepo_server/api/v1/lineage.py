"""REST API for Norm Lineage queries.

See CLAUDE.md §14.4.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.session import get_db_session
from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.norm_lineage.walker import NormLineageWalker

logger = get_logger(__name__)
router = APIRouter(prefix="/lineage", tags=["norm-lineage"])


@router.get("/{rule_id}/upstream")
async def get_upstream_lineage(
    rule_id: str,
    max_depth: int = 20,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get the upstream norm lineage chain for a rule.

    Walks DERIVES_FROM edges upward to the highest-tier norm (LAW/REGULATION).
    """
    walker = NormLineageWalker(session)
    chain = await walker.upstream(rule_id, max_depth=max_depth)
    return {
        "rule_id": rule_id,
        "direction": "upstream",
        "chain": [
            {
                "rule_id": n.rule_id,
                "statement": n.statement,
                "norm_tier": n.norm_tier,
                "norm_authority": n.norm_authority,
                "depth": n.depth,
            }
            for n in chain.nodes
        ],
    }


@router.get("/{rule_id}/downstream")
async def get_downstream_lineage(
    rule_id: str,
    max_depth: int = 20,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get the downstream norm lineage for a rule.

    Returns all rules that transitively derive from this rule.
    """
    walker = NormLineageWalker(session)
    chain = await walker.downstream(rule_id, max_depth=max_depth)
    return {
        "rule_id": rule_id,
        "direction": "downstream",
        "chain": [
            {
                "rule_id": n.rule_id,
                "statement": n.statement,
                "norm_tier": n.norm_tier,
                "norm_authority": n.norm_authority,
                "depth": n.depth,
            }
            for n in chain.nodes
        ],
    }
