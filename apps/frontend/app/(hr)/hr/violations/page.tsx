"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

type ViolationSeverity = "all" | "critical" | "high" | "medium" | "low";

interface HRViolation {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  ruleId: string;
  ruleStatement: string;
  severity: Exclude<ViolationSeverity, "all">;
  category: string;
  detectedAt: string;
  status: "open" | "acknowledged" | "resolved";
  details: string;
}


const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-blue-100 text-blue-800",
};

const STATUS_BADGE: Record<string, string> = {
  open: "bg-red-100 text-red-800",
  acknowledged: "bg-yellow-100 text-yellow-800",
  resolved: "bg-green-100 text-green-800",
};

export default function ViolationsPage() {
  const [violations, setViolations] = useState<HRViolation[]>([]);
  const [loading, setLoading] = useState(true);
  const [severity, setSeverity] = useState<ViolationSeverity>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchSeedData<{ violations: HRViolation[] }>("hr").then((d) => {
      setViolations(d.violations ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  const filtered = violations.filter((v) => {
    if (severity !== "all" && v.severity !== severity) return false;
    if (search) {
      const q = search.toLowerCase();
      return v.employeeName.toLowerCase().includes(q) || v.ruleStatement.toLowerCase().includes(q) || v.department.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">HR Violations</h1>
        <p className="mt-1 text-sm text-gray-500">Active compliance violations across labor regulations, attendance policies, and leave requirements</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Open Violations", value: violations.filter((v) => v.status === "open").length, color: "text-red-600" },
          { label: "Critical", value: violations.filter((v) => v.severity === "critical").length, color: "text-red-600" },
          { label: "Acknowledged", value: violations.filter((v) => v.status === "acknowledged").length, color: "text-yellow-600" },
          { label: "Resolved This Month", value: violations.filter((v) => v.status === "resolved").length, color: "text-green-600" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <label htmlFor="vio-search" className="text-xs font-medium text-gray-500">Search</label>
          <input id="vio-search" type="text" placeholder="Search by employee, rule, or department..." value={search} onChange={(e) => setSearch(e.target.value)} className="mt-0.5 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["all", "critical", "high", "medium", "low"] as ViolationSeverity[]).map((s) => {
          const count = s === "all" ? violations.length : violations.filter((v) => v.severity === s).length;
          return (
            <button key={s} type="button" onClick={() => setSeverity(s)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${severity === s ? "border-indigo-400 bg-indigo-100 text-indigo-800" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"}`}>
              {s.charAt(0).toUpperCase() + s.slice(1)} ({count})
            </button>
          );
        })}
      </div>

      {/* Violations table */}
      <div className="overflow-x-auto rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-5 py-3">Employee</th>
              <th className="px-5 py-3">Rule Violated</th>
              <th className="px-5 py-3">Severity</th>
              <th className="px-5 py-3">Category</th>
              <th className="px-5 py-3">Detected</th>
              <th className="px-5 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((vio) => (
              <tr key={vio.id} className="transition-colors hover:bg-gray-50">
                <td className="px-5 py-3">
                  <p className="font-medium text-gray-900">{vio.employeeName}</p>
                  <p className="text-xs text-gray-400">{vio.employeeId} / {vio.department}</p>
                </td>
                <td className="max-w-xs px-5 py-3">
                  <p className="text-sm text-gray-700">{vio.ruleStatement}</p>
                  <p className="mt-0.5 text-xs text-gray-400">{vio.details}</p>
                </td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${SEVERITY_BADGE[vio.severity]}`}>{vio.severity}</span>
                </td>
                <td className="px-5 py-3 text-gray-600">{vio.category}</td>
                <td className="px-5 py-3 text-gray-600">{vio.detectedAt}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[vio.status]}`}>{vio.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="p-8 text-center text-sm text-gray-400">No violations match the selected filters.</div>
        )}
      </div>
    </div>
  );
}
