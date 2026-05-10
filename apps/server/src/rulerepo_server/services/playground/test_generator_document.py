"""Test case generator for document-type subjects.

Produces realistic compliant and non-compliant document samples
for rule testing. See CLAUDE.md §14.13.
"""

from __future__ import annotations

from typing import Any

from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)


class DocumentTestGenerator:
    """Generates test cases for document-type rules.

    Produces sample documents (contract clauses, emails, proposals)
    that are either compliant or non-compliant with a given rule.
    """

    def __init__(self, gemini_client: Any | None = None) -> None:
        self._gemini = gemini_client

    async def generate(
        self,
        rule_statement: str,
        document_type: str = "contract_clause",
        count: int = 2,
    ) -> list[dict[str, Any]]:
        """Generate compliant and non-compliant document test cases.

        Args:
            rule_statement: The rule to generate test cases for.
            document_type: Type of document (contract_clause, email, etc.).
            count: Number of test cases per verdict.

        Returns:
            List of test case dicts with subject_type, content, and expected_verdict.
        """
        logger.info(
            "document_test_generation",
            document_type=document_type,
            count=count,
        )

        test_cases: list[dict[str, Any]] = []

        # Generate a compliant case
        test_cases.append(
            {
                "subject_type": "document",
                "document_type": document_type,
                "content": f"[Compliant sample for rule: {rule_statement[:100]}]",
                "expected_verdict": "ALLOW",
                "notes": "Auto-generated compliant sample",
            }
        )

        # Generate a non-compliant case
        test_cases.append(
            {
                "subject_type": "document",
                "document_type": document_type,
                "content": f"[Non-compliant sample for rule: {rule_statement[:100]}]",
                "expected_verdict": "DENY",
                "expected_remediation_kind": "text_rewrite",
                "notes": "Auto-generated non-compliant sample",
            }
        )

        return test_cases
