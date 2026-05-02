"""Domain model for autonomous agent governance.

Defines agent types, trust levels, and governance participation primitives.
See PROJECT_ENHANCE.md §Enhancement 2.
"""

from __future__ import annotations

import enum

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TrustLevel(str, enum.Enum):
    """Progressive trust levels earned through compliance history."""

    UNTRUSTED = "untrusted"
    LIMITED = "limited"
    STANDARD = "standard"
    ELEVATED = "elevated"
    AUTONOMOUS = "autonomous"


class AgentType(str, enum.Enum):
    """Classification of agent capabilities."""

    CODING_ASSISTANT = "coding_assistant"
    CODE_REVIEWER = "code_reviewer"
    SECURITY_SCANNER = "security_scanner"
    DEPLOYMENT_AGENT = "deployment_agent"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Trust level thresholds
# ---------------------------------------------------------------------------

TRUST_PROMOTION_THRESHOLDS: dict[TrustLevel, dict[str, object]] = {
    TrustLevel.LIMITED: {"min_days": 30, "min_compliance": 0.80},
    TrustLevel.STANDARD: {"min_days": 90, "min_compliance": 0.90},
    TrustLevel.ELEVATED: {"min_days": 180, "min_compliance": 0.95},
    TrustLevel.AUTONOMOUS: {"min_days": 365, "min_compliance": 0.98},
}

TRUST_DEMOTION_THRESHOLD = 0.70  # Drop trust level if compliance falls below this

MASTERY_CONSECUTIVE_PASSES = 50  # Consecutive ALLOW verdicts to mark mastery
MASTERY_REACTIVATION_WINDOW = 10  # Recent evals to check for violation after mastery
