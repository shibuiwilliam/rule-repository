"""Legal domain module stub — contract evaluation, clause extraction, regulatory compliance.

This is a minimal skeleton that satisfies the ``DomainModule`` protocol.
Full implementation is planned for Phase 1 (see IMPROVEMENT.md RR-008).
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


class _LegalContextAssembler:
    async def assemble(self, evaluable: dict[str, Any]) -> str:
        payload = evaluable.get("payload", {})
        parts: list[str] = []
        if clause := payload.get("clause"):
            parts.append(f"Clause:\n{clause}")
        if document := payload.get("document"):
            parts.append(f"Document:\n{document}")
        return "\n\n".join(parts) if parts else str(payload)


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


class _LegalEvaluator:
    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        return []


class LegalModule:
    """Concrete implementation of the ``DomainModule`` protocol for legal."""

    @property
    def name(self) -> str:
        return "legal"

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["contract_clause", "contract_document"]

    def context_assembler(self) -> ContextAssembler:
        return _LegalContextAssembler()

    def rule_selector(self) -> RuleSelector:
        return _LegalRuleSelector()

    def evaluator(self) -> DomainEvaluator:
        return _LegalEvaluator()

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]:
        return []

    def connectors(self) -> list[Connector]:
        return []

    def templates_path(self) -> Path:
        return Path(__file__).parent / "templates"


module = LegalModule()
