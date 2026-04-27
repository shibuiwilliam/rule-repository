# Snapshots API

The Snapshots API manages versioned, immutable captures of the rule corpus and their deployment to environments. All endpoints are prefixed with `/api/v1`.

## Snapshots

### POST /api/v1/snapshots

Create a new snapshot from the current live rule corpus.

**Request:**

```json
{
  "name": "v2.3.0",
  "description": "Q2 policy updates including new security rules"
}
```

**Response:**

```json
{
  "id": "snap-042",
  "name": "v2.3.0",
  "description": "Q2 policy updates including new security rules",
  "rule_count": 142,
  "created_at": "2026-04-25T10:00:00Z"
}
```

### GET /api/v1/snapshots

List all snapshots with pagination.

**Query Parameters:** `limit` (integer, default 20), `offset` (integer, default 0).

### GET /api/v1/snapshots/{snapshot_id}

Get a snapshot by ID, including its rule count and deployment status.

## Deployment

### POST /api/v1/snapshots/{snapshot_id}/deploy

Deploy a snapshot to an environment. The previously active snapshot for that environment is recorded in deployment history.

**Request:**

```json
{
  "environment": "staging"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `environment` | string | yes | Target environment: `production`, `staging`, or `development` |

**Response:**

```json
{
  "snapshot_id": "snap-042",
  "environment": "staging",
  "deployed_at": "2026-04-25T11:00:00Z",
  "previous_snapshot_id": "snap-039"
}
```

### POST /api/v1/snapshots/{snapshot_id}/rollback

Rollback the environment where this snapshot is deployed, re-deploying the previous snapshot.

**Response:**

```json
{
  "environment": "staging",
  "rolled_back_from": "snap-042",
  "rolled_back_to": "snap-039",
  "deployed_at": "2026-04-25T12:00:00Z"
}
```

## Simulation

### POST /api/v1/snapshots/{snapshot_id}/simulate

Compare this snapshot against another and estimate the impact of switching.

**Request:**

```json
{
  "compare_to": "snap-039",
  "sample_size": 100
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `compare_to` | string | yes | Snapshot ID to compare against (typically the current production snapshot) |
| `sample_size` | integer | no | Number of historical evaluations to replay (default 50) |

**Response:**

```json
{
  "rules_added": 3,
  "rules_removed": 1,
  "rules_modified": 5,
  "verdict_changes": {
    "total_sampled": 100,
    "changed": 8,
    "allow_to_deny": 2,
    "deny_to_allow": 1,
    "other": 5
  },
  "risk_level": "medium"
}
```

## Deployment Status

### GET /api/v1/snapshots/deployments

List the currently active snapshot for each environment.

**Response:**

```json
[
  {
    "environment": "production",
    "snapshot_id": "snap-039",
    "deployed_at": "2026-04-20T09:00:00Z"
  },
  {
    "environment": "staging",
    "snapshot_id": "snap-042",
    "deployed_at": "2026-04-25T11:00:00Z"
  }
]
```

### GET /api/v1/snapshots/deployments/{environment}

Get the active snapshot and deployment history for a specific environment.

## See Also

- [Snapshots Architecture](../architecture/snapshots.md) -- design overview
- [Evaluation Engine](../architecture/evaluation-engine.md) -- how environment selection affects evaluation
