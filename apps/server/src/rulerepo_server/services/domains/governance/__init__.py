"""Governance domain module — disclosure documents and board minute evaluation.

Handles disclosure_document and board_minute artifact types.
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


class _GovernanceRuleSelector:
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
        artifact_type = kwargs.get("artifact_type", "disclosure_document")
        return await select_rules(
            session,
            context,
            max_rules=max_rules,
            artifact_type=artifact_type,
            **passthrough,
        )


class GovernanceModule:
    """Concrete implementation of the ``DomainModule`` protocol for governance."""

    @property
    def name(self) -> str:
        return "governance"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["disclosure_document", "board_minute"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.governance.evaluation.context_assembler import (
            GovernanceContextAssembler,
        )

        return GovernanceContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _GovernanceRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.governance.evaluation.evaluator import (
            GovernanceEvaluator,
        )

        return GovernanceEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.governance.discovery.governance_policy_analyzer import (
            GovernancePolicyAnalyzer,
        )

        return [GovernancePolicyAnalyzer()]

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = GovernanceModule()
