"""Structured scope model for rules.

Extends the existing slash-separated ``scope`` string with a ``dimensions``
dictionary for multi-axis matching (jurisdiction, business unit, counterparty
type, confidentiality, etc.).

Search and selection support both: hierarchical match on ``path``, and
key-value match on ``dimensions``.

See IMPROVEMENT.md §4.5 / RR-040.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StructuredScope:
    """A structured scope combining hierarchical path with dimension axes.

    Args:
        path: Canonical hierarchical path (backwards compatible with the
            existing slash-separated format, e.g. ``engineering/python/api``).
        dimensions: Key-value pairs for multi-axis matching. Values can be
            single strings or lists of strings for multi-valued dimensions.
            Example::

                {
                    "jurisdiction": ["JP", "US"],
                    "business_unit": "consumer_finance",
                    "counterparty_type": "vendor",
                    "confidentiality": "restricted",
                }
    """

    path: str = ""
    dimensions: dict[str, str | list[str]] = field(default_factory=dict)


def matches_scope_dimensions(
    rule_scope: dict[str, str | list[str]],
    query_dimensions: dict[str, str | list[str]],
) -> bool:
    """Check if a rule's scope dimensions match a query's dimensions.

    A rule matches if for every dimension in the query, the rule's scope
    either:
    - Does not declare that dimension (wildcard match), or
    - Contains at least one overlapping value.

    Args:
        rule_scope: The rule's ``structured_scope.dimensions``.
        query_dimensions: The query's required dimensions.

    Returns:
        True if the rule's scope is compatible with the query dimensions.
    """
    for key, query_values in query_dimensions.items():
        if key not in rule_scope:
            # Rule doesn't restrict this dimension — matches everything
            continue

        rule_values = rule_scope[key]

        # Normalize to sets for comparison
        q_set = set(query_values) if isinstance(query_values, list) else {query_values}
        r_set = set(rule_values) if isinstance(rule_values, list) else {rule_values}

        # At least one value must overlap
        if not q_set & r_set:
            return False

    return True
