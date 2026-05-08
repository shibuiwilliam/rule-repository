"""Salesforce CRM connector package.

Provides bidirectional integration with Salesforce for CRM event
ingestion (opportunity updates, contract submissions, account changes)
and verdict/alert delivery.
"""

from packages.connectors.crm_salesforce.connector import SalesforceConnector

__all__ = ["SalesforceConnector"]
