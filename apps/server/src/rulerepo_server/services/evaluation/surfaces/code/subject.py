"""Code change subject — the unit of evaluation for the code surface.

See CLAUDE.md §14.2.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class CodeChange:
    """Subject representing a code change (diff, file set, or commit).

    Attributes:
        diff: Unified diff text.
        files: List of file descriptors with path and optional content.
        repository: Repository identifier.
        branch: Branch name.
        commit_sha: Commit hash if available.
        languages: Detected programming languages.
        facts: Additional structured facts (intent, scope context).
        description: Narrative description of the change.
        timestamp: When the change was created.
        locale: Locale of associated documentation (default "en").
    """

    diff: str = ""
    files: list[dict[str, str]] = field(default_factory=list)
    repository: str = ""
    branch: str = ""
    commit_sha: str = ""
    languages: list[str] = field(default_factory=list)
    facts: dict[str, object] = field(default_factory=dict)
    description: str = ""
    timestamp: datetime | None = None
    locale: str = "en"
