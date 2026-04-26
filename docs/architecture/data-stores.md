# Data Stores

The Rule Repository uses three data stores, each serving a specific role.

## PostgreSQL (System of Record)

PostgreSQL 17 holds the canonical data. All writes go through PostgreSQL first. The database contains the following tables:

| Table | Purpose |
|---|---|
| `rules` | Rule statements with metadata (modality, severity, scope, tags, effective period, governance fields). |
| `rule_revisions` | Immutable revision history for every rule change. |
| `rule_relationships` | Directed relationships between rules (type, source, target). |
| `audit_log` | Append-only, hash-chained log of all evaluations and extractions. Each row links to the previous via a hash chain column. Updates and deletes are rejected by a database trigger. |
| `documents` | Uploaded source documents (filename, MIME type, size, storage path). |
| `extractions` | Results from the extraction pipeline (candidate rules, model ID, review status). |
| `api_keys` | API key records for authenticated access. |
| `llm_cache` | Cached LLM responses keyed by hash of inputs, model, and prompt version. Invalidated on rule revision. |
| `enforcement_policies` | Gateway policies that map webhook events to evaluation rules (event source, type pattern, scope, mode, response actions). |
| `gateway_evaluations` | Results from gateway webhook evaluations (policy, event, verdict, actions taken). |

Extensions: `uuid-ossp` and `pgcrypto` are installed on first start.

Migrations are managed by **Alembic**.

## Elasticsearch (Search Index)

Elasticsearch 8.17 provides full-text and vector search over the rule corpus. There is one index:

### `rules` index

The index uses a custom analyzer (`rule_analyzer`: standard tokenizer with lowercase, stop word, and snowball filters) and the following field mappings:

| Field | Type | Notes |
|---|---|---|
| `rule_id` | keyword | Matches the PostgreSQL rule ID. |
| `statement` | text (analyzed) | Searchable rule text with a `.keyword` sub-field. |
| `tags` | keyword | For filtering. |
| `scope` | keyword | For filtering. |
| `modality` | keyword | MUST, MUST_NOT, SHOULD, MAY, INFO. |
| `severity` | keyword | LOW, MEDIUM, HIGH, CRITICAL. |
| `status` | keyword | Rule lifecycle status. |
| `effective_from` | date | Start of effective period. |
| `effective_until` | date | End of effective period. |
| `embedding` | dense_vector (768 dims, cosine) | For semantic similarity search. |
| `rationale` | text (analyzed) | Searchable rationale. |
| `created_at` / `updated_at` | date | Timestamps. |

The index template is applied by the `es-setup` container on first start from `infra/elasticsearch/rules-index-template.json`.

Search modes available:

- **Full-text** (BM25): keyword matching on `statement` and `rationale`.
- **Vector** (kNN): cosine similarity on the 768-dimensional `embedding` field.
- **Hybrid**: combined BM25 + vector scoring.
- **Category**: filter-only queries on keyword fields.
- **Context**: given a set of facts, find applicable rules.

## Neo4j (Relationship Graph)

Neo4j 5 Community stores the directed graph of rule relationships.

### Node label

One label: **`Rule`**. The `id` property matches the PostgreSQL rule ID.

### Constraints and indexes

Created on first start from `infra/neo4j/init.cypher`:

- Uniqueness constraint on `Rule.id`.
- Property indexes on `Rule.modality`, `Rule.severity`, `Rule.status`.

### Relationship types

| Relationship | Direction | Meaning |
|---|---|---|
| `REFINES` | child --> parent | A specific rule operationalizes a more abstract one. |
| `OVERRIDES` | higher --> lower | A rule takes precedence over another. |
| `CONFLICTS_WITH` | bidirectional | Two rules that contradict each other. |
| `DEPENDS_ON` | dependent --> dependency | Evaluation requires another rule's verdict. |
| `DERIVES_FROM` | derived --> source | Originates from a higher-level rule (e.g., a law). |
| `SUCCEEDS` | new --> old | A revision that replaces a prior version. |

### Consistency Model

PostgreSQL is the source of truth for rule existence and metadata. Neo4j is a derived projection of relationships.

- When a rule or relationship is created or modified through the API, both PostgreSQL and Neo4j are updated in the same service call.
- If they disagree, **PostgreSQL wins**.
- The `scripts/reconcile_graph.py` script can rebuild Neo4j entirely from PostgreSQL data as a safety net.
