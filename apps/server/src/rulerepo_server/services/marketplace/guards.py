"""Marketplace publication guards (RR-030).

Before a rule set can be published to the marketplace, it must pass:
1. Visibility check -- only explicitly public rules
2. Content scan -- no PII, secrets, or offensive content
3. Two-step confirmation -- draft -> confirm publish
4. Role check -- requires marketplace_publisher role
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PublicationCheck:
    """Result of marketplace publication eligibility checks.

    Attributes:
        passed: True if all checks passed and publication can proceed.
        checks: Map of check name to pass/fail status.
        blockers: Human-readable descriptions of failing checks.
    """

    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)


def check_publication_eligibility(
    rules: list[dict[str, Any]],
    publisher_roles: list[str],
) -> PublicationCheck:
    """Verify all guards before marketplace publication.

    Runs four checks in sequence:
    1. **Role check** -- publisher must have ``marketplace_publisher``
       or ``admin`` role.
    2. **Visibility check** -- every rule must be explicitly marked
       as public or ``public_marketplace``.
    3. **Content scan** -- no PII detected in rule statements
       (delegates to ``core.pii.redactor.detect_pii``).
    4. **Minimum quality** -- every rule must include a non-empty
       rationale.

    Args:
        rules: List of rule dicts to publish.
        publisher_roles: Roles assigned to the publishing user.

    Returns:
        A :class:`PublicationCheck` with results and any blockers.
    """
    checks: dict[str, bool] = {}
    blockers: list[str] = []

    # 1. Role check
    has_role = "marketplace_publisher" in publisher_roles or "admin" in publisher_roles
    checks["publisher_role"] = has_role
    if not has_role:
        blockers.append("Publisher lacks marketplace_publisher role")

    # 2. Visibility check
    all_public = all(
        r.get("classification", "internal") in ("public", "PUBLIC")
        or r.get("visibility", "tenant") == "public_marketplace"
        for r in rules
    )
    checks["visibility"] = all_public
    if not all_public:
        blockers.append("Some rules are not marked as public")

    # 3. Content scan (PII detection)
    from rulerepo_server.core.pii.redactor import detect_pii

    has_pii = False
    for rule in rules:
        facts = {"statement": rule.get("statement", "")}
        if detect_pii(facts):
            has_pii = True
            break
    checks["no_pii"] = not has_pii
    if has_pii:
        blockers.append("PII detected in rule statements")

    # 4. Minimum quality -- rationale required
    has_rationale = all(r.get("rationale", "").strip() for r in rules)
    checks["has_rationale"] = has_rationale
    if not has_rationale:
        blockers.append("Some rules are missing rationale")

    passed = len(blockers) == 0

    logger.info(
        "marketplace_publication_check",
        passed=passed,
        checks=checks,
        blocker_count=len(blockers),
    )

    return PublicationCheck(
        passed=passed,
        checks=checks,
        blockers=blockers,
    )
