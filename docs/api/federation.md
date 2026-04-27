# Federation API

The Federation API manages hierarchical rule composition across organizational boundaries (organization, team, project).

## Endpoints

### Create a federation node

```
POST /api/v1/federations
```

**Request body:**

```json
{
  "name": "Backend Team",
  "level": "team",
  "parent_id": "org-uuid-...",
  "description": "Backend engineering team",
  "default_scope": "backend"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Node name. |
| `level` | string | Yes | `organization`, `team`, or `project`. |
| `parent_id` | UUID | No | Parent node ID. Required for `team` and `project` levels. |
| `description` | string | No | Human-readable description. |
| `default_scope` | string | No | Default scope applied to rules at this node. |

**Response (201 Created):**

```json
{
  "id": "node-uuid-...",
  "name": "Backend Team",
  "level": "team",
  "parent_id": "org-uuid-...",
  "description": "Backend engineering team",
  "default_scope": "backend",
  "created_at": "2026-04-26T10:00:00Z"
}
```

### List federation nodes

```
GET /api/v1/federations
```

Returns the federation hierarchy as a tree structure.

**Response:**

```json
{
  "nodes": [
    {
      "id": "org-uuid-...",
      "name": "Acme Corp",
      "level": "organization",
      "children": [
        {
          "id": "team-uuid-...",
          "name": "Backend Team",
          "level": "team",
          "children": [
            {
              "id": "proj-uuid-...",
              "name": "auth-service",
              "level": "project",
              "children": []
            }
          ]
        }
      ]
    }
  ]
}
```

### Get a federation node

```
GET /api/v1/federations/{node_id}
```

Returns the node details including its direct rules and parent chain.

### Add a rule to a federation node

```
POST /api/v1/federations/{node_id}/rules
```

**Request body:**

```json
{
  "rule_id": "rule-uuid-...",
  "override_parent_rule_id": "parent-rule-uuid-..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rule_id` | UUID | Yes | The rule to attach to this node. |
| `override_parent_rule_id` | UUID | No | If set, this rule overrides the specified parent rule in the effective rule set. |

**Response (201 Created):**

```json
{
  "node_id": "node-uuid-...",
  "rule_id": "rule-uuid-...",
  "override_parent_rule_id": "parent-rule-uuid-...",
  "created_at": "2026-04-26T10:00:00Z"
}
```

### Remove a rule from a federation node

```
DELETE /api/v1/federations/{node_id}/rules/{rule_id}
```

**Response:** 204 No Content

### Get effective rules

```
GET /api/v1/federations/{node_id}/effective-rules
```

Returns the fully resolved rule set for a node after walking the ancestor chain and applying overrides.

**Response:**

```json
{
  "node_id": "proj-uuid-...",
  "effective_rules": [
    {
      "rule": { "id": "...", "statement": "..." },
      "source_node_id": "org-uuid-...",
      "overridden_rule_id": null,
      "inherited": true
    },
    {
      "rule": { "id": "...", "statement": "..." },
      "source_node_id": "proj-uuid-...",
      "overridden_rule_id": "parent-rule-uuid-...",
      "inherited": false
    }
  ],
  "total": 42
}
```

### Get diff from parent

```
GET /api/v1/federations/{node_id}/diff
```

Shows how this node's effective rules differ from its parent node -- rules added, overridden, or removed at this level.

**Response:**

```json
{
  "node_id": "team-uuid-...",
  "parent_id": "org-uuid-...",
  "added": [{ "rule_id": "...", "statement": "..." }],
  "overridden": [
    {
      "parent_rule_id": "...",
      "child_rule_id": "...",
      "parent_statement": "...",
      "child_statement": "..."
    }
  ],
  "inherited_count": 35
}
```
