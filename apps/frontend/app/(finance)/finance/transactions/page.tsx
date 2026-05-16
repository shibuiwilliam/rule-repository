"use client";

import { useState, useEffect, useCallback } from "react";
import { usePersonaTerm } from "@/lib/use-persona-term";
import {
  getDepartmentEvaluations,
  type DepartmentEvaluation,
} from "@/lib/api";

const VERDICT_STYLES: Record<string, string> = {
  allow: "bg-green-100 text-green-800",
  deny: "bg-red-100 text-red-800",
  needs_confirmation: "bg-yellow-100 text-yellow-800",
};

export default function TransactionsPage() {
  const t = usePersonaTerm();
  const [evaluations, setEvaluations] = useState<DepartmentEvaluation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [verdictFilter, setVerdictFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDepartmentEvaluations(
        "finance",
        verdictFilter || undefined,
        page,
        15,
      );
      setEvaluations(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }, [page, verdictFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPages = Math.max(1, Math.ceil(total / 15));

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("queue_name", "Transaction Approval Queue")}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Expense reports, purchase orders, and payments evaluated against financial controls
          </p>
        </div>
        <select
          value={verdictFilter}
          onChange={(e) => { setVerdictFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm"
        >
          <option value="">All verdicts</option>
          <option value="deny">Deny</option>
          <option value="allow">Allow</option>
          <option value="needs_confirmation">Needs confirmation</option>
        </select>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="py-12 text-center text-gray-400">Loading transactions...</div>
      ) : evaluations.length === 0 ? (
        <div className="rounded-xl border bg-white p-8 text-center">
          <p className="text-gray-500">No transaction evaluations found.</p>
          <p className="mt-2 text-sm text-gray-400">
            Submit transactions via{" "}
            <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">
              POST /api/v1/submissions
            </code>{" "}
            with{" "}
            <code className="rounded bg-gray-100 px-1 py-0.5 text-xs">
              kind: &quot;transaction&quot;
            </code>
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
