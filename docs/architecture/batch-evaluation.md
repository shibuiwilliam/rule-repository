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

## Surface-Based Template Routing

The batch evaluator routes to surface-specific prompt templates based on the `surface` field on `EvaluationContext`. Instead of branching on `if context.diff:` (code) vs else (facts), the evaluator selects the template dynamically:

```python
def _select_template(context: EvaluationContext) -> str:
    surface = context.surface or ("code" if context.diff else "generic")
    template_path = PROMPTS_DIR / f"evaluate_batch_{surface}.txt"
    if template_path.exists():
        return template_path.read_text()
    return (PROMPTS_DIR / "evaluate_batch_generic.txt").read_text()
```

**Available batch templates:**

| Template | Surface | Key Instructions |
|---|---|---|
| `evaluate_batch_code.txt` | code | Diff references, file paths, line numbers |
| `evaluate_batch_contract.txt` | contract | Clause references, span offsets, clause revisions |
| `evaluate_batch_transaction.txt` | transaction | JSON paths, field-level remediations, approval routing |
| `evaluate_batch_document.txt` | document | Document spans, text_rewrite, section references |
| `evaluate_batch_message.txt` | message | Message segments, tone guidance, disclaimers |
| `evaluate_batch_human_action.txt` | human_action | Process compliance, authorization, event context |
| `evaluate_batch_generic.txt` | generic (fallback) | Domain-neutral facts-based evaluation |

Non-code templates do **not** reference code concepts (file paths, line numbers, function names). Each template defines its own location format and remediation kinds appropriate to its domain.

For backward compatibility, contexts without an explicit `surface` that have a `diff` field default to the code template.
