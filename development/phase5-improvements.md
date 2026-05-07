# Phase 5: Self-Improving Governance — Implementation Reference

This document describes the Phase 5 improvements implemented and planned, with architectural details for developers continuing the work.

---

## Implemented Features

### 1. Batched Evaluation

**Problem**: N rules = N independent Gemini API calls. Expensive, slow, and each call lacks awareness of other rules.

**Solution**: `batch_evaluator.py` sends all selected rules in a single LLM call.

**Architecture**:

```
service.py (orchestrator)
    │
    ├── evaluate_batch()                  ← new entry point
    │   ├── _batch_evaluate_impl()        ← single Gemini call
    │   │   ├── Build rules block (all rules listed with index)
    │   │   ├── Build prompt from evaluate_batch.txt / evaluate_batch_facts.txt
    │   │   ├── Check cache (hash of sorted rule IDs + context)
    │   │   ├── Call Gemini Flash with structured output
    │   │   ├── Parse JSON array → list[RuleVerdict]
    │   │   └── Pro confirmation for DENY + CRITICAL rules
    │   │
    │   └── _fallback_per_rule()          ← on any failure
    │       └── asyncio.gather(evaluate_rule(...) for each rule)
    │
    └── (continues with aggregation, persistence, audit log)
```

**Files**:
- `apps/server/src/rulerepo_server/services/evaluation/batch_evaluator.py` — Core implementation
- `apps/server/src/rulerepo_server/services/evaluation/prompts/evaluate_batch.txt` — Code diff prompt
- `apps/server/src/rulerepo_server/services/evaluation/prompts/evaluate_batch_facts.txt` — Facts prompt
- `apps/server/src/rulerepo_server/services/evaluation/service.py` — Wiring (imports batch_evaluator, calls evaluate_batch)

**Key design decisions**:
- Single-rule optimization: for 1 rule, skips batching and calls `evaluate_rule()` directly
- Token budget: if prompt exceeds 30K chars, raises ValueError → fallback activates
- Cache key: `hash(sorted_rule_ids + context_hash + model_id)` — invalidated if any rule in batch changes
- Thinking level: `medium` for batches (multiple rules need more reasoning than single-rule `low`)

---

### 2. Evaluation Result Persistence

**Problem**: Analytics queries the `audit_log` table with complex `details->>'verdict'` JSON extraction. Slow, fragile, can't do per-rule analytics efficiently.

**Solution**: Dedicated `evaluations` table with structured columns.

**Schema** (migration 014):
```sql
CREATE TABLE evaluations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID REFERENCES projects(id),
    rule_id     UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    verdict     VARCHAR(30) NOT NULL,
    confidence  FLOAT NOT NULL,
    latency_ms  INTEGER NOT NULL DEFAULT 0,
    scope       VARCHAR(500),
    input_type  VARCHAR(20) NOT NULL DEFAULT 'code',
    model_id    VARCHAR(100) NOT NULL DEFAULT 'unknown',
    cached      BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Write path**: `evaluation/service.py` persists records after verdict aggregation, wrapped in try/except (persistence failure never breaks evaluation).

**Read path**: `intelligence/analytics.py` has dual-path queries:
- Primary: queries `evaluations` table directly (fast, structured)
- Fallback: queries `audit_log` with JSON extraction (for transition period when evaluations table may be empty)

**New analytics function**: `get_compliance_trend(session, days=7)` returns daily compliance rate for dashboard sparklines.

---

### 3. Dashboard Summary API

**Problem**: Home dashboard needs data from 5+ endpoints. Multiple round-trips, complex frontend state management.

**Solution**: Single `GET /api/v1/intelligence/summary` endpoint.

**Response shape**:
```json
{
    "compliance_rate": 0.847,
    "compliance_trend": [
        {"date": "2026-04-29", "total": 42, "allow_count": 35, "compliance_rate": 0.833}
    ],
    "total_rules": 677,
    "rules_by_status": {"APPROVED": 676, "DRAFT": 1},
    "top_violated_rules": [
        {"rule_id": "...", "violation_count": 5, "rule_statement": "..."}
    ],
    "recent_corrections": [
        {"id": "...", "status": "pending", "candidate_statement": "...", "created_at": "..."}
    ],
    "pending_actions": {
        "rules_pending_review": 1,
        "corrections_pending": 0,
        "active_alerts": 0
    }
}
```

**Implementation**: `IntelligenceService.get_home_summary()` runs 5 sequential queries (same SQLAlchemy session cannot run concurrent queries).

---

### 4. Outcome-Oriented Home Page

**Problem**: Home page was a placeholder with health check + 3 nav links.

**Solution**: Server Component fetching from `/api/v1/intelligence/summary`, rendering:

| Section | Data Source | What it shows |
|---------|-----------|---------------|
| Compliance Hero | compliance_rate + compliance_trend | Big percentage (color-coded) + 7-day bar chart |
| Rules Status Bar | total_rules + rules_by_status | Horizontal stacked bar (DRAFT/APPROVED/EFFECTIVE/RETIRED) |
| Pending Actions | pending_actions | 3 cards with counts linking to rules/feedback/alerts |
| Top Violated Rules | top_violated_rules | Table of top 5, linked to rule detail |
| Recent Corrections | recent_corrections | Last 5 with status badges |
| Quick Nav | static | Links to Browse Rules, Search, Documents, Playground, Intelligence |

**Graceful degradation**: If API is unreachable, renders minimal page with health status + nav links.

---

## Planned Features

### Active Rule Injection via Hooks

**Goal**: Rules reach agents proactively, without the agent needing to call MCP tools.

**Plan**:
1. `rulerepo hooks install` command writes `.claude/settings.json` with PreToolUse/PostToolUse hooks
2. `rulerepo-hook preflight --file <path>` determines scope from file path, fetches applicable rules, prints formatted rules
3. `rulerepo-hook posthoc --file <path>` evaluates the written file, prints violations (or nothing if ALLOW)

**Key files to modify**:
- `packages/cli/src/rulerepo_cli/hooks.py` — New file for `install` command
- `packages/cli/src/rulerepo_cli/hook.py` — Enhance preflight/posthoc with scope detection and formatted output

### Zero-Config Bootstrapping

**Goal**: `rulerepo init` scans a repo and generates `rules.yaml` in under 60 seconds.

**Plan**:
1. `packages/cli/src/rulerepo_cli/init.py` — New command wrapping existing discovery analyzers
2. Reuse `services/discovery/analyzers/claude_md.py`, `linter_config.py`, `code_patterns.py` for local execution
3. `POST /api/v1/rules/import/yaml` — New server endpoint for bulk import

### Correction-to-Rule Flywheel (Completed)

**Goal**: Corrections automatically generate draft rules.

**Implemented** in Phase 5/6:
1. `services/feedback/auto_drafter.py` -- Clusters corrections by cosine similarity, drafts rules via Gemini
2. Wired into arq worker as `cluster_corrections` daily cron job at 5am
3. Threshold: 3+ corrections in 14 days with confidence > 0.8 (`SIMILARITY_THRESHOLD=0.8`)
4. Creates `DraftRuleProposalModel` entries reviewed via `GET /api/v1/feedback/proposals`
5. Approved proposals create rules with `experimental` maturity (shadow mode)

### Infrastructure Tiers

**Goal**: Start with Postgres-only, add services as needed.

**Plan**:
1. Add `ELASTICSEARCH_ENABLED`, `NEO4J_ENABLED`, `REDIS_ENABLED` flags to Settings
2. Detect service availability at startup via lifespan
3. Postgres FTS fallback in search service
4. `docker-compose.lite.yml` with just Postgres + server + frontend

---

## Database Schema Updates (Phase 5)

| Migration | Table | Purpose |
|-----------|-------|---------|
| 014 | `evaluations` | Per-rule evaluation records for analytics |
| 015 | `rules.maturity_level` | Three-tier maturity model (experimental/stable/proven) |
| 016 | `draft_rule_proposals` | Auto-generated draft rule proposals from corrections |
