"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getDepartmentDashboard,
  type DepartmentDashboard,
} from "@/lib/api";

export default function HrReportsPage() {
  const [dashboard, setDashboard] = useState<DepartmentDashboard | null>(null);
  const [period, setPeriod] = useState<"7" | "30" | "90">("30");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDepartmentDashboard("hr", Number(period));
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load report data");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const complianceRate = dashboard
    ? Math.round((dashboard.compliance_rate ?? 0) * 100)
    : 0;

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Compliance Reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            HR compliance metrics and trend analysis
          </p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(e.target.value as "7" | "30" | "90")}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-400">Loading report data...</div>
      ) : dashboard ? (
        <div className="space-y-6">
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm text-gray-500">Compliance Rate</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">{complianceRate}%</p>
            </div>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm text-gray-500">Total Evaluations</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">
                {dashboard.evaluations_30d ?? 0}
              </p>
            </div>
            <div className="rounded-xl border bg-white p-5">
              <p className="text-sm text-gray-500">Active Rules</p>
              <p className="mt-1 text-3xl font-bold text-gray-900">
                {dashboard.total_rules ?? 0}
              </p>
            </div>
          </div>

          {/* Verdict breakdown */}
          {dashboard.verdict_distribution && (
            <div className="rounded-xl border bg-white p-5">
              <h2 className="text-base font-semibold text-gray-900">Verdict Distribution</h2>
              <div className="mt-4 space-y-2">
                {Object.entries(dashboard.verdict_distribution).map(([verdict, count]) => (
                  <div key={verdict} className="flex items-center justify-between">
                    <span className="text-sm capitalize text-gray-700">{verdict.replace("_", " ")}</span>
                    <span className="text-sm font-medium text-gray-900">{count as number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top violated rules */}
          {(dashboard.top_violated_rules ?? []).length > 0 && (
            <div className="rounded-xl border bg-white p-5">
              <h2 className="text-base font-semibold text-gray-900">Top Violated Rules</h2>
              <div className="mt-4 space-y-3">
                {(dashboard.top_violated_rules ?? []).map((rule) => (
                  <div key={rule.rule_id} className="flex items-start justify-between gap-4">
                    <p className="text-sm text-gray-700">{rule.statement}</p>
                    <span className="shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      {rule.violation_count} violations
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="py-12 text-center text-gray-400">No report data available</div>
      )}
    </div>
  );
}
