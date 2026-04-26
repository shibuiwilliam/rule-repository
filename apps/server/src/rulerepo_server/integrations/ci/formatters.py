"""CI output formatters — text, json, github-actions, junit.

Per CLAUDE_ENHANCE.md §3.4: format evaluation results for various CI systems.
"""

from __future__ import annotations

import json
from typing import Any


def format_text(result: dict[str, Any]) -> str:
    """Human-readable terminal output."""
    verdict = result.get("overall_verdict", "?")
    violations = result.get("violations", [])
    warnings = result.get("warnings", [])

    lines = [f"Rule Repository Evaluation: {verdict}"]
    lines.append(f"Rules evaluated: {result.get('rules_evaluated', 0)}")
    lines.append("")

    if violations:
        lines.append(f"VIOLATIONS ({len(violations)}):")
        for v in violations:
            lines.append(f"  DENY: {v.get('rule_statement', v.get('rule_id'))}")
            if v.get("issue_description"):
                lines.append(f"    Issue: {v['issue_description']}")
            if v.get("fix_suggestion"):
                lines.append(f"    Fix: {v['fix_suggestion']}")

    if warnings:
        lines.append(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  CHECK: {w.get('rule_statement', w.get('rule_id'))}")

    if result.get("fix_summary"):
        lines.append(f"\n{result['fix_summary']}")

    return "\n".join(lines)


def format_json(result: dict[str, Any]) -> str:
    """Machine-readable JSON."""
    return json.dumps(result, indent=2, default=str)


def format_github_actions(result: dict[str, Any]) -> str:
    """GitHub Actions annotations for inline PR display.

    Uses ::error and ::warning annotations to show issues on specific lines.
    """
    lines: list[str] = []
    for v in result.get("violations", []):
        locations = v.get("locations", [])
        if locations:
            loc = locations[0]
            fp = loc.get("file_path", "")
            ln = loc.get("start_line", "")
            msg = v.get("issue_description", v.get("rule_statement", ""))
            lines.append(f"::error file={fp},line={ln}::{msg}")
        else:
            msg = v.get("issue_description", v.get("rule_statement", ""))
            lines.append(f"::error::{msg}")

    for w in result.get("warnings", []):
        msg = w.get("issue_description", w.get("rule_statement", ""))
        lines.append(f"::warning::{msg}")

    return "\n".join(lines)


def format_result(result: dict[str, Any], output_format: str) -> str:
    """Format an evaluation result in the requested format.

    Args:
        result: Evaluation result dict.
        output_format: "text", "json", "github-actions".

    Returns:
        Formatted output string.
    """
    match output_format:
        case "json":
            return format_json(result)
        case "github-actions":
            return format_github_actions(result)
        case _:
            return format_text(result)
