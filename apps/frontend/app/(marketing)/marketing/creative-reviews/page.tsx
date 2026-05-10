"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getDepartmentEvaluations,
  type DepartmentEvaluation,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict.toLowerCase();
  const cls =
    v === "allow"
      ? "bg-green-100 text-green-700"
      : v === "deny"
        ? "bg-red-100 text-red-700"
        : "bg-yellow-100 text-yellow-700";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {verdict}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

type VerdictFilter = "all" | "ALLOW" | "DENY" | "NEEDS_CONFIRMATION";
type ContentTypeFilter = "all" | "email" | "social" | "press_release";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CreativeReviewsPage() {
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>("all");
  const [contentTypeFilter, setContentTypeFilter] =
    useState<ContentTypeFilter>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 20;

  const loadEvaluations = useCallback(async () => {
    setLoading(true);
    try {
      const vf = verdictFilter === "all" ? undefined : verdictFilter;
      const data = await getDepartmentEvaluations("marketing", vf, page, pageSize);
      setEvaluations(data.items);
      setTotal(data.total);
      setError(null);
    } catch {
      setError("Failed to load creative reviews");
      setEvaluations([]);
    } finally {
      setLoading(false);
    }
  }, [verdictFilter, page]);

  useEffect(() => {
    loadEvaluations();
  }, [loadEvaluations]);

  // Client-side content type filter
  const filteredEvals = evaluations.filter((e) => {
    if (
      contentTypeFilter !== "all" &&
      !e.subject_type.toLowerCase().includes(contentTypeFilter)
    ) {
      return false;
    }
    return true;
  });

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Creative Reviews</h1>
        <p className="mt-1 text-sm text-gray-500">
          Content evaluations with inline remediation previews
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Total Reviews</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-gray-900">{total}</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Denied</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-red-600">
              {evaluations.filter((e) => e.verdict.toUpperCase() === "DENY").length}
            </p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Needs Review</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-yellow-600">
              {evaluations.filter(
                (e) => e.verdict.toUpperCase() === "NEEDS_CONFIRMATION",
              ).length}
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={contentTypeFilter}
          onChange={(e) => {
            setContentTypeFilter(e.target.value as ContentTypeFilter);
            setPage(1);
          }}
          className="rounded-md border px-3 py-1.5 text-sm text-gray-700"
        >
          <option value="all">All content types</option>
          <option value="email">Email</option>
          <option value="social">Social Media</option>
          <option value="press_release">Press Release</option>
        </select>
        <select
          value={verdictFilter}
          onChange={(e) => {
            setVerdictFilter(e.target.value as VerdictFilter);
            setPage(1);
          }}
          className="rounded-md border px-3 py-1.5 text-sm text-gray-700"
        >
          <option value="all">All verdicts</option>
          <option value="ALLOW">Allow</option>
          <option value="DENY">Deny</option>
          <option value="NEEDS_CONFIRMATION">Needs confirmation</option>
        </select>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Reviews table */}
      <div className="rounded-xl border bg-white">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Content Type</th>
                <th className="px-5 py-3">Rule</th>
                <th className="px-5 py-3">Verdict</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loading && evaluations.length === 0 ? (
                <>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <tr key={i}>
                      <td colSpan={6} className="px-5 py-4">
                        <div className="h-4 animate-pulse rounded bg-gray-100" />
                      </td>
                    </tr>
                  ))}
                </>
              ) : filteredEvals.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-8 text-center text-sm text-gray-400"
                  >
                    No creative reviews found.
                  </td>
                </tr>
              ) : (
                filteredEvals.map((ev) => (
                  <>
                    <tr
                      key={ev.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() =>
                        setExpandedId(expandedId === ev.id ? null : ev.id)
                      }
                    >
                      <td className="px-5 py-3 font-mono text-xs text-gray-500">
                        {ev.id.slice(0, 8)}
                      </td>
                      <td className="px-5 py-3 text-gray-600">
                        {ev.subject_type}
                      </td>
                      <td className="max-w-xs truncate px-5 py-3 text-gray-700">
                        {ev.rule_statement}
                      </td>
                      <td className="px-5 py-3">
                        <VerdictBadge verdict={ev.verdict} />
                      </td>
                      <td className="px-5 py-3 text-xs text-gray-500">
                        {(ev.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="px-5 py-3 text-gray-500">
                        {ev.created_at?.slice(0, 10)}
                      </td>
                    </tr>
                    {expandedId === ev.id && (
                      <tr key={`${ev.id}-detail`}>
                        <td colSpan={6} className="bg-gray-50 px-5 py-4">
                          <div className="space-y-3 text-sm">
                            <div>
                              <p className="font-medium text-gray-700">
                                Rule Applied
                              </p>
                              <p className="mt-0.5 text-gray-600">
                                {ev.rule_statement}
                              </p>
                            </div>
                            {ev.issue_description && (
                              <div>
                                <p className="font-medium text-gray-700">
                                  Issue Found
                                </p>
                                <p className="mt-0.5 text-gray-600">
                                  {ev.issue_description}
                                </p>
                              </div>
                            )}
                            {ev.fix_suggestion && (
                              <div>
                                <p className="mb-1 font-medium text-gray-700">
                                  Suggested Remediation (text_rewrite)
                                </p>
                                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                                  <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                                    <p className="mb-1 text-xs font-medium uppercase text-red-600">
                                      Original
                                    </p>
                                    <p className="whitespace-pre-wrap text-sm text-red-800">
                                      {ev.issue_description || "N/A"}
                                    </p>
                                  </div>
                                  <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                                    <p className="mb-1 text-xs font-medium uppercase text-green-600">
                                      Suggested
                                    </p>
                                    <p className="whitespace-pre-wrap text-sm text-green-800">
                                      {ev.fix_suggestion}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )}
                            <p className="text-xs text-gray-400">
                              Rule ID: {ev.rule_id} / Confidence:{" "}
                              {(ev.confidence * 100).toFixed(0)}%
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t px-5 py-3">
            <p className="text-xs text-gray-500">
              Page {page} of {totalPages} ({total} total)
            </p>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40"
              >
                Prev
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border px-2 py-1 text-xs disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
