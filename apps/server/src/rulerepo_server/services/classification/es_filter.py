"""Elasticsearch document-level security filters for classification.

Every search query must include a classification filter derived from the
user's clearance and department membership. This filter is injected by
the search service and must not be bypassed.

See CLAUDE.md section 14.3 and ADR 0003.
"""

from __future__ import annotations

from rulerepo_server.core.db_context import AuthenticatedUser
from rulerepo_server.domain.classification import Classification


def classification_filter(user: AuthenticatedUser) -> dict:
    """Build an Elasticsearch bool query that enforces classification access.

    The returned filter should be combined (AND) with any other search
    filters in the query.

    Args:
        user: The authenticated user with clearance and department info.

    Returns:
        An ES bool query dict that restricts results by classification.
    """
    should_clauses: list[dict] = []

    # PUBLIC: always visible to authenticated users
    should_clauses.append({"term": {"classification": "public"}})

    # INTERNAL: visible to any authenticated org member
    should_clauses.append({"term": {"classification": "internal"}})

    # CONFIDENTIAL: visible if user has confidential or restricted clearance
    if user.clearance in (Classification.CONFIDENTIAL, Classification.RESTRICTED):
        confidential_clause: dict = {"term": {"classification": "confidential"}}
        # If the user has department membership, prefer department-scoped access.
        # If the ES index has an owner_department_id field, add a terms filter.
        if user.department_ids:
            confidential_clause = {
                "bool": {
                    "must": [
                        {"term": {"classification": "confidential"}},
                        {"terms": {"owner_department_id": user.department_ids}},
                    ]
                }
            }
        should_clauses.append(confidential_clause)

    # RESTRICTED: visible only if user has restricted clearance
    if user.clearance == Classification.RESTRICTED:
        restricted_clause: dict = {"term": {"classification": "restricted"}}
        if user.department_ids:
            restricted_clause = {
                "bool": {
                    "must": [
                        {"term": {"classification": "restricted"}},
                        {"terms": {"owner_department_id": user.department_ids}},
                    ]
                }
            }
        should_clauses.append(restricted_clause)

    return {
        "bool": {
            "should": should_clauses,
            "minimum_should_match": 1,
        }
    }
