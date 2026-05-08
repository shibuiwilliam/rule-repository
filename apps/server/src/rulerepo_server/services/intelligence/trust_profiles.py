"""Human trust profiles — track how much users trust automated verdicts (RR-037).

Monitors override patterns: when humans override LLM verdicts, the
system learns which rule x user combinations need human review vs
which can be auto-enforced.

See IMPROVEMENT.md §9.3.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrustProfile:
    """A user's trust profile for a specific domain/scope."""

    user_id: str
    domain: str
    total_verdicts: int = 0
    accepted: int = 0
    overridden: int = 0
    acceptance_rate: float = 1.0
    trust_level: str = "standard"  # "auto", "standard", "review_required"


class TrustProfileService:
    """Tracks user-verdict interaction patterns to build trust profiles."""

    def __init__(self) -> None:
        # key: (user_id, domain) -> {accepted: int, overridden: int}
        self._records: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"accepted": 0, "overridden": 0})

    def record_acceptance(self, user_id: str, domain: str) -> None:
        """Record that a user accepted an LLM verdict."""
        self._records[(user_id, domain)]["accepted"] += 1
        logger.debug("trust_acceptance", user_id=user_id, domain=domain)

    def record_override(self, user_id: str, domain: str) -> None:
        """Record that a user overrode an LLM verdict."""
        self._records[(user_id, domain)]["overridden"] += 1
        logger.info("trust_override", user_id=user_id, domain=domain)

    def get_profile(self, user_id: str, domain: str) -> TrustProfile:
        """Get or compute a trust profile for a user in a domain."""
        data = self._records.get((user_id, domain), {"accepted": 0, "overridden": 0})
        total = data["accepted"] + data["overridden"]

        if total == 0:
            return TrustProfile(
                user_id=user_id,
                domain=domain,
                trust_level="standard",
            )

        rate = data["accepted"] / total

        if rate >= 0.95 and total >= 20:
            level = "auto"
        elif rate < 0.70:
            level = "review_required"
        else:
            level = "standard"

        return TrustProfile(
            user_id=user_id,
            domain=domain,
            total_verdicts=total,
            accepted=data["accepted"],
            overridden=data["overridden"],
            acceptance_rate=round(rate, 3),
            trust_level=level,
        )

    def get_all_profiles(self, user_id: str) -> list[TrustProfile]:
        """Get trust profiles across all domains for a user."""
        domains = {domain for uid, domain in self._records if uid == user_id}
        return [self.get_profile(user_id, d) for d in sorted(domains)]
