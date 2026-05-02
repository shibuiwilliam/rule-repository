"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { type AgentProfile, getAgents } from "@/lib/api";

const TRUST_COLORS: Record<string, string> = {
  untrusted: "bg-gray-100 text-gray-700",
  limited: "bg-yellow-100 text-yellow-700",
  standard: "bg-blue-100 text-blue-700",
  elevated: "bg-green-100 text-green-700",
  autonomous: "bg-purple-100 text-purple-700",
};

function complianceColor(rate: number): string {
  if (rate >= 90) return "text-green-600";
  if (rate >= 70) return "text-yellow-600";
  return "text-red-600";
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const loadAgents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAgents(page, 20);
      setAgents(data.items);
      setTotal(data.total);
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agents</h1>
        <p className="text-sm text-gray-500 mt-1">
          Agent compliance leaderboard ({total} total)
        </p>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p>No agents registered yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 bg-white rounded-lg shadow-sm">
            <thead>
              <tr className="text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                <th className="px-4 py-3">Agent Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Trust Level</th>
                <th className="px-4 py-3">Compliance Rate (30d)</th>
                <th className="px-4 py-3">Mastered Rules</th>
                <th className="px-4 py-3">Capabilities</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {agents.map((agent: AgentProfile) => (
                <tr key={agent.agent_id} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3">
                    <Link
                      href={`/agents/${agent.agent_id}`}
                      className="text-sm font-medium text-blue-600 hover:underline"
                    >
                      {agent.display_name}
                    </Link>
                    <p className="text-xs text-gray-400">{agent.agent_id}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">{agent.agent_type}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        TRUST_COLORS[agent.trust_level] || "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {agent.trust_level}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-sm font-semibold ${complianceColor(agent.compliance_rate_30d)}`}>
                      {agent.compliance_rate_30d.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {agent.mastered_rules_count}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {agent.capabilities.slice(0, 3).map((cap: string) => (
                        <span
                          key={cap}
                          className="inline-block rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                        >
                          {cap}
                        </span>
                      ))}
                      {agent.capabilities.length > 3 && (
                        <span className="text-xs text-gray-400">
                          +{agent.capabilities.length - 3}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded border px-3 py-1 text-sm disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
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
    </div>
  );
}
