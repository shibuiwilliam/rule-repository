#!/usr/bin/env python3
"""Seed the database with sample rules for development and demo.

Loads inline sample rules via POST /api/v1/rules, then loads all YAML
templates from sample_rules/templates/ via POST /api/v1/rules/import.

Usage:
    uv run python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT / "sample_rules" / "templates"

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
    # Polyglot rule pair — EN version
    {
        "statement": "Monthly overtime hours must not exceed 45 hours per employee unless a special-clause 36-agreement is in effect.",
        "modality": "MUST_NOT",
        "severity": "CRITICAL",
        "scope": ["hr/overtime"],
        "tags": ["overtime", "36-agreement", "labor-standards-act", "polyglot"],
        "rationale": "Article 36 of the Labor Standards Act caps ordinary overtime at 45 hours per month.",
        "equivalence_id": "polyglot-overtime-45h",
        "locale": "en",
        "jurisdiction": "JP",
        "applicable_subject_types": ["event"],
        "statement_translations": {
            "ja": "月間の時間外労働時間は、特別条項付き36協定が効力を有する場合を除き、従業員1人当たり45時間を超えてはならない。",
        },
    },
    # Polyglot rule pair — JA version (linked by equivalence_id)
    {
        "statement": "月間の時間外労働時間は、特別条項付き36協定が効力を有する場合を除き、従業員1人当たり45時間を超えてはならない。",
        "modality": "MUST_NOT",
        "severity": "CRITICAL",
        "scope": ["hr/overtime"],
        "tags": ["overtime", "36-agreement", "labor-standards-act", "polyglot"],
        "rationale": "労働基準法第36条により、通常の時間外労働の上限は月45時間。",
        "equivalence_id": "polyglot-overtime-45h",
        "locale": "ja",
        "jurisdiction": "JP",
        "applicable_subject_types": ["event"],
        "statement_translations": {
            "en": "Monthly overtime hours must not exceed 45 hours per employee unless a special-clause 36-agreement is in effect.",
        },
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

        print(f"Seed data loaded: {len(SAMPLE_RULES)} inline rules.")

        # --- Seed default departments ---
        await _seed_departments(client)

        # --- Load YAML templates ---
        await _load_templates(client)


DEFAULT_DEPARTMENTS = [
    {"name": "Legal", "type": "legal"},
    {"name": "HR", "type": "hr"},
    {"name": "Finance", "type": "finance"},
    {"name": "Engineering", "type": "rnd"},
    {"name": "Sales", "type": "sales"},
    {"name": "Marketing", "type": "marketing"},
    {"name": "Operations", "type": "operations"},
]


async def _seed_departments(client) -> None:  # type: ignore[no-untyped-def]
    """Seed default departments via the departments API."""
    print(f"Seeding {len(DEFAULT_DEPARTMENTS)} default departments...")
    for dept in DEFAULT_DEPARTMENTS:
        resp = await client.post("/api/v1/departments", json=dept)
        if resp.status_code == 201:
            result = resp.json()
            print(f"  Created department: {result['name']} ({result['id'][:8]}...)")
        else:
            print(f"  Department {dept['name']}: {resp.status_code} (may already exist)")
    print(f"Department seeding complete.")


async def _load_templates(client) -> None:  # type: ignore[no-untyped-def]
    """Load all YAML templates via the bulk import endpoint."""
    try:
        import yaml
    except ImportError:
        print("PyYAML not installed — skipping template loading.")
        return

    if not TEMPLATES_DIR.is_dir():
        print(f"Templates directory not found: {TEMPLATES_DIR}")
        return

    yaml_files = sorted(TEMPLATES_DIR.glob("*.yaml"))
    if not yaml_files:
        print("No YAML templates found.")
        return

    total_rules = 0
    for yaml_path in yaml_files:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        if not data:
            continue

        # Extract rules — always at top level in canonical template format
        rules_list: list[dict] = data.get("rules", [])
        if not rules_list:
            continue

        if not rules_list:
            continue

        # Convert to import format — pass through all supported fields
        import_rules = []
        for rule in rules_list:
            item: dict = {
                "statement": rule.get("statement", ""),
                "modality": rule.get("modality", "MUST"),
                "severity": rule.get("severity", "MEDIUM"),
                "scope": rule.get("scope", []),
                "tags": rule.get("tags", []),
                "rationale": rule.get("rationale", ""),
                "context": rule.get("context", ""),
                "following_examples": rule.get("following_examples", []),
                "violation_examples": rule.get("violation_examples", []),
            }
            # Phase 7b fields
            for field in ("applicable_subject_types", "jurisdiction", "legal_force", "review_cadence", "kind"):
                if rule.get(field):
                    item[field] = rule[field]
            import_rules.append(item)

        payload = {
            "version": data.get("version", 1),
            "rules": import_rules,
        }

        resp = await client.post("/api/v1/rules/import", json=payload)
        if resp.status_code == 201:
            result = resp.json()
            created = result.get("created", len(import_rules))
            total_rules += created
            print(f"  Template {yaml_path.name}: {created} rules imported")
        else:
            print(f"  Template {yaml_path.name}: FAILED ({resp.status_code})")

    print(f"Templates loaded: {total_rules} rules from {len(yaml_files)} templates.")


if __name__ == "__main__":
    asyncio.run(main())
