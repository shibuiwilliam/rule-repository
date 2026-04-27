# Rule Playground

The Rule Playground provides a sandbox environment for testing rule evaluations without side effects. No audit log entries are written, no LLM cache is populated, and no results are persisted.

## Purpose

- **Rapid iteration**: authors can test a rule statement against sample code before committing the rule to the repository.
- **Regression testing**: attach test cases to rules and run them on demand or as part of CI to catch unintended behavior changes.
- **Exploration**: experiment with modality, severity, and statement wording to see how the evaluation engine responds.

## Sandbox Evaluation

The playground evaluate endpoint (`POST /api/v1/playground/evaluate`) accepts a rule definition and sample code inline. It runs the same Gemini-powered evaluation pipeline as the production evaluate endpoint, but with three critical differences:

1. **No audit trail** -- sandbox evaluations are not recorded in the audit log.
2. **No LLM cache** -- results are never written to the response cache, so each call is a fresh LLM invocation.
3. **No persistence** -- the rule is not stored; it exists only for the duration of the request.

This makes the playground safe for experimentation without polluting production data.

## Test Cases

Each rule can have associated test cases stored in PostgreSQL. A test case consists of:

| Field | Description |
|---|---|
| `name` | Human-readable label for the test case |
| `input` | Sample code or facts to evaluate against the rule |
| `expected_verdict` | The expected outcome (`ALLOW`, `DENY`, or `WARN`) |

### Test Case Sources

Test cases can be created in three ways:

- **Manual** -- authored by a human via the API or frontend.
- **Historical** -- derived from past evaluations of the rule (the system selects representative examples from the audit log).
- **Gemini-generated** -- the LLM generates synthetic test cases that exercise edge cases of the rule statement.

### Test Runner

The test runner (`POST /api/v1/rules/{rule_id}/test-cases/run`) executes all test cases for a rule and returns a pass/fail summary. Each test case is evaluated independently through the sandbox pipeline. The response includes:

- Per-case verdict vs. expected verdict
- Overall pass rate
- Any cases where the actual verdict diverged from the expected verdict, with the LLM's reasoning

## Frontend

The playground is accessible at `/playground` in the frontend. It uses a split-pane layout:

- **Left pane**: rule editor (statement, modality, severity) and sample code input.
- **Right pane**: evaluation result (verdict, confidence, reasoning, fix suggestion, code locations).

The test case management UI is available on the rule detail page under a "Test Cases" tab.

## See Also

- [Playground API](../api/playground.md) -- endpoint reference
- [Evaluation Engine](evaluation-engine.md) -- how the underlying evaluation works
