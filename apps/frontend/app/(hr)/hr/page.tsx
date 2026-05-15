"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getDepartmentDashboard,
  getDepartmentEvaluations,
  type DepartmentDashboard,
  type DepartmentEvaluation,
} from "@/lib/api";
import { usePersonaTerm } from "@/lib/use-persona-term";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type PeriodOption = "7" | "30" | "90";
type VerdictFilter = "" | "allow" | "deny" | "needs_confirmation";

const PERIOD_OPTIONS: { value: PeriodOption; label: string }[] = [
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
  { value: "90", label: "90 days" },
];

const VERDICT_OPTIONS: { value: VerdictFilter; label: string }[] = [
  { value: "", label: "All verdicts" },
  { value: "deny", label: "Deny" },
  { value: "allow", label: "Allow" },
  { value: "needs_confirmation", label: "Needs confirmation" },
];

const DEPARTMENT_OPTIONS = [
  { value: "hr", label: "All HR" },
  { value: "hr/attendance", label: "Attendance" },
  { value: "hr/leave", label: "Leave" },
  { value: "hr/payroll", label: "Payroll" },
  { value: "hr/benefits", label: "Benefits" },
];

const VERDICT_BADGE_STYLES: Record<string, string> = {
  allow: "bg-green-100 text-green-700",
  deny: "bg-red-100 text-red-700",
  needs_confirmation: "bg-yellow-100 text-yellow-700",
};

const PAGE_SIZE = 10;

// ---------------------------------------------------------------------------
// StatCard
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  trend,
  color = "text-gray-900",
  loading = false,
}: {
  label: string;
  value: string | number;
  trend?: string;
  color?: string;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border bg-white p-5 animate-pulse">
        <div className="h-4 w-24 rounded bg-gray-200" />
        <div className="mt-3 h-8 w-16 rounded bg-gray-200" />
        <div className="mt-2 h-3 w-32 rounded bg-gray-100" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-white p-5 transition-colors hover:border-indigo-300 hover:bg-indigo-50">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
      {trend && <p className="mt-1 text-xs text-gray-400">{trend}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Verdict Badge
// ---------------------------------------------------------------------------

function VerdictBadge({ verdict }: { verdict: string }) {
  const style = VERDICT_BADGE_STYLES[verdict] ?? "bg-gray-100 text-gray-700";
  const label = verdict.replace(/_/g, " ");
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}>
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Confidence bar
// ---------------------------------------------------------------------------

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const barColor = pct >= 80 ? "bg-green-500" : pct >= 50 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section skeleton
// ---------------------------------------------------------------------------

function SectionSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="rounded-xl border bg-white p-5 animate-pulse">
      <div className="h-5 w-40 rounded bg-gray-200" />
      <div className="mt-4 space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-4 w-full rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function HrDashboardPage() {
  // --- persona vocabulary --------------------------------------------------
  const t = usePersonaTerm();

  // --- state ---------------------------------------------------------------
  const [period, setPeriod] = useState<PeriodOption>("30");
  const [departmentFilter, setDepartmentFilter] = useState("hr");
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>("");
  const [evalPage, setEvalPage] = useState(1);

  const [dashboard, setDashboard] = useState<DepartmentDashboard | null>(null);
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [evalTotal, setEvalTotal] = useState(0);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const [loadingDash, setLoadingDash] = useState(true);
  const [loadingEvals, setLoadingEvals] = useState(true);
  const [errorDash, setErrorDash] = useState<string | null>(null);
  const [errorEvals, setErrorEvals] = useState<string | null>(null);

  // --- data fetchers -------------------------------------------------------

  const fetchDashboard = useCallback(async () => {
    setLoadingDash(true);
    setErrorDash(null);
    try {
      const data = await getDepartmentDashboard(departmentFilter, Number(period));
      setDashboard(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load dashboard";
      setErrorDash(message);
    } finally {
      setLoadingDash(false);
    }
  }, [departmentFilter, period]);

  const fetchEvaluations = useCallback(async () => {
    setLoadingEvals(true);
    setErrorEvals(null);
    try {
      const data = await getDepartmentEvaluations(
        departmentFilter,
        verdictFilter || undefined,
        evalPage,
        PAGE_SIZE,
      );
      setEvaluations(data.items);
      setEvalTotal(data.total);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load evaluations";
      setErrorEvals(message);
    } finally {
      setLoadingEvals(false);
    }
  }, [departmentFilter, verdictFilter, evalPage]);

  useEffect(() => {
    void fetchDashboard();
  }, [fetchDashboard]);

  useEffect(() => {
    void fetchEvaluations();
  }, [fetchEvaluations]);

  // Reset page when filters change
  useEffect(() => {
    setEvalPage(1);
  }, [departmentFilter, verdictFilter, period]);

  // --- derived values ------------------------------------------------------

  const totalPages = Math.max(1, Math.ceil(evalTotal / PAGE_SIZE));

  const complianceRate = dashboard ? Math.round(dashboard.compliance_rate * 100) : 0;

  const trendMax = dashboard?.violation_trend?.length
    ? Math.max(...dashboard.violation_trend.map((t) => t.count), 1)
    : 1;

  const verdictDistTotal = dashboard?.verdict_distribution
    ? Object.values(dashboard.verdict_distribution).reduce((a, b) => a + b, 0)
    : 0;

  const topViolatedMax = dashboard?.top_violated_rules?.length
    ? Math.max(...dashboard.top_violated_rules.map((r) => r.violation_count), 1)
    : 1;

  // --- render --------------------------------------------------------------

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t("landing_title", "HR Dashboard")}</h1>
          <p className="mt-1 text-sm text-gray-500">
            Labor compliance overview and workforce risk indicators
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value as PeriodOption)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
            aria-label="Period selector"
          >
            {PERIOD_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
            aria-label="Department filter"
          >
            {DEPARTMENT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          <select
            value={verdictFilter}
            onChange={(e) => setVerdictFilter(e.target.value as VerdictFilter)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
            aria-label="Violation type filter"
          >
            {VERDICT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error banner for dashboard */}
      {errorDash && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorDash}
          <button
            onClick={() => void fetchDashboard()}
            className="ml-3 font-medium underline hover:text-red-900"
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Overtime Violations (MTD)"
          value={dashboard?.violations_30d ?? 0}
          color="text-red-600"
          trend={`${period}-day window`}
          loading={loadingDash}
        />
        <StatCard
          label="Leave Compliance Rate"
          value={dashboard ? `${complianceRate}%` : "-"}
          color={complianceRate >= 90 ? "text-green-600" : "text-yellow-600"}
          trend="Target: 100%"
          loading={loadingDash}
        />
        <StatCard
          label="Upcoming Reviews"
          value={dashboard?.rules_pending_review ?? 0}
          trend="Pending review"
          loading={loadingDash}
        />
        <StatCard
          label="Active HR Rules"
          value={dashboard?.total_rules ?? 0}
          trend={`${dashboard?.rules_pending_review ?? 0} pending review`}
          loading={loadingDash}
        />
      </div>

      {/* Attendance compliance bar + Overtime trend sparkline */}
      {loadingDash ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SectionSkeleton rows={2} />
          <SectionSkeleton rows={3} />
        </div>
      ) : dashboard ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Attendance compliance rate */}
          <div className="rounded-xl border bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900">Attendance Compliance Rate</h2>
            <p className="mt-1 text-sm text-gray-500">
              Percentage of attendance records passing all HR rules
            </p>
            <div className="mt-4">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-gray-700">Compliance</span>
                <span className="font-semibold text-gray-900">{complianceRate}%</span>
              </div>
              <div className="h-4 overflow-hidden rounded-full bg-gray-100">
                <div
                  className={`h-full rounded-full transition-all ${
                    complianceRate >= 90
                      ? "bg-green-500"
                      : complianceRate >= 70
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${complianceRate}%` }}
                />
              </div>
              <div className="mt-2 flex justify-between text-xs text-gray-400">
                <span>0%</span>
                <span>Target: 100%</span>
              </div>
            </div>
          </div>

          {/* Overtime trend sparkline */}
          <div className="rounded-xl border bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900">Overtime Violation Trend</h2>
            <p className="mt-1 text-sm text-gray-500">Daily violations over the selected period</p>
            <div className="mt-4 flex items-end gap-0.5" style={{ height: "80px" }}>
              {(dashboard.violation_trend ?? []).map((day) => {
                const heightPct = trendMax > 0 ? (day.count / trendMax) * 100 : 0;
                return (
                  <div
                    key={day.date}
                    className="group relative flex-1"
                    style={{ height: "100%" }}
                  >
                    <div
                      className="absolute bottom-0 w-full rounded-t bg-indigo-400 transition-colors group-hover:bg-indigo-600"
                      style={{ height: `${Math.max(heightPct, 2)}%` }}
                    />
                    {/* Tooltip on hover */}
                    <div className="pointer-events-none absolute -top-8 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-xs text-white group-hover:block">
                      {day.date}: {day.count}
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="mt-1 flex justify-between text-xs text-gray-400">
              <span>{dashboard.violation_trend?.[0]?.date ?? ""}</span>
              <span>{dashboard.violation_trend?.[(dashboard.violation_trend?.length ?? 1) - 1]?.date ?? ""}</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* Verdict distribution + Violations by department */}
      {loadingDash ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <SectionSkeleton rows={3} />
          <SectionSkeleton rows={4} />
        </div>
      ) : dashboard ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Verdict distribution - stacked horizontal bar */}
          <div className="rounded-xl border bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900">Verdict Distribution</h2>
            <p className="mt-1 text-sm text-gray-500">
              Breakdown of evaluation outcomes ({dashboard.evaluations_30d ?? 0} total)
            </p>
            {verdictDistTotal > 0 ? (
              <>
                <div className="mt-4 flex h-6 overflow-hidden rounded-full">
                  {Object.entries(dashboard.verdict_distribution ?? {}).map(([verdict, count]) => {
                    const pct = (count / verdictDistTotal) * 100;
                    const colorMap: Record<string, string> = {
                      allow: "bg-green-400",
                      deny: "bg-red-400",
                      needs_confirmation: "bg-yellow-400",
                    };
                    const bg = colorMap[verdict] ?? "bg-gray-300";
                    return (
                      <div
                        key={verdict}
                        className={`${bg} transition-all`}
                        style={{ width: `${pct}%` }}
                        title={`${verdict}: ${count} (${Math.round(pct)}%)`}
                      />
                    );
                  })}
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs">
                  {Object.entries(dashboard.verdict_distribution ?? {}).map(([verdict, count]) => (
                    <div key={verdict} className="flex items-center gap-1.5">
                      <VerdictBadge verdict={verdict} />
                      <span className="text-gray-500">
                        {count} ({verdictDistTotal > 0 ? Math.round((count / verdictDistTotal) * 100) : 0}%)
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="mt-4 text-sm text-gray-400">No evaluations in this period.</p>
            )}
          </div>

          {/* Violations by department / rule */}
          <div className="rounded-xl border bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900">Top Violated Rules</h2>
            <p className="mt-1 text-sm text-gray-500">Most frequently violated HR rules</p>
            <div className="mt-4 space-y-3">
              {(dashboard.top_violated_rules ?? []).length > 0 ? (
                (dashboard.top_violated_rules ?? []).map((rule) => {
                  const pct = (rule.violation_count / topViolatedMax) * 100;
                  return (
                    <div key={rule.rule_id}>
                      <div className="mb-1 flex items-center justify-between text-sm">
                        <span className="max-w-[70%] truncate text-gray-700" title={rule.statement}>
                          {rule.statement}
                        </span>
                        <span className="shrink-0 text-gray-500">
                          {rule.violation_count} violation{rule.violation_count !== 1 ? "s" : ""}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div
                          className="h-full rounded-full bg-indigo-500 transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-sm text-gray-400">No violations recorded.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}

      {/* Recent violations table */}
      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Violations</h2>
          <span className="text-xs text-gray-400">{evalTotal} total</span>
        </div>

        {/* Error banner for evaluations */}
        {errorEvals && (
          <div className="border-b border-red-200 bg-red-50 px-5 py-3 text-sm text-red-700">
            {errorEvals}
            <button
              onClick={() => void fetchEvaluations()}
              className="ml-3 font-medium underline hover:text-red-900"
            >
              Retry
            </button>
          </div>
        )}

        {loadingEvals ? (
          <div className="animate-pulse p-5 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-4 w-full rounded bg-gray-100" />
            ))}
          </div>
        ) : evaluations.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-gray-400">
            No evaluations found for the selected filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-5 py-3 w-8" />
                  <th className="px-5 py-3">ID</th>
                  <th className="px-5 py-3">Rule</th>
                  <th className="px-5 py-3">Verdict</th>
                  <th className="px-5 py-3">Confidence</th>
                  <th className="px-5 py-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {evaluations.map((ev) => {
                  const isExpanded = expandedRow === ev.id;
                  return (
                    <Fragment key={ev.id}>
                      <tr
                        className="cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => setExpandedRow(isExpanded ? null : ev.id)}
                      >
                        <td className="px-5 py-3 text-gray-400">
                          <span
                            className={`inline-block transition-transform ${isExpanded ? "rotate-90" : ""}`}
                          >
                            &#9654;
                          </span>
                        </td>
                        <td className="px-5 py-3 font-mono text-xs text-gray-600">
                          {ev.id.slice(0, 8)}
                        </td>
                        <td className="max-w-xs truncate px-5 py-3 text-gray-700" title={ev.rule_statement}>
                          {ev.rule_statement}
                        </td>
                        <td className="px-5 py-3">
                          <VerdictBadge verdict={ev.verdict} />
                        </td>
                        <td className="px-5 py-3">
                          <ConfidenceBar value={ev.confidence} />
                        </td>
                        <td className="px-5 py-3 whitespace-nowrap text-gray-500">
                          {new Date(ev.created_at).toLocaleDateString("ja-JP")}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="bg-indigo-50/40">
                          <td colSpan={6} className="px-8 py-4">
                            <div className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Rule</p>
                                <p className="mt-0.5 text-gray-800">{ev.rule_statement}</p>
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Subject Type</p>
                                <p className="mt-0.5 text-gray-800">{ev.subject_type}</p>
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Issue</p>
                                <p className="mt-0.5 text-gray-800">
                                  {ev.issue_description || "No description"}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Fix Suggestion</p>
                                <p className="mt-0.5 text-gray-800">
                                  {ev.fix_suggestion || "No suggestion available"}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Confidence</p>
                                <p className="mt-0.5 text-gray-800">{Math.round(ev.confidence * 100)}%</p>
                              </div>
                              <div>
                                <p className="text-xs font-medium uppercase text-gray-500">Rule ID</p>
                                <p className="mt-0.5 font-mono text-xs text-gray-600">{ev.rule_id}</p>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {evalTotal > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t px-5 py-3">
            <p className="text-xs text-gray-500">
              Page {evalPage} of {totalPages} ({evalTotal} results)
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setEvalPage((p) => Math.max(1, p - 1))}
                disabled={evalPage <= 1}
                className="rounded-lg border px-3 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setEvalPage((p) => Math.min(totalPages, p + 1))}
                disabled={evalPage >= totalPages}
                className="rounded-lg border px-3 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link
          href="/hr/attendance"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">Check Employee</p>
          <p className="mt-1 text-xs text-gray-500">
            Evaluate an employee event against HR rules
          </p>
        </Link>
        <Link
          href="/hr/policies"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">Review Policy</p>
          <p className="mt-1 text-xs text-gray-500">Browse and update HR policy rules</p>
        </Link>
        <Link
          href="/hr/hris"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-indigo-300 hover:bg-indigo-50"
        >
          <p className="text-sm font-medium text-gray-900">HRIS Sync Status</p>
          <p className="mt-1 text-xs text-gray-500">Check HRIS sync status</p>
        </Link>
      </div>
    </div>
  );
}
