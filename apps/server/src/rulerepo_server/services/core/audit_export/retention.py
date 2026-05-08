"""Audit retention policies -- per-scope legal retention requirements.

Each scope (e.g. ``j-sox``, ``hipaa``, ``finance``) maps to a minimum
retention period in years and an optional regulatory citation. A legal
hold flag overrides retention-based deletion for any entry.

See CLAUDE.md section 11.4, IMPROVEMENT.md section 4.4 / RR-011.
"""

from __future__ import annotations

from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Regulatory retention requirements (years).
# Keys are matched case-insensitively against the scope string.
RETENTION_POLICIES: dict[str, int] = {
    "j-sox": 7,
    "sox": 7,
    "hipaa": 6,
    "gdpr": 6,
    "employment": 10,
    "finance": 7,
    "pci-dss": 7,
    "default": 5,
}


@dataclass(frozen=True)
class RetentionPolicy:
    """Describes the retention requirement for a given scope.

    Attributes:
        scope: The scope string that was matched.
        retention_years: Minimum number of years to retain audit entries.
        regulatory_citation: The regulation or standard driving the requirement.
        legal_hold: Whether entries are under legal hold (overrides deletion).
    """

    scope: str
    retention_years: int
    regulatory_citation: str = ""
    legal_hold: bool = False


def get_retention_policy(scope: str) -> RetentionPolicy:
    """Determine the retention policy for a given scope.

    Matches the scope string (case-insensitive) against known regulatory
    keys. Falls back to the default retention period when no match is found.

    Args:
        scope: The scope or regulatory label to look up.

    Returns:
        A ``RetentionPolicy`` describing the retention requirement.
    """
    scope_lower = scope.lower()
    for key, years in RETENTION_POLICIES.items():
        if key == "default":
            continue
        if key in scope_lower:
            logger.debug(
                "retention_policy_matched",
                scope=scope,
                matched_key=key,
                retention_years=years,
            )
            return RetentionPolicy(
                scope=scope,
                retention_years=years,
                regulatory_citation=key,
            )

    return RetentionPolicy(
        scope=scope,
        retention_years=RETENTION_POLICIES["default"],
        regulatory_citation="default",
    )


def check_legal_hold(entry_id: str) -> bool:
    """Check if an audit entry is under legal hold.

    Placeholder implementation. In production this would query the audit
    log for the ``_litigation_hold`` flag set by
    ``AuditLogRepository.set_litigation_hold``.

    Args:
        entry_id: The UUID of the audit entry to check.

    Returns:
        ``True`` if the entry is under legal hold, ``False`` otherwise.
    """
    # TODO: query AuditLogModel.details["_litigation_hold"] for entry_id
    return False
