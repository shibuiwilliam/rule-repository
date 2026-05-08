"""Legal domain module — contract evaluation, clause extraction, regulatory compliance.

Handles contract_clause and contract_document artifact types.
See IMPROVEMENT.md RR-008.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.services.domains._protocol import (
    Connector,
    ContextAssembler,
    DiscoveryAnalyzer,
    DomainEvaluator,
    RuleSelector,
)


class _LegalRuleSelector:
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
            artifact_type="contract_clause",
            **passthrough,
        )


class LegalModule:
    """Concrete implementation of the ``DomainModule`` protocol for legal."""

    @property
    def name(self) -> str:
        return "legal"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["contract_clause", "contract_document"]

    def context_assembler(self) -> ContextAssembler:
        from rulerepo_server.services.domains.legal.evaluation.context_assembler import LegalContextAssembler

        return LegalContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _LegalRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        from rulerepo_server.services.domains.legal.evaluation.evaluator import LegalEvaluator

        return LegalEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        from rulerepo_server.services.domains.legal.discovery.contract_analyzer import ContractAnalyzer

        return [ContractAnalyzer()]

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = LegalModule()
