# Phase 7 Demo: HR Director Walkthrough

This walkthrough shows how an HR director imports the HR attendance pack, evaluates an overtime event, and how department ownership and classification protect their rules.

Assumes the stack is running (`make up`). Auth is disabled in dev (`AUTH_REQUIRED=false`).

---

## 1. Import the HR Attendance Pack

The HR director uses the CLI to seed the HR attendance template pack.

```bash
rulerepo-ingest \
  --source template \
  --file sample_rules/templates/hr-attendance-jp.yaml \
  --scope hr/attendance \
  --department hr-jp
```

Or directly via the API:

```bash
curl -s -X POST http://localhost:8000/api/v1/rules/import \
  -H "Content-Type: application/json" \
  -d '{
    "source": "template",
    "template_id": "hr-attendance-jp",
    "scope": "hr/attendance",
    "owner_department_id": "dept-hr-jp",
    "classification": "internal"
  }' | jq '.imported_count'
# → 20
```

Verify the rules landed:

```bash
curl -s "http://localhost:8000/api/v1/rules?scope=hr/attendance&limit=5" \
  | jq '.rules[] | {id, statement, severity, subject_kinds}'
```

---

## 2. Evaluate an Overtime Event

An employee clocked 52 hours of overtime in April. The HR director evaluates this event against the attendance rules.

```bash
curl -s -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "subject_kind": "event",
    "subject": {
      "identifier": "attendance-2026-04-E001",
      "facts": {
        "employee_id": "E001",
        "event_type": "monthly_overtime",
        "overtime_hours": 52,
        "month": "2026-04",
        "has_36_agreement": true,
        "special_clause_active": false
      },
      "pii_fields": ["employee_id"],
      "locale": "ja",
      "jurisdiction": "JP"
    },
    "scope": "hr/attendance",
    "mode": "preflight"
  }' | jq '{verdict, confidence, violations: [.rule_verdicts[] | select(.verdict == "DENY") | {rule_id, reason}]}'
```

Expected response shape:

```json
{
  "verdict": "DENY",
  "confidence": 0.94,
  "violations": [
    {
      "rule_id": "hr-att-007",
      "reason": "Monthly overtime of 52h exceeds the 45h standard ceiling under Article 36. Special clause not activated."
    }
  ]
}
```

The `employee_id` field is automatically redacted in the audit log because it was listed in `pii_fields`.

---

## 3. Department Ownership and Classification in Action

### 3a. Inspect ownership

```bash
curl -s http://localhost:8000/api/v1/departments/dept-hr-jp \
  | jq '{name, type, head, capacities}'
```

```json
{
  "name": "HR Japan",
  "type": "hr",
  "head": {"user_id": "u-yamada", "display_name": "Yamada Keiko"},
  "capacities": [
    {"user_id": "u-yamada", "capacity": "owner"},
    {"user_id": "u-sato",   "capacity": "reviewer"},
    {"user_id": "u-audit",  "capacity": "auditor"}
  ]
}
```

### 3b. A Finance user cannot see INTERNAL HR rules

The HR attendance rules are classified `internal` and owned by `dept-hr-jp`. A Finance user who is not a member of that department gets an empty result set — enforced by PostgreSQL RLS.

```bash
# Finance user (not in dept-hr-jp) searches for HR rules
curl -s "http://localhost:8000/api/v1/search?q=overtime&user_id=u-finance-01&departments=dept-finance" \
  | jq '.total'
# → 0  (RLS filters them out)

# HR reviewer (member of dept-hr-jp) sees the same query
curl -s "http://localhost:8000/api/v1/search?q=overtime&user_id=u-sato&departments=dept-hr-jp" \
  | jq '.total'
# → 20
```

### 3c. Proposal routes to HR reviewers

If a rule needs updating, the proposal automatically routes to `dept-hr-jp` REVIEWERs:

```bash
curl -s -X POST http://localhost:8000/api/v1/proposals \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "hr-att-007",
    "proposed_statement": "Monthly overtime must not exceed 45 hours unless a special clause of the 36-Agreement is filed and activated.",
    "reason": "Clarify that special clause activation is a prerequisite, not just existence.",
    "author_id": "u-yamada"
  }' | jq '{proposal_id, status, routed_to}'
# routed_to → ["u-sato"]  (dept-hr-jp REVIEWERs)
```

---

## Summary

In three steps the HR director:
1. Loaded 20 HR attendance rules from a domain template pack in seconds.
2. Evaluated an actual overtime event and got a structured DENY with citation.
3. Verified that department ownership and classification prevent cross-department data leakage, and that governance proposals route through functional ownership automatically.
