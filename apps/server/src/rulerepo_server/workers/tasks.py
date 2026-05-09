"""On-demand async tasks for the arq worker.

Cron jobs are defined in settings.py. This module registers tasks
that are enqueued explicitly (e.g., from API handlers or webhooks).
"""

from __future__ import annotations

from rulerepo_server.workers.norm_lineage_propagation import (
    propagate_norm_amendment,
)

# Re-export so arq can discover the functions via this module.
__all__ = ["propagate_norm_amendment"]
