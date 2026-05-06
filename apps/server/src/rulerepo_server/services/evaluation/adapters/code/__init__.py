"""Code evaluation domain adapter.

Handles software diffs, file changes, and language-aware scope resolution.
Wraps existing logic from the flat evaluation directory.
"""

from rulerepo_server.services.evaluation.adapters.code.adapter import CodeAdapter

__all__ = ["CodeAdapter"]
