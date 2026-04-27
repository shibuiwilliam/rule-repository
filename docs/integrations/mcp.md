# MCP Server

The Rule Repository exposes a Model Context Protocol (MCP) server that allows AI coding agents to search, evaluate, and retrieve rules directly through the MCP interface.

## Transport Modes

| Mode | Use Case | URL |
|---|---|---|
| **stdio** | Local agents (e.g., Claude Code running locally) | Launched as a subprocess |
| **streamable-http** | Remote agents, multi-agent setups | `http://localhost:8001/mcp` |

## Tools

The MCP server provides 6 tools:

### `search_rules`

Search the rule corpus by keyword or natural language query.

**Parameters:** `query` (string), `scope` (string, optional), `limit` (integer, optional)

### `evaluate_compliance`

Evaluate a code change against applicable rules.

**Parameters:** `diff` (string), `file_path` (string), `intent` (string, optional), `environment` (string, optional -- when provided, evaluates against the snapshot deployed to this environment instead of the live rule corpus; valid values: `production`, `staging`, `development`)

### `explain_rule`

Get a detailed explanation of a rule, including its rationale and relationships.

**Parameters:** `rule_id` (string)

### `find_conflicts`

Find rules that conflict with each other within a scope or across scopes.

**Parameters:** `scope` (string, optional), `rule_id` (string, optional)

### `discover_rules`

Scan project artifacts (configuration files, documentation) to discover implicit rules.

**Parameters:** `file_paths` (array of strings), `repository` (string, optional)

Returns a list of candidate rules discovered from the provided files, with confidence scores and suggested metadata.

### `get_rules_for_context`

Retrieve rules applicable to specific files, formatted for agent consumption. This is the primary tool for agent integrations.

**Parameters:** `file_paths` (array of strings), `format` (string, optional), `federation` (string, optional)

**Format options:**

| Format | Description | Token Budget |
|---|---|---|
| `instructions` | Concise natural-language directives | ~500 tokens |
| `checklist` | Markdown checkboxes for each rule | Medium |
| `detailed` | Full rule metadata including scope, modality, tags, and source | Largest |

Default format is `instructions`.

When `federation` is provided (a federation node ID), rules are resolved through the federation hierarchy for that node, returning the effective rule set after applying inheritance and overrides.

## Resources

| URI Pattern | Description |
|---|---|
| `rule://{id}` | A single rule by its ID |
| `ruleset://{scope}` | All rules within a given scope |

## Prompts

The MCP server exposes 3 prompt templates:

- **review-against-rules** -- Review code changes against all applicable rules
- **explain-violations** -- Explain why specific rules were violated
- **suggest-fix** -- Suggest a fix for a rule violation

## Configuration

### Claude Code

Add the following to your Claude Code MCP configuration (`.claude/mcp.json` or project settings):

```json
{
  "mcpServers": {
    "rule-repository": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/rule-repository/apps/server",
        "rulerepo-mcp"
      ],
      "env": {
        "RULEREPO_SERVER_URL": "http://localhost:8000"
      }
    }
  }
}
```

For remote mode (streamable-http), point your MCP client to `http://localhost:8001/mcp`.

### Docker Compose

The `mcp-server` service is included in `docker-compose.yml` and listens on port 8001:

```yaml
mcp-server:
  build:
    context: .
    dockerfile: infra/docker/Dockerfile.server
  command: ["rulerepo-mcp", "--transport", "streamable-http", "--port", "8001"]
  ports:
    - "8001:8001"
  environment:
    - RULEREPO_SERVER_URL=http://server:8000
```

## Example: Agent Using get_rules_for_context

When an agent is about to edit files, it can call `get_rules_for_context` to retrieve applicable rules:

```
Tool: get_rules_for_context
Input: {"file_paths": ["src/api/routes.py", "src/services/auth.py"], "format": "instructions"}

Output:
- All public API functions must have type hints and Google-style docstrings.
- Authentication changes require review from the security team owner.
- Never raise bare Exception; use the project exception hierarchy.
```

## See Also

- [Agent Hooks](agent-hooks.md) -- CLI-based agent integration (alternative to MCP)
- [Agentic Client SDK](../sdks/agentic-client.md) -- Python SDK for programmatic access
