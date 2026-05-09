"use client";

import { useState } from "react";

type RevisionStatus = "all" | "pending" | "approved" | "rejected";

interface ContractRevision {
  id: string;
  contractName: string;
  counterparty: string;
  version: { from: string; to: string };
  changedClauses: number;
  riskFlags: number;
  submittedAt: string;
  submittedBy: string;
  status: Exclude<RevisionStatus, "all">;
}

const REVISIONS: ContractRevision[] = [
  { id: "REV-001", contractName: "ACME Corp Master Services Agreement", counterparty: "ACME Corp", version: { from: "2.3", to: "2.4" }, changedClauses: 4, riskFlags: 2, submittedAt: "2026-05-06", submittedBy: "T. Nakamura", status: "pending" },
  { id: "REV-002", contractName: "GlobalTech NDA", counterparty: "GlobalTech Inc.", version: { from: "1.0", to: "1.1" }, changedClauses: 2, riskFlags: 0, submittedAt: "2026-05-04", submittedBy: "S. Tanaka", status: "approved" },
  { id: "REV-003", contractName: "DataFlow Processing Agreement", counterparty: "DataFlow Ltd.", version: { from: "3.1", to: "4.0" }, changedClauses: 8, riskFlags: 5, submittedAt: "2026-05-03", submittedBy: "K. Yamada", status: "pending" },
  { id: "REV-004", contractName: "Vendor SOW - Q2 Deliverables", counterparty: "BuildRight LLC", version: { from: "1.2", to: "1.3" }, changedClauses: 3, riskFlags: 1, submittedAt: "2026-04-28", submittedBy: "M. Sato", status: "approved" },
  { id: "REV-005", contractName: "Cloud Infrastructure License", counterparty: "CloudScale Inc.", version: { from: "5.0", to: "5.1" }, changedClauses: 1, riskFlags: 0, submittedAt: "2026-04-25", submittedBy: "H. Lee", status: "rejected" },
];

const STATUS_BADGE: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

interface RedlineChange {
  clause: string;
  type: "added" | "removed" | "modified";
  oldText?: string;
  newText: string;
  riskLevel: "low" | "medium" | "high";
}

const SAMPLE_CHANGES: RedlineChange[] = [
  { clause: "Section 4.2 — Limitation of Liability", type: "modified", oldText: "Total liability shall not exceed the fees paid in the preceding 12 months.", newText: "Total liability shall not exceed the fees paid in the preceding 24 months.", riskLevel: "high" },
  { clause: "Section 7.1 — Governing Law", type: "modified", oldText: "This Agreement shall be governed by the laws of Tokyo, Japan.", newText: "This Agreement shall be governed by the laws of the State of Delaware, USA.", riskLevel: "high" },
  { clause: "Section 9.3 — Data Retention", type: "added", newText: "The Processor shall retain personal data for no longer than 36 months following termination, unless required by applicable law.", riskLevel: "medium" },
  { clause: "Section 2.1 — Definitions", type: "modified", oldText: "\"Confidential Information\" means any non-public information disclosed by either party.", newText: "\"Confidential Information\" means any non-public information disclosed by either party, including trade secrets, algorithms, and customer lists.", riskLevel: "low" },
];

const RISK_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
};

export default function RedlinesPage() {
  const [statusFilter, setStatusFilter] = useState<RevisionStatus>("all");
  const [selectedRevision, setSelectedRevision] = useState<string | null>(null);

  const filtered = REVISIONS.filter((r) => statusFilter === "all" || r.status === statusFilter);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Contract Redlines</h1>
        <p className="mt-1 text-sm text-gray-500">Review clause-by-clause changes between contract revisions with risk assessment</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Pending Reviews", value: REVISIONS.filter((r) => r.status === "pending").length, color: "text-yellow-600" },
          { label: "Total Risk Flags", value: REVISIONS.reduce((a, r) => a + r.riskFlags, 0), color: "text-red-600" },
          { label: "Approved This Month", value: REVISIONS.filter((r) => r.status === "approved").length, color: "text-green-600" },
          { label: "Avg. Changed Clauses", value: (REVISIONS.reduce((a, r) => a + r.changedClauses, 0) / REVISIONS.length).toFixed(1), color: "text-blue-600" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(["all", "pending", "approved", "rejected"] as RevisionStatus[]).map((s) => (
          <button key={s} type="button" onClick={() => setStatusFilter(s)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${statusFilter === s ? "border-slate-400 bg-slate-100 text-slate-800" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"}`}>
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Revisions list */}
      <div className="space-y-3">
        {filtered.map((rev) => (
          <button key={rev.id} type="button" onClick={() => setSelectedRevision(selectedRevision === rev.id ? null : rev.id)}
            className="w-full rounded-xl border bg-white p-5 text-left transition-colors hover:border-slate-300">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900">{rev.contractName}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[rev.status]}`}>{rev.status}</span>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  {rev.counterparty} — v{rev.version.from} to v{rev.version.to}
                </p>
                <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                  <span>{rev.changedClauses} clause(s) changed</span>
                  {rev.riskFlags > 0 && <span className="text-red-500">{rev.riskFlags} risk flag(s)</span>}
                  <span>Submitted {rev.submittedAt} by {rev.submittedBy}</span>
                </div>
              </div>
              <span className="ml-4 text-gray-400">{selectedRevision === rev.id ? "\u25B2" : "\u25BC"}</span>
            </div>

            {selectedRevision === rev.id && (
              <div className="mt-4 space-y-3 border-t pt-4" onClick={(e) => e.stopPropagation()}>
                <h4 className="text-xs font-semibold uppercase text-gray-500">Clause Changes</h4>
                {SAMPLE_CHANGES.map((change, i) => (
                  <div key={i} className="rounded-lg border bg-gray-50 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-700">{change.clause}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${RISK_COLORS[change.riskLevel]}`}>{change.riskLevel} risk</span>
                    </div>
                    {change.oldText && (
                      <div className="mt-2 rounded bg-red-50 px-2 py-1 text-xs text-red-700 line-through">{change.oldText}</div>
                    )}
                    <div className={`mt-1 rounded px-2 py-1 text-xs ${change.type === "added" ? "bg-green-50 text-green-700" : "bg-green-50 text-green-700"}`}>{change.newText}</div>
                  </div>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
