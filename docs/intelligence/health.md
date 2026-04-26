# Health Scoring

Every rule in the repository receives a health score from 0 to 100, computed across six dimensions. The score helps identify rules that need maintenance, clarification, or retirement.

## Dimensions

| Dimension | Weight | Status | How Computed |
|---|---|---|---|
| **Completeness** | 20% | Working | Checks 7 fields for presence |
| **Clarity** | 25% | Hardcoded | **Currently returns 50.0.** Planned: LLM assessment of statement clarity |
| **Test coverage** | 15% | Hardcoded | **Currently returns 50.0.** Planned: analysis of evaluation count and diversity |
| **Freshness** | 15% | Working | Time since last revision |
| **Activity** | 15% | Working | Evaluation volume in the scoring window |
| **Owner engagement** | 10% | Hardcoded | **Currently returns 50.0.** Planned: owner review and response activity |

### Completeness (20%)

Checks whether the rule has values for these 7 fields:

1. `statement` -- the rule text itself
2. `rationale` -- why the rule exists
3. `scope` -- where the rule applies
4. `modality` -- MUST, SHOULD, or MAY
5. `tags` -- at least one tag
6. `source_refs` -- at least one source reference
7. `governance.owner` -- an assigned owner

Each present field contributes equally. A rule with all 7 fields scores 100; a rule with 4 of 7 scores approximately 57.

### Clarity (25%)

**Currently hardcoded to 50.0.**

When implemented, this dimension will use an LLM to assess whether the rule statement is clear, unambiguous, and actionable. Factors will include:

- Is the statement specific enough to evaluate?
- Does it avoid vague terms ("appropriate", "reasonable") without definition?
- Is it testable?

### Test Coverage (15%)

**Currently hardcoded to 50.0.**

When implemented, this dimension will analyze:

- How many evaluations have been run against this rule
- Whether evaluations cover different scenarios (file types, scopes, contexts)
- Whether the rule has been evaluated recently

### Freshness (15%)

Based on the time elapsed since the rule's last revision:

| Time Since Last Revision | Score |
|---|---|
| Less than 30 days | 100 |
| 30-90 days | 75 |
| 90-180 days | 50 |
| 180-365 days | 25 |
| More than 365 days | 0 |

Rules that have never been revised score based on their creation date.

### Activity (15%)

Based on evaluation volume in the last 30 days:

| Evaluations (30 days) | Score |
|---|---|
| 10 or more | 100 |
| 5-9 | 75 |
| 1-4 | 50 |
| 0 | 0 |

A rule with zero evaluations may be unused and a candidate for retirement.

### Owner Engagement (10%)

**Currently hardcoded to 50.0.**

When implemented, this dimension will track:

- Whether the rule has an assigned owner
- How recently the owner reviewed the rule
- Whether the owner has responded to recommendations

## Overall Score Calculation

The overall health score is the weighted sum of all dimensions:

```
score = (completeness * 0.20) + (clarity * 0.25) + (test_coverage * 0.15)
      + (freshness * 0.15) + (activity * 0.15) + (owner_engagement * 0.10)
```

## Issues

Each dimension can generate issues that appear on the rule detail page and in recommendations. Examples:

- "Rule is missing a rationale" (completeness)
- "Rule has not been revised in over 6 months" (freshness)
- "Rule has zero evaluations in the last 30 days" (activity)

## API Endpoints

### GET /api/v1/intelligence/health

Returns health scores for all rules, sorted by score ascending (worst first).

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `scope` | string | All scopes | Filter by rule scope |
| `min_score` | float | 0 | Minimum score filter |
| `max_score` | float | 100 | Maximum score filter |
| `limit` | integer | 50 | Number of results |

### GET /api/v1/intelligence/health/{rule_id}

Returns the health score and dimension breakdown for a single rule.

**Response:**

```json
{
  "rule_id": "ENG-001",
  "overall_score": 68.5,
  "dimensions": {
    "completeness": {"score": 85.7, "weight": 0.20},
    "clarity": {"score": 50.0, "weight": 0.25},
    "test_coverage": {"score": 50.0, "weight": 0.15},
    "freshness": {"score": 100.0, "weight": 0.15},
    "activity": {"score": 75.0, "weight": 0.15},
    "owner_engagement": {"score": 50.0, "weight": 0.10}
  },
  "issues": [
    "Rule is missing source_refs",
    "Clarity scoring not yet implemented (using default)"
  ]
}
```

## See Also

- [Intelligence Dashboard](dashboard.md) -- corpus-wide health overview
