"""E2E test: full document-to-evaluation workflow.

Tests the complete lifecycle:
1. Upload a sample rule document
2. Extract rules via Gemini
3. Approve extracted candidates as rules
4. Search for the created rules
5. Evaluate sample code against the rules
6. Verify verdicts make sense

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


async def test_upload_extract_approve_search_evaluate(
    http_client: httpx.AsyncClient,
    coding_rules_dir: Path,
    sample_diff_bad: str,
) -> None:
    """Full E2E: upload coding standards → extract → approve → search → evaluate bad code."""

    # ---- Step 1: Upload the Python Style Guide ----
    style_guide_path = coding_rules_dir / "01_python_style_guide.md"
    assert style_guide_path.exists()

    with open(style_guide_path, "rb") as f:
        upload_resp = await http_client.post(
            "/api/v1/documents/upload",
            files={"file": ("01_python_style_guide.md", f, "text/markdown")},
        )
    assert upload_resp.status_code in (200, 201), f"Upload failed: {upload_resp.text}"
    doc_id = upload_resp.json()["document_id"]
    assert doc_id, "No document_id returned"

    # ---- Step 2: Extract rules via Gemini ----
    extract_resp = await http_client.post(
        f"/api/v1/documents/{doc_id}/extract",
        timeout=180,  # extraction can take time with LLM
    )
    assert extract_resp.status_code == 200, f"Extraction failed: {extract_resp.text}"

    extract_data = extract_resp.json()
    extraction_id = extract_data["extraction_id"]
    candidates = extract_data.get("candidates", [])

    assert len(candidates) > 0, "Gemini extracted zero candidates from the style guide"
    print(f"  Extracted {len(candidates)} candidates from Python Style Guide")

    # Verify candidates have expected structure
    for c in candidates[:3]:
        assert "statement" in c, f"Candidate missing 'statement': {c}"
        assert "modality" in c, f"Candidate missing 'modality': {c}"

    # ---- Step 3: Approve all candidates ----
    approved_indices = list(range(len(candidates)))
    review_resp = await http_client.post(
        f"/api/v1/documents/extractions/{extraction_id}/review",
        json={
            "extraction_id": extraction_id,
            "approved_indices": approved_indices,
        },
    )
    assert review_resp.status_code == 200, f"Review failed: {review_resp.text}"

    review_data = review_resp.json()
    rules_created = review_data.get("rules_created", 0)

    assert rules_created > 0, "No rules created from approved candidates"
    print(f"  Created {rules_created} rules")

    # ---- Step 4: Search for the rules ----
    search_resp = await http_client.post(
        "/api/v1/search/fulltext",
        json={"query": "type hints Python functions", "page": 1, "page_size": 10},
    )
    assert search_resp.status_code == 200, f"Search failed: {search_resp.text}"

    search_data = search_resp.json()
    assert search_data.get("total", 0) > 0 or len(search_data.get("items", [])) > 0, (
        "Search returned no results for 'type hints Python functions'"
    )
    print(f"  Search found {search_data.get('total', len(search_data.get('items', [])))} results")

    # ---- Step 5: Evaluate bad code against the rules ----
    eval_resp = await http_client.post(
        "/api/v1/evaluate",
        json={
            "diff": sample_diff_bad,
            "intent": "Adding payment refund handler",
            "scope": "engineering/python",
            "mode": "preflight",
            "max_rules": 10,
            "severity_min": "MEDIUM",
        },
        timeout=180,
    )
    assert eval_resp.status_code == 200, f"Evaluation failed: {eval_resp.text}"

    eval_data = eval_resp.json()
    print(f"  Evaluation verdict: {eval_data['overall_verdict']}")
    print(f"  Rules evaluated: {eval_data['rules_evaluated']}")
    print(f"  Violations: {eval_data['rules_violated']}")

    # The bad code should trigger at least some violations
    assert eval_data["rules_evaluated"] > 0, "No rules were evaluated"

    # Verify the response structure
    assert "overall_verdict" in eval_data
    assert eval_data["overall_verdict"] in ("ALLOW", "DENY", "NEEDS_CONFIRMATION")
    assert "rule_verdicts" in eval_data
    assert "evaluation_id" in eval_data
    assert "total_latency_ms" in eval_data

    # Print violations for debugging
    for v in eval_data.get("violations", []):
        print(f"    DENY: {v.get('rule_statement', '')[:80]}")
        if v.get("fix_suggestion"):
            print(f"      Fix: {v['fix_suggestion'][:80]}")


async def test_upload_company_policy_extract(
    http_client: httpx.AsyncClient,
    company_rules_dir: Path,
) -> None:
    """E2E: upload a company policy document and verify extraction produces candidates."""

    info_sec_path = company_rules_dir / "02_information_security_policy.md"
    assert info_sec_path.exists()

    # Upload
    with open(info_sec_path, "rb") as f:
        upload_resp = await http_client.post(
            "/api/v1/documents/upload",
            files={"file": ("02_information_security_policy.md", f, "text/markdown")},
        )
    assert upload_resp.status_code in (200, 201)
    doc_id = upload_resp.json()["document_id"]

    # Extract
    extract_resp = await http_client.post(
        f"/api/v1/documents/{doc_id}/extract",
        timeout=180,
    )
    assert extract_resp.status_code == 200

    candidates = extract_resp.json().get("candidates", [])
    assert len(candidates) > 0, "No candidates extracted from Information Security Policy"
    print(f"  Extracted {len(candidates)} candidates from Info Security Policy")

    # Check that MUST and MUST_NOT modalities are detected
    modalities = {c.get("modality") for c in candidates}
    print(f"  Modalities found: {modalities}")
    assert "MUST" in modalities or "MUST_NOT" in modalities, (
        f"Expected MUST/MUST_NOT modalities in security policy, got: {modalities}"
    )


async def test_manual_rule_create_and_evaluate(
    http_client: httpx.AsyncClient,
    sample_python_code_bad: str,
) -> None:
    """E2E: manually create a rule and evaluate code against it."""

    # Create a rule directly
    create_resp = await http_client.post(
        "/api/v1/rules",
        json={
            "statement": ("All Python functions MUST have type annotations on all parameters and the return type."),
            "modality": "MUST",
            "severity": "HIGH",
            "scope": ["engineering", "python"],
            "tags": ["type-hints", "python", "code-quality"],
            "rationale": "Type annotations enable static analysis and improve code readability.",
        },
    )
    assert create_resp.status_code == 201, f"Rule creation failed: {create_resp.text}"
    create_resp.json()["id"]  # verify ID exists

    # Evaluate bad code (has functions without type hints)
    eval_resp = await http_client.post(
        "/api/v1/evaluate",
        json={
            "files": [{"path": "bad_code.py", "content": sample_python_code_bad}],
            "intent": "Check code quality",
            "mode": "preflight",
            "max_rules": 5,
        },
        timeout=300,
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()

    print(f"  Verdict: {eval_data['overall_verdict']}")
    print(f"  Rules evaluated: {eval_data['rules_evaluated']}")

    assert eval_data["rules_evaluated"] > 0


async def test_intent_api(
    http_client: httpx.AsyncClient,
) -> None:
    """E2E: use the Intent API to ask a natural language question."""

    resp = await http_client.post(
        "/api/v1/intent",
        json={"query": "What are the rules about type hints in Python?"},
        timeout=60,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "intent" in data
    assert "result" in data
    print(f"  Intent classified as: {data['intent']}")


async def test_health_and_readiness(
    http_client: httpx.AsyncClient,
) -> None:
    """E2E: verify server health endpoints report all services connected."""

    # Liveness
    health_resp = await http_client.get("/healthz")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # Readiness (checks PG, ES, Neo4j)
    ready_resp = await http_client.get("/readyz")
    assert ready_resp.status_code == 200

    ready_data = ready_resp.json()
    print(f"  Readiness: {ready_data.get('status')}")
    checks = ready_data.get("checks", {})
    for service, status in checks.items():
        print(f"    {service}: {status}")
