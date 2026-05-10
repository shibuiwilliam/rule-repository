"use client";

import { useCallback, useEffect, useState } from "react";

import { getDepartmentRules, type Rule } from "@/lib/api";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ControlsPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDepartmentRules("finance", 1, 100);
      setRules(data.items);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const filtered = rules.filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      r.statement.toLowerCase().includes(q) ||
      r.tags.some((t) => t.toLowerCase().includes(q)) ||
      r.scope.some((s) => s.toLowerCase().includes(q))
    );
  });

  const byStatus = {
    effective: filtered.filter((r) => r.status === "EFFECTIVE" || r.status === "APPROVED").length,
    draft: filtered.filter((r) => r.status === "DRAFT").length,
    review: filtered.filter((r) => r.status === "REVIEW").length,
  };

  const bySeverity = {
    critical: filtered.filter((r) => r.severity === "CRITICAL").length,
    high: filtered.filter((r) => r.severity === "HIGH").length,
    medium: filtered.filter((r) => r.severity === "MEDIUM").length,
    low: filtered.filter((r) => r.severity === "LOW").length,
  };

  const statusBadge: Record<string, string> = {
    EFFECTIVE: "bg-green-100 text-green-800",
    APPROVED: "bg-green-100 text-green-800",
    DRAFT: "bg-gray-100 text-gray-700",
    REVIEW: "bg-yellow-100 text-yellow-700",
    RETIRED: "bg-red-100 text-red-700",
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Financial Controls</h1>
        <p className="mt-1 text-sm text-gray-500">
          Active financial rules, effectiveness scores, and threshold configurations
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Total Controls</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-blue-600">{filtered.length}</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Effective</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-green-600">{byStatus.effective}</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Pending Review</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-yellow-600">
              {byStatus.draft + byStatus.review}
            </p>
          )}
        </div>
      </div>

      {/* Severity distribution */}
      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Severity Distribution</h2>
        <div className="mt-4 space-y-3">
          {(
            [
              { label: "Critical", count: bySeverity.critical, color: "bg-red-500" },
              { label: "High", count: bySeverity.high, color: "bg-orange-500" },
              { label: "Medium", count: bySeverity.medium, color: "bg-yellow-500" },
              { label: "Low", count: bySeverity.low, color: "bg-gray-400" },
            ] as const
          ).map((s) => {
            const maxCount = Math.max(bySeverity.critical, bySeverity.high, bySeverity.medium, bySeverity.low, 1);
            return (
              <div key={s.label}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-gray-700">{s.label}</span>
                  <span className="text-gray-500">{s.count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                  <div
                    className={`h-full rounded-full ${s.color}`}
                    style={{ width: `${(s.count / maxCount) * 100}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rules table */}
      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">All Financial Rules</h2>
          <input
            type="text"
            placeholder="Search rules..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-md border px-3 py-1.5 text-sm text-gray-700 placeholder:text-gray-400"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
                <th className="px-5 py-3">Rule</th>
                <th className="px-5 py-3">Modality</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.length === 0 && !loading ? (
                <tr>
                  <td colSpan={4} className="px-5 py-8 text-center text-sm text-gray-400">
                    No rules found.
                  </td>
                </tr>
              ) : (
                filtered.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">{r.statement}</p>
                      {r.rationale && (
                        <p className="mt-0.5 text-xs text-gray-400">{r.rationale}</p>
                      )}
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          r.modality === "MUST" || r.modality === "MUST_NOT"
                            ? "bg-red-100 text-red-700"
                            : r.modality === "SHOULD"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-green-100 text-green-700"
                        }`}
                      >
                        {r.modality}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          r.severity === "CRITICAL"
                            ? "bg-red-600 text-white"
                            : r.severity === "HIGH"
                              ? "bg-orange-500 text-white"
                              : r.severity === "MEDIUM"
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {r.severity}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          statusBadge[r.status] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
