"""Format EvaluationResult as GitHub PR review comment markdown.

Per CLAUDE_ENHANCE.md §3.3: converts verdicts to structured review
with per-rule citations, locations, and fix suggestions.
"""

from __future__ import annotations

from typing import Any


def format_review_comment(result: dict[str, Any]) -> str:
    """Convert an evaluation result dict to a GitHub review comment.

    Args:
        result: EvaluationResult-compatible dict (from the evaluate API).

    Returns:
        Markdown-formatted review comment.
    """
    overall = result.get("overall_verdict", "ALLOW")
    violations = result.get("violations", [])
    warnings = result.get("warnings", [])

    if overall == "ALLOW" and not violations and not warnings:
        return "**Rule Repository**: All applicable rules pass. :white_check_mark:"

    lines: list[str] = []

    # Header
    v_count = len(violations)
    w_count = len(warnings)
    parts = []
    if v_count:
        parts.append(f"{v_count} violation(s)")
    if w_count:
        parts.append(f"{w_count} suggestion(s)")
    lines.append(f"**Rule Repository**: {', '.join(parts)} found\n")

    # Violations
    for v in violations:
        lines.append(f"### :x: DENY — {v.get('rule_statement', v.get('rule_id', '?'))}")
        locations = v.get("locations", [])
        if locations:
            loc = locations[0]
            loc_str = loc.get("file_path", "?")
            if loc.get("start_line"):
                loc_str += f":{loc['start_line']}"
            lines.append(f":round_pushpin: `{loc_str}`")
        if v.get("issue_description"):
            lines.append(f"**Issue**: {v['issue_description']}")
        if v.get("fix_suggestion"):
            lines.append(f"**Fix**: {v['fix_suggestion']}")
        lines.append("")

    # Warnings
    for w in warnings:
        lines.append(f"### :warning: SUGGESTION — {w.get('rule_statement', w.get('rule_id', '?'))}")
        if w.get("issue_description"):
            lines.append(w["issue_description"])
        lines.append("")

    return "\n".join(lines)
