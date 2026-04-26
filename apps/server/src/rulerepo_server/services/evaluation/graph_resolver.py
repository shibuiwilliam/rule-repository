"""Graph Resolver — fetch Neo4j relationships and build an evaluation plan.

Per CLAUDE_ENHANCE.md §2.2: queries Neo4j for relationships between selected
rules and builds an EvaluationPlan with ordering, overrides, and conflicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationPlan:
    """Describes how to evaluate rules considering their relationships."""

    ordered_rules: list[str] = field(default_factory=list)
    overrides: dict[str, str] = field(default_factory=dict)
    conflicts: list[tuple[str, str]] = field(default_factory=list)
    skip_if_denied: dict[str, list[str]] = field(default_factory=dict)


async def resolve_evaluation_plan(
    rule_ids: list[str],
    graph_repo: Neo4jGraphRepository,
) -> EvaluationPlan:
    """Query Neo4j for relationships between selected rules and build a plan.

    Args:
        rule_ids: List of rule IDs that were selected for evaluation.
        graph_repo: Neo4j graph repository.

    Returns:
        An EvaluationPlan describing evaluation order and conflict handling.
    """
    plan = EvaluationPlan(ordered_rules=list(rule_ids))

    if not rule_ids or len(rule_ids) < 2:
        return plan

    try:
        # Fetch all relationships between the selected rules
        for rule_id in rule_ids:
            neighbors = await graph_repo.get_neighbors(
                __import__("uuid").UUID(rule_id),
                depth=1,
            )
            for rel in neighbors:
                source = rel.get("source_id", "")
                target = rel.get("target_id", "")
                rel_type = rel.get("rel_type", "")

                # Only consider relationships between selected rules
                if source not in rule_ids or target not in rule_ids:
                    continue

                match rel_type:
                    case "OVERRIDES":
                        # source overrides target — target's verdict will be discarded
                        plan.overrides[target] = source
                    case "CONFLICTS_WITH":
                        pair = tuple(sorted([source, target]))
                        if pair not in plan.conflicts:
                            plan.conflicts.append(pair)  # type: ignore[arg-type]
                    case "DEPENDS_ON":
                        # source depends on target — evaluate target first
                        plan.skip_if_denied.setdefault(target, []).append(source)
                    case "REFINES":
                        # source refines target — source is more specific, skip target
                        plan.overrides[target] = source

        # Topological sort for DEPENDS_ON ordering
        if plan.skip_if_denied:
            plan.ordered_rules = _topological_sort(rule_ids, plan.skip_if_denied)

        logger.info(
            "evaluation_plan_resolved",
            rules=len(rule_ids),
            overrides=len(plan.overrides),
            conflicts=len(plan.conflicts),
            dependencies=len(plan.skip_if_denied),
        )

    except Exception as exc:
        logger.warning("graph_resolution_failed", error=str(exc))
        # On failure, return a simple plan (no relationship handling)

    return plan


def _topological_sort(
    rule_ids: list[str],
    dependencies: dict[str, list[str]],
) -> list[str]:
    """Sort rules so dependencies come before dependents.

    Args:
        rule_ids: All rule IDs to sort.
        dependencies: Map of prerequisite → list of dependents.

    Returns:
        Topologically sorted list of rule IDs.
    """
    # Build reverse dependency map: dependent → list of prerequisites
    prereqs: dict[str, set[str]] = {rid: set() for rid in rule_ids}
    for prereq, dependents in dependencies.items():
        for dep in dependents:
            if dep in prereqs:
                prereqs[dep].add(prereq)

    # Kahn's algorithm
    result: list[str] = []
    ready = [rid for rid in rule_ids if not prereqs[rid]]
    visited: set[str] = set()

    while ready:
        node = ready.pop(0)
        if node in visited:
            continue
        visited.add(node)
        result.append(node)

        # Check if removing this node unblocks any dependents
        for dep_list in dependencies.values():
            for dep in dep_list:
                if dep in prereqs and node in prereqs[dep]:
                    prereqs[dep].discard(node)
                    if not prereqs[dep] and dep not in visited:
                        ready.append(dep)

    # Add any remaining unvisited (cycle protection)
    for rid in rule_ids:
        if rid not in visited:
            result.append(rid)

    return result
