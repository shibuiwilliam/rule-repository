"""Code evaluation domain adapter.

Wraps existing code-evaluation logic (diff parsing, language detection,
file-path scope resolution) behind the EvaluationDomainAdapter Protocol.

This is the first adapter implementation. The existing logic in
``services/evaluation/diff_parser.py`` and ``context_assembler.py``
remains in place for backwards compatibility; this adapter delegates to it.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.services.evaluation.context_assembler import assemble_context
from rulerepo_server.services.evaluation.diff_parser import detect_language

# File-path glob → scope mapping for code evaluation
DEFAULT_SCOPE_MAP: dict[str, str] = {
    "**/*.py": "engineering/python",
    "**/*.ts": "engineering/typescript",
    "**/*.tsx": "engineering/typescript",
    "**/*.js": "engineering/javascript",
    "**/*.jsx": "engineering/javascript",
    "**/*.go": "engineering/go",
    "**/*.rs": "engineering/rust",
    "**/*.java": "engineering/java",
    "**/*.rb": "engineering/ruby",
    "**/*.sql": "engineering/database",
    "**/*.yaml": "engineering/config",
    "**/*.yml": "engineering/config",
    "**/*.toml": "engineering/config",
    "**/Dockerfile*": "engineering/devops",
    "**/*.tf": "engineering/devops",
    "**/docker-compose*": "engineering/devops",
    "**/.github/**": "engineering/ci-cd",
    "**/test*/**": "engineering/testing",
    "**/spec*/**": "engineering/testing",
}


class CodeAdapter:
    """Evaluation domain adapter for software code changes.

    Handles unified diffs, file listings, and language-aware scope resolution.
    Delegates to the existing evaluation pipeline components.
    """

    @property
    def domain(self) -> str:
        return "code"

    async def parse(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Parse a code evaluation request into an EvaluationContext.

        Args:
            payload: Request payload with optional ``diff``, ``files``,
                ``facts``, ``intent``, ``scope``, ``repository``, ``actor``.

        Returns:
            EvaluationContext as a dict.
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
        return {
            "diff": ctx.diff,
            "files_changed": ctx.files_changed,
            "file_paths": ctx.file_paths,
            "languages": ctx.languages,
            "repository": ctx.repository,
            "intent": ctx.intent,
            "actor": ctx.actor,
            "facts": ctx.facts,
            "narrative": ctx.narrative,
        }

    def resolve_scopes(self, payload: dict[str, Any]) -> list[str]:
        """Resolve rule scopes from file paths in the payload.

        Uses ``DEFAULT_SCOPE_MAP`` to map file extensions/paths to scopes.

        Args:
            payload: Request payload containing ``diff`` or ``files``.

        Returns:
            Deduplicated list of resolved scope strings.
        """
        scopes: set[str] = set()

        # Extract file paths from diff or files
        file_paths: list[str] = []
        if payload.get("files"):
            file_paths = [f.get("path", "") for f in payload["files"] if f.get("path")]

        # If diff provided but no files, parse it for paths
        if payload.get("diff") and not file_paths:
            from rulerepo_server.services.evaluation.diff_parser import (
                parse_unified_diff,
            )

            changes = parse_unified_diff(payload["diff"])
            file_paths = [c.path for c in changes]

        # Map file paths to scopes
        for path in file_paths:
            lang = detect_language(path)
            if lang:
                scopes.add(f"engineering/{lang}")

        # Add explicit scope if provided
        if payload.get("scope"):
            scope_val = payload["scope"]
            if isinstance(scope_val, list):
                scopes.update(scope_val)
            else:
                scopes.add(scope_val)

        return sorted(scopes)

    def get_prompt_fragments(self) -> dict[str, str]:
        """Return code-specific prompt fragments for the LLM judge.

        Returns:
            Dict with ``domain_intro`` and ``context_format`` placeholders.
        """
        return {
            "domain_intro": (
                "You are evaluating a software code change for compliance with "
                "engineering rules. The input is a unified diff showing the changes "
                "made to source code files."
            ),
            "context_format": (
                "The evaluation context includes:\n"
                "- A unified diff of the code changes\n"
                "- File paths affected\n"
                "- Programming languages detected\n"
                "- The developer's stated intent (if provided)"
            ),
        }
