"""Code surface adapter — wraps existing diff parsing and code evaluation logic.

Delegates to the existing ``diff_parser`` and ``context_assembler`` modules
for backwards compatibility. See CLAUDE.md §14.2.2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rulerepo_server.domain.evaluation import Surface
from rulerepo_server.services.evaluation.context_assembler import assemble_context
from rulerepo_server.services.evaluation.diff_parser import detect_language, parse_unified_diff
from rulerepo_server.services.evaluation.surfaces.base import (
    EvaluationSubjectPayload,
    SurfaceAdapter,
)

_HINTS_FILE = Path(__file__).parent / "prompts" / "code_hints.txt"


class CodeSurfaceAdapter(SurfaceAdapter):
    """Surface adapter for software code changes.

    Handles unified diffs, file listings, and language-aware scope resolution.
    """

    @property
    def surface(self) -> Surface:
        return Surface.CODE

    async def parse(self, payload: dict[str, Any]) -> EvaluationSubjectPayload:
        """Parse a code evaluation request into a uniform subject.

        Args:
            payload: Request with optional ``diff``, ``files``, ``facts``,
                ``intent``, ``scope``, ``repository``, ``actor``.

        Returns:
            EvaluationSubjectPayload with code-specific fields.
        """
        ctx = assemble_context(
            diff=payload.get("diff"),
            files=payload.get("files"),
            facts=payload.get("facts"),
            intent=payload.get("intent"),
            scope=payload.get("scope"),
            repository=payload.get("repository"),
            actor=payload.get("actor"),
        )

        # Build a human-readable description
        file_list = ", ".join(ctx.file_paths[:5])
        if len(ctx.file_paths) > 5:
            file_list += f" (+{len(ctx.file_paths) - 5} more)"
        description = f"Code change affecting {len(ctx.file_paths)} file(s): {file_list}"
        if ctx.intent:
            description = f"{ctx.intent}\n\n{description}"

        # Build identifier
        repo = payload.get("repository", "unknown")
        identifier = f"code:{repo}/{','.join(ctx.file_paths[:3])}"

        return EvaluationSubjectPayload(
            surface=Surface.CODE,
            identifier=identifier,
            description=description,
            payload={
                "diff": ctx.diff,
                "file_paths": ctx.file_paths,
                "languages": ctx.languages,
                "files_changed": [
                    {"path": f.path, "change_type": f.change_type, "language": f.language} for f in ctx.files_changed
                ],
            },
            facts=ctx.facts,
            locale="en",
        )

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve scopes from file paths."""
        scopes: set[str] = set()
        file_paths: list[str] = []

        if payload.get("files"):
            file_paths = [f.get("path", "") for f in payload["files"] if f.get("path")]
        if payload.get("diff") and not file_paths:
            changes = parse_unified_diff(payload["diff"])
            file_paths = [c.path for c in changes]

        for path in file_paths:
            lang = detect_language(path)
            if lang:
                scopes.add(f"engineering/{lang}")

        if payload.get("scope"):
            scope_val = payload["scope"]
            if isinstance(scope_val, list):
                scopes.update(scope_val)
            else:
                scopes.add(scope_val)

        return sorted(scopes) if scopes else ["engineering"]

    def get_prompt_hints(self) -> str:
        """Return code-specific prompt hints."""
        if _HINTS_FILE.exists():
            return _HINTS_FILE.read_text()
        return (
            "You are evaluating a software code change. The subject payload "
            "includes a unified diff. Focus on code quality, security, "
            "and adherence to engineering standards."
        )

    def pii_fields(self, payload: dict[str, Any]) -> list[str]:
        return []  # Code diffs typically don't contain PII

    @property
    def default_audit_retention_days(self) -> int:
        return 365
