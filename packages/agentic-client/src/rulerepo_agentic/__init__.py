"""Agentic Rule Client — Phase 2 implementation.

This package wraps the Rule Client and adds AI-agent capabilities:
- Automatic context gathering
- Two-stage evaluation
- Result caching
- Reason graphs
- Repair suggestions
- Three integration modes: preflight, posthoc, sidecar
"""

from rulerepo_agentic.client import AgenticRuleClient

__all__ = ["AgenticRuleClient"]
