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
