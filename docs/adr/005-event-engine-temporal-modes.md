# ADR 005: Event Engine Temporal Modes

**Status:** Accepted

**Date:** 2026-05-08

## Context

HR and business event evaluation requires temporal context that simple point-in-time checks cannot provide. For example, overtime compliance depends on monthly totals, leave compliance depends on annual balances, and fatigue risk depends on multi-month patterns.

## Decision

The Event Engine supports three temporal modes:

1. **Single mode** -- evaluate the event in isolation. Used for simple compliance checks (e.g., "is this leave request for a valid category?").

2. **Sequence mode** -- evaluate the event in the context of a windowed sequence of prior events. The `EventWindow` provides the N most recent events of the same type. Used for monthly aggregation (e.g., "does this overtime registration push the monthly total above 45 hours?").

3. **Calendar mode** -- evaluate the event in the context of annual aggregates. The `CalendarContext` provides year-to-date totals, monthly breakdowns, and rolling averages. Used for annual compliance (e.g., "has the employee taken the required 5 days of paid leave this year?" or "is the 360-hour annual overtime limit at risk?").

Domain types are defined in `domain/event_sequence.py`. The HR plugin's `FormEvaluator` selects the appropriate mode based on the rule's temporal requirements.

## Consequences

- Event evaluation requires the Fact Store to resolve employee state and historical data
- Calendar mode evaluations are more expensive (larger context) but catch patterns that single-mode misses
- The temporal mode is transparent to the orchestrator -- the HR plugin handles mode selection internally
