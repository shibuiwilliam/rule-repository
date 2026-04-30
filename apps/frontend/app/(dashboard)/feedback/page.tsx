"use client";

import { useState, useEffect, useCallback } from "react";
import Badge from "@/components/Badge";
import {
  type Correction,
  type FeedbackStats,
  getCorrections,
  getFeedbackStats,
  approveCorrection,
  dismissCorrection,
  submitCorrection,
} from "@/lib/api";
import { useProject } from "@/lib/project-context";

type StatusFilter = "all" | "pending" | "approved" | "dismissed";

const ANALYSIS_LABELS: Record<string, { label: string; style: string; description: string }> = {
  new_rule: {
    label: "New Rule",
    style: "bg-green-100 text-green-800",
    description: "No existing rule covers this pattern. A new rule will be proposed.",
  },
  improve_existing: {
    label: "Improve Rule",
    style: "bg-blue-100 text-blue-800",
    description: "A rule exists but is ambiguous. A rewrite will be suggested.",
  },
  adjust_scope: {
    label: "Adjust Scope",
    style: "bg-yellow-100 text-yellow-800",
    description: "A rule exists but wasn't delivered to the agent. Scope needs widening.",
  },
};

export default function FeedbackPage() {
  const { currentProject } = useProject();
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [corrections, setCorrections] = useState<Correction[]>([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Detail view
  const [expanded, setExpanded] = useState<string | null>(null);

  // Submit form
  const [showForm, setShowForm] = useState(false);
  const [originalDiff, setOriginalDiff] = useState("");
  const [correctedDiff, setCorrectedDiff] = useState("");
  const [filePaths, setFilePaths] = useState("");
  const [repository, setRepository] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState("");

  const loadStats = useCallback(async () => {
    try {
      const data = await getFeedbackStats(currentProject?.id);
      setStats(data);
    } catch {
      /* non-critical */
    }
  }, [currentProject?.id]);

  const loadCorrections = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const status = filter === "all" ? undefined : filter;
      const data = await getCorrections(status, page, 20, currentProject?.id);
      setCorrections(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load corrections.");
    } finally {
      setLoading(false);
    }
  }, [filter, page, currentProject?.id]);

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
      setError(err instanceof Error ? err.message : "Approve failed.");
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
      setError(err instanceof Error ? err.message : "Dismiss failed.");
    }
  };

  const handleBulkApprove = async () => {
    const pending = corrections.filter((c) => c.status === "pending");
    for (const c of pending) {
      await handleApprove(c.id);
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
      const paths = filePaths.split(",").map((p) => p.trim()).filter(Boolean);
      await submitCorrection({
        original_diff: originalDiff,
        corrected_diff: correctedDiff,
        file_paths: paths.length > 0 ? paths : undefined,
        repository: repository.trim() || undefined,
      });
      setSubmitMessage("Correction submitted and analyzed.");
      setOriginalDiff("");
      setCorrectedDiff("");
      setFilePaths("");
      setRepository("");
      setShowForm(false);
      loadCorrections();
      loadStats();
    } catch (err) {
      setSubmitMessage(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const totalPages = Math.ceil(total / 20);
  const pendingCount = corrections.filter((c) => c.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Correction Feedback</h1>
          <p className="mt-1 text-sm text-gray-500">
            Human corrections of AI-generated code become rule improvements
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {showForm ? "Close Form" : "Submit Correction"}
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-xs font-medium uppercase text-gray-500">Total</p>
            <p className="mt-1 text-2xl font-bold">{stats.total_corrections}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-xs font-medium uppercase text-gray-500">Rules Created</p>
            <p className="mt-1 text-2xl font-bold text-green-600">{stats.rules_created}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-xs font-medium uppercase text-gray-500">Pending Review</p>
            <p className="mt-1 text-2xl font-bold text-yellow-600">
              {stats.by_status?.pending ?? 0}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-xs font-medium uppercase text-gray-500">By Type</p>
            <div className="mt-1 flex gap-2">
              {Object.entries(stats.by_type ?? {}).map(([type, count]) => (
                <span
                  key={type}
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${ANALYSIS_LABELS[type]?.style ?? "bg-gray-100"}`}
                >
                  {ANALYSIS_LABELS[type]?.label ?? type}: {count as number}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Top violated rules */}
      {stats && stats.top_violated_rules && stats.top_violated_rules.length > 0 && (
        <div className="rounded-lg border bg-white p-4">
          <h3 className="mb-2 text-sm font-medium uppercase text-gray-500">
            Top Violated Rules (most corrections)
          </h3>
          <div className="flex flex-wrap gap-2">
            {stats.top_violated_rules.map((item: { rule_id: string; count: number }) => (
              <a
                key={item.rule_id}
                href={`/rules/${item.rule_id}`}
                className="rounded border px-2 py-1 text-xs text-blue-600 hover:bg-blue-50"
              >
                {item.rule_id.slice(0, 8)}... ({item.count}x)
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Submit form (expandable) */}
      {showForm && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Submit a Correction</h2>
          <p className="mb-4 text-sm text-gray-500">
            Paste the original code (what the agent wrote) and the corrected code (what you fixed).
            The system will analyze the delta and propose rules.
          </p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Original Code (agent-generated)
              </label>
              <textarea
                value={originalDiff}
                onChange={(e) => setOriginalDiff(e.target.value)}
                rows={10}
                className="w-full rounded-md border px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Paste the original diff or code here..."
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Corrected Code (your fix)
              </label>
              <textarea
                value={correctedDiff}
                onChange={(e) => setCorrectedDiff(e.target.value)}
                rows={10}
                className="w-full rounded-md border px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Paste the corrected diff or code here..."
              />
            </div>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-4">
            <input
              type="text"
              value={filePaths}
              onChange={(e) => setFilePaths(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
              placeholder="File paths (comma-separated, optional)"
            />
            <input
              type="text"
              value={repository}
              onChange={(e) => setRepository(e.target.value)}
              className="rounded-md border px-3 py-2 text-sm"
              placeholder="Repository (e.g., org/repo, optional)"
            />
          </div>
          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={handleSubmit}
              disabled={submitting || !originalDiff.trim() || !correctedDiff.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Analyzing..." : "Submit & Analyze"}
            </button>
            {submitMessage && <p className="text-sm text-gray-600">{submitMessage}</p>}
          </div>
        </div>
      )}

      {error && <p className="rounded bg-red-50 px-4 py-2 text-sm text-red-800">{error}</p>}

      {/* Filter + bulk action bar */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {(["all", "pending", "approved", "dismissed"] as StatusFilter[]).map((f) => (
            <button
              key={f}
              onClick={() => { setFilter(f); setPage(1); }}
              className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
                filter === f ? "bg-white shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        {pendingCount > 1 && filter !== "approved" && filter !== "dismissed" && (
          <button
            onClick={handleBulkApprove}
            className="rounded-md border border-green-300 px-3 py-1.5 text-sm font-medium text-green-700 hover:bg-green-50"
          >
            Approve All Pending ({pendingCount})
          </button>
        )}
      </div>

      {/* Corrections list */}
      <div className="space-y-3">
        {loading && <p className="text-sm text-gray-400">Loading...</p>}
        {!loading && corrections.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
            <p className="text-sm text-gray-500">
              No corrections found. Submit one above or connect your GitHub webhook for auto-capture.
            </p>
          </div>
        )}
        {corrections.map((c) => {
          const isExpanded = expanded === c.id;
          const analysis = ANALYSIS_LABELS[c.analysis_type ?? ""] ?? null;

          return (
            <div key={c.id} className="rounded-lg border bg-white">
              {/* Summary row (clickable) */}
              <button
                onClick={() => setExpanded(isExpanded ? null : c.id)}
                className="flex w-full items-center justify-between p-4 text-left hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-block h-2.5 w-2.5 rounded-full ${
                      c.status === "approved"
                        ? "bg-green-500"
                        : c.status === "dismissed"
                          ? "bg-gray-400"
                          : "bg-yellow-500"
                    }`}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      {c.file_paths && c.file_paths.length > 0 ? (
                        <span className="font-mono text-sm">{c.file_paths.join(", ")}</span>
                      ) : (
                        <span className="text-sm text-gray-400">No file paths</span>
                      )}
                      {c.repository && (
                        <span className="text-xs text-gray-400">{c.repository}</span>
                      )}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2">
                      {analysis && (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${analysis.style}`}>
                          {analysis.label}
                        </span>
                      )}
                      {c.confidence !== null && (
                        <span className="text-xs text-gray-400">
                          {Math.round(c.confidence * 100)}% confidence
                        </span>
                      )}
                      <span className="text-xs text-gray-400">
                        {new Date(c.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    label={c.status}
                    variant={c.status === "approved" ? "status" : c.status === "dismissed" ? "tag" : "severity"}
                  />
                  <svg
                    className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none" viewBox="0 0 24 24" stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="border-t px-4 pb-4 pt-3">
                  {/* Analysis explanation */}
                  {analysis && (
                    <p className="mb-3 text-sm text-gray-600">{analysis.description}</p>
                  )}

                  {/* Candidate rule proposal */}
                  {c.candidate_statement && (
                    <div className="mb-3 rounded-md border border-green-200 bg-green-50 p-3">
                      <p className="mb-1 text-xs font-medium uppercase text-green-700">Proposed Rule</p>
                      <p className="text-sm">{c.candidate_statement}</p>
                      <div className="mt-1.5 flex gap-1.5">
                        {c.candidate_modality && (
                          <Badge label={c.candidate_modality} variant="modality" />
                        )}
                        {c.candidate_severity && (
                          <Badge label={c.candidate_severity} variant="severity" />
                        )}
                      </div>
                    </div>
                  )}

                  {/* Matched rules */}
                  {c.matched_rule_ids && c.matched_rule_ids.length > 0 && (
                    <div className="mb-3">
                      <p className="mb-1 text-xs font-medium uppercase text-gray-500">Matched Existing Rules</p>
                      <div className="flex flex-wrap gap-1">
                        {c.matched_rule_ids.map((rid: string) => (
                          <a
                            key={rid}
                            href={`/rules/${rid}`}
                            className="rounded bg-blue-50 px-2 py-0.5 font-mono text-xs text-blue-600 hover:underline"
                          >
                            {rid.slice(0, 8)}...
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  {c.status === "pending" && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(c.id)}
                        className="rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                      >
                        {c.analysis_type === "new_rule" ? "Approve & Create Rule" : "Approve"}
                      </button>
                      <button
                        onClick={() => handleDismiss(c.id)}
                        className="rounded-md border px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}

                  {c.status === "approved" && (
                    <p className="text-sm text-green-600">
                      Approved{" "}
                      {c.analysis_type === "new_rule" && "— draft rule created"}
                    </p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Page {page} of {totalPages} ({total} total)</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border px-3 py-1 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border px-3 py-1 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
