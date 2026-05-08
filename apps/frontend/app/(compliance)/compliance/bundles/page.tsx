"use client";

import { useState } from "react";

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

const BUNDLES: Bundle[] = [
  {
    id: "B-001", name: "J-SOX Internal Controls", framework: "J-SOX",
    description: "Financial reporting internal controls required under the Japanese Financial Instruments and Exchange Act.",
    totalControls: 42, implementedControls: 38,
    rules: [
      { ruleId: "R-1001", statement: "All financial transactions require dual approval above JPY 1M", controlId: "JSOX-AC-01", status: "implemented", lastEvaluated: "2026-05-07", complianceRate: 96 },
      { ruleId: "R-1002", statement: "Revenue recognition must follow IFRS 15 five-step model", controlId: "JSOX-RR-01", status: "implemented", lastEvaluated: "2026-05-06", complianceRate: 100 },
      { ruleId: "R-1003", statement: "Journal entries require supporting documentation", controlId: "JSOX-JE-01", status: "implemented", lastEvaluated: "2026-05-07", complianceRate: 92 },
      { ruleId: "R-1004", statement: "Bank reconciliation within 3 business days", controlId: "JSOX-BR-01", status: "in-progress", lastEvaluated: null, complianceRate: null },
    ],
  },
  {
    id: "B-002", name: "GDPR Data Protection", framework: "GDPR",
    description: "EU General Data Protection Regulation compliance controls.",
    totalControls: 35, implementedControls: 28,
    rules: [
      { ruleId: "R-2001", statement: "Personal data processing requires documented legal basis", controlId: "GDPR-LB-01", status: "implemented", lastEvaluated: "2026-05-05", complianceRate: 88 },
      { ruleId: "R-2002", statement: "Data subject access requests within 30 days", controlId: "GDPR-DSAR-01", status: "implemented", lastEvaluated: "2026-05-04", complianceRate: 95 },
      { ruleId: "R-2003", statement: "Cross-border transfers require SCCs", controlId: "GDPR-CBT-01", status: "in-progress", lastEvaluated: null, complianceRate: null },
    ],
  },
  {
    id: "B-003", name: "EU AI Act Compliance", framework: "EU AI Act",
    description: "Controls for AI systems classified as high-risk.",
    totalControls: 18, implementedControls: 8,
    rules: [
      { ruleId: "R-3001", statement: "AI system risk classification must be documented", controlId: "EUAI-RC-01", status: "implemented", lastEvaluated: "2026-05-01", complianceRate: 100 },
      { ruleId: "R-3002", statement: "High-risk AI systems require human oversight", controlId: "EUAI-HO-01", status: "in-progress", lastEvaluated: null, complianceRate: null },
      { ruleId: "R-3003", statement: "AI training data must be bias-tested", controlId: "EUAI-TD-01", status: "not-started", lastEvaluated: null, complianceRate: null },
    ],
  },
];

const STATUS_BADGE: Record<string, string> = { implemented: "bg-green-100 text-green-700", "in-progress": "bg-yellow-100 text-yellow-700", "not-started": "bg-gray-100 text-gray-600" };

export default function BundlesPage() {
  const [expanded, setExpanded] = useState<string | null>(BUNDLES[0]?.id ?? null);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Compliance Bundles</h1>
        <p className="mt-1 text-sm text-gray-500">Manage compliance framework bundles and track control implementation</p>
      </div>

      <div className="space-y-4">
        {BUNDLES.map((bundle) => {
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
