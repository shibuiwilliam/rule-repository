"use client";

import { useCallback, useEffect, useState } from "react";

import { getDepartmentRules, type Rule } from "@/lib/api";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ModalityBadge({ modality }: { modality: string }) {
  const cls =
    modality === "MUST" || modality === "MUST_NOT"
      ? "bg-red-100 text-red-700"
      : modality === "SHOULD" || modality === "SHOULD_NOT"
        ? "bg-yellow-100 text-yellow-700"
        : "bg-gray-100 text-gray-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {modality}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "CRITICAL"
      ? "bg-red-600 text-white"
      : severity === "HIGH"
        ? "bg-orange-500 text-white"
        : severity === "MEDIUM"
          ? "bg-yellow-100 text-yellow-800"
          : "bg-gray-100 text-gray-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {severity}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function GuidelinesPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const pageSize = 20;

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDepartmentRules("marketing", page, pageSize);
      setRules(data.items);
      setTotal(data.total);
      setError(null);
    } catch {
      setError("Failed to load marketing guidelines");
      setRules([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  // Client-side keyword filter
  const filteredRules = searchQuery.trim()
    ? rules.filter((r) => {
        const q = searchQuery.toLowerCase();
        return (
          r.statement.toLowerCase().includes(q) ||
          r.rationale.toLowerCase().includes(q) ||
          r.tags.some((t) => t.toLowerCase().includes(q)) ||
          r.modality.toLowerCase().includes(q) ||
          r.severity.toLowerCase().includes(q)
        );
      })
    : rules;

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Marketing Guidelines
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Active brand, advertising, and content compliance rules
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Total Rules</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-gray-900">{total}</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">
            Mandatory (MUST / MUST_NOT)
          </p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-red-600">
              {
                rules.filter(
                  (r) => r.modality === "MUST" || r.modality === "MUST_NOT",
                ).length
              }
            </p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">
            Critical / High Severity
          </p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-orange-600">
              {
                rules.filter(
                  (r) => r.severity === "CRITICAL" || r.severity === "HIGH",
                ).length
              }
            </p>
          )}
        </div>
      </div>

      {/* Search / filter */}
      <div>
        <input
          type="text"
          placeholder="Search by keyword, tag, modality, or severity..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full rounded-lg border px-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:border-purple-300 focus:outline-none focus:ring-1 focus:ring-purple-300"
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Rule cards */}
      <div className="space-y-3">
        {loading && rules.length === 0 ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl border bg-gray-50"
              />
            ))}
          </>
        ) : filteredRules.length === 0 ? (
          <div className="rounded-xl border bg-white px-5 py-8 text-center text-sm text-gray-400">
            {searchQuery
              ? "No rules match your search."
              : "No marketing guidelines found."}
          </div>
        ) : (
          filteredRules.map((r) => (
            <div
              key={r.id}
              className="rounded-xl border bg-white px-5 py-4 transition-colors hover:bg-gray-50"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {r.statement}
                  </p>
                  {r.rationale && (
                    <p className="mt-1 text-xs text-gray-500">{r.rationale}</p>
                  )}
                </div>
                <div className="flex shrink-0 gap-2">
                  <ModalityBadge modality={r.modality} />
                  <SeverityBadge severity={r.severity} />
                </div>
              </div>

              {/* Tags */}
              {r.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {r.tags.map((tag) => (
                    <span
                      key={tag}
                      className="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-700"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Metadata row */}
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-400">
                {r.scope.length > 0 && (
                  <span>Scope: {r.scope.join(", ")}</span>
                )}
                <span>Status: {r.status}</span>
                <span>ID: {r.id.slice(0, 8)}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-500">
            Page {page} of {totalPages} ({total} total)
          </p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
