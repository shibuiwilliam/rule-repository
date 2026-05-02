# Proactive Rule Delivery & Quality Visibility

This document covers the improvements that make rules reach agents automatically, surface rule effectiveness throughout the UI, and generate quality-based alerts.

---

## 1. CLAUDE.md Context Generator

### CLI Command: `rulerepo-context`

**File:** `packages/cli/src/rulerepo_cli/context.py`

Three modes:

| Command | Purpose |
|---|---|
| `rulerepo-context generate --server URL` | Print formatted rules section to stdout |
| `rulerepo-context update --file CLAUDE.md` | Update file in-place (preserves existing content) |
| `rulerepo-context watch --file CLAUDE.md` | Poll and regenerate every N seconds |

**How in-place update works:**

1. Reads the existing file
2. Finds `<!-- rulerepo:rules:start -->` and `<!-- rulerepo:rules:end -->` markers
3. Replaces content between markers with fresh rules
4. If no markers exist, appends the section at the end
5. Writes back to file

**Output format:**

```markdown
<!-- rulerepo:rules:start -->
## Rules (auto-managed by Rule Repository)

### MUST
- All Python functions must have type annotations [HIGH]

### Never
- MUST NOT use bare except [CRITICAL]

### SHOULD
- Use dependency injection [MEDIUM]

_47 rules from project "backend-api" | Updated 2026-05-02T02:00:00Z_
<!-- rulerepo:rules:end -->
```

**Integration points:**
- Git pre-push hook: regenerate CLAUDE.md before pushing
- CI: regenerate and commit if changed
- `RULEREPO_SERVER_URL` env var for default server

---

## 2. Rule Effectiveness Visibility

### Where Effectiveness Appears

| Location | What's shown | Data source |
|---|---|---|
| **Rule detail page** | Score (0-100), precision/prevention/adoption bars, TP/FP counts | `GET /intelligence/effectiveness/{id}` |
| **Dashboard top violated** | "eff N" badge next to deny count (color-coded) | `get_home_summary()` enriches violated rules |
| **Rules list page** | Quality dot column (green/yellow/red/gray) | Client-side fetch per displayed rule |
| **Weekly digest** | `most_effective_rules` (top 5), `declining_rules` (score < 30) | `generate_weekly_digest()` |

### Rule Detail Page Implementation

**File:** `apps/frontend/app/(dashboard)/rules/[id]/page.tsx`

Fetches from `GET /api/v1/intelligence/effectiveness/{id}` (non-blocking — page renders without it). Displays:

- Composite score (big number, green >= 70, yellow >= 40, red < 40)
- Three `EffectivenessBar` components for precision, prevention rate, agent adoption
- Evaluation count + true/false positive counts

### Dashboard Implementation

**File:** `apps/server/src/rulerepo_server/services/intelligence/service.py`

In `get_home_summary()`, after fetching top violated rules, enriches each with effectiveness:

```python
from rulerepo_server.services.intelligence.effectiveness import compute_effectiveness

for item in top_violated:
    eff = await compute_effectiveness(self._session, item["rule_id"], period_days=30)
    item["effectiveness_score"] = eff["effectiveness_score"]
```

The frontend shows an "eff" badge: green (>= 60), yellow (>= 30), red (< 30).

### Rules List Implementation

**File:** `apps/frontend/app/(dashboard)/rules/page.tsx`

After loading rules, fires parallel fetch requests for effectiveness scores:

```typescript
await Promise.all(
  result.items.map(async (rule) => {
    const res = await fetch(`${API_BASE}/api/v1/intelligence/effectiveness/${rule.id}`);
    if (res.ok) scores[rule.id] = (await res.json()).effectiveness_score;
  })
);
```

Renders a colored dot in a "Quality" column.

---

## 3. Dashboard Alert Banner

**File:** `apps/frontend/app/page.tsx`

Fetches the latest active warning/critical alert:

```typescript
const alertsRes = await fetch(`${API_BASE}/api/v1/alerts?status=active&page_size=1`);
```

If found, renders a clickable banner above the compliance hero:
- Red border + background for critical alerts
- Yellow border + background for warning alerts
- Links to the rule detail page (if `rule_id` set) or `/alerts`

---

## 4. Effectiveness-Based Alerts

**File:** `apps/server/src/rulerepo_server/workers/settings.py`

In the `compute_health_scores` cron job (2am daily), after computing health scores:

```python
if total_judgments >= 10:
    eff = await compute_effectiveness(session, str(rule.id), period_days=30)
    if eff["effectiveness_score"] < 30:
        # Create effectiveness_decline alert
```

Alert includes: effectiveness score, precision, FP/TP counts, and actionable suggestion ("Consider rewriting or narrowing scope").

---

## 5. Weekly Digest Effectiveness Sections

**File:** `apps/server/src/rulerepo_server/services/intelligence/digest.py`

Two new sections in the digest response:

- `most_effective_rules` — Top 5 rules by effectiveness score (from rules with >= 3 evaluations in 7 days)
- `declining_rules` — Rules with effectiveness score < 30

Both computed by calling `compute_effectiveness()` for sampled active rules.
