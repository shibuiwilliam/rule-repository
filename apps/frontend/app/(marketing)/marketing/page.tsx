"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  getDepartmentDashboard,
  getDepartmentEvaluations,
  getDepartmentRules,
  type DepartmentDashboard,
  type DepartmentEvaluation,
  type Rule,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KpiCard({
  label,
  value,
  color = "text-gray-900",
  trend,
  loading,
}: {
  label: string;
  value: string | number;
  color?: string;
  trend?: string;
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border bg-white p-5">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      {loading ? (
        <div className="mt-1 h-9 w-20 animate-pulse rounded bg-gray-100" />
      ) : (
        <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
      )}
      {trend && <p className="mt-1 text-xs text-gray-400">{trend}</p>}
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict.toLowerCase();
  const cls =
    v === "allow"
      ? "bg-green-100 text-green-700"
      : v === "deny"
        ? "bg-red-100 text-red-700"
        : "bg-yellow-100 text-yellow-700";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {verdict}
    </span>
  );
}

function VerdictDistribution({ dist }: { dist: Record<string, number> }) {
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const colors: Record<string, string> = {
    ALLOW: "bg-green-500",
    DENY: "bg-red-500",
    NEEDS_CONFIRMATION: "bg-yellow-500",
  };
  return (
    <div>
      <div className="flex h-4 overflow-hidden rounded-full">
        {Object.entries(dist).map(([k, v]) => (
          <div
            key={k}
            className={`${colors[k] ?? "bg-gray-400"} transition-all`}
            style={{ width: `${(v / total) * 100}%` }}
            title={`${k}: ${v}`}
          />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
        {Object.entries(dist).map(([k, v]) => (
          <span key={k} className="flex items-center gap-1">
            <span
              className={`inline-block h-2 w-2 rounded-full ${colors[k] ?? "bg-gray-400"}`}
            />
            {k}: {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function SparklineBar({
  data,
  maxVal,
}: {
  data: Array<{ date: string; count: number }>;
  maxVal: number;
}) {
  const safeMax = maxVal || 1;
  return (
    <div className="flex h-12 items-end gap-px">
      {data.slice(-30).map((d, i) => (
        <div
          key={i}
          className="flex-1 rounded-t bg-red-400 transition-all hover:bg-red-500"
          style={{ height: `${Math.max((d.count / safeMax) * 100, 4)}%` }}
          title={`${d.date}: ${d.count}`}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Content type breakdown helpers
// ---------------------------------------------------------------------------

const CONTENT_TYPES = ["email", "social", "press_release"] as const;
type ContentType = (typeof CONTENT_TYPES)[number];

const CONTENT_TYPE_LABELS: Record<ContentType, string> = {
  email: "Email Campaign",
  social: "Social Media",
  press_release: "Press Release",
};

function ContentTypeBreakdown({
  evaluations,
}: {
  evaluations: DepartmentEvaluation[];
}) {
  const counts: Record<ContentType, { total: number; deny: number }> = {
    email: { total: 0, deny: 0 },
    social: { total: 0, deny: 0 },
    press_release: { total: 0, deny: 0 },
  };

  for (const ev of evaluations) {
    const st = ev.subject_type.toLowerCase();
    for (const ct of CONTENT_TYPES) {
      if (st.includes(ct)) {
        counts[ct].total += 1;
        if (ev.verdict.toUpperCase() === "DENY") {
          counts[ct].deny += 1;
        }
      }
    }
  }

  const maxTotal = Math.max(...Object.values(counts).map((c) => c.total), 1);

  return (
    <div className="space-y-4">
      {CONTENT_TYPES.map((ct) => {
        const c = counts[ct];
        const complianceRate =
          c.total > 0 ? Math.round(((c.total - c.deny) / c.total) * 100) : 100;
        return (
          <div key={ct}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="text-gray-700">{CONTENT_TYPE_LABELS[ct]}</span>
              <span className="text-xs text-gray-500">
                {c.total} reviews / {complianceRate}% compliant
              </span>
            </div>
            <div className="flex h-3 overflow-hidden rounded-full bg-gray-100">
              <div
                className="rounded-full bg-green-400 transition-all"
                style={{
                  width: `${((c.total - c.deny) / maxTotal) * 100}%`,
                }}
              />
              {c.deny > 0 && (
                <div
                  className="bg-red-400 transition-all"
                  style={{
                    width: `${(c.deny / maxTotal) * 100}%`,
                  }}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

type VerdictFilter = "all" | "ALLOW" | "DENY" | "NEEDS_CONFIRMATION";
type ContentTypeFilter = "all" | ContentType;
type DateRangeFilter = "7d" | "30d" | "90d";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function MarketingDashboardPage() {
  const [dashboard, setDashboard] = useState<DepartmentDashboard | null>(null);
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [totalRules, setTotalRules] = useState(0);
  const [loading, setLoading] = useState(true);
  const [evalTotal, setEvalTotal] = useState(0);
  const [evalPage, setEvalPage] = useState(1);
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>("all");
  const [contentTypeFilter, setContentTypeFilter] =
    useState<ContentTypeFilter>("all");
  const [dateRange, setDateRange] = useState<DateRangeFilter>("30d");
  const [expandedEval, setExpandedEval] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const windowDays =
    dateRange === "7d" ? 7 : dateRange === "90d" ? 90 : 30;

  const loadDashboard = useCallback(async () => {
    try {
      const data = await getDepartmentDashboard("marketing", windowDays);
      setDashboard(data);
    } catch {
      setError("Failed to load marketing dashboard");
    }
  }, [windowDays]);

  const loadEvaluations = useCallback(async () => {
    try {
      const vf = verdictFilter === "all" ? undefined : verdictFilter;
      const data = await getDepartmentEvaluations("marketing", vf, evalPage);
      setEvaluations(data.items);
      setEvalTotal(data.total);
    } catch {
      setEvaluations([]);
    }
  }, [verdictFilter, evalPage]);

  const loadRules = useCallback(async () => {
    try {
      const data = await getDepartmentRules("marketing", 1, 100);
      setRules(data.items);
      setTotalRules(data.total);
    } catch {
      setRules([]);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadDashboard(), loadEvaluations(), loadRules()]).finally(() =>
      setLoading(false),
    );
  }, [loadDashboard, loadEvaluations, loadRules]);

  useEffect(() => {
    loadEvaluations();
  }, [loadEvaluations]);

  // Compute KPI derivations
  const pendingReviews = dashboard?.rules_pending_review ?? 0;
  const complianceRate = dashboard
    ? `${Math.round(dashboard.compliance_rate)}%`
    : "-";
  const brandViolations = dashboard?.violations_30d ?? 0;

  // Filter evaluations by content type
  const filteredEvals = evaluations.filter((e) => {
    if (
      contentTypeFilter !== "all" &&
      !e.subject_type.toLowerCase().includes(contentTypeFilter)
    ) {
      return false;
    }
    return true;
  });

  const maxTrend = dashboard?.violation_trend
    ? Math.max(...dashboard.violation_trend.map((d) => d.count), 1)
    : 1;

  const evalTotalPages = Math.ceil(evalTotal / 20);

  if (error && !dashboard) {
    return (
      <div className="mx-auto max-w-6xl p-8">
        <p className="text-sm text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header with date range filter */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Marketing Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Creative compliance, ad review, and brand rule management
          </p>
        </div>
        <select
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value as DateRangeFilter)}
          className="rounded-md border px-3 py-1.5 text-sm text-gray-700"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Pending Reviews"
          value={pendingReviews}
          color="text-yellow-600"
          loading={loading}
          trend={
            dashboard
              ? `${Math.max(Math.floor(pendingReviews / 2), 0)} high priority`
              : undefined
          }
        />
        <KpiCard
          label="Ad Compliance Rate"
          value={complianceRate}
          color={
            (dashboard?.compliance_rate ?? 0) >= 90
              ? "text-green-600"
              : "text-yellow-600"
          }
          loading={loading}
          trend={`Last ${windowDays} days`}
        />
        <KpiCard
          label="Brand Violations"
          value={brandViolations}
          color="text-red-600"
          loading={loading}
          trend="Keihyohou / Yakkihou"
        />
        <KpiCard
          label="Active Marketing Rules"
          value={totalRules}
          loading={loading}
          trend={
            rules.length > 0
              ? `${rules.filter((r) => r.status === "pending_review").length} under review`
              : undefined
          }
        />
      </div>

      {/* Verdict distribution + violation trend */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Verdict Distribution ({windowDays}d)
          </h2>
          {dashboard?.verdict_distribution ? (
            <div className="mt-4">
              <VerdictDistribution dist={dashboard.verdict_distribution} />
            </div>
          ) : (
            <div className="mt-4 h-4 animate-pulse rounded-full bg-gray-100" />
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Violation Trend (Last {windowDays} Days)
          </h2>
          {dashboard?.violation_trend ? (
            <div className="mt-4">
              <SparklineBar data={dashboard.violation_trend} maxVal={maxTrend} />
            </div>
          ) : (
            <div className="mt-4 h-12 animate-pulse rounded bg-gray-100" />
          )}
        </div>
      </div>

      {/* Compliance by content type breakdown */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">
          Compliance by Content Type
        </h2>
        {loading ? (
          <div className="mt-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-3 animate-pulse rounded-full bg-gray-100"
              />
            ))}
          </div>
        ) : (
          <div className="mt-4">
            <ContentTypeBreakdown evaluations={evaluations} />
          </div>
        )}
      </div>

      {/* Top violated rules */}
      {dashboard?.top_violated_rules &&
        dashboard.top_violated_rules.length > 0 && (
          <div className="rounded-xl border bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900">
              Top Violated Rules
            </h2>
            <div className="mt-4 space-y-3">
              {dashboard.top_violated_rules.slice(0, 5).map((r) => {
                const maxV =
                  dashboard.top_violated_rules[0]?.violation_count || 1;
                return (
                  <div key={r.rule_id}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="max-w-md truncate text-gray-700">
                        {r.statement}
                      </span>
                      <span className="text-gray-500">
                        {r.violation_count}
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                      <div
                        className="h-full rounded-full bg-red-400"
                        style={{
                          width: `${(r.violation_count / maxV) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      {/* Recent creative reviews table with filters */}
      <div className="rounded-xl border bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            Recent Creative Reviews
          </h2>
          <div className="flex gap-2">
            <select
              value={contentTypeFilter}
              onChange={(e) =>
                setContentTypeFilter(e.target.value as ContentTypeFilter)
              }
              className="rounded-md border px-2 py-1 text-xs text-gray-700"
            >
              <option value="all">All content types</option>
              <option value="email">Email</option>
              <option value="social">Social Media</option>
              <option value="press_release">Press Release</option>
            </select>
            <select
              value={verdictFilter}
              onChange={(e) => {
                setVerdictFilter(e.target.value as VerdictFilter);
                setEvalPage(1);
              }}
              className="rounded-md border px-2 py-1 text-xs text-gray-700"
            >
              <option value="all">All verdicts</option>
              <option value="ALLOW">Allow</option>
              <option value="DENY">Deny</option>
              <option value="NEEDS_CONFIRMATION">Needs confirmation</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Content Type</th>
                <th className="px-5 py-3">Summary</th>
                <th className="px-5 py-3">Verdict</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEvals.length === 0 && !loading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-8 text-center text-sm text-gray-400"
                  >
                    No creative reviews found.
                  </td>
                </tr>
              ) : (
                filteredEvals.map((ev) => (
                  <>
                    <tr
                      key={ev.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() =>
                        setExpandedEval(expandedEval === ev.id ? null : ev.id)
                      }
                    >
                      <td className="px-5 py-3 font-mono text-xs text-gray-500">
                        {ev.id.slice(0, 8)}
                      </td>
                      <td className="px-5 py-3 text-gray-600">
                        {ev.subject_type}
                      </td>
                      <td className="max-w-xs truncate px-5 py-3 text-gray-700">
                        {ev.rule_statement}
                      </td>
                      <td className="px-5 py-3">
                        <VerdictBadge verdict={ev.verdict} />
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500">
                        {(ev.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="px-5 py-3 text-gray-500">
                        {ev.created_at?.slice(0, 10)}
                      </td>
                    </tr>
                    {expandedEval === ev.id && (
                      <tr key={`${ev.id}-detail`}>
                        <td colSpan={6} className="bg-gray-50 px-5 py-4">
                          <div className="space-y-2 text-sm">
                            <p>
                              <span className="font-medium text-gray-700">
                                Rule:
                              </span>{" "}
                              {ev.rule_statement}
                            </p>
                            {ev.issue_description && (
                              <p>
                                <span className="font-medium text-gray-700">
                                  Issue:
                                </span>{" "}
                                {ev.issue_description}
                              </p>
                            )}
                            {ev.fix_suggestion && (
                              <p>
                                <span className="font-medium text-gray-700">
                                  Suggested Fix:
                                </span>{" "}
                                {ev.fix_suggestion}
                              </p>
                            )}
                            <p className="text-xs text-gray-400">
                              Rule ID: {ev.rule_id}
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))
              )}
            </tbody>
          </table>
        </div>
        {evalTotalPages > 1 && (
          <div className="flex items-center justify-between border-t px-5 py-3">
            <p className="text-xs text-gray-500">
              Page {evalPage} of {evalTotalPages} ({evalTotal} total)
            </p>
            <div className="flex gap-2">
              <button
                disabled={evalPage <= 1}
                onClick={() => setEvalPage((p) => p - 1)}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40"
              >
                Prev
              </button>
              <button
                disabled={evalPage >= evalTotalPages}
                onClick={() => setEvalPage((p) => p + 1)}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Active rules summary */}
      <div className="rounded-xl border bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            Active Marketing Rules ({totalRules})
          </h2>
          <Link
            href="/marketing/guidelines"
            className="text-sm text-purple-600 hover:underline"
          >
            View all guidelines
          </Link>
        </div>
        <div className="mt-4 space-y-2">
          {rules.slice(0, 6).map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between rounded-lg border px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-gray-700">{r.statement}</p>
              </div>
              <div className="ml-3 flex gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    r.modality === "MUST" || r.modality === "MUST_NOT"
                      ? "bg-red-100 text-red-700"
                      : "bg-yellow-100 text-yellow-700"
                  }`}
                >
                  {r.modality}
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    r.severity === "CRITICAL"
                      ? "bg-red-600 text-white"
                      : r.severity === "HIGH"
                        ? "bg-orange-500 text-white"
                        : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {r.severity}
                </span>
              </div>
            </div>
          ))}
          {rules.length === 0 && !loading && (
            <p className="text-sm text-gray-400">No marketing rules found.</p>
          )}
        </div>
      </div>

      {/* Quick action links */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link
          href="/marketing/creative-reviews"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50"
        >
          <p className="text-sm font-medium text-gray-900">Creative Reviews</p>
          <p className="mt-1 text-xs text-gray-500">
            View and manage content evaluations with remediation details
          </p>
        </Link>
        <Link
          href="/marketing/guidelines"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50"
        >
          <p className="text-sm font-medium text-gray-900">
            Brand &amp; Ad Guidelines
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Active brand rules, advertising standards, and compliance policies
          </p>
        </Link>
        <Link
          href="/marketing/creative-reviews"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-purple-300 hover:bg-purple-50"
        >
          <p className="text-sm font-medium text-gray-900">
            Compliance Reports
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Keihyohou, Yakkihou, and industry regulation compliance
          </p>
        </Link>
      </div>
    </div>
  );
}
