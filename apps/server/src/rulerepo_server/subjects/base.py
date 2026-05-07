"""SubjectAdapter protocol — re-exported from domain.subject for convenience.

The canonical SubjectAdapter protocol is defined in domain/subject.py.
This module exists for backward compatibility with imports from subjects.base.
"""

from __future__ import annotations

from rulerepo_server.domain.subject import SubjectAdapter

__all__ = ["SubjectAdapter"]
