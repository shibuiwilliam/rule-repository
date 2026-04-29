# Health Scoring

Every rule in the repository receives a health score from 0 to 100, computed across six weighted dimensions. The score helps identify rules that need maintenance, clarification, or retirement.

## Dimensions

| Dimension | Weight | How Computed |
|---|---|---|
| **Completeness** | 20% | Checks 7 metadata fields for presence (weighted per field) |
| **Clarity** | 25% | Uses stored `clarity_score` from LLM assessment, defaults to 50.0 when not yet assessed |
| **Test coverage** | 15% | Based on evaluation count in the last 90 days (5+ evaluations = 100) |
| **Freshness** | 15% | Time since last update — 100 within 30 days, linear decay to 0 at 365 days |
| **Activity** | 15% | Evaluation volume in the last 90 days (10+ evaluations = 100) |
| **Owner engagement** | 10% | Whether the rule owner has been active recently (binary: 100 or 0) |

### Completeness (20%)

Checks whether the rule has values for these 7 fields, each with its own weight:

| Field | Weight |
|---|---|
| `statement` (>20 chars) | 20 |
| `rationale` | 20 |
| `scope` | 15 |
| `modality` | 10 |
| `tags` | 10 |
| `source_refs` | 15 |
| `governance.owner` | 10 |

A rule with all 7 fields present scores 100. Missing fields generate specific issues (e.g., "Missing or incomplete: rationale").

### Clarity (25%)

Uses the rule's stored `clarity_score` when available (set by LLM assessment during extraction or periodic analysis). Falls back to 50.0 when no clarity assessment has been performed yet.

### Test Coverage (15%)

Based on evaluation count in the last 90 days:

- 5+ evaluations = 100
- Fewer evaluations scale linearly (each evaluation adds 20 points)
- 0 evaluations = 0

### Freshness (15%)

Based on the time elapsed since the rule was last updated:

| Time Since Last Update | Score |
|---|---|
| 0-30 days | 100 |
| 30-365 days | Linear decay from 100 to 0 |
| 365+ days | 0 |

Rules that have never been updated score based on their creation date.

### Activity (15%)

Based on evaluation volume in the last 90 days:

| Evaluations (90 days) | Score |
|---|---|
| 10 or more | 100 |
| Fewer | 10 points per evaluation |
| 0 | 0 |

A rule with zero evaluations is flagged as dormant and generates the issue: "Rule has not been evaluated in the last 90 days (dormant)".

### Owner Engagement (10%)

Binary scoring based on owner activity:

- Active owner: 100
- Inactive or no owner: 0

When the owner has not been active, the issue "Rule owner has not been active recently" is generated.

## Overall Score Calculation

The overall health score is the weighted sum of all dimensions:

```
score = (completeness * 0.20) + (clarity * 0.25) + (test_coverage * 0.15)
      + (freshness * 0.15) + (activity * 0.15) + (owner_engagement * 0.10)
```

## Issues

Each health computation generates a list of issues — specific problems identified during scoring. Issues appear in the expandable row detail on the Intelligence Dashboard and feed into the recommendation engine. Examples:

- "Missing or incomplete: rationale" (completeness)
- "Missing or incomplete: source_refs" (completeness)
- "Rule has not been evaluated in the last 90 days (dormant)" (activity)
- "Rule owner has not been active recently" (owner engagement)
- "Rule has not been updated in over 6 months" (freshness)

## API Endpoints

### GET /api/v1/intelligence/health

Returns paginated health scores for all rules, sortable by any dimension.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | integer | 1 | Page number |
| `page_size` | integer | 50 | Items per page (max 200) |
| `sort_by` | string | `overall_score` | Dimension to sort by |

### GET /api/v1/intelligence/health/{rule_id}

Returns the full health breakdown for a single rule.

**Response:**

```json
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
```

## See Also

- [Intelligence Dashboard](dashboard.md) -- corpus-wide health overview and frontend UI
- [Background Workers](../integrations/workers.md) -- cron job that computes health scores daily
