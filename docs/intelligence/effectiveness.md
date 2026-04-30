# Rule Effectiveness Score

## Overview

The effectiveness score measures whether a rule is actually preventing bad code, going beyond the health score (which measures metadata completeness). It answers three questions:

1. **Is this rule catching real issues?** (Precision)
2. **Did corrections decrease after this rule was activated?** (Prevention rate)
3. **Are agents complying on the first attempt?** (Agent adoption)

## API

```
GET /api/v1/intelligence/effectiveness/{rule_id}?period_days=90
```

### Response

```json
{
  "precision": 0.85,
  "prevention_rate": 0.42,
  "agent_adoption": 0.91,
  "effectiveness_score": 72.3,
  "total_evaluations": 156,
  "true_positives": 34,
  "false_positives": 6
}
```

## Metrics

| Metric | Weight | Source | Formula |
|---|---|---|---|
| **Precision** | 40% | `rules` table (`true_positive_count`, `false_positive_count`) | TP / (TP + FP) |
| **Prevention rate** | 35% | `corrections` table (before vs after rule creation) | (before - after) / before |
| **Agent adoption** | 25% | `evaluations` table (ALLOW count / total) | ALLOW / total evaluations |

The composite **effectiveness score** ranges from 0 to 100.

## Interpretation

| Score | Meaning | Action |
|---|---|---|
| 80-100 | Excellent — rule is working as intended | No action needed |
| 40-79 | Fair — rule helps but may need refinement | Review false positives, clarify wording |
| 0-39 | Poor — rule may be too strict or ambiguous | Consider rewriting or retiring |

## Data Requirements

The effectiveness score becomes meaningful after:
- At least 10 evaluations involving the rule
- At least 7 days since rule creation (for prevention rate comparison)
- At least 1 true positive or false positive recorded

Rules with insufficient data return `precision: 1.0` (benefit of the doubt) and `prevention_rate: 0.0`.
