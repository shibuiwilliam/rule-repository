"""MCP prompt templates — structured workflows for agent interactions."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all MCP prompts on the server."""

    @mcp.prompt()
    def compliance_check(context: str, action: str) -> str:
        """Structured compliance evaluation workflow.

        Use this prompt to systematically check whether an action
        complies with organizational rules.
        """
        return f"""Evaluate the following action for compliance with organizational rules.

Context: {context}
Intended Action: {action}

Steps:
1. Use search_rules to find all rules applicable to this context and action.
2. For each relevant rule, assess whether the action complies.
3. If any rule is violated, explain which rule, why it's violated, and suggest a fix.
4. If compliance is unclear, explain the ambiguity and what additional information is needed.
5. Summarize with a verdict: ALLOW, DENY, or NEEDS_CONFIRMATION."""

    @mcp.prompt()
    def rule_summary(scope: str) -> str:
        """Generate an executive summary of rules in a given scope.

        Use this to get a quick overview of all rules that apply to
        a specific area of the organization.
        """
        return f"""Generate a concise executive summary of all rules in the scope: {scope}

Steps:
1. Use search_rules with scope="{scope}" to find all applicable rules.
2. Group rules by modality (MUST, MUST_NOT, SHOULD, MAY, INFO).
3. For each group, list the key obligations in plain language.
4. Highlight any rules with CRITICAL severity.
5. Note any known conflicts between rules."""

    @mcp.prompt()
    def impact_analysis(rule_id: str, proposed_change: str) -> str:
        """Assess the impact of a proposed rule change.

        Use this when modifying or retiring a rule to understand
        what systems and processes would be affected.
        """
        return f"""Analyze the impact of changing rule {rule_id}.

Proposed change: {proposed_change}

Steps:
1. Use explain_rule to understand the current rule, its rationale, and relationships.
2. Use find_conflicts to check if the proposed change conflicts with other rules.
3. Use search_rules to find rules that depend on or refine this rule.
4. Assess the risk: how many systems/processes rely on this rule?
5. Recommend whether to proceed, with any necessary mitigations."""
