"""On-demand async tasks for the arq worker.

Cron jobs are defined in settings.py. This module is reserved for
tasks that are enqueued explicitly (e.g., from API handlers).
"""

from __future__ import annotations
