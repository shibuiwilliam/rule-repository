"""freee ERP connector package.

Provides bidirectional integration with freee accounting for financial
event ingestion (journal entries, expense claims, payment requests) and
approval/compliance flag delivery.
"""

from packages.connectors.erp_freee.connector import FreeeConnector

__all__ = ["FreeeConnector"]
