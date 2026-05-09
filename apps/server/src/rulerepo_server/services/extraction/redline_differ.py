"""Redline differ — extracts revisions from old vs new document versions.

See CLAUDE.md §14.3.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class RedlineChange:
    """A single change between two document versions."""

    change_type: str  # "added", "removed", "modified"
    old_text: str = ""
    new_text: str = ""
    position: int = 0
    clause_type: str = ""


def compute_redline(
    old_text: str,
    new_text: str,
    *,
    context_lines: int = 3,
) -> list[RedlineChange]:
    """Compute redline changes between two document versions.

    Uses difflib to identify additions, removals, and modifications
    at the paragraph level.

    Args:
        old_text: The previous version of the document.
        new_text: The current version of the document.
        context_lines: Number of context lines around changes.

    Returns:
        List of RedlineChange objects.
    """
    old_paragraphs = [p.strip() for p in old_text.split("\n\n") if p.strip()]
    new_paragraphs = [p.strip() for p in new_text.split("\n\n") if p.strip()]

    changes: list[RedlineChange] = []
    matcher = difflib.SequenceMatcher(None, old_paragraphs, new_paragraphs)

    position = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            position += i2 - i1
            continue
        elif tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                old = old_paragraphs[i1 + k] if i1 + k < i2 else ""
                new = new_paragraphs[j1 + k] if j1 + k < j2 else ""
                changes.append(
                    RedlineChange(
                        change_type="modified",
                        old_text=old,
                        new_text=new,
                        position=position,
                    )
                )
                position += 1
        elif tag == "delete":
            for k in range(i1, i2):
                changes.append(
                    RedlineChange(
                        change_type="removed",
                        old_text=old_paragraphs[k],
                        position=position,
                    )
                )
                position += 1
        elif tag == "insert":
            for k in range(j1, j2):
                changes.append(
                    RedlineChange(
                        change_type="added",
                        new_text=new_paragraphs[k],
                        position=position,
                    )
                )
                position += 1

    return changes


def render_redline_html(changes: list[RedlineChange]) -> str:
    """Render redline changes as HTML with strikethrough/highlight markup."""
    parts = []
    parts.append("<div class='redline'>")
    for change in changes:
        if change.change_type == "removed":
            parts.append(f"<del style='color:red;text-decoration:line-through'>{change.old_text}</del>")
        elif change.change_type == "added":
            parts.append(f"<ins style='color:green;text-decoration:underline'>{change.new_text}</ins>")
        elif change.change_type == "modified":
            parts.append(f"<del style='color:red;text-decoration:line-through'>{change.old_text}</del>")
            parts.append(f"<ins style='color:green;text-decoration:underline'>{change.new_text}</ins>")
    parts.append("</div>")
    return "\n".join(parts)
