"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  type AgentProfile,
  getAgentProfile,
  getAgentExceptions,
  getAgentNegotiations,
} from "@/lib/api";

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

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [agent, setAgent] = useState<AgentProfile | null>(null);
  const [exceptions, setExceptions] = useState<Record<string, unknown>[]>([]);
  const [exceptionsTotal, setExceptionsTotal] = useState(0);
  const [negotiations, setNegotiations] = useState<Record<string, unknown>[]>([]);
  const [negotiationsTotal, setNegotiationsTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [profile, excData, negData] = await Promise.all([
        getAgentProfile(id),
        getAgentExceptions(id),
        getAgentNegotiations(id),
      ]);
      setAgent(profile);
      setExceptions(excData.items);
      setExceptionsTotal(excData.total);
      setNegotiations(negData.items);
      setNegotiationsTotal(negData.total);
    } catch {
      setError("Agent not found");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
        <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="text-center py-12 text-gray-500">
        {error || "Agent not found"}
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Back link */}
      <Link href="/agents" className="text-sm text-blue-600 hover:underline">
        Back to Agents
      </Link>

      {/* Profile header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{agent.display_name}</h1>
            <p className="text-sm text-gray-500 mt-1">{agent.agent_id}</p>
            <div className="flex items-center gap-3 mt-3">
              <span className="text-sm text-gray-600">Type: {agent.agent_type}</span>
              <span
                className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  TRUST_COLORS[agent.trust_level] || "bg-gray-100 text-gray-700"
                }`}
              >
                {agent.trust_level}
              </span>
              <span className={`text-sm font-semibold ${complianceColor(agent.compliance_rate_30d)}`}>
                {agent.compliance_rate_30d.toFixed(1)}% compliance (30d)
              </span>
            </div>
          </div>
          <div className="text-right text-xs text-gray-400">
            <p>Created: {new Date(agent.created_at).toLocaleDateString()}</p>
            <p>Updated: {new Date(agent.updated_at).toLocaleDateString()}</p>
          </div>
        </div>
      </div>

      {/* Capabilities and permissions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-3">Capabilities</h2>
          {agent.capabilities.length === 0 ? (
            <p className="text-sm text-gray-400">No capabilities listed</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {agent.capabilities.map((cap: string) => (
                <span
                  key={cap}
                  className="inline-block rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700"
                >
                  {cap}
                </span>
              ))}
            </div>
          )}
          <div className="mt-4 pt-4 border-t space-y-2">
            <p className="text-sm text-gray-600">
              Can propose rules:{" "}
              <span className="font-medium">{agent.can_propose_rules ? "Yes" : "No"}</span>
            </p>
            <p className="text-sm text-gray-600">
              Can vote on proposals:{" "}
              <span className="font-medium">{agent.can_vote_on_proposals ? "Yes" : "No"}</span>
            </p>
            <p className="text-sm text-gray-600">
              Max auto-fix severity:{" "}
              <span className="font-medium">{agent.max_auto_fix_severity}</span>
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-3">Mastery</h2>
          <p className="text-3xl font-bold text-gray-800">{agent.mastered_rules_count}</p>
          <p className="text-sm text-gray-500 mt-1">Rules mastered</p>

          <div className="mt-4 pt-4 border-t">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Strength Areas</h3>
            {agent.strength_areas.length === 0 ? (
              <p className="text-sm text-gray-400">None identified</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {agent.strength_areas.map((area: string) => (
                  <span
                    key={area}
                    className="inline-block rounded bg-green-50 px-2 py-0.5 text-xs text-green-700"
                  >
                    {area}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="mt-4 pt-4 border-t">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Weakness Areas</h3>
            {agent.weakness_areas.length === 0 ? (
              <p className="text-sm text-gray-400">None identified</p>
            ) : (
              <div className="flex flex-wrap gap-1">
                {agent.weakness_areas.map((area: string) => (
                  <span
                    key={area}
                    className="inline-block rounded bg-red-50 px-2 py-0.5 text-xs text-red-700"
                  >
                    {area}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Exception Requests */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-3">
          Exception Requests
          <span className="ml-2 text-sm font-normal text-gray-400">({exceptionsTotal})</span>
        </h2>
        {exceptions.length === 0 ? (
          <p className="text-sm text-gray-400">No exception requests</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {exceptions.map((exc: Record<string, unknown>, idx: number) => (
              <div key={String(exc.id ?? idx)} className="py-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">
                    {String(exc.rule_id ?? "Unknown rule")}
                  </span>
                  <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                    {String(exc.status ?? "unknown")}
                  </span>
                </div>
                {typeof exc.justification === "string" && exc.justification && (
                  <p className="text-sm text-gray-500 mt-1">{exc.justification}</p>
                )}
                {typeof exc.created_at === "string" && exc.created_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(exc.created_at).toLocaleString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Negotiations */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-semibold mb-3">
          Negotiations
          <span className="ml-2 text-sm font-normal text-gray-400">({negotiationsTotal})</span>
        </h2>
        {negotiations.length === 0 ? (
          <p className="text-sm text-gray-400">No negotiations</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {negotiations.map((neg: Record<string, unknown>, idx: number) => (
              <div key={String(neg.id ?? idx)} className="py-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-800">
                    {String(neg.rule_id ?? "Unknown rule")}
                  </span>
                  <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                    {String(neg.status ?? "unknown")}
                  </span>
                </div>
                {typeof neg.proposed_alternative === "string" && neg.proposed_alternative && (
                  <p className="text-sm text-gray-500 mt-1">{neg.proposed_alternative}</p>
                )}
                {typeof neg.created_at === "string" && neg.created_at && (
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(neg.created_at).toLocaleString()}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
