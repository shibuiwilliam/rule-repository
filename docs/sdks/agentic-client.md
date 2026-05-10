# Agentic Client SDK

The Agentic Client wraps the Rule Repository server API for use in AI agent workflows. It provides a high-level interface for evaluating code changes against rules and retrieving applicable rules for a given context.

## Installation

The agentic client is a workspace dependency. Install it alongside the base `rulerepo` client:

```bash
cd packages/agentic-client
uv sync
```

## Usage

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient(
    server_url="http://localhost:8000",
    scope="engineering",       # optional: limit to rules in this scope
    api_key="your-api-key",    # optional: for authenticated servers
) as client:

    # Evaluate code changes against applicable rules
    result = await client.evaluate(
        context={"file": "src/main.py", "diff": "..."},
        intent="Refactoring the config loader",
        mode="preflight",  # "preflight" (before edit) or "postcheck" (after edit)
    )
    print(result.verdict)       # "ALLOW", "DENY", or "NEEDS_CONFIRMATION"
    print(result.violations)    # list of rule violations, if any

    # Get rules that apply to specific files
    rules = await client.get_applicable_rules(
        file_paths=["src/main.py", "src/config.py"],
    )
    for rule in rules:
        print(f"{rule.id}: {rule.statement}")
```

## API Reference

### `AgenticRuleClient(server_url, scope=None, api_key=None)`

Creates a new client instance. Use as an async context manager (`async with`).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `server_url` | `str` | Yes | Base URL of the Rule Repository server |
| `scope` | `str` | No | Limit operations to rules in this scope (e.g., `"engineering"`, `"legal"`) |
| `api_key` | `str` | No | API key for authenticated servers |

### `evaluate(context, intent, mode="preflight")`

Evaluates a code change against applicable rules. Delegates to `POST /api/v1/evaluate` on the server.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `context` | `dict` | Yes | The change context (file paths, diffs, metadata) |
| `intent` | `str` | Yes | Natural-language description of what the change does |
| `mode` | `str` | No | `"preflight"` (before edit) or `"postcheck"` (after edit). Default: `"preflight"` |

**Returns:** An evaluation result with `verdict`, `violations`, and `suggestions`.

### `get_applicable_rules(file_paths)`

Returns rules that apply to the given file paths. Delegates to `POST /api/v1/evaluate` with a lookup mode.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `file_paths` | `list[str]` | Yes | File paths to match against rule scopes |

**Returns:** A list of rule objects with `id`, `statement`, `scope`, `modality`, and `tags`.

### `evaluate_subject(subject_type, payload, scope=None, mode="preflight", metadata=None)`

Evaluates a typed subject (contract, HR event, expense claim, etc.) against applicable rules using the Phase 7b subject envelope.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `subject_type` | `str` | Yes | Subject kind (e.g., `"hr_event"`, `"contract_clause"`, `"expense_claim"`) |
| `payload` | `dict` | Yes | Subject-specific data |
| `scope` | `str` | No | Override the default scope |
| `mode` | `str` | No | `"preflight"`, `"posthoc"`, or `"sidecar"`. Default: `"preflight"` |
| `metadata` | `dict` | No | Optional actor, timestamp, source system metadata |

### `get_applicable_rules_for_surface(surface, scope=None, department=None, language="ja", **kwargs)`

Get rules applicable to a specific evaluation surface.

### Domain Convenience Methods

```python
# Contract review
rules = await client.get_rules_for_contract(contract_type="nda", language="ja")
result = await client.evaluate_contract("clause text...", contract_type="nda")

# Transaction validation
rules = await client.get_rules_for_transaction(transaction_type="expense", amount=30000)
result = await client.evaluate_transaction({"amount_jpy": 30000}, transaction_type="expense")

# Communication review
rules = await client.get_rules_for_communication(channel="email", audience="external")
result = await client.evaluate_communication("Dear Customer...", channel="email")
```

## Current Limitations

The following features are planned but **not yet implemented**:

- **Result caching** -- repeated evaluations with the same inputs will make a new server request each time.
- **Reason graphs** -- the evaluation result does not yet include a structured graph of reasoning steps.

## Error Handling

The client raises `rulerepo_agentic.errors.AgenticClientError` on server communication failures. Network errors and HTTP 5xx responses are retried once before raising.

## See Also

- [CLI Tools](cli.md) -- for command-line usage in CI and hooks
- [MCP Server](../integrations/mcp.md) -- for direct MCP integration with AI agents
