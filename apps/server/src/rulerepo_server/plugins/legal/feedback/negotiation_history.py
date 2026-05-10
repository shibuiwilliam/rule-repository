"""Negotiation history feedback source — learns from clause negotiation outcomes.

Tracks contract evaluation outcomes (accepted/rejected clause modifications)
and suggests rule adjustments when patterns emerge. If a clause deviation
is consistently accepted, suggests relaxing the rule; if consistently
rejected, suggests tightening enforcement.

See: CLAUDE.md SS14.9, PROJECT.md SS6.4
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Threshold for suggesting rule adjustments
_ACCEPTANCE_THRESHOLD = 3
_REJECTION_THRESHOLD = 3


class NegotiationHistoryCapture:
    """Feedback source that captures negotiation outcomes.

    Maintains per-clause-type acceptance/rejection counts and generates
    rule adjustment suggestions when thresholds are exceeded.

    Attributes:
        _acceptance_counts: Per-clause-type count of accepted deviations.
        _rejection_counts: Per-clause-type count of rejected deviations.
        _evidence_log: Per-clause-type list of event summaries for evidence.
    """

    def __init__(self) -> None:
        self._acceptance_counts: dict[str, int] = defaultdict(int)
        self._rejection_counts: dict[str, int] = defaultdict(int)
        self._evidence_log: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def name(self) -> str:
        return "negotiation_history"

    @property
    def domain(self) -> str:
        return "legal"

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Capture a negotiation outcome event and return suggestions.

        Expected event schema:
            {
                "kind": "negotiation_outcome",
                "clause_type": str,
                "outcome": "accepted" | "rejected",
                "rule_id": str (optional),
                "deviation_description": str (optional),
                "contract_id": str (optional),
                "counterparty": str (optional),
                "timestamp": str (optional),
            }

        Args:
            event: Raw event data from the contract review workflow.

        Returns:
            List of rule adjustment suggestion dicts. Empty if no
            threshold has been crossed.
        """
        kind = event.get("kind")
        if kind != "negotiation_outcome":
            logger.debug("negotiation_history_skip_event", kind=kind)
            return []

        clause_type = event.get("clause_type")
        outcome = event.get("outcome")

        if not clause_type or outcome not in ("accepted", "rejected"):
            logger.warning(
                "negotiation_history_invalid_event",
                clause_type=clause_type,
                outcome=outcome,
            )
            return []

        # Record the event
        evidence_entry = {
            "rule_id": event.get("rule_id"),
            "deviation_description": event.get("deviation_description", ""),
            "contract_id": event.get("contract_id"),
            "counterparty": event.get("counterparty"),
            "timestamp": event.get("timestamp"),
            "outcome": outcome,
        }
        self._evidence_log[clause_type].append(evidence_entry)

        if outcome == "accepted":
            self._acceptance_counts[clause_type] += 1
        else:
            self._rejection_counts[clause_type] += 1

        logger.info(
            "negotiation_outcome_recorded",
            clause_type=clause_type,
            outcome=outcome,
            acceptance_count=self._acceptance_counts[clause_type],
            rejection_count=self._rejection_counts[clause_type],
        )

        # Check if any threshold is crossed
        suggestions: list[dict[str, Any]] = []

        acceptance_count = self._acceptance_counts[clause_type]
        rejection_count = self._rejection_counts[clause_type]

        if acceptance_count >= _ACCEPTANCE_THRESHOLD and acceptance_count == _ACCEPTANCE_THRESHOLD:
            # Threshold just crossed — suggest relaxing
            evidence = [e for e in self._evidence_log[clause_type] if e["outcome"] == "accepted"][
                -_ACCEPTANCE_THRESHOLD:
            ]
            suggestions.append(
                {
                    "type": "rule_adjustment",
                    "clause_type": clause_type,
                    "direction": "relax",
                    "reason": (
                        f"Clause type '{clause_type}' deviations have been accepted "
                        f"{acceptance_count} times. Consider relaxing the rule to "
                        f"reflect actual negotiation practice."
                    ),
                    "evidence": evidence,
                    "rule_id": event.get("rule_id"),
                    "suggested_modality": "SHOULD",
                }
            )

        if rejection_count >= _REJECTION_THRESHOLD and rejection_count == _REJECTION_THRESHOLD:
            # Threshold just crossed — suggest tightening
            evidence = [e for e in self._evidence_log[clause_type] if e["outcome"] == "rejected"][
                -_REJECTION_THRESHOLD:
            ]
            suggestions.append(
                {
                    "type": "rule_adjustment",
                    "clause_type": clause_type,
                    "direction": "tighten",
                    "reason": (
                        f"Clause type '{clause_type}' deviations have been rejected "
                        f"{rejection_count} times. Consider strengthening enforcement "
                        f"or increasing severity."
                    ),
                    "evidence": evidence,
                    "rule_id": event.get("rule_id"),
                    "suggested_modality": "MUST",
                }
            )

        if suggestions:
            logger.info(
                "negotiation_history_suggestion_generated",
                clause_type=clause_type,
                suggestion_count=len(suggestions),
            )

        return suggestions

    def get_statistics(self) -> dict[str, dict[str, int]]:
        """Return current acceptance/rejection statistics.

        Returns:
            Dict mapping clause_type to counts.
        """
        all_types = set(self._acceptance_counts.keys()) | set(self._rejection_counts.keys())
        return {
            clause_type: {
                "accepted": self._acceptance_counts[clause_type],
                "rejected": self._rejection_counts[clause_type],
            }
            for clause_type in sorted(all_types)
        }

    def reset(self) -> None:
        """Reset all counters and evidence logs."""
        self._acceptance_counts.clear()
        self._rejection_counts.clear()
        self._evidence_log.clear()
        logger.info("negotiation_history_reset")
