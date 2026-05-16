"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

type PolicyCategory = "all" | "attendance" | "leave" | "overtime" | "childcare" | "safety" | "conduct";

interface HRPolicy {
  id: string;
  title: string;
  category: Exclude<PolicyCategory, "all">;
  normTier: string;
  normAuthority: string | null;
  activeRules: number;
  lastUpdated: string;
  locale: string;
  status: "active" | "under_review" | "pending_amendment";
}


const CATEGORY_LABELS: Record<PolicyCategory, string> = {
  all: "All Categories", attendance: "Attendance", leave: "Leave",
  overtime: "Overtime", childcare: "Child/Family Care", safety: "Safety", conduct: "Conduct",
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
  LAW: "Law", REGULATION: "Regulation", GUIDELINE: "Guideline",
  CORPORATE_POLICY: "Corp. Policy", DEPARTMENT_RULE: "Dept. Rule", OPERATIONAL_RULE: "Op. Rule",
};

const STATUS_BADGE: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  under_review: "bg-yellow-100 text-yellow-800",
  pending_amendment: "bg-orange-100 text-orange-800",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Active", under_review: "Under Review", pending_amendment: "Pending Amendment",
};

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<HRPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<PolicyCategory>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchSeedData<{ policies: HRPolicy[] }>("hr").then((d) => {
      setPolicies(d.policies ?? []);
      setLoading(false);
    });
  }, []);

  const filtered = policies.filter((p) => {
    if (category !== "all" && p.category !== category) return false;
    if (search) {
      const q = search.toLowerCase();
      return p.title.toLowerCase().includes(q) || (p.normAuthority ?? "").toLowerCase().includes(q);
    }
    return true;
  });

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">HR Policy Library</h1>
        <p className="mt-1 text-sm text-gray-500">Browse HR policies, their regulatory sources, and associated compliance rules</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "Total Policies", value: policies.length, color: "text-blue-600" },
          { label: "Active Rules", value: policies.reduce((a, p) => a + p.activeRules, 0), color: "text-green-600" },
          { label: "Under Review", value: policies.filter((p) => p.status === "under_review").length, color: "text-yellow-600" },
          { label: "Pending Amendment", value: policies.filter((p) => p.status === "pending_amendment").length, color: "text-orange-600" },
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
          <label htmlFor="policy-search" className="text-xs font-medium text-gray-500">Search</label>
          <input id="policy-search" type="text" placeholder="Search policies..." value={search} onChange={(e) => setSearch(e.target.value)} className="mt-0.5 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400" />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(CATEGORY_LABELS) as PolicyCategory[]).map((cat) => {
          const count = cat === "all" ? policies.length : policies.filter((p) => p.category === cat).length;
          return (
            <button key={cat} type="button" onClick={() => setCategory(cat)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${category === cat ? "border-indigo-400 bg-indigo-100 text-indigo-800" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"}`}>
              {CATEGORY_LABELS[cat]} ({count})
            </button>
          );
        })}
      </div>

      {/* Policy cards */}
      <div className="space-y-3">
        {filtered.map((policy) => (
          <div key={policy.id} className="rounded-xl border bg-white p-5 transition-colors hover:border-indigo-300">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900">{policy.title}</h3>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${TIER_BADGE[policy.normTier]}`}>{TIER_LABELS[policy.normTier]}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[policy.status]}`}>{STATUS_LABELS[policy.status]}</span>
                </div>
                {policy.normAuthority && <p className="mt-1 text-sm text-gray-600">{policy.normAuthority}</p>}
                <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                  <span>{policy.activeRules} active rule(s)</span>
                  <span>Updated: {policy.lastUpdated}</span>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-gray-500">{policy.locale.toUpperCase()}</span>
                </div>
              </div>
              <span className="ml-4 rounded-full border px-2.5 py-0.5 text-xs font-medium text-gray-600">{CATEGORY_LABELS[policy.category]}</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="rounded-xl border bg-white p-8 text-center text-sm text-gray-400">No policies match the selected filters.</div>
        )}
      </div>
    </div>
  );
}
