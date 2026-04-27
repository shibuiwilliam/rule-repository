"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type Correction,
  type FeedbackStats,
  getCorrections,
  getFeedbackStats,
  approveCorrection,
  dismissCorrection,
  submitCorrection,
} from "@/lib/api";

type StatusFilter = "all" | "pending" | "approved" | "dismissed";

const ANALYSIS_TYPE_STYLES: Record<string, string> = {
  new_rule: "bg-green-100 text-green-800",
  improve_existing: "bg-blue-100 text-blue-800",
  adjust_scope: "bg-yellow-100 text-yellow-800",
};

export default function FeedbackPage() {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Submit form state
  const [originalDiff, setOriginalDiff] = useState("");
  const [correctedDiff, setCorrectedDiff] = useState("");
  const [filePaths, setFilePaths] = useState("");
  const [repository, setRepository] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState("");

  const loadStats = useCallback(async () => {
    try {
      const data = await getFeedbackStats();
      setStats(data);
    } catch {
      // stats are non-critical
    }
  }, []);

  const loadCorrections = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const status = filter === "all" ? undefined : filter;
      const data = await getCorrections(status, page);
      setCorrections(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load corrections.");
    } finally {
      setLoading(false);
    }
  }, [filter, page]);

  useEffect(() => {
    loadStats();
    loadCorrections();
  }, [loadStats, loadCorrections]);

  const handleApprove = async (id: string) => {
    try {
      await approveCorrection(id);
      setCorrections((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "approved" } : c)),
      );
      loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve correction.");
    }
  };

  const handleDismiss = async (id: string) => {
    try {
      await dismissCorrection(id);
      setCorrections((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "dismissed" } : c)),
      );
      loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to dismiss correction.");
    }
  };

  const handleSubmit = async () => {
    if (!originalDiff.trim() || !correctedDiff.trim()) {
      setSubmitMessage("Both original and corrected diffs are required.");
      return;
    }
    setSubmitting(true);
    setSubmitMessage("");
    try {
      const paths = filePaths
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      await submitCorrection({
        original_diff: originalDiff,
        corrected_diff: correctedDiff,
        file_paths: paths.length > 0 ? paths : undefined,
        repository: repository.trim() || undefined,
      });
      setSubmitMessage("Correction submitted successfully.");
      setOriginalDiff("");
      setCorrectedDiff("");
      setFilePaths("");
      setRepository("");
      loadCorrections();
      loadStats();
    } catch (err) {
      setSubmitMessage(err instanceof Error ? err.message : "Failed to submit correction.");
    } finally {
      setSubmitting(false);
    }
  };

  const changeFilter = (f: StatusFilter) => {
    setFilter(f);
    setPage(1);
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agent Corrections</h1>
        <p className="mt-1 text-sm text-gray-500">
          Review corrections from human reviews of AI-generated code
        </p>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Total Corrections</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {stats.total_corrections}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Rules Created</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {stats.rules_created}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Pending</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">
              {stats.by_status?.pending ?? 0}
            </p>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex space-x-1 rounded-lg bg-gray-100 p-1">
        {(["all", "pending", "approved", "dismissed"] as StatusFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => changeFilter(f)}
            className={`rounded-md px-4 py-2 text-sm font-medium capitalize transition ${
              filter === f
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      {/* Corrections table */}
      <div className="overflow-hidden rounded-lg border bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Files
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Analysis Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Candidate Rule
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Confidence
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  Loading...
                </td>
              </tr>
            ) : corrections.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                  No corrections found.
                </td>
              </tr>
            ) : (
              corrections.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-700">
                    <div className="max-w-[200px] truncate" title={c.file_paths.join(", ")}>
                      {c.file_paths.length > 0 ? c.file_paths.join(", ") : "-"}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {c.analysis_type ? (
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          ANALYSIS_TYPE_STYLES[c.analysis_type] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {c.analysis_type}
                      </span>
                    ) : (
                      <span className="text-gray-400">-</span>
                    )}
                  </td>
                  <td className="max-w-[250px] truncate px-4 py-3 text-sm text-gray-700">
                    {c.candidate_statement ?? "-"}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {c.confidence !== null ? `${Math.round(c.confidence * 100)}%` : "-"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        c.status === "approved"
                          ? "bg-green-100 text-green-800"
                          : c.status === "dismissed"
                            ? "bg-gray-100 text-gray-600"
                            : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {c.status === "pending" && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleApprove(c.id)}
                          className="rounded bg-green-600 px-2 py-1 text-xs font-medium text-white hover:bg-green-700"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleDismiss(c.id)}
                          className="rounded bg-gray-200 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300"
                        >
                          Dismiss
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-gray-500">
              Page {page} of {totalPages} ({total} total)
            </p>
            <div className="flex space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border px-3 py-1 text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Submit correction */}
      <div className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Submit Correction</h2>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Original Diff
            </label>
            <textarea
              value={originalDiff}
              onChange={(e) => setOriginalDiff(e.target.value)}
              rows={8}
              className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Paste the original diff here..."
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Corrected Diff
            </label>
            <textarea
              value={correctedDiff}
              onChange={(e) => setCorrectedDiff(e.target.value)}
              rows={8}
              className="w-full rounded-md border px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="Paste the corrected diff here..."
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              File Paths (comma-separated)
            </label>
            <input
              type="text"
              value={filePaths}
              onChange={(e) => setFilePaths(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="src/main.py, src/utils.py"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Repository
            </label>
            <input
              type="text"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              className="w-full rounded-md border px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              placeholder="owner/repo"
            />
          </div>
        </div>

        <div className="mt-4 flex items-center space-x-4">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Correction"}
          </button>
          {submitMessage && (
            <p className="text-sm text-gray-600">{submitMessage}</p>
          )}
        </div>
      </div>
    </div>
  );
}
