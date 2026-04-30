"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  type DashboardSummary,
  type HealthScore,
  type HealthScoreList,
  type CorpusAnalytics,
  type IntelligenceRecommendation,
  type RecommendationList,
  type TopViolatedRule,
  getIntelligenceDashboard,
  getHealthScores,
  getCorpusAnalytics,
  getIntelligenceRecommendations,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

/* ---------- Constants ---------- */

const PERIOD_OPTIONS = [
  { label: "7d", value: 7 },
  { label: "30d", value: 30 },
  { label: "90d", value: 90 },
  { label: "365d", value: 365 },
] as const;

const HEALTH_SORT_OPTIONS = [
  { label: "Overall", value: "overall_score" },
  { label: "Completeness", value: "completeness" },
  { label: "Clarity", value: "clarity" },
  { label: "Test Coverage", value: "test_coverage" },
  { label: "Freshness", value: "freshness" },
  { label: "Activity", value: "activity" },
  { label: "Owner Engagement", value: "owner_engagement" },
] as const;

const PRIORITY_STYLES: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-gray-100 text-gray-600 border-gray-200",
};

const TYPE_STYLES: Record<string, string> = {
  retire: "bg-gray-100 text-gray-700",
  clarify: "bg-blue-100 text-blue-700",
  escalate: "bg-red-100 text-red-700",
  strengthen: "bg-green-100 text-green-700",
};

const HEALTH_DIST_COLORS: Record<string, string> = {
  excellent: "bg-green-500",
  good: "bg-blue-500",
  fair: "bg-yellow-500",
  poor: "bg-red-500",
};

const HEALTH_DIST_TEXT: Record<string, string> = {
  excellent: "text-green-700",
  good: "text-blue-700",
  fair: "text-yellow-700",
  poor: "text-red-700",
};

const VERDICT_COLORS: Record<string, string> = {
  ALLOW: "bg-green-500",
  DENY: "bg-red-500",
  NEEDS_CONFIRMATION: "bg-yellow-500",
};

const VERDICT_TEXT: Record<string, string> = {
  ALLOW: "text-green-700",
  DENY: "text-red-700",
  NEEDS_CONFIRMATION: "text-yellow-700",
};

/* ---------- Helpers ---------- */

function healthColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  if (score >= 40) return "text-orange-500";
  return "text-red-600";
}

function healthBg(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function scoreBar(score: number, maxWidth = 100): { width: string; bg: string } {
  return { width: `${Math.min(score, maxWidth)}%`, bg: healthBg(score) };
}

/* ---------- Component ---------- */

export default function IntelligencePage() {
  const { currentProject } = useProject();
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [health, setHealth] = useState<HealthScoreList | null>(null);
  const [analytics, setAnalytics] = useState<CorpusAnalytics | null>(null);
  const [recs, setRecs] = useState<RecommendationList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Controls
  const [analyticsPeriod, setAnalyticsPeriod] = useState(30);
  const [healthPage, setHealthPage] = useState(1);
  const [healthSort, setHealthSort] = useState("overall_score");
  const [expandedRuleId, setExpandedRuleId] = useState<string | null>(null);
  const [recsPage, setRecsPage] = useState(1);

  const PAGE_SIZE = 15;
  const RECS_PAGE_SIZE = 10;

  /* ---- Data fetching ---- */

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getIntelligenceDashboard(currentProject?.id);
      setDashboard(data);
    } catch {
      setError("Failed to load dashboard data.");
    }
  }, [currentProject?.id]);

  const loadHealth = useCallback(async () => {
    try {
      const data = await getHealthScores(healthPage, PAGE_SIZE, healthSort, currentProject?.id);
      setHealth(data);
    } catch {
      // non-critical, dashboard still usable
    }
  }, [healthPage, healthSort, currentProject?.id]);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await getCorpusAnalytics(analyticsPeriod, currentProject?.id);
      setAnalytics(data);
    } catch {
      // non-critical
    }
  }, [analyticsPeriod, currentProject?.id]);

  const loadRecs = useCallback(async () => {
    try {
      const data = await getIntelligenceRecommendations("open", recsPage, RECS_PAGE_SIZE, currentProject?.id);
      setRecs(data);
    } catch {
      // non-critical
    }
  }, [recsPage, currentProject?.id]);

  // Initial load
  useEffect(() => {
    setLoading(true);
    Promise.all([loadDashboard(), loadHealth(), loadAnalytics(), loadRecs()]).finally(() =>
      setLoading(false),
    );
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Reload on control changes
  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    loadRecs();
  }, [loadRecs]);

  /* ---- Loading state ---- */
  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Intelligence Dashboard</h1>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg border bg-gray-100" />
          ))}
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-48 animate-pulse rounded-lg border bg-gray-100" />
          <div className="h-48 animate-pulse rounded-lg border bg-gray-100" />
        </div>
        <div className="h-64 animate-pulse rounded-lg border bg-gray-100" />
      </div>
    );
  }

  /* ---- Error state ---- */
  if (error && !dashboard) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">Intelligence Dashboard</h1>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      </div>
    );
  }

  const verdictTotal = dashboard
    ? (Object.values(dashboard.verdict_distribution) as number[]).reduce((a: number, b: number) => a + b, 0)
    : 0;

  const healthDistTotal = dashboard
    ? (Object.values(dashboard.health_distribution) as number[]).reduce((a: number, b: number) => a + b, 0)
    : 0;

  const healthTotalPages = health ? Math.ceil(health.total / PAGE_SIZE) : 0;
  const recsTotalPages = recs ? Math.ceil(recs.total / RECS_PAGE_SIZE) : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Intelligence Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Rule health, evaluation analytics, and automated improvement recommendations
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-2 text-sm text-yellow-800">
          {error}
        </div>
      )}

      {/* ============ Section A: Summary Cards ============ */}
      {dashboard && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <SummaryCard label="Total Rules" value={String(dashboard.total_rules)} />
          <SummaryCard
            label="Avg Health Score"
            value={dashboard.avg_health_score.toFixed(1)}
            valueClassName={healthColor(dashboard.avg_health_score)}
          />
          <SummaryCard
            label="Evaluations (30d)"
            value={dashboard.total_evaluations_30d.toLocaleString()}
          />
          <SummaryCard
            label="Open Recommendations"
            value={String(dashboard.open_recommendations)}
            valueClassName={dashboard.open_recommendations > 0 ? "text-orange-600" : undefined}
          />
          <SummaryCard
            label="Active Alerts"
            value={String(dashboard.active_drift_alerts)}
            valueClassName={dashboard.active_drift_alerts > 0 ? "text-red-600" : undefined}
          />
          <SummaryCard
            label="Cache Hit Rate"
            value={
              dashboard.cache_stats
                ? formatPercent(dashboard.cache_stats.hit_rate)
                : "N/A"
            }
            subtitle={
              dashboard.cache_stats
                ? `${dashboard.cache_stats.cache_hits} hits / ${dashboard.cache_stats.cache_misses} misses`
                : undefined
            }
          />
        </div>
      )}

      {/* ============ Section B: Distributions ============ */}
      {dashboard && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Health Distribution */}
          <div className="rounded-lg border bg-white p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Health Distribution
            </h2>
            {healthDistTotal === 0 ? (
              <p className="text-sm text-gray-400">No rules to analyze yet.</p>
            ) : (
              <div className="space-y-3">
                {/* Stacked bar */}
                <div className="flex h-6 overflow-hidden rounded-full">
                  {(["excellent", "good", "fair", "poor"] as const).map((bucket) => {
                    const count = dashboard.health_distribution[bucket] ?? 0;
                    const pct = (count / healthDistTotal) * 100;
                    if (pct === 0) return null;
                    return (
                      <div
                        key={bucket}
                        className={`${HEALTH_DIST_COLORS[bucket]} transition-all`}
                        style={{ width: `${pct}%` }}
                        title={`${bucket}: ${count} (${pct.toFixed(0)}%)`}
                      />
                    );
                  })}
                </div>
                {/* Legend */}
                <div className="flex flex-wrap gap-4 text-xs">
                  {(["excellent", "good", "fair", "poor"] as const).map((bucket) => {
                    const count = dashboard.health_distribution[bucket] ?? 0;
                    return (
                      <span key={bucket} className="flex items-center gap-1.5">
                        <span className={`inline-block h-2.5 w-2.5 rounded-full ${HEALTH_DIST_COLORS[bucket]}`} />
                        <span className={`font-medium capitalize ${HEALTH_DIST_TEXT[bucket]}`}>
                          {bucket}
                        </span>
                        <span className="text-gray-400">
                          {count} ({healthDistTotal > 0 ? ((count / healthDistTotal) * 100).toFixed(0) : 0}%)
                        </span>
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Verdict Distribution */}
          <div className="rounded-lg border bg-white p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Verdict Distribution (30d)
            </h2>
            {verdictTotal === 0 ? (
              <p className="text-sm text-gray-400">No evaluations recorded yet.</p>
            ) : (
              <div className="space-y-3">
                {/* Stacked bar */}
                <div className="flex h-6 overflow-hidden rounded-full">
                  {(["ALLOW", "DENY", "NEEDS_CONFIRMATION"] as const).map((verdict) => {
                    const count = dashboard.verdict_distribution[verdict] ?? 0;
                    const pct = (count / verdictTotal) * 100;
                    if (pct === 0) return null;
                    return (
                      <div
                        key={verdict}
                        className={`${VERDICT_COLORS[verdict]} transition-all`}
                        style={{ width: `${pct}%` }}
                        title={`${verdict}: ${count} (${pct.toFixed(0)}%)`}
                      />
                    );
                  })}
                </div>
                {/* Legend */}
                <div className="flex flex-wrap gap-4 text-xs">
                  {(["ALLOW", "DENY", "NEEDS_CONFIRMATION"] as const).map((verdict) => {
                    const count = dashboard.verdict_distribution[verdict] ?? 0;
                    return (
                      <span key={verdict} className="flex items-center gap-1.5">
                        <span className={`inline-block h-2.5 w-2.5 rounded-full ${VERDICT_COLORS[verdict]}`} />
                        <span className={`font-medium ${VERDICT_TEXT[verdict]}`}>
                          {verdict.replace("_", " ")}
                        </span>
                        <span className="text-gray-400">
                          {count} ({verdictTotal > 0 ? ((count / verdictTotal) * 100).toFixed(0) : 0}%)
                        </span>
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============ Section C: Top Violated Rules + Analytics ============ */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top Violated Rules */}
        {dashboard && (
          <div className="rounded-lg border bg-white p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
              Top Violated Rules (30d)
            </h2>
            {(!dashboard.top_violated_rules || dashboard.top_violated_rules.length === 0) ? (
              <p className="text-sm text-gray-400">No violations recorded.</p>
            ) : (
              <div className="space-y-2">
                {dashboard.top_violated_rules.map((v: TopViolatedRule, i: number) => {
                  const maxCount = dashboard.top_violated_rules[0]?.violation_count ?? 1;
                  const pct = (v.violation_count / maxCount) * 100;
                  return (
                    <div key={v.rule_id} className="flex items-center gap-3 text-sm">
                      <span className="w-5 flex-shrink-0 text-right text-xs text-gray-400">
                        {i + 1}.
                      </span>
                      <Link
                        href={`/rules/${v.rule_id}`}
                        className="w-20 flex-shrink-0 truncate font-mono text-xs text-blue-600 hover:underline"
                        title={v.rule_id}
                      >
                        {v.rule_id.slice(0, 8)}...
                      </Link>
                      <div className="flex-1">
                        <div className="h-4 overflow-hidden rounded-full bg-gray-100">
                          <div
                            className="h-full rounded-full bg-red-400 transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                      <span className="w-10 flex-shrink-0 text-right font-medium text-red-600">
                        {v.violation_count}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Corpus Analytics */}
        <div className="rounded-lg border bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
              Evaluation Analytics
            </h2>
            <div className="flex rounded-md border">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setAnalyticsPeriod(opt.value)}
                  className={`px-3 py-1 text-xs font-medium transition-colors ${
                    analyticsPeriod === opt.value
                      ? "bg-blue-600 text-white"
                      : "text-gray-600 hover:bg-gray-50"
                  } ${opt.value === 7 ? "rounded-l-md" : ""} ${opt.value === 365 ? "rounded-r-md" : ""}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
          {!analytics ? (
            <p className="text-sm text-gray-400">Loading analytics...</p>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-500">Total Evaluations</p>
                <p className="text-2xl font-bold">{analytics.total_evaluations.toLocaleString()}</p>
                <p className="text-xs text-gray-400">
                  ~{(analytics.total_evaluations / Math.max(analyticsPeriod, 1)).toFixed(1)}/day
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Avg Latency</p>
                <p className="text-2xl font-bold">{Number(analytics.avg_latency_ms || 0).toFixed(0)}</p>
                <p className="text-xs text-gray-400">ms</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Compliance Rate</p>
                <p className={`text-2xl font-bold ${analytics.total_evaluations > 0 ? "text-green-600" : ""}`}>
                  {analytics.total_evaluations > 0
                    ? formatPercent(
                        (analytics.verdict_distribution.ALLOW ?? 0) /
                          Math.max(
                            (Object.values(analytics.verdict_distribution) as number[]).reduce((a: number, b: number) => a + b, 0),
                            1,
                          ),
                      )
                    : "N/A"}
                </p>
                <p className="text-xs text-gray-400">ALLOW rate</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ============ Section D: Health Scores Table ============ */}
      <div className="rounded-lg border bg-white p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Rule Health Scores
            {health && <span className="ml-2 font-normal normal-case text-gray-400">({health.total} rules)</span>}
          </h2>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-500">Sort by:</label>
            <select
              value={healthSort}
              onChange={(e) => { setHealthSort(e.target.value); setHealthPage(1); }}
              className="rounded border px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
            >
              {HEALTH_SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {!health || health.items.length === 0 ? (
          <p className="text-sm text-gray-400">No rules to analyze yet. Create rules to see health scores.</p>
        ) : (
          <>
            {/* Table header */}
            <div className="mb-1 grid grid-cols-[1fr_repeat(7,_minmax(0,_70px))] gap-2 border-b pb-2 text-xs font-semibold text-gray-500">
              <span>Rule</span>
              <span className="text-right">Overall</span>
              <span className="text-right">Complete</span>
              <span className="text-right">Clarity</span>
              <span className="text-right">Coverage</span>
              <span className="text-right">Fresh</span>
              <span className="text-right">Activity</span>
              <span className="text-right">Owner</span>
            </div>

            {/* Rows */}
            <div className="divide-y">
              {health.items.map((h: HealthScore) => (
                <HealthRow
                  key={h.rule_id}
                  score={h}
                  expanded={expandedRuleId === h.rule_id}
                  onToggle={() =>
                    setExpandedRuleId(expandedRuleId === h.rule_id ? null : h.rule_id)
                  }
                />
              ))}
            </div>

            {/* Pagination */}
            {healthTotalPages > 1 && (
              <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                <span>
                  Showing {(healthPage - 1) * PAGE_SIZE + 1}–
                  {Math.min(healthPage * PAGE_SIZE, health.total)} of {health.total}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setHealthPage((p) => Math.max(1, p - 1))}
                    disabled={healthPage === 1}
                    className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="px-2 py-1 text-gray-400">
                    {healthPage} / {healthTotalPages}
                  </span>
                  <button
                    onClick={() => setHealthPage((p) => Math.min(healthTotalPages, p + 1))}
                    disabled={healthPage === healthTotalPages}
                    className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ============ Section E: Recommendations ============ */}
      <div className="rounded-lg border bg-white p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Recommendations
          {recs && recs.total > 0 && (
            <span className="ml-2 font-normal normal-case text-gray-400">({recs.total} open)</span>
          )}
        </h2>

        {!recs || recs.items.length === 0 ? (
          <p className="text-sm text-gray-400">No recommendations at this time. All rules are in good shape.</p>
        ) : (
          <>
            <div className="space-y-3">
              {recs.items.map((r: IntelligenceRecommendation) => (
                <RecommendationCard key={r.id} rec={r} />
              ))}
            </div>

            {/* Pagination */}
            {recsTotalPages > 1 && (
              <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
                <span>
                  Showing {(recsPage - 1) * RECS_PAGE_SIZE + 1}–
                  {Math.min(recsPage * RECS_PAGE_SIZE, recs.total)} of {recs.total}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setRecsPage((p) => Math.max(1, p - 1))}
                    disabled={recsPage === 1}
                    className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="px-2 py-1 text-gray-400">
                    {recsPage} / {recsTotalPages}
                  </span>
                  <button
                    onClick={() => setRecsPage((p) => Math.min(recsTotalPages, p + 1))}
                    disabled={recsPage === recsTotalPages}
                    className="rounded border px-3 py-1 hover:bg-gray-100 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ---------- Sub-components ---------- */

function SummaryCard({
  label,
  value,
  valueClassName,
  subtitle,
}: {
  label: string;
  value: string;
  valueClassName?: string;
  subtitle?: string;
}) {
  return (
    <div className="rounded-lg border bg-white p-4">
      <p className="text-xs font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${valueClassName ?? ""}`}>{value}</p>
      {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
    </div>
  );
}

function HealthRow({
  score: h,
  expanded,
  onToggle,
}: {
  score: HealthScore;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div>
      <div
        className="grid cursor-pointer grid-cols-[1fr_repeat(7,_minmax(0,_70px))] items-center gap-2 py-2 text-sm hover:bg-gray-50"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <svg
            className={`h-3.5 w-3.5 flex-shrink-0 text-gray-400 transition-transform ${expanded ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <Link
            href={`/rules/${h.rule_id}`}
            className="truncate font-mono text-xs text-blue-600 hover:underline"
            onClick={(e) => e.stopPropagation()}
            title={h.rule_id}
          >
            {h.rule_id.slice(0, 12)}...
          </Link>
        </div>
        <ScoreCell value={h.overall_score} bold />
        <ScoreCell value={h.completeness} />
        <ScoreCell value={h.clarity} />
        <ScoreCell value={h.test_coverage} />
        <ScoreCell value={h.freshness} />
        <ScoreCell value={h.activity} />
        <ScoreCell value={h.owner_engagement} />
      </div>

      {/* Expanded detail: issues + score bars */}
      {expanded && (
        <div className="border-t bg-gray-50 px-4 py-3">
          <div className="mb-3 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
            {[
              { label: "Completeness", value: h.completeness },
              { label: "Clarity", value: h.clarity },
              { label: "Test Coverage", value: h.test_coverage },
              { label: "Freshness", value: h.freshness },
              { label: "Activity", value: h.activity },
              { label: "Owner Engagement", value: h.owner_engagement },
            ].map((dim) => {
              const bar = scoreBar(dim.value);
              return (
                <div key={dim.label}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-gray-500">{dim.label}</span>
                    <span className={`font-medium ${healthColor(dim.value)}`}>
                      {dim.value.toFixed(0)}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                    <div className={`h-full rounded-full ${bar.bg}`} style={{ width: bar.width }} />
                  </div>
                </div>
              );
            })}
          </div>

          {h.issues.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs font-semibold text-gray-500">Issues</p>
              <ul className="space-y-1">
                {h.issues.map((issue: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                    <span className="mt-0.5 inline-block h-1.5 w-1.5 flex-shrink-0 rounded-full bg-orange-400" />
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreCell({ value, bold }: { value: number; bold?: boolean }) {
  return (
    <span
      className={`text-right text-xs ${healthColor(value)} ${bold ? "font-bold" : ""}`}
      title={value.toFixed(1)}
    >
      {value.toFixed(0)}
    </span>
  );
}

function RecommendationCard({ rec: r }: { rec: IntelligenceRecommendation }) {
  const priorityBorderColor: Record<string, string> = {
    critical: "border-l-red-500",
    high: "border-l-orange-500",
    medium: "border-l-yellow-500",
    low: "border-l-gray-300",
  };

  return (
    <div className={`rounded-lg border border-l-4 ${priorityBorderColor[r.priority] ?? "border-l-gray-300"} bg-white p-4`}>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_STYLES[r.priority] ?? "bg-gray-100"}`}
        >
          {r.priority}
        </span>
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${TYPE_STYLES[r.type] ?? "bg-gray-100 text-gray-700"}`}>
          {r.type}
        </span>
        {r.rule_id && (
          <Link
            href={`/rules/${r.rule_id}`}
            className="font-mono text-xs text-blue-600 hover:underline"
          >
            {r.rule_id.slice(0, 8)}...
          </Link>
        )}
      </div>
      <p className="mt-2 text-sm font-medium">{r.title}</p>
      <p className="mt-0.5 text-xs text-gray-500">{r.description}</p>
      {r.suggested_change && (
        <div className="mt-2 rounded bg-blue-50 px-3 py-2">
          <p className="text-xs font-semibold text-blue-700">Suggested change:</p>
          <p className="text-xs text-blue-600">{r.suggested_change}</p>
        </div>
      )}
      {r.related_rule_ids && r.related_rule_ids.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          <span className="text-xs text-gray-400">Related:</span>
          {r.related_rule_ids.map((id: string) => (
            <Link
              key={id}
              href={`/rules/${id}`}
              className="font-mono text-xs text-blue-600 hover:underline"
            >
              {id.slice(0, 8)}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
