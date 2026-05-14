# Finance Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Finance Portal

Open http://localhost:3000/finance. The Finance shell loads with an emerald-themed sidebar showing: Dashboard, Transactions, Expense Policy, Audit Reports, Controls.

## 2. View the Finance Dashboard

The dashboard shows 4 KPI cards:
- **Active Finance Rules**: total rules owned by Finance department
- **Expense Violations (30d)**: number of expense-related DENY verdicts in the last 30 days
- **Evaluations (30d)**: total transaction evaluations processed
- **Compliance Rate**: percentage of evaluations that passed

Below: Violation Trend sparkline, Verdict Distribution bar, Top Violated Rules, Recent Transaction Evaluations table.

## 3. Submit an Expense Claim

```bash
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "subject_kind": "transaction",
    "payload": {
      "document_type": "expense_claim",
      "amount": 42000,
      "currency": "JPY",
      "category": "entertainment",
      "per_person_entertainment": 10500,
      "attendees": 4,
      "receipt_attached": true
    },
    "actor": {
      "kind": "human",
      "identifier": "emp:S042",
      "attributes": {"department": "Sales", "role": "Account Manager"}
    },
    "intent": "submit_expense",
    "mode": "preflight"
  }'
```

The response returns DENY because `per_person_entertainment=10500` exceeds the 5,000 JPY cap. This is a deterministic check — the `constraints` field on the rule contains `{field_path: "per_person_entertainment", operator: "<=", threshold: 5000}`.

The `field_change` remediation suggests reducing the per-person amount.

## 4. Review Expense Policy Rules

Navigate to **Expense Policy**. The rules list shows expense rules with severity badges. Rules with `kind: computational` display their structured constraints inline.

Example: EXP-005 ("Entertainment expenses must not exceed 5,000 JPY per person") shows:
- `constraints: [{type: numeric, field_path: per_person_entertainment, operator: <=, threshold: 5000, unit: JPY}]`
- Bilingual statement (EN + JA translation)

## 5. View Audit Reports

Navigate to **Audit Reports**. This shows the hash-chained audit trail of all financial evaluations, filterable by date range and verdict type.

## 6. Review Controls

Navigate to **Controls**. This page shows segregation-of-duties rules and approval workflows — who can approve what at which threshold.

## Verification

- [ ] Finance dashboard loads with KPIs
- [ ] Expense submission returns DENY for over-cap entertainment
- [ ] Deterministic evaluator produces the verdict (not LLM)
- [ ] Expense rules show bilingual statements
- [ ] Audit trail is populated
