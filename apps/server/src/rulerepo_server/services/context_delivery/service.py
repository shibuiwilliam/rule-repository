"""ContextDeliveryService — orchestrates smart rule selection and formatting.

Per PROJECT_ENHANCE.md §2.3: this is what makes the Rule Repository
indispensable to coding agents. Rules must reach the agent at the right
moment, in the right format, filtered to what matters.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from rulerepo_server.core.logging import get_logger
from rulerepo_server.services.context_delivery.formatter import format_rules
from rulerepo_server.services.context_delivery.scope_registry import ScopeRegistry
from rulerepo_server.services.evaluation.diff_parser import detect_language

logger = get_logger(__name__)


class ContextDeliveryService:
    """Delivers the right rules to agents at the right moment.

    Combines the ScopeRegistry (fast file-path matching) with the
    RuleFormatter (token-efficient output) to produce context-ready
    rule summaries.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._registry = ScopeRegistry()

    async def get_formatted_rules(
        self,
        *,
        file_paths: list[str] | None = None,
        repository: str | None = None,
        task_description: str | None = None,
        languages: list[str] | None = None,
        scope: str | None = None,
        max_rules: int = 15,
        format_type: str = "instructions",
        federation_id: str | None = None,
    ) -> str:
        """Get rules formatted for agent context injection.

        Args:
            file_paths: Files being worked on.
            repository: Repository identifier.
            task_description: Natural language description of the task.
            languages: Programming languages (auto-detected from file_paths if not provided).
            scope: Explicit scope filter.
            max_rules: Maximum rules to return.
            format_type: "instructions", "checklist", or "detailed".
            federation_id: If provided, resolve rules through federation hierarchy.

        Returns:
            Formatted plain text ready for agent context window.
        """
        # When federation_id is provided, resolve rules through federation
        if federation_id is not None:
            from rulerepo_server.services.federation.resolver import resolve_effective_rules

            effective = await resolve_effective_rules(federation_id, self._session)
            rules = effective[:max_rules]
            label = _build_context_label(file_paths, repository, task_description)
            return format_rules(rules, format_type=format_type, context_label=label)

        # Auto-detect languages from file paths
        if not languages and file_paths:
            detected = set()
            for fp in file_paths:
                lang = detect_language(fp)
                if lang:
                    detected.add(lang)
            languages = sorted(detected) if detected else None

        # Load rules into registry
        await self._registry.load(self._session)

        # Get matching rules
        if file_paths or repository or languages:
            rules = self._registry.get_rules_for_paths(
                file_paths or [],
                repository=repository,
                languages=languages,
                max_rules=max_rules,
            )
        else:
            # Fallback: return all rules (limited)
            rules = self._registry._rules[:max_rules]

        # Build context label
        label = _build_context_label(file_paths, repository, task_description)

        return format_rules(rules, format_type=format_type, context_label=label)


def _build_context_label(
    file_paths: list[str] | None,
    repository: str | None,
    task_description: str | None,
) -> str:
    """Build a human-readable label for the context."""
    parts: list[str] = []
    if file_paths:
        if len(file_paths) == 1:
            parts.append(file_paths[0])
        else:
            parts.append(f"{len(file_paths)} files")
    if repository:
        parts.append(f"in {repository}")
    if task_description:
        parts.append(f"({task_description})")
    return " ".join(parts) if parts else "your current context"
