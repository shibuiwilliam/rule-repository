"""Code diff subject adapter — handles diff-based evaluations.

This adapter preserves full behavioral parity with the pre-refactor
evaluation pipeline. It is the default adapter for legacy requests.

See: CLAUDE.md §12.1
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation import EvaluationContext, Remediation
from rulerepo_server.domain.subject import PromptFormat, SubjectKind
from rulerepo_server.subjects.registry import register


@register(SubjectKind.CODE_DIFF)
class CodeDiffAdapter:
    """Adapter for code diff evaluations."""

    kind = SubjectKind.CODE_DIFF

    @property
    def identifier(self) -> str:
        return "code_diff"

    @property
    def subject_type(self) -> str:
        """Backward-compatible alias."""
        return self.kind.value

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
        return payload.get("scopes", ["engineering"])

    def render_for_llm(self, facts: dict[str, Any], format: PromptFormat = PromptFormat.FULL) -> str:
        """Format the diff as prompt context."""
        diff = facts.get("diff", "")
        if not diff:
            return "No code changes provided."
        lines = diff.split("\n")
        if len(lines) > 200:
            return "\n".join(lines[:200]) + f"\n... ({len(lines) - 200} more lines)"
        return diff

    def format_prompt_context(self, payload: dict[str, Any]) -> str:
        """Legacy alias for render_for_llm."""
        return self.render_for_llm(payload)

    def extract_features(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract code-specific features."""
        return {
            "has_diff": bool(payload.get("diff")),
            "file_paths": payload.get("file_paths", []),
        }

    def parse_remediation(self, raw: dict[str, Any]) -> Remediation | None:
        """Parse a code remediation from raw LLM output."""
        if not raw.get("file_path"):
            return None
        return Remediation(
            type=raw.get("type", "replace"),
            file_path=raw.get("file_path", ""),
            start_line=raw.get("start_line", 0),
            end_line=raw.get("end_line"),
            original=raw.get("original"),
            replacement=raw.get("replacement"),
            description=raw.get("description", ""),
            auto_applicable=raw.get("auto_applicable", False),
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        """Code diffs generally don't contain PII."""
        return []


# Backward-compatible alias
CodeChangeAdapter = CodeDiffAdapter
