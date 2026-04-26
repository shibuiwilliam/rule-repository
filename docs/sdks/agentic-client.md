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
    print(result.verdict)       # "ALLOW", "WARN", or "DENY"
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

## Current Limitations

The following features are planned but **not yet implemented**:

- **Result caching** -- repeated evaluations with the same inputs will make a new server request each time.
- **Reason graphs** -- the evaluation result does not yet include a structured graph of reasoning steps.
- **Two-stage evaluation** -- preflight and postcheck currently use the same evaluation path; a dedicated two-stage pipeline with diff-aware re-evaluation is planned.

## Error Handling

The client raises `rulerepo_agentic.errors.AgenticClientError` on server communication failures. Network errors and HTTP 5xx responses are retried once before raising.

## See Also

- [CLI Tools](cli.md) -- for command-line usage in CI and hooks
- [MCP Server](../integrations/mcp.md) -- for direct MCP integration with AI agents
