# Intelligence Dashboard

The Intelligence Dashboard provides a corpus-wide view of rule health, evaluation analytics, and improvement recommendations. Access it in the frontend at `/intelligence`.

## API Endpoints

### GET /api/v1/intelligence/dashboard

Returns a summary of the entire rule corpus.

**Response:**

```json
{
  "total_rules": 142,
  "avg_health": 72.5,
  "evaluations_30d": 1893,
  "verdict_distribution": {
    "ALLOW": 1547,
    "WARN": 289,
    "DENY": 57
  },
  "open_recommendations": 23,
  "active_alerts": 5,
  "active_drift_alerts": 2
}
```

| Field | Description |
|---|---|
| `total_rules` | Total number of active rules in the repository |
| `avg_health` | Average health score across all rules (0-100) |
| `evaluations_30d` | Number of evaluations run in the last 30 days |
| `verdict_distribution` | Breakdown of evaluation verdicts (ALLOW, WARN, DENY) |
| `open_recommendations` | Number of unresolved improvement recommendations |
| `active_alerts` | Number of alerts in `active` status (not acknowledged or resolved) |
| `active_drift_alerts` | Count of active alerts specifically related to rule drift (health decline, dormant rules) sourced from the alerts table |

### GET /api/v1/intelligence/analytics?period_days=30

Returns corpus-wide analytics for the specified period.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period_days` | integer | 30 | Number of days to include in the analytics window |

**Response includes:**

- Evaluation volume over time (daily counts)
- Top violated rules
- Most evaluated scopes
- Verdict trend (ALLOW/WARN/DENY ratio over time)

### GET /api/v1/intelligence/analytics/{rule_id}

Returns analytics for a single rule.

**Response includes:**

- Evaluation count and verdict breakdown for this rule
- Health score and dimension breakdown
- Related rules (from the relationship graph)
- Recent evaluation history

### GET /api/v1/intelligence/recommendations

Returns improvement recommendations for the rule corpus.

**Response:**

```json
[
  {
    "type": "retire",
    "rule_id": "ENG-042",
    "reason": "No evaluations in 90 days and superseded by ENG-078",
    "priority": "medium"
  },
  {
    "type": "clarify",
    "rule_id": "SEC-003",
    "reason": "High WARN rate (68%) suggests the rule statement is ambiguous",
    "priority": "high"
  }
]
```

**Recommendation types:**

| Type | Description |
|---|---|
| `retire` | Rule is unused or superseded; consider setting `valid_until` |
| `clarify` | Rule has a high WARN rate or ambiguous statement |
| `escalate` | Rule has a high DENY rate; may need stronger enforcement or owner attention |
| `strengthen` | Rule is frequently overridden; may need scope or modality adjustment |
| `completeness` | Rule is missing fields (rationale, tags, source references, etc.) |

## Frontend Sections

The `/intelligence` page is organized into the following sections:

### Summary Cards

Top-level metrics: total rules, average health, evaluation count (30 days), and open recommendations. Each card links to the relevant detail view.

### Verdict Distribution

A chart showing the ALLOW/WARN/DENY breakdown over the selected time period. Helps identify trends in compliance.

### Top Violated Rules

A ranked list of rules with the highest DENY and WARN counts. Each entry links to the rule detail page.

### Health Distribution

A histogram of rule health scores across the corpus. Highlights clusters of unhealthy rules that need attention.

### Recommendations

A prioritized list of improvement recommendations. Each recommendation includes the rule, the suggestion type, the reason, and a link to take action.

### Alerts Panel

A live feed of active alerts, ordered by creation time. Each alert shows its type, the affected rule, and the trigger message. Alerts can be acknowledged or resolved directly from the panel. The `active_drift_alerts` count in the summary cards reflects the real count from the alerts table (not a placeholder).

Alert types displayed:

| Type | Icon | Description |
|---|---|---|
| `dormant_rule` | Clock | Rule has not been evaluated recently |
| `high_deny_rate` | Warning | Rule DENY rate exceeds threshold |
| `health_decline` | TrendingDown | Rule health score dropped significantly |
| `conflict_detected` | Zap | New conflict detected in the rule graph |

## See Also

- [Health Scoring](health.md) -- how individual rule health scores are calculated
- [Alerts API](../api/alerts.md) -- alert endpoints
- [Background Workers](../integrations/workers.md) -- cron jobs that generate alerts
- [Contributing](../dev/contributing.md) -- how to improve the intelligence features
