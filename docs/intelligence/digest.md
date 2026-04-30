# Weekly Governance Digest

## Overview

The weekly digest is an automated report generated every Monday at 9am that summarizes rule governance activity over the past week. It answers the question: *"Is our rule system getting better?"*

## API

```
GET /api/v1/intelligence/digest?project_id=<optional>
```

### Response

```json
{
  "period": "7d",
  "compliance": {
    "current_rate": 0.91,
    "previous_rate": 0.87,
    "change_pp": 4.0,
    "trend": "improving",
    "daily_trend": [{"date": "2026-05-01", "total": 42, "allow_count": 38, "compliance_rate": 0.905}],
    "total_evaluations": 156
  },
  "rules": {
    "total": 47,
    "new_this_week": 3,
    "maturity_distribution": {"experimental": 5, "stable": 30, "proven": 12}
  },
  "top_violated_rules": [...],
  "attention_needed": [
    {"rule_id": "...", "statement": "...", "issue": "67% false positive rate", "severity": "warning"}
  ],
  "corrections": {
    "this_week": 12,
    "pending_proposals": 2
  },
  "pending_actions": {
    "proposals_pending": 2,
    "active_alerts": 1
  }
}
```

## Sections

| Section | What it shows | Data source |
|---|---|---|
| **Compliance** | This week vs last week rate, trend direction | `evaluations` table |
| **Rules** | Total count, new rules, maturity distribution | `rules` table |
| **Top Violated** | Rules with most DENY verdicts this week | `evaluations` table |
| **Attention Needed** | Rules with >30% false positive rate | `rules` table (FP/TP counts) |
| **Corrections** | Corrections captured, pending proposals | `corrections` + `draft_rule_proposals` tables |
| **Pending Actions** | Outstanding approvals and alerts | `draft_rule_proposals` + `alerts` tables |

## Webhook Delivery

Set `DIGEST_WEBHOOK_URL` in your environment to receive the digest as a JSON POST every Monday morning. Compatible with Slack incoming webhooks, email relay services, or any HTTP endpoint.

## Background Worker

The `send_weekly_digest` cron job runs at Monday 9am via arq + Redis. It generates the digest and, if `DIGEST_WEBHOOK_URL` is configured, delivers it via HTTP POST.
