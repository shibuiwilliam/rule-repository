"use client";

import { useState, useEffect, useCallback } from "react";
import {
  type AuditEntry,
  type AuditChainVerification,
  getAuditEntries,
  verifyAuditChain,
} from "@/lib/api";

const PAGE_SIZE = 20;

const ACTION_COLORS: Record<string, string> = {
  rule_created: "bg-green-100 text-green-700",
  rule_updated: "bg-blue-100 text-blue-700",
  rule_retired: "bg-gray-100 text-gray-700",
  evaluation_completed: "bg-purple-100 text-purple-700",
  extraction_completed: "bg-yellow-100 text-yellow-700",
  proposal_created: "bg-indigo-100 text-indigo-700",
  proposal_enacted: "bg-emerald-100 text-emerald-700",
};

function ActionBadge({ action }: { action: string }) {
  const color = ACTION_COLORS[action] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${color}`}>
      {action}
    </span>
  );
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Filters
  const [actionFilter, setActionFilter] = useState("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState("");

  // Chain verification
  const [verification, setVerification] = useState<AuditChainVerification | null>(null);
  const [verifying, setVerifying] = useState(false);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAuditEntries(
        page,
        PAGE_SIZE,
        actionFilter || undefined,
        undefined,
        resourceTypeFilter || undefined,
      );
      setEntries(data.entries);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log");
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter, resourceTypeFilter]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const result = await verifyAuditChain();
      setVerification(result);
    } catch {
      setVerification({ verified: false, entries_checked: 0, first_broken_entry_id: null, message: "Verification request failed" });
    } finally {
      setVerifying(false);
    }
  };

  const handleExportCsv = () => {
    const header = "id,timestamp,action,actor,resource_type,resource_id,entry_hash\n";
    const rows = entries.map(e =>
      [e.id, e.timestamp, e.action, e.actor, e.resource_type, e.resource_id, e.entry_hash].join(",")
    ).join("\n");
    const blob = new Blob([header + rows], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit Log</h1>
          <p className="mt-1 text-sm text-gray-500">
            Immutable, hash-chained record of all system actions. {total} entries total.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExportCsv}
            disabled={entries.length === 0}
            className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Export CSV
          </button>
          <button
            onClick={handleVerify}
            disabled={verifying}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {verifying ? "Verifying..." : "Verify Chain"}
          </button>
        </div>
      </div>

      {/* Chain verification result */}
      {verification && (
        <div className={`mb-4 rounded-lg border p-4 ${verification.verified ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
          <p className={`text-sm font-medium ${verification.verified ? "text-green-800" : "text-red-800"}`}>
            {verification.verified ? "Chain integrity verified" : "Chain integrity BROKEN"}
            {" "}&mdash; {verification.entries_checked} entries checked
          </p>
          <p className="mt-1 text-xs text-gray-600">{verification.message}</p>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="rounded-md border px-3 py-1.5 text-sm"
        >
          <option value="">All actions</option>
          <option value="rule_created">rule_created</option>
          <option value="rule_updated">rule_updated</option>
          <option value="rule_retired">rule_retired</option>
          <option value="evaluation_completed">evaluation_completed</option>
          <option value="extraction_completed">extraction_completed</option>
          <option value="proposal_created">proposal_created</option>
          <option value="proposal_enacted">proposal_enacted</option>
        </select>
        <select
          value={resourceTypeFilter}
          onChange={(e) => { setResourceTypeFilter(e.target.value); setPage(1); }}
          className="rounded-md border px-3 py-1.5 text-sm"
        >
          <option value="">All resource types</option>
          <option value="rule">rule</option>
          <option value="evaluation">evaluation</option>
          <option value="extraction">extraction</option>
          <option value="proposal">proposal</option>
        </select>
      </div>

      {/* Error */}
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      {/* Loading */}
      {loading && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100" />
          ))}
        </div>
      )}

      {/* Table */}
      {!loading && entries.length === 0 && (
        <div className="py-12 text-center text-gray-500">No audit entries found.</div>
      )}

      {!loading && entries.length > 0 && (
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {entries.map((entry) => (
                <tr key={entry.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-gray-600">
                    {new Date(entry.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <ActionBadge action={entry.action} />
                  </td>
                  <td className="px-4 py-3 text-gray-700">{entry.actor}</td>
                  <td className="px-4 py-3">
                    <span className="text-gray-500">{entry.resource_type}/</span>
                    <span className="font-mono text-xs text-gray-700">{entry.resource_id.slice(0, 8)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-400" title={entry.entry_hash}>
                      {entry.entry_hash.slice(0, 12)}...
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
