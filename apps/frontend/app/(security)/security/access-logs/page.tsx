"use client";

import { useState } from "react";

interface AccessLog {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  classification: string;
  result: "allowed" | "denied";
}

const SAMPLE_LOGS: AccessLog[] = [
  { id: "AL-001", timestamp: "2026-05-16 09:15:23", actor: "user:alice@acme.co", action: "READ", resource: "rule:R-L002 (Anti-social forces clause)", classification: "CONFIDENTIAL", result: "allowed" },
  { id: "AL-002", timestamp: "2026-05-16 09:12:10", actor: "agent:claude-code-1", action: "EVALUATE", resource: "ruleset:hr/attendance", classification: "INTERNAL", result: "allowed" },
  { id: "AL-003", timestamp: "2026-05-16 09:10:45", actor: "user:bob@acme.co", action: "EXPORT", resource: "ruleset:finance/expense", classification: "RESTRICTED", result: "denied" },
  { id: "AL-004", timestamp: "2026-05-16 08:55:01", actor: "user:carol@acme.co", action: "READ", resource: "rule:R-F010 (Procurement threshold)", classification: "INTERNAL", result: "allowed" },
  { id: "AL-005", timestamp: "2026-05-16 08:42:33", actor: "agent:ci-pipeline", action: "EVALUATE", resource: "ruleset:engineering/python", classification: "PUBLIC", result: "allowed" },
];

const RESULT_BADGE: Record<string, string> = {
  allowed: "bg-green-100 text-green-700",
  denied: "bg-red-100 text-red-700",
};

export default function AccessLogsPage() {
  const [filter, setFilter] = useState<"all" | "denied">("all");
  const filtered = filter === "all" ? SAMPLE_LOGS : SAMPLE_LOGS.filter((l) => l.result === "denied");

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Access Logs</h1>
          <p className="mt-1 text-sm text-gray-500">Read-access audit trail for classified resources</p>
        </div>
        <select value={filter} onChange={(e) => setFilter(e.target.value as "all" | "denied")} className="rounded border px-3 py-1 text-sm">
          <option value="all">All access</option>
          <option value="denied">Denied only</option>
        </select>
      </div>

      <div className="rounded-xl border bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50">
            <tr>
              <th className="px-5 py-3 font-medium text-gray-600">Timestamp</th>
              <th className="px-5 py-3 font-medium text-gray-600">Actor</th>
              <th className="px-5 py-3 font-medium text-gray-600">Action</th>
              <th className="px-5 py-3 font-medium text-gray-600">Resource</th>
              <th className="px-5 py-3 font-medium text-gray-600">Level</th>
              <th className="px-5 py-3 font-medium text-gray-600">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filtered.map((l) => (
              <tr key={l.id}>
                <td className="px-5 py-3 text-xs text-gray-500 tabular-nums">{l.timestamp}</td>
                <td className="px-5 py-3 font-mono text-xs text-gray-700">{l.actor}</td>
                <td className="px-5 py-3">{l.action}</td>
                <td className="px-5 py-3 text-gray-700">{l.resource}</td>
                <td className="px-5 py-3 text-xs">{l.classification}</td>
                <td className="px-5 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${RESULT_BADGE[l.result]}`}>{l.result}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
