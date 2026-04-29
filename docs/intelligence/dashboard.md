# Intelligence Dashboard

The Intelligence Dashboard provides a corpus-wide view of rule health, evaluation analytics, and improvement recommendations. Access it in the frontend at `/intelligence`.

## API Endpoints

### GET /api/v1/intelligence/dashboard

Returns a summary of the entire rule corpus.

**Response:**

```json
{
  "total_rules": 142,
  "avg_health_score": 72.5,
  "total_evaluations_30d": 1893,
  "verdict_distribution": {
    "ALLOW": 1547,
    "DENY": 289,
    "NEEDS_CONFIRMATION": 57
  },
  "active_drift_alerts": 5,
  "open_recommendations": 23,
  "health_distribution": {
    "excellent": 45,
    "good": 52,
    "fair": 30,
    "poor": 15
  },
  "cache_stats": {
    "cache_hits": 1420,
    "cache_misses": 473,
    "hit_rate": 0.750,
    "period_days": 30
  },
  "top_violated_rules": [
    {"rule_id": "abc-123", "violation_count": 47},
    {"rule_id": "def-456", "violation_count": 31}
  ]
}
```

| Field | Description |
|---|---|
| `total_rules` | Total number of rules in the repository |
| `avg_health_score` | Average health score across all rules (0-100) |
| `total_evaluations_30d` | Number of evaluations in the last 30 days |
| `verdict_distribution` | Breakdown of evaluation verdicts (ALLOW, DENY, NEEDS_CONFIRMATION) |
| `active_drift_alerts` | Count of active alerts (dormant rules, health decline, high deny rate) |
| `open_recommendations` | Number of unresolved improvement recommendations |
| `health_distribution` | Rules bucketed by health: excellent (80+), good (60-79), fair (40-59), poor (<40) |
| `cache_stats` | LLM cache performance: hits, misses, and hit rate for the period |
| `top_violated_rules` | Rules with the most DENY verdicts, ordered by violation count |

### GET /api/v1/intelligence/health

Returns paginated health scores for all rules.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 50 | Items per page (max 200) |
| `sort_by` | string | `overall_score` | Dimension to sort by |

**Response:**

```json
{
  "items": [
    {
      "rule_id": "abc-123",
      "overall_score": 68.5,
      "completeness": 85.7,
      "clarity": 50.0,
      "test_coverage": 40.0,
      "freshness": 100.0,
      "activity": 70.0,
      "owner_engagement": 0.0,
      "issues": [
        "Missing or incomplete: source_refs",
        "Rule owner has not been active recently"
      ]
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 50
}
```

### GET /api/v1/intelligence/health/{rule_id}

Returns the health score and dimension breakdown for a single rule.

### GET /api/v1/intelligence/analytics?period_days=30

Returns corpus-wide evaluation analytics for the specified period.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `period_days` | integer | 30 | Number of days to aggregate (1-365) |

**Response:**

```json
{
  "total_evaluations": 1893,
  "verdict_distribution": {
    "ALLOW": 1547,
    "DENY": 289,
    "NEEDS_CONFIRMATION": 57
  },
  "avg_latency_ms": 342.5
}
```

### GET /api/v1/intelligence/analytics/{rule_id}

Returns per-rule analytics: evaluation count, verdict rates, average latency.

### GET /api/v1/intelligence/recommendations

Returns paginated improvement recommendations.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `status` | string | `open` | Filter by status |
| `page` | integer | 1 | Page number |
| `page_size` | integer | 50 | Items per page (max 200) |

**Response:**

```json
{
  "items": [
    {
      "id": "rec-001",
      "rule_id": "abc-123",
      "type": "retire",
      "title": "Consider retiring dormant rule",
      "description": "This rule has not been evaluated in the last 90 days.",
      "suggested_change": null,
      "related_rule_ids": [],
      "priority": "medium",
      "status": "open"
    }
  ],
  "total": 23,
  "page": 1,
  "page_size": 50
}
```

**Recommendation types:**

| Type | Trigger | Priority |
|---|---|---|
| `retire` | Zero evaluations in 90+ days | medium |
| `clarify` | NEEDS_CONFIRMATION rate > 30%, or completeness score < 60 | high or medium |
| `escalate` | Deny rate > 50% with 10+ evaluations | critical |
| `strengthen` | 100% ALLOW rate with SHOULD modality and 10+ evaluations | low |

## Frontend Sections

The `/intelligence` page is a fully interactive client component organized into six sections:

### Summary Cards

Six cards in a responsive grid:

1. **Total Rules** — count of all rules in the corpus
2. **Avg Health Score** — color-coded (green >= 80, yellow >= 60, orange >= 40, red < 40)
3. **Evaluations (30d)** — evaluation volume for the last 30 days
4. **Open Recommendations** — count of actionable suggestions (orange when > 0)
5. **Active Alerts** — count of unresolved alerts (red when > 0)
6. **Cache Hit Rate** — LLM cache performance percentage with hit/miss detail

### Distribution Overviews

Two side-by-side panels:

- **Health Distribution** — stacked color bar showing excellent/good/fair/poor buckets with legend and percentages
- **Verdict Distribution (30d)** — stacked color bar showing ALLOW/DENY/NEEDS_CONFIRMATION breakdown with legend and percentages

### Top Violated Rules

Ranked list of rules with the most DENY verdicts in the last 30 days. Each entry shows a linked rule ID, a proportional bar chart, and the violation count.

### Evaluation Analytics

Corpus-wide metrics with a **period selector** (7d / 30d / 90d / 365d):

- Total evaluations and evaluations per day
- Average latency (ms)
- Compliance rate (ALLOW percentage)

### Rule Health Scores

Full table showing all six dimensions for each rule:

- **Columns**: Rule ID (linked), Overall, Completeness, Clarity, Test Coverage, Freshness, Activity, Owner Engagement
- **Sort**: dropdown to sort by any dimension
- **Pagination**: Previous/Next controls with page indicator
- **Expandable rows**: click a row to see detailed score bars for each dimension and a list of identified issues

### Recommendations

Priority-sorted list with:

- Priority badge (critical/high/medium/low) with colored left border
- Type badge (retire/clarify/escalate/strengthen)
- Linked rule ID
- Title, description, and suggested change (when available)
- Related rule links
- Pagination controls

## See Also

- [Health Scoring](health.md) -- how individual rule health scores are calculated
- [Alerts API](../api/alerts.md) -- alert endpoints
- [Background Workers](../integrations/workers.md) -- cron jobs that generate alerts and recommendations
