# Rule Maturity Model

New rules don't immediately block PRs. They progress through three maturity levels, with automatic promotion based on accuracy data.

## Maturity Levels

| Level | Verdict Behavior | Auto-Promotion Criteria |
|---|---|---|
| **experimental** | DENY downgraded to NEEDS_CONFIRMATION (shadow mode) | 30+ days, 20+ evaluations, FP rate < 5% |
| **stable** | DENY enforced, owner notified | 60+ days, FP rate < 1% |
| **proven** | DENY enforced, fully trusted | -- |

## Shadow Mode

When a rule has `maturity_level=experimental`, the evaluation engine intercepts DENY verdicts and downgrades them to NEEDS_CONFIRMATION. The reasoning is prefixed with `[SHADOW]` to indicate the rule would have blocked but didn't.

This means experimental rules:
- Appear in evaluation results (visible in audit trail)
- Never block CI or PR merges
- Accumulate accuracy data for auto-promotion

## Auto-Promotion Worker

The `auto_promote_rules` background worker runs daily at 4:00 AM UTC.

### Promotion Logic

For each rule with status APPROVED or EFFECTIVE and 20+ total evaluations:

1. Calculate false-positive rate: `false_positive_count / (false_positive_count + true_positive_count)`
2. Check days since creation

Transitions:
- **experimental → stable**: rule is 30+ days old AND FP rate < 5%
- **stable → proven**: rule is 60+ days old AND FP rate < 1%
- **stable/proven → experimental** (demotion): FP rate > 10%

### Accuracy Tracking

Two counters on each rule track accuracy:
- `true_positive_count`: incremented when an evaluation verdict is accepted (no correction filed)
- `false_positive_count`: incremented when a correction is submitted that matches the rule

## Database

Migration 015 adds to the `rules` table:
- `maturity_level` VARCHAR(20) DEFAULT 'experimental'
- `false_positive_count` INTEGER DEFAULT 0
- `true_positive_count` INTEGER DEFAULT 0

Existing APPROVED/EFFECTIVE rules are backfilled as `proven`.

## API

Rules returned by the API include `maturity_level` in the response. The `GET /api/v1/rules` endpoint accepts `maturity_level` as a filter parameter.

## Domain Model

`domain/rule.py` includes the `MaturityLevel` enum:
```python
class MaturityLevel(str, enum.Enum):
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    PROVEN = "proven"
```

## See Also

- [Evaluation Engine](evaluation-engine.md) -- shadow mode implementation
- [Background Workers](../integrations/workers.md) -- auto-promotion cron job
- [Correction Flywheel](../intelligence/flywheel.md) -- how corrections feed accuracy tracking
