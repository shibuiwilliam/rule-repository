"""Subject adapters — domain-specific evaluation logic per subject type.

Each adapter knows how to parse its payload, assemble evaluation context,
format prompts, and interpret remediations. The evaluation pipeline
dispatches to the correct adapter based on SubjectType.

See: IMPROVEMENT.md Phase 7b
"""

from rulerepo_server.subjects.base import SubjectAdapter
from rulerepo_server.subjects.registry import get_adapter, register_adapter

__all__ = ["SubjectAdapter", "get_adapter", "register_adapter"]
