# Feature Flags Reference

> Complete inventory of feature flags, their defaults, and lifecycle status.
> See CLAUDE.md for operational details and PROJECT.md for architectural context.

---

## Feature Flag Categories

### Infrastructure Tier Toggles

Control which optional infrastructure services are required. These determine the deployment tier (1/2/3).

| Flag | Default | Description | Tier Impact |
|------|---------|-------------|-------------|
| `ELASTICSEARCH_ENABLED` | `false` | Enable Elasticsearch for hybrid search (BM25 + kNN). Falls back to Postgres FTS when disabled. | Tier 2+ |
| `NEO4J_ENABLED` | `false` | Enable Neo4j for rule relationship graph. Falls back to Postgres adjacency table when disabled. | Tier 3 |
| `REDIS_ENABLED` | `false` | Enable Redis for arq background job queue. Background workers disabled when off. | Tier 2+ |
| `MCP_ENABLED` | `false` | Enable MCP server for AI agent integration (stdio or streamable-http). | Tier 3 |

**Tier derivation**: Tier 1 = Postgres only. Tier 2 = +ES or +Redis. Tier 3 = +Neo4j.

---

### Cross-Organizational Features (Phase 7 — default ON)

Core features that make the platform cross-organizational. All default to `true`.

| Flag | Default | Description | Phase |
|------|---------|-------------|-------|
| `CROSS_ORG_FEATURES_ENABLED` | `true` | Master switch for cross-organizational capabilities. Disabling reverts to engineering-only mode. | 7 |
| `DEPARTMENT_RBAC_ENABLED` | `true` | Department-based access control. Every API endpoint filters rules by caller's department membership. | 7d |
| `ASSISTANT_ENABLED` | `true` | Conversational Rule Assistant (`/assistant` route, `/api/v1/assistant/...` endpoints). | 7g |
| `COMPLIANCE_COCKPIT_ENABLED` | `true` | Compliance Cockpit dashboard (`/compliance` route, `/api/v1/compliance/...` endpoints). | 7h |
| `POLYGLOT_VERIFICATION_ENABLED` | `true` | Weekly polyglot translation equivalence verification cron and drift alerts. | 7i |

---

### Opt-in Features (default OFF)

Features that are fully implemented but disabled by default. Enable per-deployment when needed.

| Flag | Default | Description | Phase |
|------|---------|-------------|-------|
| `MULTI_AGENT_SESSIONS_ENABLED` | `false` | Multi-agent governance sessions (session creation, negotiation, consensus). Single-agent profiles and trust levels remain active regardless. | 6b |
| `GITHUB_APP_ENABLED` | `false` | GitHub App webhook receiver for PR review integration. The CLI (`rulerepo-check`) provides equivalent CI functionality without the app. | 2 |
| `AUDIT_WORM_ENABLED` | `false` | Write-Once-Read-Many audit log export to S3 (requires `AUDIT_WORM_S3_BUCKET` and `AUDIT_WORM_S3_REGION`). | RR-011 |

---

### Frozen Features (Phase 6 Freeze — default OFF)

Features that were implemented but frozen under the Cross-Organizational direction. Code remains in the repository but is gated behind flags. These are not part of the supported surface.

| Flag | Default | Description | Phase | Reason Frozen |
|------|---------|-------------|-------|---------------|
| `GATEWAY_ENABLED` | `false` | Webhook gateway for external event ingestion (policy engine, normalizers). Replaced by `/api/v1/events/ingest` as the cross-org ingress. | 4 | Superseded by Business Event API |
| `NEXT_PUBLIC_GATEWAY_ENABLED` | `false` | Frontend toggle for Gateway sidebar item. Must match `GATEWAY_ENABLED`. | 4 | Frontend counterpart |
| `ADVANCED_OBSERVABILITY_ENABLED` | `false` | Advanced analytics: digest delivery, agent analytics, effectiveness scoring, cross-project comparison dashboards. Core metrics (compliance rate, top violations) remain available regardless. | 5 | Scope reduction for cross-org focus |
| `NEXT_PUBLIC_ADVANCED_OBSERVABILITY_ENABLED` | `false` | Frontend toggle for advanced observability pages. Must match `ADVANCED_OBSERVABILITY_ENABLED`. | 5 | Frontend counterpart |

---

### Delivery Mode Flags

Control how alerts and digests are delivered. Not feature flags per se, but affect operational behavior.

| Flag | Default | Description | Values |
|------|---------|-------------|--------|
| `ALERT_OUTPUT_MODE` | `local` | Where alert notifications are written. | `local` (in-app inbox), `webhook` (external URL), `both` |
| `ALERT_WEBHOOK_URL` | (empty) | External webhook URL for alert delivery. Only used when `ALERT_OUTPUT_MODE` includes `webhook`. | URL |
| `DIGEST_OUTPUT_MODE` | `local` | Where weekly digest reports are written. | `local`, `webhook`, `both` |
| `DIGEST_WEBHOOK_URL` | (empty) | External webhook URL for digest delivery. Only used when `DIGEST_OUTPUT_MODE` includes `webhook`. | URL |

---

### Domain Pack Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLED_PACKS` | all discovered | Comma-separated list of domain packs to load at startup. If unset, all packs in `domain_packs/` are loaded. Available packs: `code`, `contract`, `hr_attendance`, `communication`, `expense`, `legal`, `sales`, `it_security`, `governance`. |
| `DEFAULT_PERSONA` | `admin` | Default persona for the frontend when no persona is selected. |
| `DEFAULT_LOCALE` | `en` | Default locale for rule display and evaluation prompts. |
| `SUPPORTED_LOCALES` | `en,ja` | Comma-separated list of supported UI/rule locales. |

---

## How Feature Flags Are Consumed

1. **`core/config.py`** (`Settings` class) — reads all env vars via `pydantic-settings`. This is the single source of truth for typed configuration.
2. **`core/feature_flags.py`** (`FeatureFlags` class) — mirrors feature-level flags from `Settings` and derives the deployment tier. Used by middleware, routers, and services to check feature availability.
3. **`main.py`** — checks `FeatureFlags` to conditionally register routers (e.g., gateway, GitHub App) and initialize services (e.g., DomainPackLoader).
4. **Frontend** — uses `NEXT_PUBLIC_*` env vars at build time to conditionally render sidebar items and routes.

## Frozen Schema

Tables belonging to frozen features are moved to the `frozen` PostgreSQL schema (migration 037). This keeps them out of the default `public` namespace while preserving all data.

| Table | Schema | Feature Flag |
|-------|--------|-------------|
| `enforcement_policies` | `frozen` | `GATEWAY_ENABLED` |
| `gateway_evaluations` | `frozen` | `GATEWAY_ENABLED` |
| `governance_sessions` | `frozen` | `MULTI_AGENT_SESSIONS_ENABLED` |
| `agent_negotiations` | `frozen` | `MULTI_AGENT_SESSIONS_ENABLED` |

Tables that remain in `public` even when their parent feature is opt-in:
- `agent_profiles` — single-agent tracking is always active
- `agent_exception_requests` — exception workflow is always active

## Graceful Degradation

When a feature flag is disabled:
- The corresponding API routers are **not registered** (return 404, not 500).
- Background workers for that feature are **not started**.
- Frontend sidebar items are **hidden**.
- Frozen tables live in the `frozen` PostgreSQL schema (not dropped).
- No import errors or module-level crashes occur — all imports are guarded behind the flag check.
- The full test suite passes regardless of flag state (tests mock dependencies, not flags).
