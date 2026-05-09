"""Domain Module protocol — the contract every domain plugin must implement.

See CLAUDE.md §10.1 for the full specification.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ContextAssembler(Protocol):
    """Transforms an Evaluable into LLM-ready context for a specific domain."""

    async def assemble(self, evaluable: dict[str, Any]) -> str: ...


@runtime_checkable
class RuleSelector(Protocol):
    """Narrows the rule corpus for a specific domain's artifact types."""

    async def select(
        self,
        context: Any,
        *,
        max_rules: int = 20,
        **kwargs: Any,
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class DomainEvaluator(Protocol):
    """Domain-specific evaluation judge with custom prompt."""

    async def evaluate(
        self,
        context: str,
        rules: list[dict[str, Any]],
        **kwargs: Any,
    ) -> list[dict[str, Any]]: ...


@runtime_checkable
class DiscoveryAnalyzer(Protocol):
    """Analyzes domain-specific sources to discover candidate rules."""

    async def analyze(self, source: Any) -> list[dict[str, Any]]: ...


@runtime_checkable
class DomainModule(Protocol):
    """The top-level protocol every domain module must implement.

    Each module under ``services/domains/<name>/`` exposes a single
    module-level instance satisfying this protocol.  The registry in
    ``services/domains/__init__`` discovers them automatically.
    """

    @property
    def name(self) -> str: ...

    @property
    def supported_artifact_types(self) -> list[str]: ...

    def context_assembler(self) -> ContextAssembler: ...

    def rule_selector(self) -> RuleSelector: ...

    def evaluator(self) -> DomainEvaluator: ...

    def discovery_analyzers(self) -> list[DiscoveryAnalyzer]: ...

    def templates_path(self) -> Path: ...
