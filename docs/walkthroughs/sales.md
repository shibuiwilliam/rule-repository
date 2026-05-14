# Sales Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Sales Portal

Open http://localhost:3000/sales. The Sales shell loads with an orange-themed sidebar showing: Dashboard, Pricing Approvals, Discount Requests, Proposals, Communication.

## 2. View the Sales Dashboard

The dashboard shows 4 KPI cards:
- **Active Sales Rules**: total rules owned by Sales department
- **Pricing Violations (30d)**: discount/pricing DENY verdicts
- **Evaluations (30d)**: total sales evaluations
- **Compliance Rate**: pass rate

Below: Violation Trend sparkline, Verdict Distribution, Top Violated Rules, Recent Sales Evaluations table, Active Sales Rules list, Quick Action cards.

## 3. Evaluate a Discount Request

```bash
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "subject_kind": "transaction",
    "payload": {
      "document_type": "discount_request",
      "deal_id": "DEAL-2026-1847",
      "customer": "Tanaka Manufacturing",
      "list_price": 5000000,
      "proposed_discount_pct": 25,
      "proposed_price": 3750000,
      "contract_term_months": 24,
      "auto_renewal": true
    },
    "actor": {
      "kind": "human",
      "identifier": "emp:S042",
      "attributes": {"department": "Sales", "role": "Account Executive"}
    },
    "intent": "request_discount_approval",
    "mode": "preflight"
  }'
```

Expected violations:
- SAL-001: 25% discount exceeds 15% standard limit (requires Sales Director approval)
- SAL-005: 24-month term with `auto_renewal=true` violates sunset clause requirement

## 4. Evaluate Customer Communication

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/document \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "email",
    "content": "Dear Customer, our product is guaranteed to reduce your costs by 50% within 3 months. This is the best deal available anywhere.",
    "language": "en",
    "scope": "sales/communication"
  }'
```

Expected flags:
- Unsubstantiated performance claim ("reduce costs by 50%")
- Misleading superlative ("best deal available anywhere")

The system returns `text_rewrite` remediations with suggested compliant alternatives.

## 5. Browse Sales Rules

Navigate to the Engineering portal via the persona switcher, then to **Rules**. Filter by scope `sales/*`. You see pricing rules, discount governance rules, and communication compliance rules.

Each rule includes `jurisdiction` (e.g., "JP"), `norm_authority` (e.g., "Antimonopoly Act Article 2(9)(iv)"), and bilingual statements.

## Verification

- [ ] Sales dashboard loads with KPIs and orange accent theme
- [ ] Discount request returns violations for over-limit discount
- [ ] Customer email evaluation flags unsubstantiated claims
- [ ] Sales rules are visible with norm_authority metadata
- [ ] Persona switcher navigates to all other portals
