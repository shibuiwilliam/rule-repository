"use client";

import { useCallback, useEffect, useState } from "react";

import { getDepartmentEvaluations, getDepartmentRules, type DepartmentEvaluation, type Rule } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type CategoryFilter = "all" | "travel" | "entertainment" | "supplies" | "it" | "development";
type StatusFilter = "all" | "ALLOW" | "DENY" | "NEEDS_CONFIRMATION";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ExpensePolicyPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [evalTotal, setEvalTotal] = useState(0);
  const [evalPage, setEvalPage] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const vf = statusFilter === "all" ? undefined : statusFilter;
      const [rulesData, evalsData] = await Promise.all([
        getDepartmentRules("finance", 1, 100),
        getDepartmentEvaluations("finance", vf, evalPage),
      ]);
      setRules(rulesData.items);
      setEvaluations(evalsData.items);
      setEvalTotal(evalsData.total);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [statusFilter, evalPage]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const expenseRules = rules.filter((r) =>
    r.scope.some((s) => s.includes("expense") || s.includes("finance")),
  );

  const filteredEvals = evaluations.filter((e) => {
    if (categoryFilter !== "all") {
      const subj = JSON.stringify(e.details).toLowerCase();
      if (!subj.includes(categoryFilter)) return false;
    }
    return true;
  });

  const totalViolations = evaluations.filter((e) => e.verdict === "DENY").length;
  const categories = [...new Set(expenseRules.flatMap((r) => r.tags))];
  const evalTotalPages = Math.ceil(evalTotal / 20);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Expense Policies</h1>
        <p className="mt-1 text-sm text-gray-500">
          Spending limits, approval requirements, and violation tracking by category
        </p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Expense Rules", value: expenseRules.length, color: "text-blue-600" },
          { label: "Total Rules", value: rules.length, color: "text-green-600" },
          { label: "Recent Violations", value: totalViolations, color: "text-red-600" },
          { label: "Categories", value: categories.length || "-", color: "text-purple-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            {loading ? (
              <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
            ) : (
              <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
            )}
          </div>
        ))}
      </div>

      {/* Active expense rules */}
      <div className="rounded-xl border bg-white">
        <div className="border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Active Expense Rules</h2>
        </div>
        <div className="divide-y">
          {expenseRules.length === 0 && !loading ? (
            <p className="px-5 py-8 text-center text-sm text-gray-400">No expense rules found.</p>
          ) : (
            expenseRules.slice(0, 10).map((r) => (
              <div key={r.id} className="flex items-center justify-between px-5 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-gray-800">{r.statement}</p>
                  {r.rationale && (
                    <p className="mt-0.5 truncate text-xs text-gray-400">{r.rationale}</p>
                  )}
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
                      r.severity === "CRITICAL" || r.severity === "HIGH"
                        ? "bg-orange-100 text-orange-700"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {r.severity}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Recent expense evaluations */}
      <div className="rounded-xl border bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Recent Expense Evaluations</h2>
          <div className="flex gap-2">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as StatusFilter);
                setEvalPage(1);
              }}
              className="rounded-md border px-2 py-1 text-xs text-gray-700"
            >
              <option value="all">All verdicts</option>
              <option value="ALLOW">Allow</option>
              <option value="DENY">Deny</option>
              <option value="NEEDS_CONFIRMATION">Needs confirmation</option>
            </select>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as CategoryFilter)}
              className="rounded-md border px-2 py-1 text-xs text-gray-700"
            >
              <option value="all">All categories</option>
              <option value="travel">Travel</option>
              <option value="entertainment">Entertainment</option>
              <option value="supplies">Supplies</option>
              <option value="it">IT</option>
              <option value="development">Development</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Rule</th>
                <th className="px-5 py-3">Verdict</th>
                <th className="px-5 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredEvals.length === 0 && !loading ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-sm text-gray-400">
                    No evaluations found.
                  </td>
                </tr>
              ) : (
                filteredEvals.map((ev) => (
                  <>
                    <tr
                      key={ev.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => setExpandedId(expandedId === ev.id ? null : ev.id)}
                    >
                      <td className="px-5 py-3 font-mono text-xs text-gray-500">
                        {ev.id.slice(0, 8)}
                      </td>
                      <td className="max-w-xs truncate px-5 py-3 text-gray-700">
                        {ev.rule_statement}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            ev.verdict === "ALLOW"
                              ? "bg-green-100 text-green-700"
                              : ev.verdict === "DENY"
                                ? "bg-red-100 text-red-700"
                                : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {ev.verdict}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500">{ev.created_at?.slice(0, 10)}</td>
                    </tr>
                    {expandedId === ev.id && (
                      <tr key={`${ev.id}-detail`}>
                        <td colSpan={4} className="bg-gray-50 px-5 py-4">
                          <div className="space-y-2 text-sm">
                            {ev.issue_description && (
                              <p>
                                <span className="font-medium text-gray-700">Issue:</span>{" "}
                                {ev.issue_description}
                              </p>
                            )}
                            {ev.fix_suggestion && (
                              <p>
                                <span className="font-medium text-gray-700">Fix:</span>{" "}
                                {ev.fix_suggestion}
                              </p>
                            )}
                            <p className="text-xs text-gray-400">
                              Confidence: {(ev.confidence * 100).toFixed(0)}%
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
    </div>
  );
}
