"""Evaluation core — surface-agnostic evaluation pipeline.

This package contains the universal evaluation logic that works
across all surfaces. No module in this package may import from
``services.evaluation.surfaces``.

See CLAUDE.md §7.2 and §14.2.2.
"""

# Re-export the canonical core components so callers can use either
# the new ``core.`` paths or the legacy flat paths during migration.
from rulerepo_server.services.evaluation.batch_evaluator import evaluate_batch
from rulerepo_server.services.evaluation.conflict_aggregator import (
    aggregate_with_conflicts,
)
from rulerepo_server.services.evaluation.evaluation_core import evaluate_rule
from rulerepo_server.services.evaluation.graph_resolver import (
    EvaluationPlan,
    resolve_evaluation_plan,
)
from rulerepo_server.services.evaluation.impact_preview import (
    ImpactPreview,
    preview_impact,
)
from rulerepo_server.services.evaluation.rule_selector import select_rules
from rulerepo_server.services.evaluation.verdict_aggregator import aggregate_verdicts

__all__ = [
    "EvaluationPlan",
    "ImpactPreview",
    "aggregate_verdicts",
    "aggregate_with_conflicts",
    "evaluate_batch",
    "evaluate_rule",
    "preview_impact",
    "resolve_evaluation_plan",
    "select_rules",
]
