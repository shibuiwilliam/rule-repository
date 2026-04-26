"""Rule Formatter — converts raw rules into context-efficient text for LLM agents.

Per CLAUDE_ENHANCE.md §2.3: three output formats, all return plain text
because the consumer is an LLM agent that reads it as context.

- instructions: concise MUST/SHOULD/MAY hierarchy (~500 tokens for 15 rules)
- checklist: markdown checkbox list for PR review
- detailed: full rule metadata for deep understanding
"""

from __future__ import annotations

from typing import Any


def format_rules(
    rules: list[dict[str, Any]],
    *,
    format_type: str = "instructions",
    context_label: str = "your current context",
) -> str:
    """Format rules for agent consumption.

    Args:
        rules: List of rule dicts with id, statement, modality, severity, etc.
        format_type: "instructions", "checklist", or "detailed".
        context_label: Label describing what context these rules apply to.

    Returns:
        Formatted plain text optimized for LLM context injection.
    """
    if not rules:
        return f"No applicable rules found for {context_label}."

    match format_type:
        case "checklist":
            return _format_checklist(rules, context_label)
        case "detailed":
            return _format_detailed(rules, context_label)
        case _:
            return _format_instructions(rules, context_label)


def _format_instructions(rules: list[dict[str, Any]], label: str) -> str:
    """Concise MUST/SHOULD/MAY hierarchy — optimized for token efficiency.

    Each rule is one line with rule ID in brackets.
    Grouped by modality. Critical rules first.
    Target: <500 tokens for 15 rules.
    """
    groups: dict[str, list[dict[str, Any]]] = {
        "MUST": [],
        "MUST_NOT": [],
        "SHOULD": [],
        "MAY": [],
        "INFO": [],
    }
    for r in rules:
        modality = r.get("modality", "INFO")
        groups.setdefault(modality, []).append(r)

    lines: list[str] = [f"## Rules for {label}\n"]

    must_rules = groups.get("MUST", []) + groups.get("MUST_NOT", [])
    if must_rules:
        lines.append("### MUST (violations will block merge)")
        for r in must_rules:
            prefix = "Never:" if r.get("modality") == "MUST_NOT" else "-"
            lines.append(f"{prefix} {r['statement']} [Rule #{r['id'][:8]}]")
        lines.append("")

    should_rules = groups.get("SHOULD", [])
    if should_rules:
        lines.append("### SHOULD (best practice, flag if not followed)")
        for r in should_rules:
            lines.append(f"- {r['statement']} [Rule #{r['id'][:8]}]")
        lines.append("")

    may_rules = groups.get("MAY", []) + groups.get("INFO", [])
    if may_rules:
        lines.append("### MAY / INFO")
        for r in may_rules:
            lines.append(f"- {r['statement']} [Rule #{r['id'][:8]}]")

    return "\n".join(lines)


def _format_checklist(rules: list[dict[str, Any]], label: str) -> str:
    """Markdown checkbox list for PR review."""
    lines = [f"## Compliance Checklist — {label}\n"]
    for r in rules:
        severity_tag = f"[{r.get('severity', 'MEDIUM')}]"
        lines.append(f"- [ ] {r['statement']} {severity_tag} [Rule #{r['id'][:8]}]")
    return "\n".join(lines)


def _format_detailed(rules: list[dict[str, Any]], label: str) -> str:
    """Full rule metadata — for deep understanding."""
    lines = [f"## Detailed Rules — {label}\n"]
    for r in rules:
        lines.append(f"### Rule #{r['id'][:8]}: {r['statement'][:80]}")
        lines.append(f"- **Statement**: {r['statement']}")
        mod = r.get("modality", "?")
        sev = r.get("severity", "?")
        lines.append(f"- **Modality**: {mod} | **Severity**: {sev}")
        if r.get("rationale"):
            lines.append(f"- **Rationale**: {r['rationale']}")
        if r.get("scope"):
            scope_val = r["scope"]
            scope_str = ", ".join(scope_val) if isinstance(scope_val, list) else str(scope_val)
            lines.append(f"- **Scope**: {scope_str}")
        if r.get("tags"):
            tags = r["tags"] if isinstance(r["tags"], list) else [r["tags"]]
            lines.append(f"- **Tags**: {', '.join(tags)}")
        lines.append("")
    return "\n".join(lines)
