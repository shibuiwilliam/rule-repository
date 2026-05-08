"""SmartHR HRIS connector package.

Provides bidirectional integration with SmartHR for employee event
ingestion (attendance, overtime, leave requests, status changes) and
verdict/notification delivery.
"""

from packages.connectors.hris_smarthr.connector import SmartHRConnector

__all__ = ["SmartHRConnector"]
