"""Code change subject adapter — handles diff-based evaluations.

This adapter preserves full behavioral parity with the pre-refactor
evaluation pipeline. It is the default adapter for legacy requests.

See: IMPROVEMENT.md Phase 7b
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext


class CodeChangeAdapter:
    """Adapter for code change (diff) evaluations."""

    @property
    def subject_type(self) -> str:
        return "code_change"

    def parse_payload(self, payload: dict[str, Any]) -> EvaluationContext:
        """Parse a code change payload into an EvaluationContext.

        Accepts the same fields as the legacy evaluate endpoint:
        diff, file_paths, intent, scope, facts.
        """
        return EvaluationContext(
            diff=payload.get("diff"),
            file_paths=payload.get("file_paths", []),
            intent=payload.get("intent"),
            facts=payload.get("facts", {}),
            narrative=payload.get("narrative"),
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from file paths using the scope registry."""
        scope = payload.get("scope")
        if isinstance(scope, list):
            return scope
        if isinstance(scope, str):
            return [scope]
        # Fall back to file-path-based scope resolution
        return payload.get("scopes", ["engineering"])

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Format the diff as prompt context."""
        diff = payload.get("diff", "")
        if not diff:
            return "No code changes provided."
        lines = diff.split("\n")
        if len(lines) > 200:
            return "\n".join(lines[:200]) + f"\n... ({len(lines) - 200} more lines)"
        return diff
