"""Norm Lineage service — walks the DERIVES_FROM chain in the rule graph.

See CLAUDE.md §14.4.
"""

from rulerepo_server.services.norm_lineage.walker import NormLineageWalker

__all__ = ["NormLineageWalker"]
