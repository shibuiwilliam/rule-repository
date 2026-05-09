"""Sales domain module — ad copy compliance, discount governance, quote evaluation.

Handles ad_copy, discount_request, and quote artifact types.
See IMPROVEMENT.md RR-018.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.services.domains._protocol import (
    ContextAssembler,
    DiscoveryAnalyzer,
    DomainEvaluator,
    RuleSelector,
)


class _SalesRuleSelector:
    async def select(
        self,
        context: Any,
        *,
        max_rules: int = 20,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        from rulerepo_server.services.evaluation.rule_selector import select_rules

        session = kwargs.get("session")
        if session is None:
            return []
        passthrough = {k: v for k, v in kwargs.items() if k != "session"}
        return await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type="ad_copy",
            **passthrough,
        )


class SalesModule:
    """Concrete implementation of the ``DomainModule`` protocol for sales."""

    @property
    def name(self) -> str:
        return "sales"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["ad_copy", "discount_request", "quote"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.sales.evaluation.context_assembler import (
            SalesContextAssembler,
        )

        return SalesContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _SalesRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.sales.evaluation.evaluator import (
            SalesEvaluator,
        )

        return SalesEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.sales.discovery.marketing_policy_analyzer import (
            MarketingPolicyAnalyzer,
        )

        return [MarketingPolicyAnalyzer()]

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = SalesModule()
