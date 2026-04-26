"""Policy engine — matches incoming events to enforcement policies.

Per CLAUDE_ENHANCE.md §3.4: uses fnmatch for event_type_pattern matching.
Policies are matched in-memory (there will be <1000 policies in any deployment).
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any

from rulerepo_server.core.logging import get_logger
from rulerepo_server.gateway.schemas import NormalizedEvent

logger = get_logger(__name__)


def match_policies(
    event: NormalizedEvent,
    policies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Find all enabled policies that match an incoming event.

    Args:
        event: The normalized event to match against.
        policies: List of policy dicts (from database).

    Returns:
        List of matching policy dicts.
    """
    matched = []
    for policy in policies:
        if not policy.get("enabled", True):
            continue
        if policy.get("event_source") != event.source:
            continue
        pattern = policy.get("event_type_pattern", "*")
        if fnmatch(event.event_type, pattern):
            matched.append(policy)

    logger.info(
        "policies_matched",
        event_source=event.source,
        event_type=event.event_type,
        matched_count=len(matched),
    )
    return matched
