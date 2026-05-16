"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getDepartmentEvaluations,
  type DepartmentEvaluation,
} from "@/lib/api";

const VERDICT_STYLES: Record<string, string> = {
  allow: "bg-green-100 text-green-800",
  deny: "bg-red-100 text-red-800",
  needs_confirmation: "bg-yellow-100 text-yellow-800",
};

export default function ContractReviewPage() {
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDepartmentEvaluations("legal", undefined, page, 15);
      setEvaluations(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load contracts");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPages = Math.max(1, Math.ceil(total / 15));

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Contract Review Queue</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review contracts and document artifacts evaluated against legal rules
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-400">Loading contract reviews...</div>
      ) : evaluations.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center">
          <p className="text-gray-500">No contract evaluations found.</p>
          <p className="mt-2 text-sm text-gray-400">
            Submit contracts for review via{" "}
            <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">
              POST /api/v1/submissions
            </code>{" "}
            with <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">kind: &quot;document_artifact&quot;</code>
          </p>
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Rule</th>
                  <th className="px-4 py-3">Verdict</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {evaluations.map((ev) => (
                  <tr key={ev.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 line-clamp-1">
                        {ev.rule_statement || ev.rule_id}
                      </p>
                      {ev.issue_description && (
                        <p className="mt-0.5 text-xs text-gray-500 line-clamp-1">
                          {ev.issue_description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${VERDICT_STYLES[ev.verdict] ?? "bg-gray-100 text-gray-700"}`}
                      >
                        {ev.verdict}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {Math.round(ev.confidence * 100)}%
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {new Date(ev.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded border px-3 py-1 text-sm disabled:opacity-40"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-sm text-gray-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="rounded border px-3 py-1 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
