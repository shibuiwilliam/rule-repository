# Feature Flags Reference

> Complete inventory of feature flags, their defaults, lifecycle status, and
> where each flag is consumed in the codebase.
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

**Tier derivation** (computed in `FeatureFlags.tier`): Tier 1 = Postgres only. Tier 2 = +ES or +Redis. Tier 3 = +Neo4j.

**Where consumed:**
- `main.py` lifespan — conditionally initializes ES client, Neo4j driver based on flags.
- `main.py` readyz — only checks connectivity for enabled services.

---

### Cross-Organizational Features (Phase 7 — default ON)

Core features that make the platform cross-organizational. All default to `true`.

| Flag | Default | Description | Gated Endpoints / UI |
|------|---------|-------------|----------------------|
| `CROSS_ORG_FEATURES_ENABLED` | `true` | Master switch for cross-organizational capabilities. Disabling reverts to engineering-only mode. | Multiple services check this as a prerequisite. |
| `DEPARTMENT_RBAC_ENABLED` | `true` | Department-based access control. API endpoints filter rules by caller's department membership. | `services/departments/authz.py` |
| `ASSISTANT_ENABLED` | `true` | Conversational Rule Assistant. | `POST /api/v1/assistant/turn` returns 404 when off (`api/v1/assistant.py:59`). Frontend: `/assistant` page. |
| `COMPLIANCE_COCKPIT_ENABLED` | `true` | Compliance Cockpit dashboard. | `GET/POST /api/v1/compliance/*` returns 404 when off (`api/v1/cockpit.py:88`). Frontend: `/compliance` page. |
| `POLYGLOT_VERIFICATION_ENABLED` | `true` | Weekly polyglot translation equivalence verification cron and drift alerts. | `workers/polyglot_validator.py`, `workers/translation_drift.py` |

---

### Opt-in Features (default OFF)

Features that are fully implemented but disabled by default. Enable per-deployment when needed.

| Flag | Default | Description | Gated Endpoints / Behavior |
|------|---------|-------------|----------------------------|
| `MULTI_AGENT_SESSIONS_ENABLED` | `false` | Multi-agent governance sessions (session creation, joining, consensus). Single-agent profiles and trust levels remain active regardless. | `POST /api/v1/agent-governance/session` and `POST /api/v1/agent-governance/session/join` return 404 when off (`api/v1/agent_governance.py:220`). DB tables moved to `frozen` schema. |
| `GITHUB_APP_ENABLED` | `false` | GitHub App webhook receiver for PR review integration. The CLI (`rulerepo-check`) provides equivalent CI functionality without the app. | Entire GitHub router not registered in `main.py:239` when off. |
| `AUDIT_WORM_ENABLED` | `false` | Write-Once-Read-Many audit log export to S3. Requires `AUDIT_WORM_S3_BUCKET` and `AUDIT_WORM_S3_REGION`. | `services/core/audit_export/worm_writer.py` |

---

### Deferred Features (Phase 6 — default OFF, per CLAUDE.md §14.11)

Features that were implemented but are explicitly deferred under the Cross-Organizational refocus. Code remains in the repository and is gated behind flags. Do not re-enable without a PROJECT.md update.

| Flag | Default | Description | Gated Endpoints / Behavior | Reason Deferred |
|------|---------|-------------|----------------------------|-----------------|
| `MARKETPLACE_ENABLED` | `false` | Cross-organization rule package sharing (publish, subscribe, import). | Marketplace router and sidebar entry hidden. Models preserved for re-enablement. | Out of scope until cross-org core is solid. |
| `GATEWAY_ENABLED` | `false` | Webhook gateway for external event ingestion (policy engine, normalizers for Slack, Teams, GitHub, email, generic). | Entire gateway router not registered in `main.py:235` when off. DB tables (`enforcement_policies`, `gateway_evaluations`) moved to `frozen` schema. | Superseded by `POST /api/v1/events/ingest` and `POST /api/v1/submissions`. |
| `NEXT_PUBLIC_GATEWAY_ENABLED` | `false` | Frontend toggle for Gateway sidebar item. Must match `GATEWAY_ENABLED`. | `/gateway` nav item hidden in `Sidebar.tsx:10,35` when off. | Frontend counterpart of `GATEWAY_ENABLED`. |
| `ADVANCED_OBSERVABILITY_ENABLED` | `false` | Advanced analytics: agent analytics, per-rule effectiveness scoring, weekly digest delivery, cross-project comparison. Core metrics (compliance rate, top violations, dashboard summary) remain available regardless. | 5 intelligence endpoints return 404 when off (`api/v1/intelligence.py:112,126,146,163,179`): `/agents`, `/agents/{id}`, `/effectiveness/{rule_id}`, `/digest`, `/comparison`. Weekly digest worker skips execution (`workers/settings.py:404`). | Scope reduction for cross-org focus. |
| `NEXT_PUBLIC_ADVANCED_OBSERVABILITY_ENABLED` | `false` | Frontend toggle for advanced observability pages. Must match `ADVANCED_OBSERVABILITY_ENABLED`. | Frontend counterpart. | Frontend counterpart. |
| `GATEWAY_EXTERNAL_INTAKE_ENABLED` | `false` | External webhook intake from public sources (Slack, generic webhooks). Internal API form (`/api/v1/events/ingest`) remains available. | Guards external-facing webhook processing paths. | Local-first; external connectors deferred. |
| `OBSERVABILITY_DIGEST_DELIVERY_ENABLED` | `false` | External delivery of governance digests to webhooks. Metrics are still computed internally. | Guards the delivery step in digest generation. | Compute internally; do not deliver externally. |
| `AGENT_TRUST_AUTO_PROMOTION_ENABLED` | `false` | Automatic trust-level promotion for agents based on evaluation history. Agent profile creation and manual trust setting remain active. | Agent governance endpoints requiring auto-promotion return 404 (`api/v1/agent_governance.py:212`). | Deferred until cross-org core is solid. |
| `AGENT_NEGOTIATION_ENABLED` | `false` | Agent-to-agent verdict negotiation (challenge, counter-propose). | `POST /api/v1/agent-governance/negotiate` and `GET /api/v1/agent-governance/negotiations` return 404 when off (`api/v1/agent_governance.py:204`). | Deferred until cross-org core is solid. |

---

### Refocus Migration Toggles (default ON except ABAC)

Feature flags controlling the rollout of cross-organizational refocus abstractions. These default to `true` in development and are expected to remain on. Flip to `false` only for rollback.

| Flag | Default | Description | What It Guards |
|------|---------|-------------|----------------|
| `EVALUATION_SUBJECT_V2_ENABLED` | `true` | New `EvaluationSubject` abstraction with 6 concrete variants (code_change, business_event, document_artifact, transaction, communication, decision_request). | `domain/evaluation_subject.py`, `services/evaluation/subjects/`, `POST /api/v1/submissions`, `schemas/submissions.py` |
| `STRUCTURED_SCOPE_ENABLED` | `true` | Structured `Scope` dataclass with `domain`, `org_unit`, `subject_type`, `attributes` fields replacing the legacy slash-separated scope string. | `domain/scope.py` (`Scope` class), scope matching logic, Elasticsearch structured scope fields. |
| `RULE_KIND_POLYMORPHISM_ENABLED` | `true` | `RuleKind` enum (`normative`, `computational`, `procedural`, `definitional`, `principle`) and typed body variants on the `Rule` entity. | `domain/rule.py` (`RuleKind`, body dataclasses), `services/evaluation/deterministic/runner.py` dispatch. |
| `DOMAIN_PACKS_ENABLED` | `true` | Domain Pack loading from `packages/domain-packs/`. Each pack contributes prompts, analyzers, templates, and metadata schemas. | `services/domain_packs/loader.py`, `packages/domain-packs/*/pack.yaml`, `main.py` pack loading at startup. |
| `HYBRID_EVALUATION_ENABLED` | `true` | Two-layer evaluation: deterministic layer (numeric via `asteval`, schema via Pydantic, lookup via tables) + LLM layer. | `services/evaluation/deterministic/{runner,numeric_evaluator,schema_evaluator,lookup_evaluator}.py` |
| `PERSONA_ROUTING_ENABLED` | `true` | Persona-aware frontend routing with per-persona vocabulary, layouts, and dashboards. | Frontend `use-persona-term.ts`, `(dashboard)/vocabulary.ts`, `(legal)/vocabulary.ts`, etc. |
| `ABAC_GOVERNANCE_ENABLED` | `false` | Attribute-based access control governance policies (domain x action x principal). Off until Step 4 of the roadmap. | `domain/governance.py`, `services/governance/resolver.py` |

---

### Delivery Mode Flags

Control how alerts and digests are delivered. Not boolean feature flags, but affect operational behavior.

| Flag | Default | Description | Values |
|------|---------|-------------|--------|
| `ALERT_OUTPUT_MODE` | `local` | Where alert notifications are written. | `local` (in-app inbox only), `webhook` (external URL only), `both` |
| `ALERT_WEBHOOK_URL` | (empty) | External webhook URL for alert delivery. Only used when `ALERT_OUTPUT_MODE` includes `webhook`. | URL string |
| `DIGEST_OUTPUT_MODE` | `local` | Where weekly digest reports are written. | `local`, `webhook`, `both` |
| `DIGEST_WEBHOOK_URL` | (empty) | External webhook URL for digest delivery. Only used when `DIGEST_OUTPUT_MODE` includes `webhook`. | URL string |
| `NOTIFICATION_WEBHOOK_URL` | (empty) | Slack/Teams incoming webhook for proposal notifications (Phase 6a). | URL string |
| `NOTIFICATION_WEBHOOK_TYPE` | `slack` | Type of notification webhook. | `slack`, `teams`, `generic` |

---

### Domain Pack Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLED_PACKS` | all discovered | Comma-separated list of domain packs to load at startup. Read by `services/domain_packs/loader.py` via `os.environ.get("ENABLED_PACKS")`. If unset, all packs with a `pack.yaml` are loaded. Available server-side packs: `code`, `contract`, `hr_attendance`, `communication`, `expense`, `legal`, `sales`, `it_security`, `governance`. External packs in `packages/domain-packs/`: `engineering`, `legal`, `hr`, `finance`, `sales`, `communication`. |
| `DEFAULT_PERSONA` | `admin` | Default persona for the frontend when no persona is selected. |
| `DEFAULT_LOCALE` | `en` | Default locale for rule display and evaluation prompts. |
| `SUPPORTED_LOCALES` | `en,ja` | Comma-separated list of supported UI/rule locales. |

---

### Agent Governance Tuning

These are not feature flags but configuration parameters for the agent governance subsystem.

| Flag | Default | Description |
|------|---------|-------------|
| `AGENT_TRUST_PROMOTION_ENABLED` | `true` | Enable trust-level promotion (manual). Distinct from `AGENT_TRUST_AUTO_PROMOTION_ENABLED` which controls *automatic* promotion. |
| `AGENT_MASTERY_THRESHOLD` | `50` | Consecutive passes required to mark an agent as having "mastered" a rule. |
| `AGENT_PATTERN_MIN_EVIDENCE` | `10` | Minimum evidence count before an agent pattern report is generated. |

---

### LLM Provider Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `LLM_PROVIDER_PRIMARY` | `gemini` | Primary LLM provider. Options: `gemini`, `anthropic`, `openai`, `local`. |
| `LLM_PROVIDER_FALLBACK` | (empty) | Fallback LLM provider if primary fails. |
| `LLM_PROVIDER_SELF_HOSTED_URL` | (empty) | URL for a self-hosted LLM endpoint. |
| `LLM_PROVIDER_SELF_HOSTED_API_KEY` | (empty) | API key for self-hosted LLM. |
| `LLM_TENANT_OVERRIDES` | `{}` | JSON: per-tenant LLM provider/model overrides. |
| `LLM_DEFAULT_MODEL` | `gemini-3-flash-preview` | Default model for high-throughput tasks. |
| `LLM_JUDGE_MODEL` | `gemini-3.1-pro-preview` | Model for high-stakes judgment (evaluation of CRITICAL rules). |
| `LLM_TENANT_MONTHLY_BUDGET_USD` | `0.0` | Monthly LLM spend budget per tenant (0 = unlimited). |
| `LLM_TENANT_BUDGET_WARNING_THRESHOLD` | `0.8` | Budget utilization fraction that triggers a warning. |

---

### Intelligence Cron Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `INTELLIGENCE_HEALTH_CRON` | `"0 2 * * *"` | Cron schedule for health score computation (daily at 2am). |
| `INTELLIGENCE_DRIFT_CRON` | `"0 3 * * *"` | Cron schedule for drift detection (daily at 3am). |
| `INTELLIGENCE_MAX_SIMULATION_REPLAYS` | `100` | Maximum historical evaluations to replay in change impact simulation. |

---

### Environment Variables Read Outside Settings

These are read directly from `os.environ.get()` in specific modules, not via the `Settings` class.

| Variable | Default | Where Read | Description |
|----------|---------|------------|-------------|
| `MCP_TRANSPORT` | `stdio` | `mcp/__init__.py` | MCP server transport: `stdio` or `streamable-http`. |
| `MCP_PORT` | `8001` | `mcp/__init__.py` | Port for streamable-http MCP transport. |
| `MCP_HOST` | `0.0.0.0` | `mcp/__init__.py` | Host for streamable-http MCP transport. |
| `PII_SHADOW_KEY` | (generated) | `core/pii/shadow_store.py` | Encryption key for PII shadow store. If absent, an ephemeral key is generated per process. |
| `CMEK_PROVIDER` | `local` | `services/compliance/cmek.py` | Customer-managed encryption key provider: `local`, `aws_kms`, `gcp_kms`, `azure_keyvault`. |
| `GATEWAY_SKIP_VERIFICATION` | `false` | `.env.example` only | Skip verification in gateway normalizers (development only). |
| `INTERNAL_API_URL` | (falls back to `NEXT_PUBLIC_API_BASE_URL`) | `apps/frontend/lib/api.ts`, `rules/[id]/page.tsx` | Server-side API URL for Next.js server components. |

---

## How Feature Flags Are Consumed

### Backend

1. **`core/config.py`** (`Settings` class) — reads all env vars via `pydantic-settings` with `.env` file support. Single source of truth for typed configuration. 47 settings fields total.
2. **`core/feature_flags.py`** (`FeatureFlags` class) — mirrors boolean flags from `Settings` using `getattr()` with defaults. Derives the deployment tier. Accessed via `get_feature_flags()` singleton.
3. **`main.py`** — checks `FeatureFlags` at app creation to:
   - Conditionally register the gateway router (`gateway_enabled`).
   - Conditionally register the GitHub App router (`github_app_enabled`).
   - Conditionally initialize ES, Neo4j, Redis in the lifespan.
   - Load Domain Packs at startup.
4. **API routers** — individual endpoints call guard functions that raise `HTTPException(404)` when their flag is off:
   - `api/v1/intelligence.py` — `_require_advanced_observability()` gates 5 endpoints.
   - `api/v1/agent_governance.py` — `_require_agent_negotiation()`, `_require_agent_trust_auto_promotion()`, `_require_multi_agent_sessions()` gate 4+ endpoints.
   - `api/v1/cockpit.py` — `_require_compliance_cockpit()` gates cockpit endpoints.
   - `api/v1/assistant.py` — `_require_assistant()` gates the assistant turn endpoint.
5. **Workers** (`workers/settings.py`) — `send_weekly_digest()` checks `advanced_observability_enabled` and skips if off.

### Frontend

1. **`NEXT_PUBLIC_API_BASE_URL`** — used in 15+ pages/components to construct API URLs.
2. **`NEXT_PUBLIC_GATEWAY_ENABLED`** — checked at build time in `Sidebar.tsx` to conditionally include the `/gateway` nav item.
3. **`NEXT_PUBLIC_ADVANCED_OBSERVABILITY_ENABLED`** — defined in `.env.example`; available for frontend conditional rendering.
4. **`INTERNAL_API_URL`** — server-side only; used in `lib/api.ts` and SSR pages.

---

## Frozen Schema

Tables belonging to frozen features are moved to the `frozen` PostgreSQL schema (migration 037). This keeps them out of the default `public` namespace while preserving all data and foreign keys.

| Table | Schema | Feature Flag |
|-------|--------|-------------|
| `enforcement_policies` | `frozen` | `GATEWAY_ENABLED` |
| `gateway_evaluations` | `frozen` | `GATEWAY_ENABLED` |
| `governance_sessions` | `frozen` | `MULTI_AGENT_SESSIONS_ENABLED` |
| `agent_negotiations` | `frozen` | `MULTI_AGENT_SESSIONS_ENABLED` |

Tables that remain in `public` even when their parent feature is opt-in:
- `agent_profiles` — single-agent tracking is always active.
- `agent_exception_requests` — exception workflow is always active.

---

## Graceful Degradation

When a feature flag is disabled:
- API routers are either **not registered** (gateway, GitHub App) or individual endpoints **return 404** (intelligence, agent governance, cockpit, assistant).
- Background workers for that feature **skip execution** with a log message.
- Frontend sidebar items and routes are **hidden** via `NEXT_PUBLIC_*` build-time checks.
- Frozen tables live in the `frozen` PostgreSQL schema (not dropped).
- No import errors or module-level crashes occur — all imports are guarded behind lazy imports inside the flag check.
- The full test suite passes regardless of flag state (tests mock dependencies, not flags).

---

## Flag Interaction Rules

1. **Do not re-enable deferred flags** (`MARKETPLACE_ENABLED`, `GATEWAY_EXTERNAL_INTAKE_ENABLED`, etc.) without updating PROJECT.md and CLAUDE.md first. See CLAUDE.md §13 rule 12.
2. **Frontend `NEXT_PUBLIC_*` flags must match their backend counterparts** — `NEXT_PUBLIC_GATEWAY_ENABLED` must equal `GATEWAY_ENABLED`.
3. **Refocus migration toggles** should remain `true` during normal operation. Set to `false` only for rollback during migration issues.
4. **`ABAC_GOVERNANCE_ENABLED`** is the only refocus toggle that defaults to `false` — it will be flipped to `true` when the governance resolver is fully integrated.
5. **Tier toggles are infrastructure-level**, not feature-level. They control service availability, not business logic.
