"use client";

import { useEffect, useState } from "react";

interface DepartmentTrend {
  department: string;
  evaluation_count: number;
  deny_count: number;
  deny_rate: number;
}

interface PolicyMetric {
  policy_group: string;
  fire_count: number;
  deny_count: number;
}

interface AuditSummary {
  window_days: number;
  evaluation_count: number;
  denial_count: number;
  manual_override_count: number;
}

interface Dashboard {
  department_trends: DepartmentTrend[];
  policy_metrics: PolicyMetric[];
  audit_summary: AuditSummary | null;
}

export default function ComplianceCockpitPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [windowDays, setWindowDays] = useState(30);

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
        const resp = await fetch(
          `${apiBase}/api/v1/compliance/dashboard?window_days=${windowDays}`
        );
        if (resp.ok) {
          setDashboard(await resp.json());
        }
      } catch {
        // Silently handle fetch errors in dev
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [windowDays]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Compliance Cockpit</h1>
          <p className="text-sm text-gray-500">
            Organization-wide compliance posture and action queue
          </p>
        </div>
        <select
          value={windowDays}
          onChange={(e) => setWindowDays(Number(e.target.value))}
          className="rounded border px-3 py-1 text-sm"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : dashboard ? (
        <>
          {/* Audit Summary */}
          {dashboard.audit_summary && (
            <div className="grid grid-cols-3 gap-4">
              <StatCard
                label="Evaluations"
                value={dashboard.audit_summary.evaluation_count}
              />
              <StatCard
                label="Denials"
                value={dashboard.audit_summary.denial_count}
                accent="red"
              />
              <StatCard
                label="Manual Overrides"
                value={dashboard.audit_summary.manual_override_count}
                accent="yellow"
              />
            </div>
          )}

          {/* Department Trends */}
          <section>
            <h2 className="mb-3 text-lg font-semibold">Department Violation Trends</h2>
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-2">Department</th>
                    <th className="px-4 py-2">Evaluations</th>
                    <th className="px-4 py-2">Denials</th>
                    <th className="px-4 py-2">Deny Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.department_trends.map((t) => (
                    <tr key={t.department} className="border-t">
                      <td className="px-4 py-2 font-medium capitalize">{t.department}</td>
                      <td className="px-4 py-2">{t.evaluation_count}</td>
                      <td className="px-4 py-2">{t.deny_count}</td>
                      <td className="px-4 py-2">{(t.deny_rate * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Policy Metrics */}
          <section>
            <h2 className="mb-3 text-lg font-semibold">Per-Policy Metrics</h2>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              {dashboard.policy_metrics.map((m) => (
                <div
                  key={m.policy_group}
                  className="rounded-lg border p-4"
                >
                  <p className="text-xs font-semibold uppercase text-gray-400">
                    {m.policy_group}
                  </p>
                  <p className="mt-1 text-2xl font-bold">{m.fire_count}</p>
                  <p className="text-xs text-gray-500">
                    {m.deny_count} denials
                  </p>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : (
        <p className="text-gray-400">Unable to load dashboard data.</p>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  accent = "blue",
}: {
  label: string;
  value: number;
  accent?: string;
}) {
  const colors: Record<string, string> = {
    blue: "border-blue-200 bg-blue-50",
    red: "border-red-200 bg-red-50",
    yellow: "border-yellow-200 bg-yellow-50",
  };

  return (
    <div className={`rounded-lg border p-4 ${colors[accent] || colors.blue}`}>
      <p className="text-xs font-semibold uppercase text-gray-500">{label}</p>
      <p className="mt-1 text-3xl font-bold">{value}</p>
    </div>
  );
}
