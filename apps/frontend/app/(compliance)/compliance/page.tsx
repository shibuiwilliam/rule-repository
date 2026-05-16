"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePersonaTerm } from "@/lib/use-persona-term";
import { fetchSeedData } from "@/lib/seed-data";

interface Bundle {
  id: string;
  name: string;
  framework: string;
  totalControls: number;
  implementedControls: number;
  lastAudit: string;
  status: string;
}

interface Exception {
  id: string;
  rule: string;
  department: string;
  reason: string;
  grantedBy: string;
  expiresAt: string;
  status: string;
}

const STATUS_BADGE: Record<string, string> = {
  "on-track": "bg-green-100 text-green-700", "at-risk": "bg-yellow-100 text-yellow-700", behind: "bg-red-100 text-red-700",
  active: "bg-green-100 text-green-700", "pending-renewal": "bg-yellow-100 text-yellow-700",
};

export default function ComplianceDashboardPage() {
  const t = usePersonaTerm();
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ bundles: Bundle[]; exceptions: Exception[] }>("compliance").then((d) => {
      setBundles(d.bundles ?? []);
      setExceptions(d.exceptions ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t("landing_title", "Compliance Dashboard")}</h1>
        <p className="mt-1 text-sm text-gray-500">Framework progress, control status, and exception management</p>
      </div>

      <div>
        <h2 className="mb-3 text-base font-semibold text-gray-900">Bundle Progress</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {bundles.map((b) => {
            const pct = Math.round((b.implementedControls / b.totalControls) * 100);
            return (
              <div key={b.id} className="rounded-xl border bg-white p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-900">{b.name}</h3>
                    <p className="text-xs text-gray-500">{b.framework}</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[b.status]}`}>{b.status.replace("-", " ")}</span>
                </div>
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">{b.implementedControls}/{b.totalControls} controls</span>
                    <span className="font-medium text-gray-900">{pct}%</span>
                  </div>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div className={`h-full rounded-full ${pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-gray-400">Last audit: {b.lastAudit}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Control Framework Status</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
            <p className="text-3xl font-bold text-green-700">161</p>
            <p className="mt-1 text-sm text-green-600">Implemented</p>
          </div>
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-center">
            <p className="text-3xl font-bold text-yellow-700">16</p>
            <p className="mt-1 text-sm text-yellow-600">In Progress</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-center">
            <p className="text-3xl font-bold text-red-700">11</p>
            <p className="mt-1 text-sm text-red-600">Not Started</p>
          </div>
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
            <p className="text-3xl font-bold text-blue-700">3</p>
            <p className="mt-1 text-sm text-blue-600">Exceptions</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border bg-white">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Exception Queue</h2>
          <Link href="/compliance/exceptions" className="text-sm text-blue-600 hover:underline">View all</Link>
        </div>
        <div className="divide-y">
          {exceptions.map((ex) => (
            <div key={ex.id} className="flex items-start gap-4 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">{ex.rule}</p>
                <p className="mt-0.5 text-xs text-gray-500">{ex.department} | Granted by {ex.grantedBy} | Expires {ex.expiresAt}</p>
                <p className="mt-0.5 text-xs text-gray-400">Reason: {ex.reason}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[ex.status]}`}>{ex.status.replace("-", " ")}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border bg-white p-5">
        <h2 className="text-base font-semibold text-gray-900">Regulatory Horizon</h2>
        <div className="mt-4 space-y-3">
          {[
            { date: "2026-06-15", event: "Updated Subcontract Act enforcement standards", impact: "medium" },
            { date: "2026-07-01", event: "Revised APPI Guidelines effective", impact: "high" },
            { date: "2026-08-01", event: "EU AI Act - High-Risk System Requirements", impact: "high" },
            { date: "2026-12-31", event: "J-SOX annual reporting deadline", impact: "high" },
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-4 rounded-lg border p-3">
              <div className="w-20 text-center">
                <p className="text-xs font-semibold text-gray-900">{item.date.split("-").slice(1).join("/")}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-gray-700">{item.event}</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${item.impact === "high" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"}`}>{item.impact}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
