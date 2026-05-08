"""Rule coverage heatmap -- identifies gaps in rule coverage (RR-034).

Analyzes the rule corpus to find scopes and artifact types that
have thin or no coverage, helping organizations prioritize
rule creation efforts.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CoverageCell:
    """A single cell in the coverage heatmap (scope x artifact_type)."""

    scope: str
    artifact_type: str
    rule_count: int
    severity_distribution: dict[str, int] = field(default_factory=dict)
    coverage_level: str = "none"  # "none", "thin", "moderate", "strong"


def compute_coverage_heatmap(
    rules: list[dict[str, Any]],
) -> list[CoverageCell]:
    """Compute a coverage heatmap from the rule corpus.

    Returns cells for each scope x artifact_type combination
    with coverage level assessment.

    Args:
        rules: List of rule dicts with "scope", "applicable_subject_types",
               and "severity" keys.

    Returns:
        Sorted list of CoverageCell objects.
    """
    grid: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for rule in rules:
        scopes = rule.get("scope", [])
        if isinstance(scopes, str):
            scopes = [scopes]
        artifact_types = rule.get("applicable_subject_types", ["code_diff"])
        if isinstance(artifact_types, str):
            artifact_types = [artifact_types]

        for scope in scopes or ["unscoped"]:
            top_scope = scope.split("/")[0] if "/" in scope else scope
            for art_type in artifact_types:
                grid[(top_scope, art_type)].append(rule)

    cells: list[CoverageCell] = []
    for (scope, art_type), matched_rules in sorted(grid.items()):
        severity_dist: dict[str, int] = defaultdict(int)
        for r in matched_rules:
            severity_dist[r.get("severity", "MEDIUM")] += 1

        count = len(matched_rules)
        if count == 0:
            level = "none"
        elif count < 3:
            level = "thin"
        elif count < 10:
            level = "moderate"
        else:
            level = "strong"

        cells.append(
            CoverageCell(
                scope=scope,
                artifact_type=art_type,
                rule_count=count,
                severity_distribution=dict(severity_dist),
                coverage_level=level,
            )
        )

    logger.info("coverage_heatmap_computed", cells=len(cells))
    return cells


def identify_gaps(
    heatmap: list[CoverageCell],
    all_scopes: list[str] | None = None,
    all_artifact_types: list[str] | None = None,
) -> list[dict[str, str]]:
    """Identify scope x artifact_type combinations with no coverage.

    Args:
        heatmap: The computed heatmap cells.
        all_scopes: Expected scopes. Defaults to the eight standard domains.
        all_artifact_types: Expected artifact types.

    Returns:
        List of dicts with "scope" and "artifact_type" for uncovered combos.
    """
    if all_scopes is None:
        all_scopes = [
            "engineering",
            "legal",
            "hr",
            "finance",
            "sales",
            "it_security",
            "communications",
            "governance",
        ]
    if all_artifact_types is None:
        all_artifact_types = [
            "code_diff",
            "contract_clause",
            "leave_request",
            "journal_entry",
            "ad_copy",
            "iac_plan",
            "email_message",
            "disclosure_document",
        ]

    covered = {(c.scope, c.artifact_type) for c in heatmap}
    gaps: list[dict[str, str]] = []
    for scope in all_scopes:
        for art_type in all_artifact_types:
            if (scope, art_type) not in covered:
                gaps.append({"scope": scope, "artifact_type": art_type})

    return gaps
