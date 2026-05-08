"use client";

import { useState } from "react";

type ClauseCategory = "all" | "nda" | "liability" | "indemnity" | "ip" | "termination" | "data-processing" | "payment";

interface StandardClause {
  id: string;
  category: Exclude<ClauseCategory, "all">;
  title: string;
  summary: string;
  version: string;
  lastUpdated: string;
  usageCount: number;
  deviationCount: number;
}

const CLAUSES: StandardClause[] = [
  { id: "SC-001", category: "nda", title: "Mutual NDA - Standard Confidentiality", summary: "Mutual obligations to protect confidential information. 2-year survival period.", version: "3.1", lastUpdated: "2026-04-15", usageCount: 142, deviationCount: 3 },
  { id: "SC-002", category: "liability", title: "Limitation of Liability - Capped", summary: "Total liability capped at 12 months of fees paid. Excludes IP infringement and data breach.", version: "4.2", lastUpdated: "2026-04-01", usageCount: 98, deviationCount: 8 },
  { id: "SC-003", category: "indemnity", title: "Mutual Indemnification", summary: "Each party indemnifies the other for third-party claims arising from breach of representations.", version: "2.3", lastUpdated: "2026-02-28", usageCount: 85, deviationCount: 5 },
  { id: "SC-004", category: "ip", title: "IP Ownership - Work for Hire", summary: "All deliverables created under the agreement are owned by the commissioning party.", version: "3.0", lastUpdated: "2026-01-15", usageCount: 67, deviationCount: 2 },
  { id: "SC-005", category: "termination", title: "Termination for Convenience", summary: "Either party may terminate with 30 days written notice. Includes wind-down obligations.", version: "2.1", lastUpdated: "2026-03-10", usageCount: 120, deviationCount: 4 },
  { id: "SC-006", category: "data-processing", title: "Data Processing Agreement (JP APPI)", summary: "Compliance with Japan APPI for personal data processing. Includes cross-border transfer provisions.", version: "2.5", lastUpdated: "2026-04-20", usageCount: 45, deviationCount: 6 },
  { id: "SC-007", category: "payment", title: "Net 30 Payment Terms", summary: "Payment due 30 days from invoice date. 1.5% monthly late payment interest.", version: "1.2", lastUpdated: "2026-02-01", usageCount: 200, deviationCount: 12 },
];

const CATEGORY_LABELS: Record<ClauseCategory, string> = {
  all: "All Categories", nda: "NDA / Confidentiality", liability: "Limitation of Liability",
  indemnity: "Indemnification", ip: "Intellectual Property", termination: "Termination",
  "data-processing": "Data Processing", payment: "Payment Terms",
};

export default function ClausesPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<ClauseCategory>("all");

  const filtered = CLAUSES.filter((c) => {
    if (category !== "all" && c.category !== category) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.title.toLowerCase().includes(q) || c.summary.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Standard Clause Library</h1>
        <p className="mt-1 text-sm text-gray-500">Approved clause templates, usage statistics, and deviation tracking</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1">
          <label htmlFor="clause-search" className="text-xs font-medium text-gray-500">Search</label>
          <input id="clause-search" type="text" placeholder="Search clauses..." value={search} onChange={(e) => setSearch(e.target.value)} className="mt-0.5 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-700 placeholder:text-gray-400" />
        </div>
        <div>
          <label htmlFor="cat-filter" className="text-xs font-medium text-gray-500">Category</label>
          <select id="cat-filter" value={category} onChange={(e) => setCategory(e.target.value as ClauseCategory)} className="mt-0.5 block rounded-lg border bg-white px-3 py-2 text-sm text-gray-700">
            {(Object.keys(CATEGORY_LABELS) as ClauseCategory[]).map((cat) => (
              <option key={cat} value={cat}>{CATEGORY_LABELS[cat]}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(CATEGORY_LABELS) as ClauseCategory[]).filter((c) => c !== "all").map((cat) => {
          const count = CLAUSES.filter((c) => c.category === cat).length;
          return (
            <button key={cat} type="button" onClick={() => setCategory(cat === category ? "all" : cat)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${category === cat ? "border-slate-400 bg-slate-100 text-slate-800" : "border-gray-200 bg-white text-gray-600 hover:border-gray-300"}`}>
              {CATEGORY_LABELS[cat]} ({count})
            </button>
          );
        })}
      </div>

      <div className="space-y-3">
        {filtered.map((clause) => (
          <div key={clause.id} className="rounded-xl border bg-white p-5 transition-colors hover:border-slate-300">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-gray-900">{clause.title}</h3>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">v{clause.version}</span>
                </div>
                <p className="mt-1 text-sm text-gray-600">{clause.summary}</p>
                <div className="mt-2 flex items-center gap-4 text-xs text-gray-400">
                  <span>Updated: {clause.lastUpdated}</span>
                  <span>Used in {clause.usageCount} contracts</span>
                  {clause.deviationCount > 0 && <span className="text-yellow-600">{clause.deviationCount} deviation{clause.deviationCount !== 1 ? "s" : ""}</span>}
                </div>
              </div>
              <span className="ml-4 rounded-full border px-2.5 py-0.5 text-xs font-medium text-gray-600">{CATEGORY_LABELS[clause.category]}</span>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="rounded-xl border bg-white p-8 text-center text-sm text-gray-400">No clauses match the selected filters.</div>
        )}
      </div>
    </div>
  );
}
