# Intelligence Dashboard — Implementation Plan

> Status: **COMPLETED**
> Date: 2026-04-29

---

## 1. Problem Statement

The Intelligence Dashboard (`/intelligence`) is the primary analytics surface for the Rule Repository. It is currently at ~40% completion — the backend provides rich analytics, health scoring, cache statistics, and top violation data, but the frontend renders only a skeleton with 4 summary cards, a truncated health table (3 of 6 dimensions), and a basic recommendation list.

Every other dashboard page (Discover, Feedback, Snapshots, Playground, etc.) is at 95-100% completion. The Intelligence page is the clear outlier and does not match the production quality of the rest of the application.

---

## 2. Gap Analysis

### 2.1 Backend Endpoints Available

| Endpoint | What It Returns | Frontend Status |
|---|---|---|
| `GET /intelligence/dashboard` | total_rules, avg_health, evaluations_30d, verdict_distribution, health_distribution, cache_stats, top_violated_rules, active_drift_alerts, open_recommendations | **Partial** — only 4 of 9 fields displayed |
| `GET /intelligence/health` | Paginated health scores with 6 dimensions + issues | **Partial** — 3 of 6 dimensions, no pagination controls |
| `GET /intelligence/health/{rule_id}` | Single rule health detail | **Unused** |
| `GET /intelligence/analytics` | Corpus-wide analytics (total evals, verdict rates, avg latency) | **Unused** |
| `GET /intelligence/analytics/{rule_id}` | Per-rule analytics | **Unused** |
| `GET /intelligence/recommendations` | Paginated recommendations with suggested_change, related_rule_ids | **Partial** — missing fields |

### 2.2 Structural Issues

1. **Raw fetch()** — Intelligence is the only page that uses raw `fetch()` instead of typed functions from `lib/api.ts`
2. **Server Component only** — No client-side interactivity (no sorting, pagination controls, drill-down, period selection)
3. **No responsive design** — Hard-coded `grid-cols-4` and `grid-cols-2`
4. **No loading/error states** — Silent failures when API is down

### 2.3 Comparison with Other Pages

| Page | Completeness | Interactive | Typed API | Actions |
|---|---|---|---|---|
| Rules | 100% | - | Yes | Create, link |
| Discover | 95% | Yes | Yes | Approve, dismiss, batch |
| Feedback | 100% | Yes | Yes | Approve, dismiss, submit |
| Snapshots | 100% | Yes | Yes | Create, deploy, simulate |
| Playground | 100% | Yes | Yes | Evaluate |
| **Intelligence** | **40%** | **No** | **No** | **None** |

---

## 3. Implementation Plan

### Priority 1: Data Layer (lib/api.ts)

Add typed TypeScript interfaces and API functions for all intelligence endpoints:

```typescript
// Interfaces
DashboardSummary, HealthScore, RuleAnalytics, Recommendation, CacheStats, TopViolatedRule

// Functions
getIntelligenceDashboard()
getHealthScores(page, pageSize, sortBy)
getRuleHealth(ruleId)
getAnalytics(periodDays)
getRuleAnalytics(ruleId, periodDays)
getRecommendations(status, page, pageSize)
```

### Priority 2: Full Dashboard Rewrite

Convert to a **client component** (`"use client"`) with the following sections:

#### Section A: Summary Cards (6 cards, responsive grid)
1. Total Rules
2. Avg Health Score (color-coded)
3. Evaluations (30d)
4. Open Recommendations
5. Active Alerts
6. Cache Hit Rate (percentage)

#### Section B: Distribution Overviews (2-column)
- **Health Distribution** — horizontal bar showing excellent/good/fair/poor counts with color
- **Verdict Distribution** — ALLOW/DENY/NEEDS_CONFIRMATION breakdown with percentage bars

#### Section C: Top Violated Rules
- Table: rule ID (linked), violation count, visual bar
- From `dashboard.top_violated_rules`

#### Section D: Rule Health Scores (full table)
- All 6 dimensions: overall, completeness, clarity, test_coverage, freshness, activity, owner_engagement
- Expandable rows showing issues list
- Sort by any dimension (column header click)
- Pagination controls
- Color-coded scores
- Link to rule detail page

#### Section E: Corpus Analytics
- Total evaluations, evaluations/day
- Average latency
- Period selector (7d / 30d / 90d / 365d)

#### Section F: Recommendations
- Priority-sorted list with badges
- Suggested change text (when available)
- Link to related rule
- Rule ID linkable

### Priority 3: Polish
- Loading skeleton states during data fetch
- Error banner on API failure
- Responsive grid (mobile-friendly breakpoints)
- Empty states with guidance

---

## 4. Files Changed

| File | Change |
|---|---|
| `apps/frontend/lib/api.ts` | Add Intelligence types + API functions |
| `apps/frontend/app/(dashboard)/intelligence/page.tsx` | Full rewrite |

---

## 5. Non-Goals

- No new backend endpoints or schema changes needed — backend already provides everything
- No new component files — intelligence page is self-contained (matching pattern of feedback, gateway pages)
- No chart library added — use CSS-based visualizations (bars, distribution indicators) to avoid new dependencies per CLAUDE.md rule 12

---

## 6. Implementation Result

All priorities were implemented. The page grew from 177 lines (server component, 40% complete) to 789 lines (client component, fully featured).

**Changes delivered:**
- `apps/frontend/lib/api.ts` — 8 typed interfaces and 5 API functions added for intelligence endpoints
- `apps/frontend/app/(dashboard)/intelligence/page.tsx` — full rewrite with all 6 sections (summary cards, distributions, top violated, health table, analytics, recommendations), client-side interactivity (period selector, sort, pagination, expandable rows), loading skeletons, and error handling

**Validation:** zero TypeScript errors, zero ESLint errors in changed files, successful build.
