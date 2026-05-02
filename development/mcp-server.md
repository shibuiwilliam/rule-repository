# MCP Server

The Rule Repository exposes an MCP (Model Context Protocol) server that allows AI coding agents (Claude Code, Cursor, etc.) to search rules, evaluate compliance, and understand rule relationships through a standardized tool interface.

Source code: `apps/server/src/rulerepo_server/mcp/`

Architecture principle: the MCP server is a **thin adapter layer**. All tools delegate to existing services (`SearchService`, `EvaluationService`, `ContextDeliveryService`, `DiscoveryService`, etc.). Business logic must never be duplicated in MCP tool implementations.

---

## Transport

The MCP server supports two transport modes, controlled by the `MCP_TRANSPORT` environment variable:

| Transport | When to use | Default |
|---|---|---|
| **stdio** | Local agents (Claude Code, Cursor). The agent spawns the process and communicates over stdin/stdout. | Yes (default) |
| **streamable-http** | Remote agents, multi-client scenarios. Runs an HTTP server. | Set `MCP_TRANSPORT=streamable-http` |

For HTTP transport, the server listens on the port specified by `MCP_PORT` (default `8001`).

---

## Startup

### Local (stdio)

```bash
cd apps/server
uv run rulerepo-mcp
```

Or via Makefile targets:

```bash
make mcp.stdio          # stdio transport
make mcp.http           # streamable-http transport on port 8001
```

### Docker

The `mcp-server` service in `docker-compose.yml` runs the MCP server alongside the main API server. It connects to the same PostgreSQL, Elasticsearch, and Neo4j instances.

---

## Claude Code Configuration

Add the following to your Claude Code MCP configuration (`.claude/settings.json` or the global MCP config):

```json
{
  "mcpServers": {
    "rule-repository": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rule-repository/apps/server", "rulerepo-mcp"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://rule:rule@localhost:5432/ruledb",
        "ELASTICSEARCH_URL": "http://localhost:9200",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "ruledev"
      }
    }
  }
}
```

If the Rule Repository stack is running via Docker Compose, adjust the connection URLs to point to `localhost` with the exposed ports (5432, 9200, 7687).

---

## Tools

All 12 tools are registered in `mcp/tools.py` via the `register_tools()` function.

### search_rules

Search the rule repository for rules matching a natural language query.

```
search_rules(
    query: str,                          # Natural language search query (required)
    scope: str | None = None,            # Narrow to scope (e.g., "engineering/python")
    modality: str | None = None,         # MUST, MUST_NOT, SHOULD, MAY, INFO
    severity: str | None = None,         # LOW, MEDIUM, HIGH, CRITICAL
    top_k: int = 10                      # Maximum results
) -> list[dict]
```

**Delegates to**: `ElasticsearchRuleIndex.search_fulltext()`, then hydrates from `PostgresRuleRepository`.

**Returns**: List of rule dicts with id, statement, modality, severity, scope, tags, rationale, status.

**When to use**: When you need to find organizational rules, policies, regulations, or guidelines relevant to a task or decision.

---

### explain_rule

Get a detailed explanation of a rule including rationale, provenance, relationships, and revision history.

```
explain_rule(
    rule_id: str,                        # UUID of the rule (required)
    depth: int = 2                       # Relationship traversal depth (1-5)
) -> dict
```

**Delegates to**: `PostgresRuleRepository.get_by_id()`, `.get_revisions()`, `.get_relationships()`.

**Returns**: Full rule metadata including statement, modality, severity, status, rationale, scope, tags, source_refs, governance, effective_period, revision_count, latest_revision (number, changed_by, note), and relationships (type, source_id, target_id).

**When to use**: When you need to understand WHY a rule exists, WHERE it came from, and HOW it relates to other rules.

---

### find_conflicts

Find rules that may conflict with a given rule or proposed rule statement.

```
find_conflicts(
    rule_id: str | None = None,          # UUID of an existing rule
    proposed_statement: str | None = None,# Text of a proposed new rule
    scope: str | None = None             # Limit search to a scope
) -> list[dict]
```

**Delegates to**: `ElasticsearchRuleIndex.search_fulltext()` for semantic similarity search.

If `rule_id` is provided without `proposed_statement`, the tool fetches the rule's statement and uses it as the search query. The source rule is excluded from results.

**Returns**: List of dicts with `rule_id`, `similarity_score`, `potential_conflict: true`. Returns up to 10 results.

**When to use**: When proposing a new rule or changing an existing one, to check for contradictions with the existing corpus.

---

### evaluate_compliance

Evaluate whether a code change or action complies with applicable rules.

```
evaluate_compliance(
    diff: str | None = None,             # Unified diff text
    file_paths: list[str] | None = None, # Files being modified
    intended_action: str | None = None,  # NL description of the action
    scope: str | None = None,            # Rule scope filter
    facts: str | None = None,            # JSON string of key-value context facts
    environment: str | None = None       # Deployment environment (e.g., "production")
) -> dict
```

**Delegates to**: `EvaluationService.evaluate()` with `mode="preflight"`.

**The `environment` parameter**: When provided (e.g., `"production"`, `"staging"`), the evaluation uses the snapshot deployed to that environment instead of the live rule corpus. This enables deterministic evaluation against a pinned rule set. The rule selector looks up the active `RuleSetDeploymentModel` for the given environment, deserializes the associated snapshot, and evaluates only against those rules.

**Returns**: Dict with `overall_verdict` (ALLOW/DENY/NEEDS_CONFIRMATION), `rules_evaluated`, `rules_violated`, `violations` (list with rule_id, rule_statement, issue, fix), `warnings`, `fix_summary`.

**When to use**: Before making changes that may be subject to organizational rules. Accepts a unified diff, file paths, or a natural language action description.

---

### discover_rules

Discover implicit rules from a codebase. Analyzes code patterns, config files, and CLAUDE.md to propose candidate rules.

```
discover_rules(
    file_contents: str,                  # JSON string mapping file paths to contents
    repository: str | None = None,       # Repository name or URL
    sources: list[str] | None = None     # Source types to analyze
) -> str
```

**Delegates to**: `DiscoveryService.start_scan()` and `DiscoveryService.get_candidates()`.

**Input**: `file_contents` must be a valid JSON string mapping file paths to file content strings (e.g., `'{"pyproject.toml": "...", "CLAUDE.md": "..."}'`).

**Default sources**: `["code_patterns", "linter_config", "claude_md"]` when not specified.

**Returns**: Formatted text summary listing discovered candidate rules with source type, confidence, statement, and rationale. Includes the scan ID for subsequent approve/dismiss via the REST API.

**When to use**: When bootstrapping rules for a new project. Provide contents of relevant files (configs, CLAUDE.md, linter configs, representative source files) and the service will extract implicit conventions as candidate rules.

---

### get_rules_for_context

**This is the key tool for coding agents.** Returns rules formatted for context injection, optimized for the agent's context window.

```
get_rules_for_context(
    file_paths: list[str] | None = None, # Files being worked on
    repository: str | None = None,       # Repository name
    task_description: str | None = None, # What you're doing
    languages: list[str] | None = None,  # Languages (auto-detected if omitted)
    max_rules: int = 15,                 # Maximum rules to return
    format: str = "instructions",        # Output format
    federation: str | None = None        # UUID of a federation node
) -> str
```

**Delegates to**: `ContextDeliveryService.get_formatted_rules()`.

**The `federation` parameter**: When provided, only rules effective in that federation (including inherited rules and overrides resolved through the ancestor chain) are returned. This allows agents to get project-specific or team-specific rule sets within a federated hierarchy. The federation resolver walks from the specified node up to the root, collecting rules and applying overrides at each level, producing the final merged set.

**Output formats**:

| Format | Best for | Description |
|---|---|---|
| `instructions` | Working context (default) | Concise MUST/SHOULD/MAY hierarchy, optimized for agent consumption |
| `checklist` | PR review | Markdown checkboxes suitable for review checklists |
| `detailed` | Learning/onboarding | Full metadata with rationale, scope, and governance info |

**When to use**: Call this when you start working on a file or task to understand what organizational rules, conventions, and policies apply. This should be the first tool a coding agent calls.

---

### create_proposal

Create a governance proposal for a rule change (Phase 6a).

```
create_proposal(
    title: str,                          # Proposal title (required)
    description: str,                    # Detailed description (required)
    proposal_type: str,                  # "create", "modify", or "retire"
    rule_id: str | None = None,          # UUID of existing rule (for modify/retire)
    proposed_changes: str | None = None  # JSON string of proposed changes
) -> dict
```

**Delegates to**: `ProposalService.create_proposal()`.

**Returns**: Dict with proposal ID, title, status, and creation timestamp.

**When to use**: When you want to formally propose creating a new rule, modifying an existing one, or retiring a rule through the governance workflow.

---

### get_proposal_status

Check the status of a governance proposal (Phase 6a).

```
get_proposal_status(
    proposal_id: str                     # UUID of the proposal (required)
) -> dict
```

**Delegates to**: `ProposalService.get_proposal()`.

**Returns**: Dict with proposal details including status, votes, comments, and enactment state.

**When to use**: When you need to check whether a proposal has been approved, how many votes it has received, or whether it has been enacted.

---

### register_agent

Register an agent profile for personalized governance (Phase 6b).

```
register_agent(
    agent_id: str,                       # Unique agent identifier (required)
    name: str,                           # Human-readable agent name (required)
    description: str | None = None,      # Agent description
    capabilities: str | None = None      # JSON string of agent capabilities
) -> dict
```

**Delegates to**: `AgentGovernanceService.register_agent()`.

**Returns**: Dict with agent profile including ID, name, trust level, and registration timestamp.

**When to use**: When an agent first connects and needs to establish its identity for trust-based rule personalization.

---

### get_personalized_rules

Get rules tailored to an agent's trust level and compliance history (Phase 6b).

```
get_personalized_rules(
    agent_id: str,                       # Registered agent ID (required)
    scope: str | None = None,            # Rule scope filter
    file_paths: list[str] | None = None  # Files being worked on
) -> dict
```

**Delegates to**: `AgentGovernanceService.get_personalized_rules()`.

**Returns**: Dict with personalized rule set, trust level context, and any active exceptions.

**When to use**: Instead of `get_rules_for_context` when the agent is registered and wants rules adapted to its trust level and demonstrated mastery.

---

### challenge_verdict

Challenge an evaluation verdict through the negotiation mechanism (Phase 6b).

```
challenge_verdict(
    agent_id: str,                       # Registered agent ID (required)
    rule_id: str,                        # UUID of the rule being challenged (required)
    evaluation_id: str,                  # UUID of the evaluation (required)
    argument: str                        # Reasoning for the challenge (required)
) -> dict
```

**Delegates to**: `AgentGovernanceService.create_negotiation()`.

**Returns**: Dict with negotiation ID, status, and initial response.

**When to use**: When an agent believes a DENY verdict is incorrect and wants to formally challenge it with reasoning.

---

### request_exception

Request a temporary exception from a specific rule (Phase 6b).

```
request_exception(
    agent_id: str,                       # Registered agent ID (required)
    rule_id: str,                        # UUID of the rule (required)
    reason: str,                         # Justification for the exception (required)
    duration: str | None = None          # Duration (e.g., "24h", "7d")
) -> dict
```

**Delegates to**: `AgentGovernanceService.request_exception()`.

**Returns**: Dict with exception request ID, status, and expiration if approved.

**When to use**: When an agent needs a temporary exemption from a rule for a justified reason (e.g., emergency fix, migration in progress).

---

## Resources

Resources are registered in `mcp/resources.py` via `register_resources()`.

### rule://{rule_id}

A single rule with full metadata, accessible by UUID.

**Returns**: Dict with id, statement, modality, severity, status, scope, tags, rationale, governance.

**Delegates to**: `PostgresRuleRepository.get_by_id()`.

### ruleset://{scope}

A formatted rule set for a scope -- like a dynamic CLAUDE.md section that is always up-to-date.

**Example**: `ruleset://engineering/python` returns all Python coding rules formatted as actionable instructions.

**Returns**: Formatted string (using the `instructions` format from `ContextDeliveryService`).

**Delegates to**: `ContextDeliveryService.get_formatted_rules()`.

---

## Prompts

Prompts are registered in `mcp/prompts.py` via `register_prompts()`. They provide structured workflows that guide the agent through multi-step tasks.

### compliance_check

Parameters: `context` (string), `action` (string).

Workflow: search for applicable rules, assess compliance for each, explain violations with fix suggestions, summarize with ALLOW/DENY/NEEDS_CONFIRMATION verdict.

### rule_summary

Parameters: `scope` (string).

Workflow: search rules in scope, group by modality, list key obligations, highlight CRITICAL rules, note conflicts.

### impact_analysis

Parameters: `rule_id` (string), `proposed_change` (string).

Workflow: explain current rule, check for conflicts with proposed change, find dependent rules, assess risk, recommend whether to proceed.

---

## Server Creation

The MCP server is created by `create_mcp_server()` in `mcp/server.py`. It instantiates a `FastMCP` instance with a descriptive name and description, then registers all tools, resources, and prompts via their respective `register_*` functions.

```python
mcp = FastMCP(
    "Rule Repository",
    description="Search, evaluate, and manage natural-language rules..."
)
register_tools(mcp)
register_resources(mcp)
register_prompts(mcp)
```

---

## Testing

### Unit Tests

Mock the underlying services (database sessions, Elasticsearch client, Gemini client) in unit tests. The MCP tools are thin wrappers, so testing focuses on parameter mapping and response formatting.

### Integration Tests

Use the MCP client SDK to connect to the server in stdio mode and invoke tools end-to-end. Requires the full Docker Compose stack (PostgreSQL, Elasticsearch, Neo4j) to be running.

### Key Testing Rules

- Never call the real Gemini API in unit tests. Use a mock client.
- Gate live LLM integration tests behind `RULEREPO_LIVE_LLM=1`.
- Test error paths: missing rules, unavailable services, invalid parameters.
