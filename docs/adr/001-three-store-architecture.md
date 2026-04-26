# ADR-001: Use PostgreSQL + Elasticsearch + Neo4j as Complementary Data Stores

**Status:** Accepted

**Date:** 2025-01-15

**Deciders:** Project team

---

## Context

The Rule Repository stores natural-language rules (laws, contracts, policies, engineering standards) and must support three fundamentally different access patterns:

1. **Transactional CRUD with ACID guarantees.** Rules have lifecycle states (DRAFT, REVIEW, APPROVED, EFFECTIVE, RETIRED), revision history, an append-only audit log with hash chaining, and governance metadata. These require strong consistency and relational integrity.

2. **Full-text and semantic search.** Users search rules by natural-language queries, filter by scope/modality/severity, and expect ranked results. The Intent API supports hybrid search combining BM25 keyword matching with 768-dimensional dense vector similarity for semantic relevance.

3. **Graph traversal of rule relationships.** Rules relate to each other via typed, directed edges: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`. Queries like "find all rules that transitively depend on rule X" or "detect conflict cycles" require efficient multi-hop graph traversal.

No single database excels at all three. PostgreSQL handles transactions and relational queries well but is slow at multi-hop graph traversal and lacks native BM25+vector hybrid search. Elasticsearch provides excellent full-text and vector search but has no ACID transactions or graph traversal. Neo4j is purpose-built for graph queries but is not a reliable system of record for structured data with complex schema evolution.

---

## Decision

Use three complementary data stores, each playing to its strength:

| Store | Role | Data |
|---|---|---|
| **PostgreSQL** | System of record | Rules, revisions, source documents, evaluations, audit log. All ACID-critical data. |
| **Elasticsearch** | Search index | `rules` index with `statement` (analyzed text), `tags`, `scope`, `modality`, `effective_period`, `embedding` (768-dim `dense_vector` for hybrid search). BM25 + kNN scoring. |
| **Neo4j** | Relationship graph | One node label (`Rule`, keyed by PG rule ID). Directed relationships: `REFINES`, `OVERRIDES`, `CONFLICTS_WITH`, `DEPENDS_ON`, `DERIVES_FROM`, `SUCCEEDS`. |

### Ownership and consistency model

- **PostgreSQL is the single source of truth.** If any store disagrees with PG, PG wins.
- Elasticsearch and Neo4j are **derived projections**. They can be fully rebuilt from PostgreSQL data at any time.
- Writes go through a service layer that updates all three stores in the same operation. If ES or Neo4j writes fail, the PG commit still succeeds and the failed projection is queued for retry.
- A reconciliation script (`scripts/reconcile_graph.py`) can rebuild Neo4j entirely from PG. An equivalent reindexing path exists for Elasticsearch.

### Search strategy

- Default search uses BM25 full-text matching on the `statement` field.
- Hybrid search combines BM25 with kNN vector similarity on the `embedding` field (768-dimensional dense vectors).
- LLM-assisted reranking of top-k results is available when the user requests "smart" search, but is not the default path.

---

## Consequences

### Benefits

- **Each store is used for its designed strength.** PG handles transactions and schema, ES handles search ranking, Neo4j handles graph traversal. No store is forced into an access pattern it was not built for.
- **The system of record is clear.** PostgreSQL owns the truth. ES and Neo4j are rebuildable projections, reducing the blast radius of data corruption in either derived store.
- **Search quality is high.** BM25 + dense vector hybrid scoring outperforms either approach alone for natural-language rule queries.
- **Graph queries are efficient.** Multi-hop traversal (conflict cycle detection, transitive dependency chains) runs in milliseconds in Neo4j, whereas the equivalent recursive SQL in PG would be slower and harder to maintain.

### Costs

- **Operational complexity increases.** Three databases to provision, monitor, back up, and upgrade. Docker Compose handles local dev; production will need separate infrastructure for each.
- **Write path is more complex.** Every rule mutation touches up to three stores. The service layer must handle partial failures gracefully (PG commit succeeds even if ES/Neo4j fail, with retry for the projections).
- **Eventual consistency between stores.** ES and Neo4j may lag behind PG briefly during failures or high load. The reconciliation scripts mitigate drift but add another operational task.
- **Developer onboarding cost.** Contributors need familiarity with SQL (PG), the Elasticsearch query DSL, and Cypher (Neo4j). The service layer abstracts most of this, but debugging requires knowledge of all three.

### Mitigations

- Docker Compose brings up all three stores with `docker compose up --build`. Local dev is a single command.
- `scripts/reconcile_graph.py` rebuilds Neo4j from PG if the graph drifts.
- The adapter layer (`adapters/postgres/`, `adapters/elasticsearch/`, `adapters/neo4j/`) isolates each store's client code. Business logic in `services/` never imports store-specific libraries directly.
- Health endpoints (`/healthz`, `/readyz`) check connectivity to all three stores, surfacing issues early.
