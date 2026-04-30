# Compliance Dashboard

## Overview

The home page of the Rule Repository serves as an **outcome-oriented dashboard** that answers the question: "Are my rules working?"

It displays the agent compliance rate, rule status distribution, top violated rules, recent corrections, and pending actions — all in a single view.

## Dashboard Summary API

All dashboard data is served from a single endpoint:

```
GET /api/v1/intelligence/summary?project_id=<optional>
```

### Response

```json
{
  "compliance_rate": 0.847,
  "compliance_trend": [
    {"date": "2026-04-24", "total": 15, "allow_count": 12, "compliance_rate": 0.8},
    {"date": "2026-04-25", "total": 22, "allow_count": 19, "compliance_rate": 0.864}
  ],
  "total_rules": 677,
  "rules_by_status": {
    "APPROVED": 650,
    "EFFECTIVE": 20,
    "DRAFT": 5,
    "REVIEW": 2
  },
  "top_violated_rules": [
    {
      "rule_id": "abc-123",
      "violation_count": 12,
      "rule_statement": "All functions MUST have type annotations"
    }
  ],
  "recent_corrections": [
    {
      "id": "def-456",
      "status": "pending",
      "candidate_statement": "Add error handling for API calls",
      "analysis_type": "new_rule",
      "created_at": "2026-04-30T10:00:00Z"
    }
  ],
  "pending_actions": {
    "rules_pending_review": 7,
    "corrections_pending": 3,
    "active_alerts": 1
  }
}
```

## Dashboard Sections

### Compliance Hero

The largest element on the dashboard. Shows the **agent compliance rate** — the percentage of rule evaluations that resulted in ALLOW over the last 30 days.

- Green (>= 90%): Rules are working well
- Yellow (70-89%): Some rules need attention
- Red (< 70%): Significant compliance issues

A 7-day trend bar chart shows whether compliance is improving or declining.

### Rules Status Bar

A horizontal stacked bar showing the distribution of rules by status:

- **Effective**: Rules actively enforced
- **Approved**: Rules approved but not yet deployed
- **Draft**: Rules in progress
- **Review**: Rules awaiting approval
- **Retired**: Rules no longer active

### Pending Actions

Three cards showing counts that need attention:

| Card | Count | Links to |
|------|-------|----------|
| Rules Pending Review | DRAFT + REVIEW status | `/rules` |
| Corrections Pending | pending status | `/feedback` |
| Active Alerts | active status | `/alerts` |

### Top Violated Rules

Table of the 5 rules with the highest DENY count in the last 30 days. Each rule links to its detail page where you can see evaluation history, test cases, and health score.

### Recent Corrections

The last 5 corrections submitted through the feedback system, with status badges (pending, approved, dismissed).

## Data Sources

The dashboard data comes from two tables:

- **`evaluations` table** (primary): Per-rule evaluation records with structured verdict, confidence, and latency columns. Fast queries without JSON parsing.
- **`audit_log` table** (fallback): Used during transition when the evaluations table may be empty. Analytics queries automatically fall back to audit_log if needed.

## Evaluation Persistence

Every rule evaluation persists a record to the `evaluations` table:

```sql
INSERT INTO evaluations (rule_id, project_id, verdict, confidence, latency_ms, scope, input_type, model_id, cached)
VALUES (...);
```

This happens after verdict aggregation in the evaluation service. Persistence failure is caught and logged — it never breaks the evaluation response.
