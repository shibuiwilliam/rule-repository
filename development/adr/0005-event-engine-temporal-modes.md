# ADR 0005: Event Engine Temporal Modes

## Status

Accepted

## Context

The Event Engine from Phase 7 supports single-event evaluation. HR compliance requires temporal reasoning: monthly overtime accumulations (Labor Standards Act §36), annual ceilings (720-hour cap), and 36-Agreement special clause thresholds. A single overtime entry of 10 hours is compliant; the 46th cumulative hour in a month may not be.

## Decision

### Evaluation Modes

The Event Engine supports three modes via `evaluation_mode` parameter:

1. **single** (default) — evaluate the event alone
2. **sequence** — include an `EventWindow` (monthly prior events) as context
3. **calendar** — include a `CalendarContext` (annual aggregates) as context

### Domain Types

- `EventEvaluationMode` enum in `domain/event_sequence.py`
- `EventRecord` — a historical event for context
- `EventWindow` — time-bounded window with events and pre-computed aggregates
- `CalendarContext` — fiscal year aggregates including YTD overtime, monthly breakdown, 36-Agreement status
- `SequenceContext` — combined wrapper

### Temporal Context in Prompts

The `EventAdapter.render_for_llm()` includes temporal context in the narrative sent to the LLM. Dedicated prompt templates under `prompts/event/` guide the LLM to reason about cumulative thresholds.

### API

`POST /api/v1/evaluate/event` accepts `evaluation_mode`, `event_window`, and `calendar_context` parameters. The endpoint routes through the standard evaluation pipeline with `subject_kind=event`.

### Context Source

The caller is responsible for providing the temporal context. In production, this context comes from HR system adapters (Workday, SmartHR, freee HR) that query recent events and aggregates. The API accepts pre-computed context to remain adapter-agnostic.

## Consequences

- Sequence mode enables monthly threshold detection (e.g., 45-hour monthly overtime cap).
- Calendar mode enables annual ceiling enforcement (e.g., 720-hour annual cap).
- The Event Engine remains subject-agnostic in the orchestrator; temporal logic is in the adapter and prompts.
- HR system adapters (Phase 10) will provide the temporal context automatically.
