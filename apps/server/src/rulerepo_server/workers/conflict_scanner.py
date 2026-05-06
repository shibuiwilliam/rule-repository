"""Continuous Conflict Detector — Tier 1.2 background worker.

Runs daily at 1am to detect potential conflicts between active rules.
Pre-filters candidate pairs by scope overlap, then applies a heuristic
to identify contradictory rules (MUST vs MUST_NOT with similar statements).

Detected conflicts are surfaced as Proposals with type ``resolve_conflict``.

See CLAUDE.md §15.2 item 2 for the specification.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from itertools import combinations
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_LLM_CANDIDATES: int = 200
"""Maximum number of candidate pairs to evaluate per run."""

STATEMENT_SIMILARITY_THRESHOLD: float = 0.4
"""Minimum statement similarity ratio (0-1) for a pair to be flagged."""

CONTRADICTORY_MODALITY_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"MUST", "MUST_NOT"}),
    }
)
"""Modality combinations that represent direct contradictions."""


# ---------------------------------------------------------------------------
# Pure helper functions (testable without DB)
# ---------------------------------------------------------------------------


def compute_scope_overlap(scope_a: list[str], scope_b: list[str]) -> set[str]:
    """Return the intersection of two scope lists.

    Args:
        scope_a: Scope tags for the first rule.
        scope_b: Scope tags for the second rule.

    Returns:
        A set of shared scope strings. Empty if no overlap.
    """
    return set(scope_a) & set(scope_b)


def compute_statement_similarity(stmt_a: str, stmt_b: str) -> float:
    """Compute a similarity ratio between two rule statements.

    Uses ``difflib.SequenceMatcher`` for a quick heuristic comparison.

    Args:
        stmt_a: Statement text of the first rule.
        stmt_b: Statement text of the second rule.

    Returns:
        A float between 0.0 and 1.0 where 1.0 means identical.
    """
    return SequenceMatcher(None, stmt_a.lower(), stmt_b.lower()).ratio()


def is_contradictory_pair(modality_a: str, modality_b: str) -> bool:
    """Check whether two modalities form a contradictory pair.

    Args:
        modality_a: Modality string of the first rule.
        modality_b: Modality string of the second rule.

    Returns:
        True if the pair is contradictory.
    """
    return frozenset({modality_a, modality_b}) in CONTRADICTORY_MODALITY_PAIRS


def is_potential_conflict(
    scope_a: list[str],
    scope_b: list[str],
    modality_a: str,
    modality_b: str,
    statement_a: str,
    statement_b: str,
    similarity_threshold: float = STATEMENT_SIMILARITY_THRESHOLD,
) -> bool:
    """Determine whether two rules are a potential conflict.

    A pair is flagged when all three conditions hold:
    1. They share at least one scope tag.
    2. Their modalities are contradictory (e.g. MUST vs MUST_NOT).
    3. Their statements are similar above the threshold.

    Args:
        scope_a: Scope tags for the first rule.
        scope_b: Scope tags for the second rule.
        modality_a: Modality of the first rule.
        modality_b: Modality of the second rule.
        statement_a: Statement text of the first rule.
        statement_b: Statement text of the second rule.
        similarity_threshold: Minimum similarity ratio.

    Returns:
        True if the pair should be flagged as a potential conflict.
    """
    if not compute_scope_overlap(scope_a, scope_b):
        return False

    if not is_contradictory_pair(modality_a, modality_b):
        return False

    similarity = compute_statement_similarity(statement_a, statement_b)
    return similarity >= similarity_threshold


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------


async def scan_conflicts(ctx: dict) -> None:
    """Scan active rules for potential conflicts and create proposals.

    This function is designed to be registered as an arq cron job.
    It creates its own database session via the worker session factory.

    Args:
        ctx: arq worker context dict (unused but required by arq).
    """
    from rulerepo_server.workers.settings import _get_worker_session

    session = await _get_worker_session()
    try:
        await _scan_conflicts_with_session(session)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("conflict_scanner_failed")
        raise
    finally:
        await session.close()


async def _scan_conflicts_with_session(session: AsyncSession) -> None:
    """Core scanning logic operating on a provided session.

    Separated from ``scan_conflicts`` so that callers with their own
    session (e.g. tests or ad-hoc scripts) can invoke it directly.

    Args:
        session: An active SQLAlchemy async session.
    """
    from rulerepo_server.adapters.postgres.models import ProposalModel, RuleModel

    logger.info("conflict_scanner_started")

    # 1. Load all active rules
    result = await session.execute(select(RuleModel).where(RuleModel.status.in_(["APPROVED", "EFFECTIVE"])))
    rules = list(result.scalars().all())
    logger.info("conflict_scanner_rules_loaded", count=len(rules))

    if len(rules) < 2:
        logger.info("conflict_scanner_skipped", reason="fewer_than_2_active_rules")
        return

    # 2. Generate candidate pairs with scope overlap, bounded by MAX_LLM_CANDIDATES
    candidates: list[tuple[object, object]] = []
    for rule_a, rule_b in combinations(rules, 2):
        if len(candidates) >= MAX_LLM_CANDIDATES:
            break
        scope_a: list[str] = rule_a.scope if isinstance(rule_a.scope, list) else []
        scope_b: list[str] = rule_b.scope if isinstance(rule_b.scope, list) else []
        if compute_scope_overlap(scope_a, scope_b):
            candidates.append((rule_a, rule_b))

    logger.info("conflict_scanner_candidates", count=len(candidates))

    # 3. Check each candidate pair for conflicts
    conflicts_found = 0
    for rule_a, rule_b in candidates:
        scope_a = rule_a.scope if isinstance(rule_a.scope, list) else []
        scope_b = rule_b.scope if isinstance(rule_b.scope, list) else []

        if is_potential_conflict(
            scope_a=scope_a,
            scope_b=scope_b,
            modality_a=rule_a.modality,
            modality_b=rule_b.modality,
            statement_a=rule_a.statement,
            statement_b=rule_b.statement,
        ):
            # Create a resolve_conflict proposal
            shared_scopes = compute_scope_overlap(scope_a, scope_b)
            similarity = compute_statement_similarity(rule_a.statement, rule_b.statement)

            proposal = ProposalModel(
                id=str(uuid4()),
                project_id=rule_a.project_id,
                proposal_type="resolve_conflict",
                status="draft",
                author_id="system:conflict_scanner",
                title=(f"Potential conflict detected between rules {str(rule_a.id)[:8]} and {str(rule_b.id)[:8]}"),
                description=(
                    f"The conflict scanner detected a potential contradiction "
                    f"between two rules with overlapping scope.\n\n"
                    f"Rule A ({rule_a.modality}): {rule_a.statement[:200]}\n"
                    f"Rule B ({rule_b.modality}): {rule_b.statement[:200]}\n\n"
                    f"Shared scopes: {', '.join(sorted(shared_scopes))}\n"
                    f"Statement similarity: {similarity:.2f}"
                ),
                target_rule_ids=[str(rule_a.id), str(rule_b.id)],
                change_spec={
                    "conflict_type": "modality_contradiction",
                    "rule_a_id": str(rule_a.id),
                    "rule_b_id": str(rule_b.id),
                    "shared_scopes": sorted(shared_scopes),
                    "similarity_score": round(similarity, 3),
                },
            )
            session.add(proposal)
            conflicts_found += 1

    logger.info(
        "conflict_scanner_completed",
        pairs_checked=len(candidates),
        conflicts_found=conflicts_found,
    )
