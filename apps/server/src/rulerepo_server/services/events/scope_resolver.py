"""Resolve event_type strings to scope sets for rule selection.

Convention: ``{department}.{action}.{noun}`` maps to scopes.
See CLAUDE.md §14.8.
"""

from __future__ import annotations

from rulerepo_server.core.logging import get_logger
from rulerepo_server.domain.business_event import DEFAULT_EVENT_SCOPE_MAP

logger = get_logger(__name__)


class EventScopeResolver:
    """Maps business event types to scope sets.

    Uses the default mapping from domain/business_event.py, with optional
    overrides from configuration.
    """

    def __init__(self, overrides: dict[str, list[str]] | None = None) -> None:
        self._map = {**DEFAULT_EVENT_SCOPE_MAP}
        if overrides:
            self._map.update(overrides)

    def resolve(self, event_type: str) -> list[str]:
        """Resolve an event_type to a list of scope strings.

        Falls back to deriving scopes from the event_type structure if no
        explicit mapping exists.

        Args:
            event_type: Dot-separated event name.

        Returns:
            List of scope strings for rule selection.
        """
        if event_type in self._map:
            return self._map[event_type]

        # Convention fallback: department.action.noun -> [department/action]
        parts = event_type.split(".")
        if len(parts) >= 2:
            scope = f"{parts[0]}/{parts[1]}"
            logger.info("event_scope_fallback", event_type=event_type, scope=scope)
            return [scope]

        logger.warning("event_scope_unresolved", event_type=event_type)
        return []
