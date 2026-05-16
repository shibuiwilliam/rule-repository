"use client";

import { useState, useEffect } from "react";
import { fetchSeedData } from "@/lib/seed-data";

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


const CATEGORY_LABELS: Record<ClauseCategory, string> = {
  all: "All Categories", nda: "NDA / Confidentiality", liability: "Limitation of Liability",
  indemnity: "Indemnification", ip: "Intellectual Property", termination: "Termination",
  "data-processing": "Data Processing", payment: "Payment Terms",
};

export default function ClausesPage() {
  const [clauses, setClauses] = useState<StandardClause[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<ClauseCategory>("all");

  useEffect(() => {
    fetchSeedData<{ clauses: StandardClause[] }>("legal").then((d) => {
      setClauses(d.clauses ?? []);
      setLoading(false);
    });
  }, []);

  const filtered = clauses.filter((c) => {
    if (category !== "all" && c.category !== category) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.title.toLowerCase().includes(q) || c.summary.toLowerCase().includes(q);
    }
    return true;
  });

  if (loading) {
    return <div className="flex items-center justify-center py-12 text-sm text-gray-400">Loading...</div>;
  }

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
          const count = clauses.filter((c) => c.category === cat).length;
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
