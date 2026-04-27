# Snapshots

Snapshots provide immutable, versioned captures of the rule corpus at a point in time. They enable controlled deployment of rule sets to different environments, rollback to previous versions, and impact simulation before promoting changes.

## Concepts

### Snapshot

A snapshot is a frozen copy of all active rules and their metadata at the moment of creation. Once created, a snapshot is immutable -- rules within it cannot be modified. Snapshots are stored in PostgreSQL with references to the specific rule revisions they contain.

### Environments

Snapshots are deployed to named environments. The three standard environments are:

| Environment | Purpose |
|---|---|
| `production` | Live rule set used by production evaluations |
| `staging` | Pre-production validation environment |
| `development` | Active development and testing |

Each environment has at most one active snapshot at a time. Deploying a new snapshot to an environment replaces the previous one.

### Environment Parameter

The `environment` parameter is wired into the evaluation and MCP pipelines. When a caller specifies an environment, the system evaluates against the snapshot deployed to that environment rather than the live rule corpus. This allows:

- Production evaluations to use a stable, tested rule set.
- Staging evaluations to validate upcoming changes before promotion.
- Development evaluations to test work-in-progress rules.

If no environment is specified, the system falls back to the live rule corpus (current head of all rules).

## Rollback

Each environment maintains a deployment history. Rolling back (`POST /api/v1/snapshots/{id}/rollback`) re-deploys the previously active snapshot for that environment. The rollback is itself recorded as a deployment event.

## Impact Simulation

Before deploying a snapshot, you can simulate the impact (`POST /api/v1/snapshots/{id}/simulate`). Simulation compares two snapshots and reports:

- **Structural diff**: rules added, removed, or modified between the two snapshots.
- **Verdict impact**: a sample of historical evaluations is re-run against both snapshots, and the system reports how many verdicts would change.
- **Risk assessment**: a summary of the magnitude of change (low, medium, high) based on the number and severity of affected rules.

The `compare_to` parameter specifies the baseline snapshot (typically the one currently deployed to the target environment). The `sample_size` parameter controls how many historical evaluations to replay.

## Data Flow

1. Author creates a snapshot from the current live rule corpus.
2. The snapshot is deployed to `development` for testing.
3. After validation, the snapshot is deployed to `staging`.
4. Impact simulation compares the staging snapshot against the current production snapshot.
5. If the impact is acceptable, the snapshot is deployed to `production`.
6. If issues arise, the previous production snapshot is rolled back.

## See Also

- [Snapshots API](../api/snapshots.md) -- endpoint reference
- [MCP Server](../integrations/mcp.md) -- environment parameter in MCP tools
- [Evaluation Engine](evaluation-engine.md) -- how environment selection affects evaluation
