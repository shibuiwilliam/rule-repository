"""Context assembler for CodeChangeSubject.

Extracts context from diffs, file paths, and repository metadata.
Delegates to the existing diff_parser and evaluation logic.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.domain.evaluation_subject import CodeChangeSubject


async def assemble_context(subject: CodeChangeSubject) -> dict[str, Any]:
    """Assemble evaluation context from a code change subject.

    This wraps the existing diff parsing and context assembly logic
    to work with the new EvaluationSubject abstraction.
    """
    context: dict[str, Any] = {
        "kind": "code_change",
        "diff": subject.diff,
        "files": subject.files,
        "repository": subject.repository,
    }
    if subject.actor_id:
        context["actor_id"] = subject.actor_id
    if subject.metadata:
        context["metadata"] = subject.metadata
    return context
