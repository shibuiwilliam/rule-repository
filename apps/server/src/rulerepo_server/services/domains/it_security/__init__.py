"""IT Security domain module — IaC plan evaluation and access request review.

Handles iac_plan and access_request artifact types.
See IMPROVEMENT.md RR-017.
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


class _ITSecurityRuleSelector:
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
            artifact_type="iac_plan",
            **passthrough,
        )


class ITSecurityModule:
    """Concrete implementation of the ``DomainModule`` protocol for IT Security."""

    @property
    def name(self) -> str:
        return "it_security"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["iac_plan", "access_request"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.it_security.evaluation.context_assembler import (
            ITSecurityContextAssembler,
        )

        return ITSecurityContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _ITSecurityRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.it_security.evaluation.evaluator import (
            ITSecurityEvaluator,
        )

        return ITSecurityEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.it_security.discovery.security_policy_analyzer import (
            SecurityPolicyAnalyzer,
        )

        return [SecurityPolicyAnalyzer()]

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = ITSecurityModule()
