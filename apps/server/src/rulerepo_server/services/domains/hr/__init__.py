"""HR domain module — attendance, leave, and evaluation-comment rules.

Handles attendance_record, leave_request, and evaluation_comment artifact types.
See IMPROVEMENT.md RR-009.
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


class _HRRuleSelector:
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
            artifact_type="leave_request",
            **passthrough,
        )


class HRModule:
    """Concrete implementation of the ``DomainModule`` protocol for HR."""

    @property
    def name(self) -> str:
        return "hr"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["attendance_record", "leave_request", "evaluation_comment"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.hr.evaluation.context_assembler import HRContextAssembler

        return HRContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _HRRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.hr.evaluation.evaluator import HREvaluator

        return HREvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.hr.discovery.policy_analyzer import PolicyAnalyzer

        return [PolicyAnalyzer()]

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = HRModule()
