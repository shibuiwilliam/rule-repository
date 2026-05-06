"""Adapter registry for evaluation domain adapters.

Provides a central mapping from domain name to adapter instance.
"""

from __future__ import annotations

from rulerepo_server.services.evaluation.adapters.base import EvaluationDomainAdapter
from rulerepo_server.services.evaluation.adapters.business_event.adapter import (
    BusinessEventAdapter,
)
from rulerepo_server.services.evaluation.adapters.code.adapter import CodeAdapter
from rulerepo_server.services.evaluation.adapters.document_diff.adapter import (
    DocumentDiffAdapter,
)
from rulerepo_server.services.evaluation.adapters.documentation.adapter import (
    DocumentationAdapter,
)

ADAPTERS: dict[str, EvaluationDomainAdapter] = {
    "code": CodeAdapter(),
    "business_event": BusinessEventAdapter(),
    "document_diff": DocumentDiffAdapter(),
    "documentation": DocumentationAdapter(),
}


def get_adapter(domain: str) -> EvaluationDomainAdapter:
    """Get the evaluation domain adapter for the given domain.

    Args:
        domain: Domain name (e.g., "code", "business_event").

    Returns:
        The corresponding adapter instance.

    Raises:
        KeyError: If no adapter is registered for the given domain.
    """
    if domain not in ADAPTERS:
        available = ", ".join(sorted(ADAPTERS.keys()))
        msg = f"Unknown evaluation domain '{domain}'. Available: {available}"
        raise KeyError(msg)
    return ADAPTERS[domain]
