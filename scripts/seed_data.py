#!/usr/bin/env python3
"""Seed the database with sample rules for development and demo.

Usage:
    uv run python scripts/seed_data.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))

SAMPLE_RULES = [
    {
        "statement": "Monthly overtime must not exceed 45 hours per employee",
        "modality": "MUST_NOT",
        "severity": "HIGH",
        "scope": ["hr/attendance"],
        "tags": ["overtime", "labor-law", "article-36"],
        "rationale": "Required by Labor Standards Act Article 36 agreement",
    },
    {
        "statement": (
            "All production code changes must be reviewed by at least one peer before merging to the main branch"
        ),
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["engineering"],
        "tags": ["code-review", "ci-cd", "quality"],
        "rationale": "Prevents bugs and ensures knowledge sharing across the team",
    },
    {
        "statement": "Contract values exceeding $10,000 must be approved by the procurement department",
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["procurement", "contracts"],
        "tags": ["approval", "procurement", "contracts"],
        "rationale": "Financial controls require procurement oversight for significant expenditures",
    },
    {
        "statement": "Engineers should write unit tests for all public API functions",
        "modality": "SHOULD",
        "severity": "MEDIUM",
        "scope": ["engineering"],
        "tags": ["testing", "quality", "best-practice"],
        "rationale": "Unit tests catch regressions early and serve as documentation",
    },
    {
        "statement": "Customer PII must not be logged in application log files",
        "modality": "MUST_NOT",
        "severity": "CRITICAL",
        "scope": ["engineering", "security"],
        "tags": ["privacy", "pii", "compliance", "gdpr"],
        "rationale": "GDPR and privacy regulations prohibit storing PII in logs",
    },
    {
        "statement": "Teams may choose their own sprint cadence between 1 and 4 weeks",
        "modality": "MAY",
        "severity": "LOW",
        "scope": ["engineering"],
        "tags": ["agile", "process", "team-autonomy"],
        "rationale": "Teams should self-organize within reasonable bounds",
    },
    {
        "statement": "All API endpoints must return structured error responses with an error code and message",
        "modality": "MUST",
        "severity": "MEDIUM",
        "scope": ["engineering", "api"],
        "tags": ["api-design", "error-handling", "standards"],
        "rationale": "Consistent error handling improves client developer experience",
    },
    {
        "statement": "Employees should submit expense reports within 30 days of the expense",
        "modality": "SHOULD",
        "severity": "LOW",
        "scope": ["finance", "all-employees"],
        "tags": ["expenses", "finance", "policy"],
        "rationale": "Timely expense reporting ensures accurate financial records",
    },
    {
        "statement": "Database migrations must be backward-compatible with the previous schema version",
        "modality": "MUST",
        "severity": "HIGH",
        "scope": ["engineering", "database"],
        "tags": ["database", "migrations", "deployment"],
        "rationale": "Enables zero-downtime deployments with rolling updates",
    },
    {
        "statement": "For information: the company handbook is updated quarterly and available on the internal wiki",
        "modality": "INFO",
        "severity": "LOW",
        "scope": ["all-employees"],
        "tags": ["handbook", "information", "onboarding"],
        "rationale": "New employees should know where to find the handbook",
    },
]


async def main() -> None:
    import httpx

    server_url = os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000")

    async with httpx.AsyncClient(base_url=server_url, timeout=30) as client:
        # Check health
        resp = await client.get("/healthz")
        if resp.status_code != 200:
            print(f"Server not healthy: {resp.status_code}")
            return

        print(f"Seeding {len(SAMPLE_RULES)} rules to {server_url}...")

        for i, rule_data in enumerate(SAMPLE_RULES):
            resp = await client.post("/api/v1/rules", json=rule_data)
            if resp.status_code == 201:
                rule = resp.json()
                print(f"  [{i + 1}/{len(SAMPLE_RULES)}] Created: {rule['id'][:8]}... - {rule_data['statement'][:60]}")
            else:
                print(f"  [{i + 1}/{len(SAMPLE_RULES)}] Failed ({resp.status_code}): {rule_data['statement'][:60]}")

        print("Seed data loaded.")


if __name__ == "__main__":
    asyncio.run(main())
