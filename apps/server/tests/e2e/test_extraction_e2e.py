"""E2E test: document extraction with real Gemini API.

Tests that the extraction pipeline produces meaningful rule candidates
from real policy/coding standard documents.

Requires: RULEREPO_LIVE_LLM=1, running docker-compose stack.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        __import__("os").environ.get("RULEREPO_LIVE_LLM") != "1",
        reason="E2E tests require RULEREPO_LIVE_LLM=1",
    ),
]


async def _upload_and_extract(client: httpx.AsyncClient, file_path: Path) -> tuple[str, list[dict]]:
    """Helper: upload a file and extract candidates."""
    with open(file_path, "rb") as f:
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": (file_path.name, f, "text/markdown")},
        )
    assert upload_resp.status_code in (200, 201)
    doc_id = upload_resp.json()["document_id"]

    extract_resp = await client.post(
        f"/api/v1/documents/{doc_id}/extract",
        timeout=180,
    )
    assert extract_resp.status_code == 200
    candidates = extract_resp.json().get("candidates", [])
    return doc_id, candidates


async def test_extract_python_style_guide(
    http_client: httpx.AsyncClient,
    coding_rules_dir: Path,
) -> None:
    """Extract rules from the Python Style Guide — should find type hint and naming rules."""
    _, candidates = await _upload_and_extract(http_client, coding_rules_dir / "01_python_style_guide.md")

    assert len(candidates) >= 5, f"Expected at least 5 rules, got {len(candidates)}"
    print(f"  Python Style Guide: {len(candidates)} candidates")

    statements = " ".join(c.get("statement", "") for c in candidates).lower()
    # The style guide has strong opinions on type hints and naming
    assert "type" in statements or "hint" in statements or "annotation" in statements, (
        "Expected candidates to mention type hints/annotations"
    )


async def test_extract_security_standards(
    http_client: httpx.AsyncClient,
    coding_rules_dir: Path,
) -> None:
    """Extract rules from Security Standards — should find OWASP/injection/auth rules."""
    _, candidates = await _upload_and_extract(http_client, coding_rules_dir / "08_security_standards.md")

    assert len(candidates) >= 5
    print(f"  Security Standards: {len(candidates)} candidates")

    modalities = {c.get("modality") for c in candidates}
    assert "MUST" in modalities or "MUST_NOT" in modalities, (
        f"Security standards should have MUST/MUST_NOT rules, got: {modalities}"
    )


async def test_extract_company_code_of_conduct(
    http_client: httpx.AsyncClient,
    company_rules_dir: Path,
) -> None:
    """Extract rules from the Code of Conduct — should find behavioral/ethics rules."""
    _, candidates = await _upload_and_extract(http_client, company_rules_dir / "01_code_of_conduct.md")

    assert len(candidates) >= 3
    print(f"  Code of Conduct: {len(candidates)} candidates")

    # Should detect various modalities
    modalities = {c.get("modality") for c in candidates}
    print(f"  Modalities: {modalities}")
    assert len(modalities) >= 2, "Expected multiple modality types in code of conduct"


async def test_extract_expense_policy(
    http_client: httpx.AsyncClient,
    company_rules_dir: Path,
) -> None:
    """Extract rules from the Expense & Travel Policy — should find approval thresholds."""
    _, candidates = await _upload_and_extract(http_client, company_rules_dir / "05_expense_and_travel_policy.md")

    assert len(candidates) >= 3
    print(f"  Expense Policy: {len(candidates)} candidates")

    statements = " ".join(c.get("statement", "") for c in candidates).lower()
    assert "approv" in statements or "expense" in statements or "travel" in statements, (
        "Expected candidates about approvals/expenses/travel"
    )


async def test_document_list_after_uploads(
    http_client: httpx.AsyncClient,
) -> None:
    """After previous tests uploaded documents, the list endpoint should return them."""
    resp = await http_client.get("/api/v1/documents?page=1&page_size=50")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0, "Expected at least one document after uploads"
    print(f"  Total documents: {data['total']}")

    # Verify document structure
    for doc in data["items"][:3]:
        assert "id" in doc
        assert "filename" in doc
        assert "mime_type" in doc
        assert "size_bytes" in doc
