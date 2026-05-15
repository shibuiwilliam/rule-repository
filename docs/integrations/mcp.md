# MCP Server

The Rule Repository exposes a Model Context Protocol (MCP) server that allows AI agents to search, evaluate, govern, and retrieve rules directly through the MCP interface.

## Transport Modes

| Mode | Use Case | URL |
|---|---|---|
| **stdio** | Local agents (e.g., Claude Code running locally) | Launched as a subprocess |
| **streamable-http** | Remote agents, multi-agent setups | `http://localhost:8001/mcp` |

## Tools

The MCP server provides 24 tools organized into four categories: search and context, evaluation and compliance, governance, and cross-organizational.

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

**Parameters:** `diff` (string), `file_paths` (array of strings, optional), `intended_action` (string, optional), `scope` (string, optional), `facts` (string, optional -- JSON key-value context), `environment` (string, optional -- when provided, evaluates against the snapshot deployed to this environment instead of the live rule corpus; valid values: `production`, `staging`, `development`)

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

### Domain-Specific Rule Retrieval

#### `get_rules_for_contract_review`

Get applicable rules for reviewing a contract. Primary tool for legal review agents.

**Parameters:** `contract_type` (string), `parties` (array, optional), `governing_law` (string, optional), `language` (string, default "ja"), `max_rules` (integer, default 15), `format` (string, default "instructions")

#### `get_rules_for_transaction`

Get applicable rules for validating a business transaction. Primary tool for finance/HR automation agents.

**Parameters:** `transaction_type` (string), `amount` (number, optional), `department` (string, optional), `actor_role` (string, optional), `max_rules` (integer, default 15), `format` (string, default "instructions")

#### `get_rules_for_communication`

Get applicable rules for reviewing communications. Primary tool for content review and compliance agents.

**Parameters:** `channel` (string), `audience` (string, optional), `content_type` (string, optional), `max_rules` (integer, default 15), `format` (string, default "instructions")

### Domain-Specific Evaluation

#### `evaluate_contract`

Evaluate a contract or contract clause against applicable rules. Returns verdicts with clause-level remediations.

**Parameters:** `contract_text` (string), `contract_type` (string, default "other"), `language` (string, default "ja"), `focus_areas` (array, optional)

#### `evaluate_transaction`

Evaluate a business transaction against applicable rules. Returns verdicts with field-level remediations.

**Parameters:** `transaction_payload` (string — JSON), `transaction_type` (string, default "other"), `actor_role` (string, optional), `department` (string, optional)

#### `evaluate_communication`

Evaluate a communication draft against applicable rules. Returns verdicts with text-level remediations.

**Parameters:** `text` (string), `channel` (string, default "email"), `audience` (string, default "external"), `language` (string, default "ja")

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

---

> **Tool count accuracy note (2026-05-15):** The 24 tools listed above have been verified against the `async def` function definitions in `apps/server/src/rulerepo_server/mcp/tools.py`. If tools are added or removed in the code, update this document accordingly.

## See Also

- [Agent Hooks](agent-hooks.md) -- CLI-based agent integration (alternative to MCP)
- [Agentic Client SDK](../sdks/agentic-client.md) -- Python SDK for programmatic access
- [Agent Tracking](../intelligence/agent-tracking.md) -- Agent performance analytics
