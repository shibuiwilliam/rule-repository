# HR Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the HR Portal

Open http://localhost:3000/hr. The HR shell loads with an indigo-themed sidebar showing: Dashboard, Violations, Attendance, Leave Management, Employee Lifecycle, Compliance Reports, Policy Library, HRIS Status.

## 2. View the HR Dashboard

The dashboard shows 4 KPI cards:
- **Overtime Violations**: employees exceeding the 45h/month limit
- **Leave Compliance Rate**: percentage of employees meeting the 5-day annual leave obligation
- **Upcoming Reviews**: policy reviews due in the next 30 days
- **Active HR Rules**: total HR department rules

Below: Attendance Compliance gauge, Overtime Violation Trend (30-day sparkline), Verdict Distribution, Top Violated Rules.

## 3. Submit an Attendance Event

```bash
curl -X POST http://localhost:8000/api/v1/submissions \
  -H "Content-Type: application/json" \
  -d '{
    "subject_kind": "event",
    "payload": {
      "event_type": "overtime_register",
      "employee_id": "E001",
      "monthly_overtime_hours": 52,
      "rest_period_hours": 8,
      "date": "2026-05-14"
    },
    "actor": {
      "kind": "human",
      "identifier": "emp:E001",
      "attributes": {"department": "Engineering", "role": "engineer"}
    },
    "intent": "register_overtime",
    "mode": "preflight"
  }'
```

The response returns DENY because:
- `monthly_overtime_hours=52` exceeds the 45-hour cap (deterministic check — no LLM needed)
- `rest_period_hours=8` is below the 11-hour minimum

The deterministic evaluator handles these checks instantly. Only ambiguous rules (like "special 36-agreement" exceptions) go to the LLM.

## 4. View Computational vs Normative Rules

In the HR Policy Library, notice rules with `kind: computational`:
- "Monthly overtime MUST NOT exceed 45 hours" — has `constraints: [{type: numeric, field_path: monthly_overtime_hours, operator: "<=", threshold: 45}]`
- These are evaluated deterministically, saving LLM tokens and improving latency

Rules with `kind: normative` (e.g., "A valid 36-agreement MUST be filed before overtime is assigned") go through full LLM evaluation.

## 5. Check Attendance Violations

Navigate to **Violations** in the HR sidebar. The violations list shows employees who have triggered HR rules, with expandable details showing which rules were violated, the verdicts, and suggested remediations.

## Verification

- [ ] HR dashboard loads with KPIs
- [ ] Overtime submission returns DENY with deterministic check
- [ ] Computational rules show constraint metadata
- [ ] Violations list is populated from evaluation history
- [ ] Persona switcher navigates to other portals
