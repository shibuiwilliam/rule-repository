# Federation

Federation enables hierarchical rule composition across organizational boundaries. Rules can be defined at the organization level and inherited, extended, or overridden at the team and project levels.

## Hierarchy

Federation uses a three-level hierarchy:

```
Organization
  └── Team
        └── Project
```

Each level is represented by a **FederationNode** that can hold its own rules and optionally override rules inherited from its parent.

## Domain Models

### FederationNode

A node in the federation hierarchy.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique identifier |
| `name` | string | Node name (e.g., "Engineering", "Backend Team", "auth-service") |
| `level` | enum | `organization`, `team`, or `project` |
| `parent_id` | UUID (nullable) | Parent node (null for organization-level nodes) |
| `description` | string | Human-readable description |
| `default_scope` | string | Default scope applied to rules at this node |

### EffectiveRule

A rule as seen from a specific federation node, after applying the ancestor chain.

| Field | Type | Description |
|---|---|---|
| `rule` | Rule | The resolved rule |
| `source_node_id` | UUID | The federation node where this rule is defined |
| `overridden_rule_id` | UUID (nullable) | The parent rule this overrides, if any |
| `inherited` | boolean | Whether the rule is inherited from an ancestor |

## Federation Resolver

When rules are requested for a federation node, the resolver:

1. **Walks the ancestor chain** from the requested node up to the organization root.
2. **Collects rules** at each level.
3. **Applies overrides**: if a child node defines a rule that overrides a parent rule, the child version wins.
4. Returns the **effective rule set** -- the merged result of all levels.

This ensures that project-level teams see organization-wide policies plus their own customizations, without duplication.

## Integration Points

### Evaluation

The evaluation engine accepts a `federation_id` in the rule selector. When provided, the engine resolves the effective rule set for that federation node before evaluating compliance.

### MCP

The `get_rules_for_context` MCP tool accepts an optional `federation` parameter. When set, rules are resolved through the federation hierarchy for the specified node.

### Diff View

The federation API provides a diff endpoint (`GET /api/v1/federations/{node_id}/diff`) that shows how a node's effective rules differ from its parent -- useful for auditing overrides.

## API

See [Federation API](../api/federation.md) for endpoint details.

## See Also

- [Architecture Overview](overview.md) -- system-wide component map
- [Evaluation Engine](evaluation-engine.md) -- how federation integrates with evaluation
