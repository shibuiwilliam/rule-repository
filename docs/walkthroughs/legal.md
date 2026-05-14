# Legal Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Legal Portal

Open http://localhost:3000/legal. The Legal shell loads with a slate-themed sidebar showing: Dashboard, Contract Review, Clause Library, Redlines, Norm Lineage, Regulatory Horizon, Citations.

## 2. View the Legal Dashboard

The dashboard shows 4 KPI cards:
- **Pending Reviews**: contracts awaiting clause-level evaluation
- **Clause Deviations**: clauses that deviate from standard templates
- **Regulatory Updates**: upstream norm changes affecting legal rules
- **Active Rules**: total legal department rules

Below: Contract Review Queue table, Risk Distribution chart, Clause Compliance gauge, Top Violated Rules.

## 3. Review a Contract

Navigate to **Contract Review**. The system lists contracts that have been uploaded and evaluated. Each contract shows clause-by-clause verdicts.

A sample NDA contract shows:
- Confidentiality clause: ALLOW (matches standard)
- Limitation of liability: DENY — "unlimited liability clause detected" with a `text_rewrite` remediation suggesting a capped liability alternative
- Jurisdiction clause: NEEDS_CONFIRMATION — "foreign jurisdiction, requires legal review"

## 4. Evaluate a Document via API

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/document \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "contract",
    "content": "The Receiving Party shall hold all Confidential Information in strict confidence. Liability under this Agreement shall be unlimited.",
    "language": "en",
    "scope": "legal/contract"
  }'
```

The response includes per-rule verdicts with span-level remediations pointing to the unlimited liability clause.

## 5. Browse Legal Rules

Navigate back to the Engineering portal via the persona switcher, then to **Rules**. Filter by scope `legal/*`. You see contract clause rules, privacy rules, and regulatory compliance rules.

Each rule shows its `norm_tier` (LAW, REGULATION, CORPORATE_POLICY), `norm_authority` (e.g., "APPI Article 27"), and bilingual statements (EN/JA).

## 6. Check Norm Lineage

Navigate to **Norm Lineage** in the Legal portal. The lineage view shows derivation chains:
- LAW (e.g., "APPI Article 27") → CORPORATE_POLICY (e.g., "Third-party data sharing requires consent") → DEPARTMENT_RULE (e.g., "Marketing email opt-in must be explicit")

When an upstream law changes, downstream rules are flagged for review.

## Verification

- [ ] Legal dashboard loads with KPIs
- [ ] Contract review queue is populated
- [ ] Document evaluation returns clause-level verdicts
- [ ] Legal rules have norm_tier and norm_authority metadata
- [ ] Persona switcher returns to Engineering
