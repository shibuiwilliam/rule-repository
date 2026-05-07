"""Subject adapters — domain-specific evaluation logic per subject kind.

Each adapter knows how to parse its payload, assemble evaluation context,
format prompts, and interpret remediations. The evaluation pipeline
dispatches to the correct adapter via the SubjectKind registry.

See: PROJECT.md §5.2, CLAUDE.md §11
"""

from rulerepo_server.domain.subject import SubjectAdapter, SubjectKind
from rulerepo_server.subjects.registry import (
    UnsupportedSubjectKindError,
    get_adapter,
    register,
    register_adapter,
    resolve,
)

__all__ = [
    "SubjectAdapter",
    "SubjectKind",
    "UnsupportedSubjectKindError",
    "get_adapter",
    "register",
    "register_adapter",
    "resolve",
]
