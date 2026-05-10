# MCP Server

The Rule Repository exposes a Model Context Protocol (MCP) server that allows AI agents to search, evaluate, govern, and retrieve rules directly through the MCP interface.

## Transport Modes

| Mode | Use Case | URL |
|---|---|---|
| **stdio** | Local agents (e.g., Claude Code running locally) | Launched as a subprocess |
| **streamable-http** | Remote agents, multi-agent setups | `http://localhost:8001/mcp` |

## Tools

The MCP server provides 18 tools organized into four categories: search and context, evaluation and compliance, governance, and cross-organizational.

### Search and Context

#### `search_rules`

Search the rule corpus by keyword or natural language query.

**Parameters:** `query` (string), `scope` (string, optional), `limit` (integer, optional)

#### `explain_rule`

Get a detailed explanation of a rule, including its rationale, context, preconditions, exceptions, and relationships.

**Parameters:** `rule_id` (string)

#### `get_rules_for_context`

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

#### `find_conflicts`

Find rules that conflict with each other within a scope or across scopes.

**Parameters:** `scope` (string, optional), `rule_id` (string, optional)

#### `discover_rules`

Scan project artifacts (configuration files, documentation) to discover implicit rules.

**Parameters:** `file_paths` (array of strings), `repository` (string, optional)

Returns a list of candidate rules discovered from the provided files, with confidence scores and suggested metadata.

### Evaluation and Compliance

#### `evaluate_compliance`

Evaluate a code change or action against applicable rules.

**Parameters:** `diff` (string), `file_path` (string), `intent` (string, optional), `environment` (string, optional -- when provided, evaluates against the snapshot deployed to this environment instead of the live rule corpus; valid values: `production`, `staging`, `development`)

#### `submit_feedback`

Submit a correction when an agent disagrees with or improves upon a rule verdict. Feeds the self-improving flywheel.

**Parameters:** `rule_id` (string), `evaluation_id` (string, optional), `correction` (string), `reason` (string, optional)

### Governance

#### `create_proposal`

Create a governance proposal for rule changes (create, amend, retire, merge, split, override). Proposals go through draft, review, approval, and enactment stages.

**Parameters:** `type` (string), `title` (string), `description` (string), `rule_id` (string, optional), `changes` (object, optional)

#### `get_proposal_status`

Check the current status, votes, and comments on a governance proposal.

**Parameters:** `proposal_id` (string)

#### `register_agent`

Register an AI agent with the governance system. Enables personalized rule delivery, trust level progression, and governance participation. Agents register with a classification clearance level that determines which rules they can access.

**Parameters:** `agent_id` (string), `agent_type` (string), `capabilities` (array of strings, optional), `clearance` (string, optional -- one of `public`, `internal`, `confidential`, `restricted`; defaults to `internal`)

#### `get_personalized_rules`

Get rules personalized to the agent's history and current task. Mastered rules are suppressed, and historically-violated rules are weighted higher.

**Parameters:** `agent_id` (string), `file_paths` (array of strings, optional), `task_context` (string, optional)

#### `challenge_verdict`

Challenge a verdict the agent disagrees with. Creates an audit trail and may trigger rule improvements if similar challenges accumulate.

**Parameters:** `verdict_id` (string), `reason` (string), `proposed_verdict` (string, optional)

#### `request_exception`

Request a formal exception to a rule for a specific context. If similar exceptions are requested frequently, the system may auto-draft a rule amendment proposal.

**Parameters:** `rule_id` (string), `context` (string), `justification` (string)

### Cross-Organizational

#### `evaluate_subject`

Evaluate any subject kind (code diff, contract clauses, HR event, transaction, etc.) against applicable rules using the polymorphic evaluation pipeline.

**Parameters:** `subject_kind` (string), `payload` (object), `facts` (object, optional), `mode` (string, optional)

#### `list_available_surfaces`

List all registered evaluation surfaces with their descriptions and supported subject kinds.

**Parameters:** none

#### `lookup_norm_lineage`

Trace a rule's derivation chain upstream to its source law/regulation, or downstream to all derived operational rules.

**Parameters:** `rule_id` (string), `direction` (string — `upstream` or `downstream`), `max_depth` (integer, optional)

#### `find_clause_conflicts`

Analyze a contract for clause-level conflicts against organizational standard clause rules.

**Parameters:** `contract_text` (string), `contract_type` (string, optional)

#### `check_action`

Evaluate a human action (overtime registration, leave request, expense submission) against applicable rules.

**Parameters:** `actor` (string), `action` (string), `payload` (object)

#### `review_communication`

Review an outbound communication (email, Slack message) for compliance with communication policies.

**Parameters:** `channel` (string), `content` (string), `recipient_type` (string, optional)

---

## Resources

| URI Pattern | Description |
|---|---|
| `rule://{id}` | A single rule by its ID |
| `ruleset://{scope}` | All rules within a given scope |

---

## Prompts

The MCP server exposes 3 prompt templates:

- **compliance_check** -- Systematic compliance evaluation against applicable rules
- **rule_summary** -- Executive summary of rules by scope
- **impact_analysis** -- Proposed change impact assessment

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

## Example: Agent Governance Flow

A coding agent can register, receive personalized rules, and challenge verdicts:

```
1. register_agent(agent_id="claude-code-1", agent_type="coding_assistant")
2. get_personalized_rules(agent_id="claude-code-1", file_paths=["src/api/auth.py"])
   -> Returns rules tailored to this agent's history (mastered rules suppressed)
3. evaluate_compliance(diff="...", file_path="src/api/auth.py")
   -> DENY on rule-42
4. challenge_verdict(verdict_id="v-123", reason="Rule does not apply to internal endpoints")
   -> Challenge recorded; if pattern accumulates, may auto-draft rule amendment
```

## See Also

- [Agent Hooks](agent-hooks.md) -- CLI-based agent integration (alternative to MCP)
- [Agentic Client SDK](../sdks/agentic-client.md) -- Python SDK for programmatic access
- [Agent Tracking](../intelligence/agent-tracking.md) -- Agent performance analytics
