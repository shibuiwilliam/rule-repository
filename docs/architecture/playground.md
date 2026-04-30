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

## Suggest by LLM

The playground provides a `POST /api/v1/playground/suggest-input` endpoint that uses Gemini to generate realistic test inputs for a rule. You can request either a **violating** input (should trigger DENY) or a **compliant** input (should trigger ALLOW), in either code or scenario mode.

The endpoint accepts `rule_id` (to look up an existing rule) or inline `rule_statement`/`rule_modality`/`rule_severity`. It returns a `sample_input` string and a `description` explaining what the generated input demonstrates.

## Frontend

The playground is accessible at `/playground` in the frontend. It uses a two-column layout:

- **Left column**: rule definition with two modes:
  - **Pick Rules** -- search for and select one or more registered rules from the database. Multi-select supported; each selected rule is evaluated independently.
  - **Manual** -- type a rule statement directly with modality and severity dropdowns.
- **Right column**: test input with two tabs:
  - **Code** tab: textarea for code snippets or unified diffs.
  - **Scenario** tab: narrative textarea for describing a situation, plus an optional structured facts editor (dynamic key-value pairs).
  - **Suggest by LLM**: two buttons ("Violating Input" / "Compliant Input") that call Gemini to generate a realistic test input and populate the textarea automatically.
- **Below**: evaluation results. For multi-rule evaluation, a summary bar shows ALLOW/DENY/NEEDS_CONFIRMATION counts, followed by per-rule result cards.

The test case management UI is available on the rule detail page under a "Test Cases" tab.

## See Also

- [Playground API](../api/playground.md) -- endpoint reference
- [Evaluation Engine](evaluation-engine.md) -- how the underlying evaluation works
