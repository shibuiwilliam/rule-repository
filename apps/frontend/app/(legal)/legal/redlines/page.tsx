"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

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


const RISK_COLORS: Record<string, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
};

export default function RedlinesPage() {
  const [revisions, setRevisions] = useState<ContractRevision[]>([]);
  const [sampleChanges, setSampleChanges] = useState<RedlineChange[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<RevisionStatus>("all");
  const [selectedRevision, setSelectedRevision] = useState<string | null>(null);

  useEffect(() => {
    fetchSeedData<{ redlines: { revisions: ContractRevision[]; changes: RedlineChange[] } }>("legal").then((d) => {
      setRevisions(d.redlines?.revisions ?? []);
      setSampleChanges(d.redlines?.changes ?? []);
      setLoading(false);
    });
  }, []);

  const filtered = revisions.filter((r) => statusFilter === "all" || r.status === statusFilter);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Contract Redlines</h1>
        <p className="mt-1 text-sm text-gray-500">Review clause-by-clause changes between contract revisions with risk assessment</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Pending Reviews", value: revisions.filter((r) => r.status === "pending").length, color: "text-yellow-600" },
          { label: "Total Risk Flags", value: revisions.reduce((a, r) => a + r.riskFlags, 0), color: "text-red-600" },
          { label: "Approved This Month", value: revisions.filter((r) => r.status === "approved").length, color: "text-green-600" },
          { label: "Avg. Changed Clauses", value: revisions.length > 0 ? (revisions.reduce((a, r) => a + r.changedClauses, 0) / revisions.length).toFixed(1) : "0", color: "text-blue-600" },
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
                {sampleChanges.map((change, i) => (
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
