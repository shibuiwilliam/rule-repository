"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getDepartmentDashboard,
  getDepartmentEvaluations,
  getDepartmentRules,
} from "@/lib/api";
import type {
  DepartmentDashboard,
  DepartmentEvaluation,
  Rule,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEPARTMENT = "legal";

const CONTRACT_TYPES = [
  { value: "", label: "All Types" },
  { value: "contract_clause", label: "Contract Clause" },
  { value: "document_draft", label: "Document Draft" },
  { value: "email", label: "Email" },
  { value: "minutes", label: "Minutes" },
  { value: "proposal", label: "Proposal" },
];

const RISK_LEVELS = [
  { value: "", label: "All Severities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const VERDICT_OPTIONS = [
  { value: "", label: "All Verdicts" },
  { value: "allow", label: "Allow" },
  { value: "deny", label: "Deny" },
  { value: "needs_confirmation", label: "Needs Confirmation" },
];

const VERDICT_BADGE: Record<string, string> = {
  allow: "bg-green-100 text-green-700",
  deny: "bg-red-100 text-red-700",
  needs_confirmation: "bg-yellow-100 text-yellow-700",
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  critical: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-red-600 bg-red-50",
  high: "border-l-red-500 bg-red-50",
  medium: "border-l-yellow-500 bg-yellow-50",
  low: "border-l-blue-400 bg-blue-50",
};

const IMPACT_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

const PAGE_SIZE = 10;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function formatShortDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function inferPriority(evaluation: DepartmentEvaluation): "high" | "medium" | "low" {
  if (evaluation.verdict === "deny" && evaluation.confidence > 0.8) return "high";
  if (evaluation.verdict === "deny") return "medium";
  if (evaluation.verdict === "needs_confirmation") return "medium";
  return "low";
}

function inferSeverityFromRule(rule: Rule): "critical" | "high" | "medium" | "low" {
  const s = rule.severity.toLowerCase();
  if (s === "critical" || s === "high" || s === "medium" || s === "low") {
    return s as "critical" | "high" | "medium" | "low";
  }
  return "medium";
}

function computeSeverityBreakdown(rules: Rule[]): { high: number; medium: number; low: number } {
  let high = 0;
  let medium = 0;
  let low = 0;
  for (const r of rules) {
    const sev = inferSeverityFromRule(r);
    if (sev === "critical" || sev === "high") high++;
    else if (sev === "medium") medium++;
    else low++;
  }
  return { high, medium, low };
}

// ---------------------------------------------------------------------------
// Skeleton components
// ---------------------------------------------------------------------------

function KpiSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border bg-white p-5">
      <div className="h-4 w-24 rounded bg-gray-200" />
      <div className="mt-3 h-8 w-16 rounded bg-gray-200" />
      <div className="mt-2 h-3 w-32 rounded bg-gray-100" />
    </div>
  );
}

function TableSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-3 p-5">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          <div className="h-4 w-16 rounded bg-gray-200" />
          <div className="h-4 flex-1 rounded bg-gray-200" />
          <div className="h-4 w-20 rounded bg-gray-200" />
          <div className="h-4 w-16 rounded bg-gray-100" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function LegalDashboardPage() {
  // Data state
  const [dashboard, setDashboard] = useState<DepartmentDashboard | null>(null);
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [evalTotal, setEvalTotal] = useState(0);
  const [rules, setRules] = useState<Rule[]>([]);

  // Loading / error
  const [dashLoading, setDashLoading] = useState(true);
  const [evalLoading, setEvalLoading] = useState(true);
  const [rulesLoading, setRulesLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [contractType, setContractType] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("");

  // Pagination
  const [evalPage, setEvalPage] = useState(1);

  // Expandable rows
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  // -----------------------------------------------------------------------
  // Data loaders
  // -----------------------------------------------------------------------

  const loadDashboard = useCallback(async () => {
    setDashLoading(true);
    try {
      const data = await getDepartmentDashboard(DEPARTMENT);
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setDashLoading(false);
    }
  }, []);

  const loadEvaluations = useCallback(async () => {
    setEvalLoading(true);
    try {
      const v = verdictFilter || undefined;
      const data = await getDepartmentEvaluations(DEPARTMENT, v, evalPage, PAGE_SIZE);
      setEvaluations(data.items);
      setEvalTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluations");
    } finally {
      setEvalLoading(false);
    }
  }, [verdictFilter, evalPage]);

  const loadRules = useCallback(async () => {
    setRulesLoading(true);
    try {
      const data = await getDepartmentRules(DEPARTMENT, 1, 100);
      setRules(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rules");
    } finally {
      setRulesLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    void loadRules();
  }, [loadDashboard, loadRules]);

  useEffect(() => {
    void loadEvaluations();
  }, [loadEvaluations]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setEvalPage(1);
  }, [verdictFilter]);

  // -----------------------------------------------------------------------
  // Derived data
  // -----------------------------------------------------------------------

  const severityBreakdown = computeSeverityBreakdown(rules);
  const severityTotal = severityBreakdown.high + severityBreakdown.medium + severityBreakdown.low;

  const filteredEvaluations = evaluations.filter((ev) => {
    if (contractType && ev.subject_type !== contractType) return false;
    if (riskLevel) {
      const p = inferPriority(ev);
      const mapped = riskLevel === "critical" ? "high" : riskLevel;
      if (p !== mapped) return false;
    }
    return true;
  });

  const denyEvaluations = (dashboard?.recent_evaluations ?? []).filter(
    (ev) => ev.verdict === "deny"
  );

  const regulatoryImpactEvals = (dashboard?.recent_evaluations ?? []).slice(0, 4);

  const totalEvalPages = Math.max(1, Math.ceil(evalTotal / PAGE_SIZE));

  // -----------------------------------------------------------------------
  // Verdict distribution bar data
  // -----------------------------------------------------------------------

  const verdictDist = dashboard?.verdict_distribution ?? {};
  const verdictTotal = Object.values(verdictDist).reduce((a, b) => a + b, 0);

  // Top violated rules bar data
  const topViolated = dashboard?.top_violated_rules ?? [];
  const maxViolationCount = topViolated.length > 0
    ? Math.max(...topViolated.map((r) => r.violation_count))
    : 1;

  // -----------------------------------------------------------------------
  // Violation trend sparkline (30 days)
  // -----------------------------------------------------------------------

  const trendData = dashboard?.violation_trend ?? [];
  const trendMax = trendData.length > 0
    ? Math.max(...trendData.map((t) => t.count), 1)
    : 1;

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Legal Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Contract pipeline, regulatory changes, and clause compliance
        </p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 font-medium underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {dashLoading ? (
          <>
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
            <KpiSkeleton />
          </>
        ) : (
          <>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm font-medium text-gray-500">Pending Reviews</p>
              <p className="mt-1 text-3xl font-bold text-yellow-600">
                {dashboard?.rules_pending_review ?? 0}
              </p>
              <p className="mt-1 text-xs text-gray-400">Rules awaiting approval</p>
            </div>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm font-medium text-gray-500">Clause Deviations</p>
              <p className="mt-1 text-3xl font-bold text-red-600">
                {dashboard?.violations_30d ?? 0}
              </p>
              <p className="mt-1 text-xs text-gray-400">Last 30 days</p>
            </div>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm font-medium text-gray-500">Regulatory Updates</p>
              <p className="mt-1 text-3xl font-bold text-blue-600">
                {denyEvaluations.length}
              </p>
              <p className="mt-1 text-xs text-gray-400">Flagged for review</p>
            </div>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm font-medium text-gray-500">Active Legal Rules</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">
                {dashboard?.total_rules ?? 0}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                {dashboard?.rules_pending_review ?? 0} under review
              </p>
            </div>
          </>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={contractType}
          onChange={(e) => setContractType(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 focus:border-slate-400 focus:outline-none"
        >
          {CONTRACT_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>
              {ct.label}
            </option>
          ))}
        </select>
        <select
          value={riskLevel}
          onChange={(e) => setRiskLevel(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 focus:border-slate-400 focus:outline-none"
        >
          {RISK_LEVELS.map((rl) => (
            <option key={rl.value} value={rl.value}>
              {rl.label}
            </option>
          ))}
        </select>
        <select
          value={verdictFilter}
          onChange={(e) => setVerdictFilter(e.target.value)}
          className="rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 focus:border-slate-400 focus:outline-none"
        >
          {VERDICT_OPTIONS.map((vo) => (
            <option key={vo.value} value={vo.value}>
              {vo.label}
            </option>
          ))}
        </select>
        {(contractType || riskLevel || verdictFilter) && (
          <button
            onClick={() => {
              setContractType("");
              setRiskLevel("");
              setVerdictFilter("");
            }}
            className="text-sm text-gray-500 underline hover:text-gray-700"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Contract Review Queue */}
      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            Contract Review Queue
          </h2>
          <span className="text-xs text-gray-400">
            {filteredEvaluations.length} of {evalTotal} evaluations
          </span>
        </div>
        {evalLoading ? (
          <TableSkeleton rows={5} />
        ) : filteredEvaluations.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-gray-400">
            No evaluations match the current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  <th className="px-5 py-3">ID</th>
                  <th className="px-5 py-3">Subject</th>
                  <th className="px-5 py-3">Rule</th>
                  <th className="px-5 py-3">Verdict</th>
                  <th className="px-5 py-3">Confidence</th>
                  <th className="px-5 py-3">Priority</th>
                  <th className="px-5 py-3">Date</th>
                  <th className="px-5 py-3 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredEvaluations.map((ev) => {
                  const priority = inferPriority(ev);
                  const isExpanded = expandedRow === ev.id;
                  return (
                    <tr key={ev.id} className="group">
                      <td className="px-5 py-3">
                        <button
                          onClick={() => setExpandedRow(isExpanded ? null : ev.id)}
                          className="font-mono text-xs text-blue-600 hover:underline"
                        >
                          {ev.id.slice(0, 8)}
                        </button>
                      </td>
                      <td className="px-5 py-3 text-gray-600">{ev.subject_type}</td>
                      <td className="max-w-[200px] truncate px-5 py-3 text-gray-900" title={ev.rule_statement}>
                        {ev.rule_statement}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${VERDICT_BADGE[ev.verdict] ?? "bg-gray-100 text-gray-600"}`}
                        >
                          {ev.verdict}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500">
                        {(ev.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${PRIORITY_BADGE[priority]}`}
                        >
                          {priority}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500">
                        {formatShortDate(ev.created_at)}
                      </td>
                      <td className="px-5 py-3">
                        <button
                          onClick={() => setExpandedRow(isExpanded ? null : ev.id)}
                          className="text-gray-400 hover:text-gray-600"
                          aria-label={isExpanded ? "Collapse row" : "Expand row"}
                        >
                          <svg
                            className={`h-4 w-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      </td>
                      {/* Expanded detail row */}
                      {isExpanded && (
                        <td colSpan={8} className="border-t bg-gray-50 px-5 py-4">
                          <div className="space-y-3">
                            <div>
                              <p className="text-xs font-semibold uppercase text-gray-500">
                                Issue Description
                              </p>
                              <p className="mt-1 text-sm text-gray-800">
                                {ev.issue_description || "No description available."}
                              </p>
                            </div>
                            {ev.fix_suggestion && (
                              <div>
                                <p className="text-xs font-semibold uppercase text-gray-500">
                                  Redline Preview
                                </p>
                                <div className="mt-1 rounded border bg-white p-3 text-sm">
                                  <span className="line-through text-red-600">
                                    {ev.issue_description
                                      ? ev.issue_description.slice(0, 60) + "..."
                                      : "Original text"}
                                  </span>
                                  <span className="ml-2 bg-green-100 text-green-800">
                                    {ev.fix_suggestion}
                                  </span>
                                </div>
                              </div>
                            )}
                            <div className="flex gap-4 text-xs text-gray-500">
                              <span>Rule ID: {ev.rule_id}</span>
                              <span>Confidence: {(ev.confidence * 100).toFixed(1)}%</span>
                              <span>Created: {formatDate(ev.created_at)}</span>
                            </div>
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalEvalPages > 1 && (
          <div className="flex items-center justify-between border-t px-5 py-3">
            <p className="text-xs text-gray-500">
              Page {evalPage} of {totalEvalPages}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setEvalPage((p) => Math.max(1, p - 1))}
                disabled={evalPage <= 1}
                className="rounded border px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => setEvalPage((p) => Math.min(totalEvalPages, p + 1))}
                disabled={evalPage >= totalEvalPages}
                className="rounded border px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Middle row: Risk Distribution + Compliance Rate + Violation Trend */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Risk Distribution */}
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Risk Distribution
          </h2>
          <p className="mt-1 text-xs text-gray-400">
            Severity breakdown across {rules.length} rules
          </p>
          {rulesLoading ? (
            <div className="mt-4 animate-pulse">
              <div className="h-6 rounded bg-gray-200" />
            </div>
          ) : severityTotal === 0 ? (
            <p className="mt-4 text-sm text-gray-400">No rules loaded.</p>
          ) : (
            <div className="mt-4 space-y-3">
              <div className="flex h-6 overflow-hidden rounded-full">
                {severityBreakdown.high > 0 && (
                  <div
                    className="bg-red-500"
                    style={{ width: `${(severityBreakdown.high / severityTotal) * 100}%` }}
                    title={`High/Critical: ${severityBreakdown.high}`}
                  />
                )}
                {severityBreakdown.medium > 0 && (
                  <div
                    className="bg-yellow-400"
                    style={{ width: `${(severityBreakdown.medium / severityTotal) * 100}%` }}
                    title={`Medium: ${severityBreakdown.medium}`}
                  />
                )}
                {severityBreakdown.low > 0 && (
                  <div
                    className="bg-gray-300"
                    style={{ width: `${(severityBreakdown.low / severityTotal) * 100}%` }}
                    title={`Low: ${severityBreakdown.low}`}
                  />
                )}
              </div>
              <div className="flex justify-between text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
                  High: {severityBreakdown.high}
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-yellow-400" />
                  Medium: {severityBreakdown.medium}
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-300" />
                  Low: {severityBreakdown.low}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Clause Compliance Rate */}
        <div className="flex flex-col items-center justify-center rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Clause Compliance
          </h2>
          {dashLoading ? (
            <div className="mt-4 h-16 w-24 animate-pulse rounded bg-gray-200" />
          ) : (
            <>
              <p className="mt-3 text-5xl font-bold text-gray-900">
                {((dashboard?.compliance_rate ?? 0) * 100).toFixed(1)}%
              </p>
              <p className="mt-2 text-xs text-gray-400">30-day compliance rate</p>
              <div className="mt-3 h-2 w-full max-w-[180px] overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full rounded-full bg-green-500"
                  style={{ width: `${(dashboard?.compliance_rate ?? 0) * 100}%` }}
                />
              </div>
            </>
          )}
        </div>

        {/* Violation Trend Sparkline */}
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Violation Trend
          </h2>
          <p className="mt-1 text-xs text-gray-400">Last 30 days</p>
          {dashLoading ? (
            <div className="mt-4 flex h-16 animate-pulse items-end gap-0.5">
              {Array.from({ length: 15 }).map((_, i) => (
                <div
                  key={i}
                  className="flex-1 rounded-t bg-gray-200"
                  style={{ height: `${20 + Math.random() * 60}%` }}
                />
              ))}
            </div>
          ) : trendData.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">No trend data available.</p>
          ) : (
            <div className="mt-4">
              <div className="flex h-16 items-end gap-px">
                {trendData.map((point, i) => (
                  <div
                    key={i}
                    className="group relative flex-1 rounded-t bg-red-400 transition-colors hover:bg-red-500"
                    style={{
                      height: `${Math.max(4, (point.count / trendMax) * 100)}%`,
                    }}
                    title={`${formatShortDate(point.date)}: ${point.count} violations`}
                  >
                    <div className="pointer-events-none absolute -top-8 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-1.5 py-0.5 text-[10px] text-white group-hover:block">
                      {point.count}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-gray-400">
                {trendData.length > 0 && (
                  <>
                    <span>{formatShortDate(trendData[0].date)}</span>
                    <span>{formatShortDate(trendData[trendData.length - 1].date)}</span>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Verdict Distribution + Top Violated Rules */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Verdict Distribution */}
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Verdict Distribution
          </h2>
          <p className="mt-1 text-xs text-gray-400">
            {verdictTotal} evaluations in the last 30 days
          </p>
          {dashLoading ? (
            <div className="mt-4 animate-pulse">
              <div className="h-8 rounded bg-gray-200" />
            </div>
          ) : verdictTotal === 0 ? (
            <p className="mt-4 text-sm text-gray-400">No evaluations yet.</p>
          ) : (
            <div className="mt-4 space-y-3">
              <div className="flex h-8 overflow-hidden rounded-lg">
                {(["allow", "deny", "needs_confirmation"] as const).map((v) => {
                  const count = verdictDist[v] ?? 0;
                  if (count === 0) return null;
                  const pct = (count / verdictTotal) * 100;
                  const colors: Record<string, string> = {
                    allow: "bg-green-500",
                    deny: "bg-red-500",
                    needs_confirmation: "bg-yellow-400",
                  };
                  return (
                    <div
                      key={v}
                      className={`flex items-center justify-center text-[10px] font-medium text-white ${colors[v]}`}
                      style={{ width: `${pct}%` }}
                      title={`${v}: ${count} (${pct.toFixed(1)}%)`}
                    >
                      {pct > 10 ? `${pct.toFixed(0)}%` : ""}
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
                  Allow: {verdictDist["allow"] ?? 0}
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" />
                  Deny: {verdictDist["deny"] ?? 0}
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full bg-yellow-400" />
                  Needs Confirmation: {verdictDist["needs_confirmation"] ?? 0}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Top Violated Rules */}
        <div className="rounded-xl border bg-white p-5">
          <h2 className="text-base font-semibold text-gray-900">
            Top Violated Rules
          </h2>
          <p className="mt-1 text-xs text-gray-400">Most frequent violations</p>
          {dashLoading ? (
            <div className="mt-4 animate-pulse space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-6 rounded bg-gray-200" />
              ))}
            </div>
          ) : topViolated.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">No violations recorded.</p>
          ) : (
            <div className="mt-4 space-y-3">
              {topViolated.map((rule) => (
                <div key={rule.rule_id}>
                  <div className="flex items-center justify-between text-xs">
                    <span
                      className="max-w-[260px] truncate text-gray-700"
                      title={rule.statement}
                    >
                      {rule.statement}
                    </span>
                    <span className="ml-2 font-medium text-gray-900">
                      {rule.violation_count}
                    </span>
                  </div>
                  <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-red-400"
                      style={{
                        width: `${(rule.violation_count / maxViolationCount) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Regulatory Change Impact Panel */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            Regulatory Change Impact
          </h2>
        </div>
        {dashLoading ? (
          <TableSkeleton rows={3} />
        ) : regulatoryImpactEvals.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-gray-400">
            No recent regulatory impact data.
          </div>
        ) : (
          <div className="divide-y">
            {regulatoryImpactEvals.map((ev) => {
              const impact =
                ev.verdict === "deny"
                  ? "high"
                  : ev.verdict === "needs_confirmation"
                    ? "medium"
                    : "low";
              return (
                <div key={ev.id} className="flex items-start gap-4 px-5 py-4">
                  <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-medium text-gray-600">
                    {formatShortDate(ev.created_at).split(" ")[0]}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900">
                      {ev.summary}
                    </p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      Type: {ev.subject_type} | Rules checked: {ev.rule_count} |{" "}
                      {formatDate(ev.created_at)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${IMPACT_BADGE[impact]}`}
                    >
                      {impact} impact
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${VERDICT_BADGE[ev.verdict] ?? "bg-gray-100 text-gray-600"}`}
                    >
                      {ev.verdict}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Clause Deviation Alerts */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">
          Clause Deviation Alerts
        </h2>
        <p className="mt-1 text-xs text-gray-400">
          Recent DENY evaluations requiring attention
        </p>
        {evalLoading ? (
          <div className="mt-4 animate-pulse space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-16 rounded bg-gray-200" />
            ))}
          </div>
        ) : denyEvaluations.length === 0 ? (
          <p className="mt-4 text-sm text-gray-400">No clause deviations detected.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {denyEvaluations.slice(0, 5).map((ev) => {
              const severity =
                ev.rule_count > 3
                  ? "high"
                  : ev.rule_count > 1
                    ? "medium"
                    : "low";
              return (
                <div
                  key={ev.id}
                  className={`rounded-lg border-l-4 p-3 ${SEVERITY_BORDER[severity] ?? SEVERITY_BORDER["medium"]}`}
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-900">
                      {ev.summary}
                    </p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_BADGE[severity]}`}
                    >
                      {severity}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-600">
                    {ev.subject_type} | {ev.rule_count} rules flagged
                  </p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {formatDate(ev.created_at)}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Action Links */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link
          href="/legal/contracts"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
        >
          <p className="text-sm font-medium text-gray-900">Upload Contract</p>
          <p className="mt-1 text-xs text-gray-500">
            Submit a contract for automated clause analysis
          </p>
        </Link>
        <Link
          href="/legal/clauses"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
        >
          <p className="text-sm font-medium text-gray-900">Search Clauses</p>
          <p className="mt-1 text-xs text-gray-500">
            Browse the standard clause library
          </p>
        </Link>
        <Link
          href="/legal/regulatory"
          className="rounded-xl border bg-white p-4 transition-colors hover:border-slate-300 hover:bg-slate-50"
        >
          <p className="text-sm font-medium text-gray-900">View Regulatory Feed</p>
          <p className="mt-1 text-xs text-gray-500">
            Track upcoming regulatory changes and impacts
          </p>
        </Link>
      </div>
    </div>
  );
}
