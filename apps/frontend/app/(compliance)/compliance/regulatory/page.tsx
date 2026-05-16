"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

interface RegulatoryUpdate {
  id: string;
  title: string;
  source: string;
  normTier: string;
  publishedAt: string;
  effectiveAt: string;
  impactedRules: number;
  status: "new" | "assessed" | "propagated" | "resolved";
  summary: string;
}

const TIER_BADGE: Record<string, string> = { LAW: "bg-red-100 text-red-800", REGULATION: "bg-orange-100 text-orange-800", GUIDELINE: "bg-yellow-100 text-yellow-800" };
const STATUS_BADGE: Record<string, string> = { new: "bg-blue-100 text-blue-800", assessed: "bg-yellow-100 text-yellow-800", propagated: "bg-green-100 text-green-800", resolved: "bg-gray-100 text-gray-700" };

export default function RegulatoryFeedPage() {
  const [updates, setUpdates] = useState<RegulatoryUpdate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSeedData<{ regulatory_updates: RegulatoryUpdate[] }>("compliance").then((d) => {
      setUpdates(d.regulatory_updates ?? []);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regulatory Feed</h1>
        <p className="mt-1 text-sm text-gray-500">Track upstream regulatory changes and their downstream impact on internal rules</p>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "New Updates", value: updates.filter((u) => u.status === "new").length, color: "text-blue-600" },
          { label: "Being Assessed", value: updates.filter((u) => u.status === "assessed").length, color: "text-yellow-600" },
          { label: "Propagated", value: updates.filter((u) => u.status === "propagated").length, color: "text-green-600" },
          { label: "Total Impacted Rules", value: updates.reduce((a, u) => a + u.impactedRules, 0), color: "text-red-600" },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border bg-white p-5">
            <p className="text-xs font-medium text-gray-500">{s.label}</p>
            <p className={`mt-1 text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {updates.map((u) => (
          <div key={u.id} className="rounded-xl border bg-white p-5 hover:border-amber-300 transition-colors">
            <div className="flex items-center gap-2">
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_BADGE[u.normTier] ?? "bg-gray-100 text-gray-700"}`}>{u.normTier}</span>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[u.status]}`}>{u.status}</span>
              <span className="text-xs text-gray-400">{u.id}</span>
            </div>
            <h3 className="mt-2 text-sm font-semibold text-gray-900">{u.title}</h3>
            <p className="mt-1 text-sm text-gray-600">{u.summary}</p>
            <div className="mt-2 flex gap-4 text-xs text-gray-400">
              <span>Source: {u.source}</span>
              <span>Published: {u.publishedAt}</span>
              <span>Effective: {u.effectiveAt}</span>
              <span className="text-red-500">{u.impactedRules} rule(s) impacted</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
