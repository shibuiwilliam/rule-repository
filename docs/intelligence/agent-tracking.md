# Agent Performance Tracking

The Rule Repository tracks per-agent compliance metrics, enabling teams to measure which AI coding agents produce the most compliant code, identify improvement trends, and deliver targeted rule guidance.

## How It Works

Every evaluation can include an `agent_id` — a free-form identifier like `"claude-code"`, `"cursor"`, or `"ci-pipeline"`. When provided, the evaluation record is tagged with the agent identity, enabling per-agent analytics.

### Providing Agent Identity

**Via the API:**

```json
POST /api/v1/evaluate
{
  "diff": "...",
  "agent_id": "claude-code"
}
```

**Via CLI hooks:**

```bash
rulerepo-hook posthoc --file src/api.py --agent-id claude-code
# Or via environment variable:
export RULEREPO_AGENT_ID=claude-code
rulerepo-hook posthoc --file src/api.py
```

**Via MCP tools:**

The `evaluate_compliance` MCP tool accepts an optional `agent_id` parameter.

## API Endpoints

### GET /api/v1/intelligence/agents

Lists all agents with evaluation counts and compliance rates.

**Query Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `period_days` | 30 | Number of days to look back |

**Response:**

```json
{
  "agents": [
    {
      "agent_id": "claude-code",
      "total_evaluations": 1247,
      "compliance_rate": 0.892,
      "deny_count": 135
    },
    {
      "agent_id": "cursor",
      "total_evaluations": 834,
      "compliance_rate": 0.845,
      "deny_count": 129
    }
  ],
  "period_days": 30
}
```

### GET /api/v1/intelligence/agents/{agent_id}

Detailed analytics for a single agent.

**Response:**

```json
{
  "agent_id": "claude-code",
  "total_evaluations": 1247,
  "compliance_rate": 0.892,
  "compliance_trend": [
    { "date": "2026-04-20", "total": 45, "allow_count": 41, "compliance_rate": 0.911 },
    { "date": "2026-04-21", "total": 52, "allow_count": 44, "compliance_rate": 0.846 }
  ],
  "top_violations": [
    { "rule_id": "abc-123", "violation_count": 23, "rule_statement": "All functions MUST have docstrings" },
    { "rule_id": "def-456", "violation_count": 18, "rule_statement": "SQL queries MUST use parameterized inputs" }
  ]
}
```

## Targeted Rule Delivery

When an agent's identity is known, the rule selector **boosts rules the agent historically violates**. This means agents that struggle with a particular rule see it more prominently in their context.

The boost is +20 relevance points for rules in the agent's top 10 most-violated list. This happens automatically in `select_rules()` when `agent_id` is provided.

**Effect:** An agent that repeatedly breaks the "parameterized SQL queries" rule will see that rule ranked higher in its rule context, even if the file path match is weak.

## Database

Migration 017 adds `agent_id` VARCHAR(100) nullable column to the `evaluations` table with an index for fast per-agent queries.

## See Also

- [Intelligence Dashboard](dashboard.md) — corpus-wide analytics
- [Background Workers](../integrations/workers.md) — cron jobs including auto-promotion
- [Evaluation Engine](../architecture/evaluation-engine.md) — where agent_id flows through
