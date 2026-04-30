"""EvaluationService — orchestrates the full evaluation pipeline.

Per CLAUDE_ENHANCE.md §1.4: Context Assembly → Rule Selection → Evaluation → Aggregation.
All LLM calls are audited. Results are cached.
"""

from __future__ import annotations

import time
from typing import Any

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.adapters.postgres.audit_repo import AuditLogRepository
from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.evaluation import EvaluationResult
from rulerepo_server.services.evaluation.batch_evaluator import evaluate_batch
from rulerepo_server.services.evaluation.conflict_aggregator import (
    aggregate_with_conflicts,
)
from rulerepo_server.services.evaluation.context_assembler import assemble_context
from rulerepo_server.services.evaluation.graph_resolver import resolve_evaluation_plan
from rulerepo_server.services.evaluation.rule_selector import select_rules
from rulerepo_server.services.evaluation.verdict_aggregator import aggregate_verdicts

logger = get_logger(__name__)


class EvaluationService:
    """Orchestrates the Code-Aware Evaluation Engine pipeline.

    Pipeline: assemble context → select rules → evaluate each rule → aggregate verdicts.
    """

    def __init__(
        self,
        session: AsyncSession,
        gemini_client: genai.Client | None = None,
    ) -> None:
        self._session = session
        self._gemini_client = gemini_client
        self._audit_repo = AuditLogRepository(session)

    async def evaluate(
        self,
        *,
        diff: str | None = None,
        files: list[dict[str, str]] | None = None,
        facts: dict[str, Any] | None = None,
        intent: str | None = None,
        scope: str | None = None,
        repository: str | None = None,
        mode: str = "preflight",
        max_rules: int = 20,
        severity_min: str = "MEDIUM",
        actor: str | None = None,
        environment: str | None = None,
    ) -> EvaluationResult:
        """Run the full evaluation pipeline.

        Args:
            diff: Unified diff text (for code evaluations).
            files: List of {"path": ..., "content": ...} dicts.
            facts: Key-value pairs for non-code evaluations.
            intent: Natural language description of the change.
            scope: Rule scope filter.
            repository: Repository identifier.
            mode: "preflight" or "posthoc".
            max_rules: Maximum rules to evaluate.
            severity_min: Minimum rule severity to include.
            actor: Who triggered the evaluation.
            environment: Deployment environment for snapshot-based evaluation.

        Returns:
            EvaluationResult with overall verdict and per-rule breakdowns.
        """
        start_time = time.time()

        # 1. Assemble context
        context = assemble_context(
            diff=diff,
            files=files,
            facts=facts,
            intent=intent,
            scope=scope,
            repository=repository,
            actor=actor,
        )

        # 2. Select applicable rules
        modality_filter = ["MUST", "MUST_NOT"]
        if mode == "posthoc":
            modality_filter = ["MUST", "MUST_NOT", "SHOULD"]

        rules = await select_rules(
            self._session,
            context,
            max_rules=max_rules,
            severity_min=severity_min,
            modality_filter=modality_filter,
            scope=scope,
            environment=environment,
        )

        logger.info(
            "evaluation_rules_selected",
            rules_count=len(rules),
            mode=mode,
            has_diff=bool(diff),
            file_count=len(context.file_paths),
        )

        # 3. If no Gemini client or no rules, return ALLOW
        if not rules:
            return aggregate_verdicts([], [], 0)

        if not self._gemini_client:
            logger.warning("evaluation_no_llm_client")
            return aggregate_verdicts([], [], 0)

        # 4. Resolve relationship graph for conflict-aware evaluation
        rule_id_list = [r["id"] for r in rules]
        try:
            from rulerepo_server.adapters.neo4j.client import get_neo4j_driver
            from rulerepo_server.adapters.neo4j.graph_repo import Neo4jGraphRepository

            graph_repo = Neo4jGraphRepository(get_neo4j_driver())
            plan = await resolve_evaluation_plan(rule_id_list, graph_repo)
        except Exception as exc:
            logger.warning("graph_resolution_skipped", error=str(exc))
            from rulerepo_server.services.evaluation.graph_resolver import EvaluationPlan

            plan = EvaluationPlan(ordered_rules=rule_id_list)

        # 5. Evaluate each rule (concurrently)
        # Pass LLM cache repo for caching (CLAUDE_ENHANCE.md §0.2)
        cache_repo = None
        try:
            from rulerepo_server.adapters.postgres.cache_repo import LLMCacheRepository

            cache_repo = LLMCacheRepository(self._session)
        except Exception:
            pass

        batch_results = await evaluate_batch(rules, context, self._gemini_client, cache_repo=cache_repo)

        verdicts = []
        model_ids: list[str] = []
        total_rule_latency = 0

        for result_item in batch_results:
            verdict, model_id, latency_ms = result_item
            verdicts.append(verdict)
            model_ids.append(model_id)
            total_rule_latency += latency_ms

        # 6. Conflict-aware aggregation (or simple if no relationships)
        total_latency = int((time.time() - start_time) * 1000)

        if plan.overrides or plan.conflicts or plan.skip_if_denied:
            rule_dict_map = {r["id"]: r for r in rules}
            overall_verdict, conflict_resolutions = aggregate_with_conflicts(verdicts, plan, rule_dict_map)
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)
            eval_result.overall_verdict = overall_verdict
            eval_result.conflict_resolutions = [
                {
                    "rule_a_id": cr.rule_a_id,
                    "rule_b_id": cr.rule_b_id,
                    "relationship": cr.relationship,
                    "winner_id": cr.winner_id,
                    "reason": cr.reason,
                    "discarded_verdict": cr.discarded_verdict,
                }
                for cr in conflict_resolutions
            ]
        else:
            eval_result = aggregate_verdicts(verdicts, model_ids, total_latency)

        # 6. Persist evaluation records
        try:
            from rulerepo_server.adapters.postgres.models import (
                DEFAULT_PROJECT_ID,
                EvaluationRecordModel,
            )

            input_type = "code" if diff else "facts"
            eval_scope = scope or ""
            latency_per_rule = [total_rule_latency // max(len(verdicts), 1)] * len(verdicts)
            for i, (v, mid) in enumerate(zip(verdicts, model_ids, strict=False)):
                record = EvaluationRecordModel(
                    project_id=DEFAULT_PROJECT_ID,
                    rule_id=v.rule_id,
                    verdict=v.verdict.value,
                    confidence=v.confidence,
                    latency_ms=latency_per_rule[i] if i < len(latency_per_rule) else 0,
                    scope=eval_scope,
                    input_type=input_type,
                    model_id=mid,
                    cached=False,
                )
                self._session.add(record)
            await self._session.flush()
        except Exception as exc:
            logger.warning("evaluation_persistence_failed", error=str(exc))

        # 7. Audit log
        await self._audit_repo.append(
            action="evaluate",
            actor=actor or "system",
            resource_type="evaluation",
            resource_id=eval_result.evaluation_id,
            details={
                "overall_verdict": eval_result.overall_verdict.value,
                "rules_evaluated": eval_result.rules_evaluated,
                "rules_violated": eval_result.rules_violated,
                "mode": mode,
                "has_diff": bool(diff),
                "file_paths": context.file_paths[:10],
                "model_ids": list(set(model_ids)),
                "latency_ms": total_latency,
            },
        )

        logger.info(
            "evaluation_complete",
            evaluation_id=eval_result.evaluation_id,
            verdict=eval_result.overall_verdict.value,
            rules_evaluated=eval_result.rules_evaluated,
            violations=eval_result.rules_violated,
            latency_ms=total_latency,
        )

        return eval_result

    async def get_applicable_rules(
        self,
        *,
        file_paths: list[str] | None = None,
        repository: str | None = None,
        scope: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get rules that would apply to given file paths, without running evaluation.

        Args:
            file_paths: List of file paths to check.
            repository: Repository identifier.
            scope: Rule scope filter.

        Returns:
            List of applicable rule dicts.
        """
        context = assemble_context(
            files=[{"path": p} for p in (file_paths or [])],
            repository=repository,
            scope=scope,
        )
        return await select_rules(
            self._session,
            context,
            max_rules=50,
            severity_min="LOW",
            modality_filter=["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"],
            scope=scope,
        )
