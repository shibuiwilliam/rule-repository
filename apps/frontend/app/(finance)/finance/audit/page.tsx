"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getAuditEntries,
  verifyAuditChain,
  type AuditEntry,
  type AuditChainVerification,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AuditReportsPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [chainStatus, setChainStatus] = useState<AuditChainVerification | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [actionFilter, setActionFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAuditEntries(
        page,
        20,
        actionFilter || undefined,
        undefined,
        "evaluation",
      );
      setEntries(data.entries);
      setTotal(data.total);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [page, actionFilter]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const result = await verifyAuditChain();
      setChainStatus(result);
    } catch {
      setChainStatus({
        verified: false,
        entries_checked: 0,
        first_broken_entry_id: null,
        message: "Verification failed - could not reach server",
      });
    } finally {
      setVerifying(false);
    }
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Reports</h1>
        <p className="mt-1 text-sm text-gray-500">
          Financial evaluation audit trail with hash chain verification
        </p>
      </div>

      {/* Summary + chain verification */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Total Audit Entries</p>
          {loading ? (
            <div className="mt-1 h-8 w-16 animate-pulse rounded bg-gray-100" />
          ) : (
            <p className="mt-1 text-2xl font-bold text-blue-600">{total}</p>
          )}
        </div>
        <div className="rounded-xl border bg-white p-5">
          <p className="text-xs font-medium text-gray-500">Chain Status</p>
          {chainStatus ? (
            <p
              className={`mt-1 text-2xl font-bold ${
                chainStatus.verified ? "text-green-600" : "text-red-600"
              }`}
            >
              {chainStatus.verified ? "Verified" : "Broken"}
            </p>
          ) : (
            <p className="mt-1 text-2xl font-bold text-gray-400">Not checked</p>
          )}
          {chainStatus && (
            <p className="mt-1 text-xs text-gray-400">
              {chainStatus.entries_checked} entries checked
            </p>
          )}
        </div>
        <div className="flex items-center rounded-xl border bg-white p-5">
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
          >
            {verifying ? "Verifying..." : "Verify Hash Chain"}
          </button>
        </div>
      </div>

      {chainStatus && !chainStatus.verified && (
        <div className="rounded-xl border-l-4 border-l-red-500 bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">Chain Integrity Failure</p>
          <p className="mt-1 text-xs text-red-600">{chainStatus.message}</p>
          {chainStatus.first_broken_entry_id && (
            <p className="mt-1 text-xs text-red-500">
              First broken entry: {chainStatus.first_broken_entry_id}
            </p>
          )}
        </div>
      )}

      {/* Audit log table */}
      <div className="rounded-xl border bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
          <h2 className="text-base font-semibold text-gray-900">Audit Log</h2>
          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-md border px-2 py-1 text-xs text-gray-700"
          >
            <option value="">All actions</option>
            <option value="evaluation_completed">Evaluation completed</option>
            <option value="rule_created">Rule created</option>
            <option value="rule_updated">Rule updated</option>
            <option value="rule_retired">Rule retired</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                <th className="px-5 py-3">Timestamp</th>
                <th className="px-5 py-3">Action</th>
                <th className="px-5 py-3">Actor</th>
                <th className="px-5 py-3">Resource</th>
                <th className="px-5 py-3">Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {entries.length === 0 && !loading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-sm text-gray-400">
                    No audit entries found.
                  </td>
                </tr>
              ) : (
                entries.map((e) => (
                  <>
                    <tr
                      key={e.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                    >
                      <td className="px-5 py-3 text-xs text-gray-500">
                        {new Date(e.timestamp).toLocaleString()}
                      </td>
                      <td className="px-5 py-3">
                        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                          {e.action}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-600">{e.actor}</td>
                      <td className="px-5 py-3 text-xs text-gray-500">
                        {e.resource_type}:{e.resource_id.slice(0, 8)}
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-gray-400">
                        {e.entry_hash.slice(0, 12)}...
                      </td>
                    </tr>
                    {expandedId === e.id && (
                      <tr key={`${e.id}-detail`}>
                        <td colSpan={5} className="bg-gray-50 px-5 py-4">
                          <div className="space-y-2 text-xs">
                            <p>
                              <span className="font-medium text-gray-600">Full Hash:</span>{" "}
                              <code className="font-mono text-gray-500">{e.entry_hash}</code>
                            </p>
                            <p>
                              <span className="font-medium text-gray-600">Previous Hash:</span>{" "}
                              <code className="font-mono text-gray-500">{e.previous_hash}</code>
                            </p>
                            <p>
                              <span className="font-medium text-gray-600">Details:</span>
                            </p>
                            <pre className="overflow-x-auto rounded bg-gray-100 p-2 text-xs text-gray-600">
                              {JSON.stringify(e.details, null, 2)}
                            </pre>
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
