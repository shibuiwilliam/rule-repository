"""Structured scope model for rules.

Extends the existing slash-separated ``scope`` string with a ``dimensions``
dictionary for multi-axis matching (jurisdiction, business unit, counterparty
type, confidentiality, etc.).

The three primary axes — ``domain``, ``org_unit``, and ``subject_type`` — are
stored as dedicated keys inside ``dimensions`` so that indexing and filtering
can target them efficiently (e.g. Elasticsearch keyword fields, GIN indexes
on JSONB).  Additional ad-hoc attributes live alongside them in the same dict.

Search and selection support both: hierarchical match on ``path``, and
key-value match on ``dimensions``.

See IMPROVEMENT.md §2.2, §3 Proposal 2 / RR-040.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Keys for the three primary scope axes.  These are ordinary dimension keys
# that happen to receive special treatment in indexing and selection.
DOMAIN_KEY = "domain"
ORG_UNIT_KEY = "org_unit"
SUBJECT_TYPE_KEY = "subject_type"

_PRIMARY_KEYS = frozenset({DOMAIN_KEY, ORG_UNIT_KEY, SUBJECT_TYPE_KEY})


@dataclass(frozen=True)
class StructuredScope:
    """A structured scope combining hierarchical path with dimension axes.

    Args:
        path: Canonical hierarchical path (backwards compatible with the
            existing slash-separated format, e.g. ``engineering/python/api``).
        dimensions: Key-value pairs for multi-axis matching. Values can be
            single strings or lists of strings for multi-valued dimensions.

            Three keys receive first-class treatment:

            * ``domain`` — business domain (``legal``, ``hr``, ``finance``,
              ``sales``, ``engineering``, …).
            * ``org_unit`` — organizational hierarchy path
              (``acme/jp/sales``).
            * ``subject_type`` — what the rule evaluates (``contract``,
              ``expense``, ``code_file``, ``employee``, …).

            Any other keys are treated as generic attributes (e.g.
            ``jurisdiction``, ``role``, ``confidentiality``).

            Example::

                {
                    "domain": "finance",
                    "org_unit": "acme/us",
                    "subject_type": "expense",
                    "jurisdiction": ["JP", "US"],
                    "role": "manager",
                    "confidentiality": "restricted",
                }
    """

    path: str = ""
    dimensions: dict[str, str | list[str]] = field(default_factory=dict)

    # -- Convenience accessors for the primary axes ----------------------------

    @property
    def domain(self) -> str | None:
        """Business domain (``legal``, ``hr``, ``finance``, …) or ``None``."""
        v = self.dimensions.get(DOMAIN_KEY)
        if isinstance(v, list):
            return v[0] if v else None
        return v

    @property
    def org_unit(self) -> str | None:
        """Organizational unit path (``acme/jp/sales``) or ``None``."""
        v = self.dimensions.get(ORG_UNIT_KEY)
        if isinstance(v, list):
            return v[0] if v else None
        return v

    @property
    def subject_type(self) -> str | None:
        """Subject type (``contract``, ``expense``, ``code_file``, …) or ``None``."""
        v = self.dimensions.get(SUBJECT_TYPE_KEY)
        if isinstance(v, list):
            return v[0] if v else None
        return v

    @property
    def attributes(self) -> dict[str, str | list[str]]:
        """All non-primary dimension key-value pairs."""
        return {k: v for k, v in self.dimensions.items() if k not in _PRIMARY_KEYS}

    # -- Factory ---------------------------------------------------------------

    @classmethod
    def from_legacy(cls, scope_parts: list[str]) -> StructuredScope:
        """Build a ``StructuredScope`` from a legacy slash-separated scope list.

        Heuristic: the first segment is treated as the ``domain``, the rest as
        ``subject_type``.  For example ``["engineering", "python"]`` becomes
        ``{domain: "engineering", subject_type: "python"}``.

        Args:
            scope_parts: Legacy scope tokens (e.g. ``["engineering", "python"]``).

        Returns:
            A new ``StructuredScope`` with the legacy path preserved.
        """
        if not scope_parts:
            return cls()
        path = "/".join(scope_parts)
        dims: dict[str, str | list[str]] = {DOMAIN_KEY: scope_parts[0]}
        if len(scope_parts) > 1:
            dims[SUBJECT_TYPE_KEY] = scope_parts[1]
        return cls(path=path, dimensions=dims)

    def to_es_fields(self) -> dict[str, str | list[str] | dict[str, str | list[str]] | None]:
        """Return a flat dict suitable for Elasticsearch indexing.

        Returns:
            Dict with ``scope_domain``, ``scope_org_unit``,
            ``scope_subject_type``, and ``scope_dimensions`` keys.
        """
        return {
            "scope_domain": self.domain,
            "scope_org_unit": self.org_unit,
            "scope_subject_type": self.subject_type,
            "scope_dimensions": self.dimensions,
        }


@dataclass(frozen=True)
class Scope:
    """Multi-axis structured scope per PROJECT.md §6.2.

    Matching semantics: a rule's scope matches a request's scope when:
    - domain is equal (or rule's domain is None = global)
    - org_unit is None or is an ancestor of request's org_unit
    - subject_type is None or equals request's subject_type
    - every attribute key in rule's attributes is present and equal in request's attributes
    """

    domain: str | None = None
    org_unit: str | None = None
    subject_type: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)

    def matches(self, request_scope: Scope) -> bool:
        """Check if this rule scope matches a request scope."""
        if self.domain is not None and self.domain != request_scope.domain:
            return False
        if self.org_unit is not None:
            if request_scope.org_unit is None:
                return False
            if request_scope.org_unit != self.org_unit and not request_scope.org_unit.startswith(self.org_unit + "/"):
                return False
        if self.subject_type is not None and self.subject_type != request_scope.subject_type:
            return False
        return all(request_scope.attributes.get(key) == value for key, value in self.attributes.items())

    @classmethod
    def from_legacy_string(cls, scope_str: str) -> Scope:
        """Normalize a legacy slash-separated scope string.

        E.g., ``"engineering/python"`` -> ``Scope(domain="engineering", subject_type="python_source")``
        """
        if not scope_str:
            return cls()
        parts = scope_str.strip("/").split("/")
        domain = parts[0] if parts else None
        subject_type = None
        if len(parts) > 1:
            subject_type = parts[1]
            # Normalize common engineering subject types
            if subject_type in ("python", "py"):
                subject_type = "python_source"
            elif subject_type in ("typescript", "ts"):
                subject_type = "typescript_source"
            elif subject_type in ("react",):
                subject_type = "react_component"
        return cls(domain=domain, subject_type=subject_type)

    def to_dict(self) -> dict[str, object]:
        """Serialize to a dict suitable for JSONB storage."""
        result: dict[str, object] = {}
        if self.domain is not None:
            result["domain"] = self.domain
        if self.org_unit is not None:
            result["org_unit"] = self.org_unit
        if self.subject_type is not None:
            result["subject_type"] = self.subject_type
        if self.attributes:
            result["attributes"] = self.attributes
        return result

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Scope:
        """Deserialize from a JSONB dict."""
        return cls(
            domain=data.get("domain"),  # type: ignore[arg-type]
            org_unit=data.get("org_unit"),  # type: ignore[arg-type]
            subject_type=data.get("subject_type"),  # type: ignore[arg-type]
            attributes=data.get("attributes", {}),  # type: ignore[arg-type]
        )


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
