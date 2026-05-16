"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";
import NormLineageViewer from "@/components/NormLineageViewer";
import type { LineageChain } from "@/components/NormLineageViewer";

/* ---------- demo data ---------- */

interface TrackedRule {
  id: string;
  statement: string;
  norm_tier: string;
  norm_authority: string | null;
  upstreamCount: number;
  downstreamCount: number;
  pendingReview: boolean;
}


const TIER_BADGE: Record<string, string> = {
  LAW: "bg-red-100 text-red-800",
  REGULATION: "bg-orange-100 text-orange-800",
  GUIDELINE: "bg-yellow-100 text-yellow-800",
  CORPORATE_POLICY: "bg-green-100 text-green-800",
  DEPARTMENT_RULE: "bg-blue-100 text-blue-800",
  OPERATIONAL_RULE: "bg-purple-100 text-purple-800",
};

const TIER_LABELS: Record<string, string> = {
  LAW: "Law",
  REGULATION: "Regulation",
  GUIDELINE: "Guideline",
  CORPORATE_POLICY: "Corporate Policy",
  DEPARTMENT_RULE: "Department Rule",
  OPERATIONAL_RULE: "Operational Rule",
};

export default function LineagePage() {
  const [trackedRules, setTrackedRules] = useState<TrackedRule[]>([]);
  const [upstream, setUpstream] = useState<LineageChain | undefined>(undefined);
  const [downstream, setDownstream] = useState<LineageChain | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [selectedRule, setSelectedRule] = useState<string | null>(null);

  useEffect(() => {
    fetchSeedData<{ lineage: { tracked_rules: TrackedRule[]; upstream: LineageChain; downstream: LineageChain } }>("legal").then((d) => {
      setTrackedRules(d.lineage?.tracked_rules ?? []);
      setUpstream(d.lineage?.upstream);
      setDownstream(d.lineage?.downstream);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Norm Lineage</h1>
        <p className="mt-1 text-sm text-gray-500">Trace rules from operational procedures up to source laws and regulations. Identify downstream impact of upstream amendments.</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Tracked Norms", value: trackedRules.length, color: "text-blue-600" },
          { label: "Pending Norm Reviews", value: trackedRules.filter((r) => r.pendingReview).length, color: "text-yellow-600" },
          { label: "Laws / Regulations", value: trackedRules.filter((r) => r.norm_tier === "LAW" || r.norm_tier === "REGULATION").length, color: "text-red-600" },
          { label: "Total Derivatives", value: trackedRules.reduce((a, r) => a + r.downstreamCount, 0), color: "text-green-600" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Rule list */}
      <div className="space-y-3">
        {trackedRules.map((rule) => (
          <button key={rule.id} type="button" onClick={() => setSelectedRule(selectedRule === rule.id ? null : rule.id)}
            className="w-full rounded-xl border bg-white p-5 text-left transition-colors hover:border-slate-300">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_BADGE[rule.norm_tier]}`}>{TIER_LABELS[rule.norm_tier]}</span>
                  <span className="text-xs text-gray-400">{rule.id}</span>
                  {rule.pendingReview && <span className="rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">Pending Review</span>}
                </div>
                <p className="mt-1.5 text-sm font-medium text-gray-900">{rule.statement}</p>
                {rule.norm_authority && <p className="mt-0.5 text-xs text-gray-500">{rule.norm_authority}</p>}
                <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                  <span>{rule.upstreamCount} upstream</span>
                  <span>{rule.downstreamCount} downstream</span>
                </div>
              </div>
              <span className="ml-4 text-gray-400">{selectedRule === rule.id ? "\u25B2" : "\u25BC"}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Lineage viewer for selected rule */}
      {selectedRule && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Lineage for {selectedRule}</h2>
          <NormLineageViewer
            ruleId={selectedRule}
            upstream={selectedRule === "R-POL-012" ? upstream : undefined}
            downstream={selectedRule === "R-POL-012" ? downstream : undefined}
          />
        </div>
      )}
    </div>
  );
}
