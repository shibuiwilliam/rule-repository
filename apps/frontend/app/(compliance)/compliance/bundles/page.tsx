"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface BundleRule {
  ruleId: string;
  statement: string;
  controlId: string;
  status: "implemented" | "in-progress" | "not-started";
  lastEvaluated: string | null;
  complianceRate: number | null;
}

interface Bundle {
  id: string;
  name: string;
  framework: string;
  description: string;
  totalControls: number;
  implementedControls: number;
  rules: BundleRule[];
}

const STATUS_BADGE: Record<string, string> = { implemented: "bg-green-100 text-green-700", "in-progress": "bg-yellow-100 text-yellow-700", "not-started": "bg-gray-100 text-gray-600" };

export default function BundlesPage() {
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetchSeedData<{ bundles: Bundle[] }>("compliance").then((d) => {
      const data = d.bundles ?? [];
      setBundles(data);
      setExpanded(data[0]?.id ?? null);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance Bundles</h1>
        <p className="mt-1 text-sm text-gray-500">Manage compliance framework bundles and track control implementation</p>
      </div>

      <div className="space-y-4">
        {bundles.map((bundle) => {
          const pct = Math.round((bundle.implementedControls / bundle.totalControls) * 100);
          const isOpen = expanded === bundle.id;
          return (
            <div key={bundle.id} className="rounded-xl border bg-white">
              <button type="button" onClick={() => setExpanded(isOpen ? null : bundle.id)} className="flex w-full items-center justify-between px-5 py-4 text-left">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-base font-semibold text-gray-900">{bundle.name}</h3>
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{bundle.framework}</span>
                  </div>
                  <p className="mt-0.5 text-sm text-gray-500">{bundle.description}</p>
                  <div className="mt-2 flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-32 overflow-hidden rounded-full bg-gray-100">
                        <div className={`h-full rounded-full ${pct >= 90 ? "bg-green-500" : pct >= 70 ? "bg-yellow-500" : "bg-red-500"}`} style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs font-medium text-gray-600">{pct}%</span>
                    </div>
                    <span className="text-xs text-gray-400">{bundle.implementedControls}/{bundle.totalControls} controls</span>
                  </div>
                </div>
                <svg className={`h-5 w-5 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {isOpen && (
                <div className="border-t">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        <th className="px-5 py-3">Control ID</th>
                        <th className="px-5 py-3">Rule</th>
                        <th className="px-5 py-3">Status</th>
                        <th className="px-5 py-3">Last Eval</th>
                        <th className="px-5 py-3">Compliance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {bundle.rules.map((r) => (
                        <tr key={r.ruleId} className="hover:bg-gray-50">
                          <td className="px-5 py-3 font-mono text-xs text-gray-500">{r.controlId}</td>
                          <td className="max-w-md px-5 py-3 text-gray-700">{r.statement}</td>
                          <td className="px-5 py-3"><span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[r.status]}`}>{r.status.replace("-", " ")}</span></td>
                          <td className="px-5 py-3 text-gray-500">{r.lastEvaluated ?? "-"}</td>
                          <td className="px-5 py-3">{r.complianceRate !== null ? <span className={`font-medium ${r.complianceRate >= 90 ? "text-green-600" : "text-yellow-600"}`}>{r.complianceRate}%</span> : <span className="text-gray-400">-</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
