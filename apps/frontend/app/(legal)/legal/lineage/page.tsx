"use client";

import { useState } from "react";
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

const TRACKED_RULES: TrackedRule[] = [
  { id: "R-LAW-001", statement: "Personal information shall not be provided to third parties without consent of the individual.", norm_tier: "LAW", norm_authority: "Act on the Protection of Personal Information (APPI), Art. 27", upstreamCount: 0, downstreamCount: 4, pendingReview: false },
  { id: "R-REG-003", statement: "Overtime work shall not exceed 45 hours per month and 360 hours per year.", norm_tier: "REGULATION", norm_authority: "Labor Standards Act, Art. 36", upstreamCount: 1, downstreamCount: 3, pendingReview: true },
  { id: "R-POL-012", statement: "All vendor contracts exceeding JPY 10M require dual legal review before execution.", norm_tier: "CORPORATE_POLICY", norm_authority: "Internal Procurement Policy v3.2", upstreamCount: 2, downstreamCount: 2, pendingReview: false },
  { id: "R-DEPT-045", statement: "Engineering pull requests modifying authentication modules require security-team approval.", norm_tier: "DEPARTMENT_RULE", norm_authority: "Engineering Security Handbook, Ch. 4", upstreamCount: 3, downstreamCount: 0, pendingReview: false },
  { id: "R-POL-018", statement: "Customer data must be encrypted at rest using AES-256 or equivalent.", norm_tier: "CORPORATE_POLICY", norm_authority: "Data Protection Policy v2.1", upstreamCount: 1, downstreamCount: 5, pendingReview: true },
];

const DEMO_UPSTREAM: LineageChain = {
  root_rule_id: "R-POL-012",
  direction: "upstream",
  nodes: [
    { rule_id: "R-LAW-JP-COMP", statement: "Companies Act requires proper internal controls for corporate transactions.", norm_tier: "LAW", norm_authority: "Companies Act (Japan), Art. 362", depth: 2 },
    { rule_id: "R-REG-PROC", statement: "Procurement of services above regulatory thresholds shall follow competitive bidding procedures.", norm_tier: "REGULATION", norm_authority: "Internal Audit Standards, Sect. 4.1", depth: 1 },
    { rule_id: "R-POL-012", statement: "All vendor contracts exceeding JPY 10M require dual legal review before execution.", norm_tier: "CORPORATE_POLICY", norm_authority: "Internal Procurement Policy v3.2", depth: 0 },
  ],
};

const DEMO_DOWNSTREAM: LineageChain = {
  root_rule_id: "R-POL-012",
  direction: "downstream",
  nodes: [
    { rule_id: "R-POL-012", statement: "All vendor contracts exceeding JPY 10M require dual legal review before execution.", norm_tier: "CORPORATE_POLICY", norm_authority: "Internal Procurement Policy v3.2", depth: 0 },
    { rule_id: "R-DEPT-PROC-1", statement: "Engineering vendor contracts must include SLA and data-handling appendices.", norm_tier: "DEPARTMENT_RULE", norm_authority: "Eng Procurement SOP", depth: 1 },
    { rule_id: "R-OP-PROC-1", statement: "Cloud infrastructure vendor agreements must specify uptime guarantees of 99.9% or higher.", norm_tier: "OPERATIONAL_RULE", norm_authority: null, depth: 2 },
  ],
};

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
  const [selectedRule, setSelectedRule] = useState<string | null>(null);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Norm Lineage</h1>
        <p className="mt-1 text-sm text-gray-500">Trace rules from operational procedures up to source laws and regulations. Identify downstream impact of upstream amendments.</p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Tracked Norms", value: TRACKED_RULES.length, color: "text-blue-600" },
          { label: "Pending Norm Reviews", value: TRACKED_RULES.filter((r) => r.pendingReview).length, color: "text-yellow-600" },
          { label: "Laws / Regulations", value: TRACKED_RULES.filter((r) => r.norm_tier === "LAW" || r.norm_tier === "REGULATION").length, color: "text-red-600" },
          { label: "Total Derivatives", value: TRACKED_RULES.reduce((a, r) => a + r.downstreamCount, 0), color: "text-green-600" },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{stat.label}</p>
            <p className={`mt-1 text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Rule list */}
      <div className="space-y-3">
        {TRACKED_RULES.map((rule) => (
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
            upstream={selectedRule === "R-POL-012" ? DEMO_UPSTREAM : undefined}
            downstream={selectedRule === "R-POL-012" ? DEMO_DOWNSTREAM : undefined}
          />
        </div>
      )}
    </div>
  );
}
