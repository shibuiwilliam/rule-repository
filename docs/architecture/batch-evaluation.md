# Batched Evaluation

## Overview

The evaluation engine supports **batched evaluation** — sending all selected rules to the LLM in a single call instead of making one API call per rule. This delivers 5-20x fewer API calls, lower latency, and better verdicts because the LLM can see rule interactions.

## How It Works

```
┌─────────────────────────────────┐
│        EvaluationService         │
│ service.py → evaluate_batch()    │
└───────────┬─────────────────────┘
            │
    ┌───────▼────────┐
    │ batch_evaluator │
    │                 │
    │  ┌────────────┐ │
    │  │ Build      │ │   All rules + context in one prompt
    │  │ prompt     │ │
    │  └─────┬──────┘ │
    │        │        │
    │  ┌─────▼──────┐ │
    │  │ Gemini     │ │   Single Flash API call
    │  │ Flash      │ │   → JSON array of per-rule verdicts
    │  └─────┬──────┘ │
    │        │        │
    │  ┌─────▼──────┐ │
    │  │ Pro        │ │   Only for DENY + CRITICAL rules
    │  │ confirm    │ │   (confirmation pass)
    │  └─────┬──────┘ │
    │        │        │
    │  ┌─────▼──────┐ │
    │  │ Fallback   │ │   On any failure → per-rule asyncio.gather()
    │  │ per-rule   │ │
    │  └────────────┘ │
    └─────────────────┘
```

## Structured Output Schema

The batch call requests a JSON object with a `verdicts` array:

```json
{
  "verdicts": [
    {
      "rule_index": 0,
      "rule_id": "uuid",
      "verdict": "ALLOW",
      "confidence": 0.95,
      "reasoning": "The code change does not affect...",
      "issue_description": "",
      "fix_suggestion": null,
      "locations": []
    }
  ]
}
```

Each entry corresponds to one rule, in the order they were listed in the prompt.

## Tiered Model Strategy

| Rule Severity | Batch (Flash) | Confirmation (Pro) |
|--------------|---------------|-------------------|
| LOW / MEDIUM | Evaluated | Not re-evaluated |
| HIGH | Evaluated | Not re-evaluated |
| CRITICAL + DENY | Evaluated | Re-evaluated with Pro model |
| CRITICAL + ALLOW | Evaluated | Not re-evaluated |

Only rules that receive a DENY verdict **and** have CRITICAL severity get a Pro confirmation pass. This keeps Pro costs minimal while ensuring high-severity denials are accurate.

## Fallback Behavior

If the batch call fails for any reason (API error, timeout, response parsing failure, prompt too large), the system transparently falls back to per-rule evaluation using `asyncio.gather()` — the same behavior as before batching was introduced.

## Caching

- Batch cache key: `hash(sorted_rule_ids + context_hash + model_id)`
- If any rule in the batch has been revised since the cache entry was stored, the cache entry is invalidated
- Pro confirmation results are cached individually using the existing per-rule cache

## Configuration

Batching is the default evaluation path. No configuration flag is needed to enable it.

- Max prompt size: 30,000 characters (configurable in `batch_evaluator.py`)
- Max diff size: 8,000 characters (truncated if longer)
- Thinking level: `medium` for batches, `high` for Pro confirmation
