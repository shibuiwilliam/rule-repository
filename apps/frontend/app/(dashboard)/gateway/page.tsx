"use client";

import { useState, useEffect } from "react";
import { useProject } from "@/lib/project-context";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Policy {
  id: string;
  name: string;
  event_source: string;
  event_type_pattern: string;
  rule_scope: string | null;
  evaluation_mode: string;
  on_deny: string;
  enabled: boolean;
  created_at: string;
}

interface Evaluation {
  id: string;
  policy_id: string;
  event_source: string;
  event_type: string;
  verdict: string;
  latency_ms: number | null;
  created_at: string;
}

export default function GatewayPage() {
  const { currentProject } = useProject();
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const projectParam = currentProject?.id ? `?project_id=${currentProject.id}` : "";
    Promise.all([
      fetch(`${API_BASE}/api/v1/gateway/policies${projectParam}`).then((r) => r.json()),
      fetch(`${API_BASE}/api/v1/gateway/evaluations${projectParam}`).then((r) => r.json()),
    ])
      .then(([pols, evals]) => {
        setPolicies(pols);
        setEvaluations(evals.items ?? []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [currentProject?.id]);

  const verdictColor = (v: string) => {
    if (v === "ALLOW") return "bg-green-100 text-green-800";
    if (v === "DENY") return "bg-red-100 text-red-800";
    return "bg-yellow-100 text-yellow-800";
  };

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Enforcement Gateway</h1>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="grid grid-cols-2 gap-6">
          {/* Policies */}
          <div className="rounded-lg border bg-white p-4">
            <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
              Enforcement Policies ({policies.length})
            </h2>
            {policies.length === 0 ? (
              <p className="text-sm text-gray-500">
                No policies configured. Create one via the API.
              </p>
            ) : (
              <div className="space-y-3">
                {policies.map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded border p-3">
                    <div>
                      <p className="text-sm font-medium">{p.name}</p>
                      <p className="text-xs text-gray-500">
                        {p.event_source} / {p.event_type_pattern}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
                        {p.evaluation_mode}
                      </span>
                      <span
                        className={`h-2.5 w-2.5 rounded-full ${p.enabled ? "bg-green-500" : "bg-gray-300"}`}
                        title={p.enabled ? "Enabled" : "Disabled"}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent evaluations */}
          <div className="rounded-lg border bg-white p-4">
            <h2 className="mb-3 text-sm font-medium uppercase text-gray-500">
              Recent Evaluations
            </h2>
            {evaluations.length === 0 ? (
              <p className="text-sm text-gray-500">No evaluations yet. Send a webhook to begin.</p>
            ) : (
              <div className="space-y-2">
                {evaluations.map((e) => (
                  <div key={e.id} className="flex items-center justify-between text-sm">
                    <div>
                      <span className="font-mono text-xs text-gray-500">
                        {e.event_source}/{e.event_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${verdictColor(e.verdict)}`}
                      >
                        {e.verdict}
                      </span>
                      {e.latency_ms && (
                        <span className="text-xs text-gray-400">{e.latency_ms}ms</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
