# Rule Playground

The Rule Playground provides a sandbox environment for testing rule evaluations without side effects. No audit log entries are written, no LLM cache is populated, and no results are persisted.

## Purpose

- **Rapid iteration**: authors can test a rule statement against sample code or real-world scenarios before committing the rule to the repository.
- **Regression testing**: attach test cases to rules and run them on demand or as part of CI to catch unintended behavior changes.
- **Exploration**: experiment with modality, severity, and statement wording to see how the evaluation engine responds.

## Sandbox Evaluation

The playground evaluate endpoint (`POST /api/v1/playground/evaluate`) accepts a rule definition and either sample code or scenario facts inline. It runs the same Gemini-powered evaluation pipeline as the production evaluate endpoint, but with three critical differences:

1. **No audit trail** -- sandbox evaluations are not recorded in the audit log.
2. **No LLM cache** -- results are never written to the response cache, so each call is a fresh LLM invocation.
3. **No persistence** -- the rule is not stored; it exists only for the duration of the request.

This makes the playground safe for experimentation without polluting production data.

### Two Input Modes

The playground supports two input modes, each routed to a different evaluation prompt:

| Mode | Parameter | Evaluation Prompt | Best for |
|---|---|---|---|
| **Code** | `sample_code` (string) | `evaluate_code_change.txt` | Testing coding standards, API design rules, security rules |
| **Scenario** | `sample_facts` (dict with optional `narrative` key) | `evaluate_facts.txt` | Testing HR policies, contract clauses, expense rules, business procedures |

When `sample_code` is provided, the evaluation engine treats it as a code change (diff) and looks for specific file locations and line numbers. When `sample_facts` is provided, the engine evaluates the scenario as a facts-based situation and returns compliance reasoning without code-specific locations.

## Test Cases

Each rule can have associated test cases stored in PostgreSQL. A test case consists of:

| Field | Description |
|---|---|
| `name` | Human-readable label for the test case |
| `sample_input` | Code snippet, scenario description, or structured facts |
| `input_type` | `"code"` or `"facts"` — determines how the test runner evaluates the input |
| `expected_verdict` | The expected outcome (`ALLOW`, `DENY`, or `NEEDS_CONFIRMATION`) |

### Test Case Sources

Test cases can be created in three ways:

- **Manual** -- authored by a human via the API or frontend.
- **Historical** -- derived from past evaluations of the rule (the system selects representative examples from the audit log).
- **Gemini-generated** -- the LLM generates synthetic test cases that exercise edge cases of the rule statement.

### Test Runner

The test runner (`POST /api/v1/rules/{rule_id}/test-cases/run`) executes all test cases for a rule and returns a pass/fail summary. Each test case is evaluated independently through the sandbox pipeline, with the `input_type` field determining whether the input is treated as code or facts. The response includes:

- Per-case verdict vs. expected verdict
- Overall pass rate
- Any cases where the actual verdict diverged from the expected verdict, with the LLM's reasoning

## Frontend

The playground is accessible at `/playground` in the frontend. It uses a two-column layout:

- **Left column**: rule editor (statement, modality, severity).
- **Right column**: input with two tabs:
  - **Code** tab: textarea for code snippets or unified diffs.
  - **Scenario** tab: narrative textarea for describing a situation, plus an optional structured facts editor (dynamic key-value pairs).
- **Below**: evaluation result (verdict, confidence, reasoning, fix suggestion, and code locations for code mode).

The test case management UI is available on the rule detail page under a "Test Cases" tab.

## See Also

- [Playground API](../api/playground.md) -- endpoint reference
- [Evaluation Engine](evaluation-engine.md) -- how the underlying evaluation works
