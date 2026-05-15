# Post-Refocus Changes

Changes made after the cross-organizational refocus (Phase 8) completion.

---

## 2026-05-16 — Schema and Governance Additions

### New Alembic Migrations (37 → 40)

| Migration | Description |
|---|---|
| `039_add_body_jsonb_column` | Flexible JSONB `body` storage for rule kind polymorphism. Supports `NormativeBody`, `ComputationalBody`, `ProceduralBody`, `DefinitionalBody`, and `PrincipleBody` variants as a discriminated union on `rule.kind`. |
| `040_add_language_column` | `language` column on the `rules` table for multilingual support. Defaults to `en`. Used by search analyzers and the translation verification pipeline. |
| `041_create_governance_policies_table` | `governance_policies` table for Attribute-Based Access Control (ABAC). Stores policies with `domain`, `org_unit`, `action`, `principals`, and `effect` columns. Feature-flagged off by default (`FEATURE_ABAC_GOVERNANCE_ENABLED=false`). |

### LLM Provider Implementation

Pluggable LLM providers moved from "planned" to fully implemented:

| Provider | Module | Status |
|---|---|---|
| Gemini (Google) | `adapters/llm/gemini.py` | Primary (default) |
| Anthropic Claude | `adapters/llm/anthropic.py` | Available |
| OpenAI | `adapters/llm/openai.py` | Available |
| Self-hosted | `adapters/llm/local.py` | Available |

The LLM router (`adapters/llm/router.py`) provides fallback chains, circuit breaker pattern, and per-tenant provider overrides.

### Updated Metrics

| Metric | Phase 8 | Current |
|--------|---------|---------|
| API Routers | 40 | 40 |
| ORM Models | 37 | 37 |
| Alembic Migrations | 37 | 40 |
| Test Files | 117 | 102 |
| MCP Tools | 24 | 24 |
| Frontend Pages | 61 | 61 |
| Domain Packs (packages/) | 6 | 6 |
| Domain Packs (server) | 9 | 9 |

Note: Test file count decreased from 117 to 102 due to consolidation of connector-related and redundant test files during the refocus cleanup.
